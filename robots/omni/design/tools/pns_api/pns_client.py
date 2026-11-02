# Python client for the private KiCad build's push-and-shove router API (RouteTrack / DragItem / OptimizeNets),
# plus the helpers around it: start the private pcbnew on a board, rip up nets, DRC summary via kicad-cli, PNG plot
# of a board region. All coordinates and sizes are mm; layers are KiCad names ("F.Cu", "In1.Cu", "B.Cu").
#   from pns_client import PNS
#   p = PNS.open("C:/.../copy.kicad_pcb")          # starts the private pcbnew (or attaches if already running)
#   p.route_track("SDA", [(100.0, 80.0), (104.0, 80.0, "B.Cu"), (110.0, 85.0)], width=0.15, mode="shove")
# See README.md in this folder for the build and the server side.
import json, math, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kipy import KiCad                                                    # noqa: E402
from kipy.proto.board import board_types_pb2, board_commands_pb2          # noqa: E402
from kipy.proto.common.types import base_types_pb2                        # noqa: E402
from kipy.proto.common.types.base_types_pb2 import DocumentType           # noqa: E402
import router_commands_pb2 as rc                                          # noqa: E402

DEV = os.environ.get("KICAD_DEV_ROOT", r"C:\Users\Jerome\kicad-dev")
DEV_BIN = os.environ.get("KICAD_DEV_BIN", os.path.join(DEV, "src", "build", "install", "msvc-win64-release", "bin"))
RUN_TMP = os.path.join(DEV, "run", "tmp")                    # private TEMP => private API socket, no clash with KiCad 10
CONFIG = os.path.join(DEV, "config")                         # private KICAD_CONFIG_HOME
SOCKET = "ipc://" + os.path.join(RUN_TMP, "kicad", "api.sock")
KICAD_CLI = os.environ.get("KICAD_CLI", r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
NM = 1e6
OPT_MERGE_SEGMENTS, OPT_SMART_PADS, OPT_MERGE_OBTUSE, OPT_FANOUT_CLEANUP, OPT_MERGE_COLINEAR = 0x01, 0x02, 0x04, 0x08, 0x80
MODES = {"shove": rc.RTM_SHOVE, "walkaround": rc.RTM_WALKAROUND, "highlight": rc.RTM_HIGHLIGHT,
         "mark": rc.RTM_HIGHLIGHT, None: rc.RTM_UNKNOWN, "": rc.RTM_UNKNOWN}


def layer_id(name):
    """'F.Cu' -> BL_F_Cu (int); None / '' -> BL_UNKNOWN."""
    if not name:
        return board_types_pb2.BL_UNKNOWN
    if isinstance(name, int):
        return name
    return board_types_pb2.BoardLayer.Value("BL_" + name.replace(".", "_"))


def layer_name(lid):
    return board_types_pb2.BoardLayer.Name(lid)[3:].replace("_", ".")


def v2(x, y):
    return base_types_pb2.Vector2(x_nm=int(round(x * NM)), y_nm=int(round(y * NM)))


def dist(mm):
    return base_types_pb2.Distance(value_nm=int(round((mm or 0) * NM)))


def _result(r):
    return {"committed": r.committed, "completed": r.completed,
            "reached": [r.reached.x_nm / NM, r.reached.y_nm / NM], "message": r.message,
            "added": [{"id": c.id.value, "type": c.type, "net": c.net} for c in r.added],
            "removed": [{"id": c.id.value, "type": c.type, "net": c.net} for c in r.removed],
            "modified": [{"id": c.id.value, "type": c.type, "net": c.net} for c in r.modified]}


def coupled_net(name):
    """KiCad's diff pair naming: X_P/X_N, XP/XN, X+/X- (returns None if not a pair net)."""
    for a, b in (("+", "-"), ("P", "N"), ("-", "+"), ("N", "P")):
        if name.endswith(a):
            return name[:-1] + b
    return None


def KIIDw(value):
    k = base_types_pb2.KIID(); k.value = value
    return k


def offset_polyline(pts, d):
    """Offset a polyline by d (left of the direction of travel when d > 0, KiCad's y-down frame), mitred."""
    out = []
    n = len(pts)
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1.0
        return (dy / L, -dx / L)
    for i in range(n):
        if i == 0:
            nx, ny = normal(pts[0], pts[1]); s = 1.0
        elif i == n - 1:
            nx, ny = normal(pts[-2], pts[-1]); s = 1.0
        else:
            n1, n2 = normal(pts[i - 1], pts[i]), normal(pts[i], pts[i + 1])
            mx, my = n1[0] + n2[0], n1[1] + n2[1]; L = math.hypot(mx, my) or 1.0
            nx, ny = mx / L, my / L
            s = 1.0 / max(0.2, nx * n1[0] + ny * n1[1])               # miter length
        out.append((pts[i][0] + nx * d * s, pts[i][1] + ny * d * s))
    return out


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class PNS:
    """One connection to the private pcbnew, with its board kept loaded between calls."""

    def __init__(self, timeout_ms=60000):
        self.kicad = KiCad(socket_path=SOCKET, kicad_token="", client_name="pns_client", timeout_ms=timeout_ms)
        self.board = self.kicad.get_board()
        self.doc = self.board.document

    # ---- process ----------------------------------------------------------------------------------------------
    @staticmethod
    def running():
        try:
            k = KiCad(socket_path=SOCKET, kicad_token="", client_name="pns_probe", timeout_ms=2000)
            k.ping()
            return bool(k.get_open_documents(DocumentType.DOCTYPE_PCB))
        except Exception:
            return False

    @classmethod
    def open(cls, board_path=None, wait=180):
        """Attach to the private pcbnew, starting it on board_path if it is not running. Never point this at an
        original design file: routing edits the open board (saved only by save())."""
        if cls.running():
            p = cls()
            if board_path and os.path.normcase(os.path.abspath(board_path)) != os.path.normcase(
                    os.path.abspath(p.board_path())):
                raise RuntimeError("Private pcbnew already has %s open; close it first (PNS.close())" % p.board_path())
            return p
        if not board_path:
            raise RuntimeError("Private pcbnew is not running; pass a board path to start it")
        start_pcbnew(board_path)
        end = time.time() + wait
        while time.time() < end:
            if cls.running():
                return cls()
            time.sleep(1.0)
        raise TimeoutError("Private pcbnew did not come up within %d s" % wait)

    def close(self):
        """Quit the private pcbnew without saving."""
        for p in _dev_pcbnew_pids():
            subprocess.run(["taskkill", "/PID", str(p), "/F"], capture_output=True)

    def board_path(self):
        proj = self.doc.project
        return os.path.join(proj.path, self.doc.board_filename) if proj.path else self.doc.board_filename

    # ---- router -----------------------------------------------------------------------------------------------
    def route_track(self, net, points, layer=None, width=0, via=(0, 0), mode="shove", allow_partial=False,
                    dry_run=False, step=0.1, diff_pair=False, gap=0):
        """points: [(x, y) | (x, y, layer)]; the first is the start (on a pad/track/via of the net). A layer on a
        waypoint means 'continue on that layer from here' (a via is placed there)."""
        cmd = rc.RouteTrack(net=net or "", layer=layer_id(layer), width=dist(width), via_diameter=dist(via[0]),
                            via_drill=dist(via[1]), mode=MODES[mode], allow_partial=allow_partial, dry_run=dry_run,
                            step=dist(step), diff_pair=diff_pair, diff_pair_gap=dist(gap))
        cmd.board.CopyFrom(self.doc)
        for pt in points:
            w = cmd.points.add()
            w.position.CopyFrom(v2(pt[0], pt[1]))
            if len(pt) > 2 and pt[2]:
                w.layer = layer_id(pt[2])
        r = _result(self.kicad._client.send(cmd, rc.RouterResult))
        if r["committed"] and r["added"]:                 # the placer can leave zero-length stubs at a snapped end
            ids = {a["id"] for a in r["added"]}
            stubs = [t for t in self.board.get_tracks() if t.id.value in ids and t.start.x == t.end.x
                     and t.start.y == t.end.y]
            if stubs:
                self.board.remove_items(stubs)
                r["added"] = [a for a in r["added"] if a["id"] not in {s.id.value for s in stubs}]
        return r

    def drag_item(self, item=None, target=(0, 0), at=None, grab=None, layer=None, mode="shove", free_angle=False,
                  force=False, dry_run=False, step=0.1):
        """Drag a track segment or via (by id, or the one nearest to 'at') to target, shoving others."""
        if item is None:
            if at is None:
                raise ValueError("give item (KIID) or at=(x, y)")
            found = self.items_at(at[0], at[1], layer=layer, radius=1.0)
            if not found:
                raise ValueError("no track or via near %s" % (at,))
            item = found[0]["id"]
            grab = grab or at
        cmd = rc.DragItem(target=v2(*target), mode=MODES[mode], free_angle=free_angle, force=force, dry_run=dry_run,
                          step=dist(step))
        cmd.board.CopyFrom(self.doc)
        cmd.item.value = item
        if grab:
            cmd.grab.CopyFrom(v2(*grab))
        return _result(self.kicad._client.send(cmd, rc.RouterResult))

    def route_diff_pair(self, net, points, layer=None, width=0, gap=0, via=(0, 0), mode="shove",
                        allow_partial=False, step=0.1, fallback=True):
        """Route net and its coupled net (X_P/X_N, XP/XN, X+/X-) as a pair; points are the pair's centreline,
        points[0] on a pad of either net. KiCad's pair placer is tried first; it commits each leg and cannot turn
        right after a fixed point, so if it does not finish, its partial legs are removed and (fallback=True) the
        two nets are routed as single tracks along exact offset polylines (centreline +- pitch/2). Single-layer
        only for the fallback."""
        other = coupled_net(net)
        if not other:
            raise ValueError("no coupled net for %s (needs a P/N or +/- suffix)" % net)
        before = {t.id.value for n in (net, other) for t in self.tracks(n)} | \
                 {v.id.value for n in (net, other) for v in self.vias(n)}
        r = self.route_track(net, points, layer, width, via, mode, allow_partial, False, step, True, gap)
        r["method"] = "pair_placer"
        if r["completed"] or allow_partial or not fallback or any(len(pt) > 2 and pt[2] for pt in points[1:]):
            return r
        new = [i.id for n in (net, other) for i in list(self.tracks(n)) + list(self.vias(n))
               if i.id.value not in before]
        if new:
            self.board.remove_items_by_id(new)
        return self._route_pair_offset(net, other, points, layer, width, gap, mode, step, r["message"])

    def _pair_sizes(self, net, width, gap):
        if width and gap:
            return width, gap
        nets = [n for n in self.board.get_nets() if n.name == net]
        nc = list(self.board.get_netclass_for_nets(nets).values())[0] if nets else None
        w = width or (nc.diff_pair_track_width or nc.track_width or 200000) / NM if nc else width or 0.2
        g = gap or (nc.diff_pair_gap or nc.clearance or 150000) / NM if nc else gap or 0.15
        return w, g

    def _route_pair_offset(self, net, other, points, layer, width, gap, mode, step, why):
        w, g = self._pair_sizes(net, width, gap)
        half = (w + g) / 2
        pads = {n: [(q.position.x / NM, q.position.y / NM) for q in self.board.get_pads() if q.net.name == n]
                for n in (net, other)}
        c0 = points[0][:2]
        start = {n: min(pads[n], key=lambda q: math.dist(q, c0)) for n in (net, other)}
        mid = ((start[net][0] + start[other][0]) / 2, (start[net][1] + start[other][1]) / 2)
        cl = [mid] + [tuple(pt[:2]) for pt in points[1:]]
        d0 = (cl[1][0] - cl[0][0], cl[1][1] - cl[0][1])
        sp = (start[net][0] - mid[0], start[net][1] - mid[1])
        side = -1 if d0[0] * sp[1] - d0[1] * sp[0] > 0 else 1        # which side of the centreline net lies on
        offs = {net: offset_polyline(cl, side * half)[1:], other: offset_polyline(cl, -side * half)[1:]}
        cn = cl[-1]
        res = {}
        for n in (net, other):
            path = [start[n]] + offs[n]
            end_pad = [q for q in pads[n] if math.dist(q, cn) < 2 * half + 0.5 and q != start[n]]
            if end_pad:
                path[-1] = min(end_pad, key=lambda q: math.dist(q, path[-1]))
            res[n] = self.route_track(n, path, layer, w, mode=mode, step=step)
        ok = all(x["committed"] and x["completed"] for x in res.values())
        if not ok:                                                    # nothing half-done
            for x in res.values():
                if x["committed"]:
                    self.board.remove_items_by_id([KIIDw(a["id"]) for a in x["added"]])
        return {"committed": ok, "completed": ok, "method": "offset_tracks",
                "message": ("pair placer: %s; " % why if why else "") + "; ".join(
                    "%s: %s" % (n, x["message"] or "ok") for n, x in res.items()),
                "width": w, "gap": g, "nets": {n: {k: x[k] for k in ("committed", "completed", "reached")}
                                               for n, x in res.items()},
                "added": sum((x["added"] for x in res.values()), []),
                "removed": sum((x["removed"] for x in res.values()), []),
                "modified": sum((x["modified"] for x in res.values()), [])}

    def optimize_nets(self, nets=(), keep_topology=False, effort=0, dry_run=False, area=None):
        """Router optimizer on the nets' lines (only lines touching area=(x0, y0, x1, y1) if given; with an area
        and no nets, every net with tracks in the area)."""
        cmd = rc.OptimizeNets(nets=[nets] if isinstance(nets, str) else list(nets), keep_topology=keep_topology,
                              effort=effort, dry_run=dry_run)
        if area:
            x0, x1 = sorted((area[0], area[2])); y0, y1 = sorted((area[1], area[3]))
            cmd.area.position.CopyFrom(v2(x0, y0)); cmd.area.size.CopyFrom(v2(x1 - x0, y1 - y0))
        cmd.board.CopyFrom(self.doc)
        return _result(self.kicad._client.send(cmd, rc.RouterResult))

    def optimize_tracks(self, nets=(), area=None, keep_topology=False, dry_run=False):
        """Clean-up pass for grid-router output: merge collinear segments, smooth to 45 deg, remove staircases."""
        return self.optimize_nets(nets, keep_topology, OPT_MERGE_SEGMENTS | OPT_SMART_PADS | OPT_MERGE_OBTUSE |
                                  OPT_MERGE_COLINEAR, dry_run, area)

    def tune_length(self, item=None, at=None, start=None, end=None, target=0, mode="single", tolerance=0.1,
                    max_amplitude=0, spacing=0, dry_run=False):
        """Meander a track (by id, or the one nearest 'at') between start and end (points on it; default its ends)
        to reach target mm (mode single / diff_pair / skew; target 0 = rules)."""
        if item is None:
            hits = [h for h in self.items_at(at[0], at[1], radius=0.5) if h["type"] == "track"]
            if not hits:
                raise ValueError("no track near %s" % (at,))
            item = hits[0]["id"]
            start = start or hits[0]["start"]; end = end or hits[0]["end"]
        cmd = rc.TuneLength(mode={"single": rc.TM_SINGLE, "diff_pair": rc.TM_DIFF_PAIR, "skew": rc.TM_DIFF_PAIR_SKEW}[mode],
                            target=dist(target), tolerance=dist(tolerance), max_amplitude=dist(max_amplitude),
                            spacing=dist(spacing), dry_run=dry_run)
        cmd.board.CopyFrom(self.doc)
        cmd.item.value = item
        cmd.start.CopyFrom(v2(*start)); cmd.end.CopyFrom(v2(*end))
        r = self.kicad._client.send(cmd, rc.TuneLengthResult)
        return {"committed": r.committed, "status": r.status, "length": r.length_nm / NM, "message": r.message}

    # ---- analysis ---------------------------------------------------------------------------------------------
    def get_unrouted(self, nets=None):
        """Every open ratsnest link: {net, length, a: {pos, layer, layers, type, desc, id}, b: {...}}."""
        cmd = rc.GetUnrouted(nets=[nets] if isinstance(nets, str) else list(nets or []))
        cmd.board.CopyFrom(self.doc)
        r = self.kicad._client.send(cmd, rc.UnroutedResponse)
        ep = lambda e: {"pos": [e.position.x_nm / NM, e.position.y_nm / NM], "layer": layer_name(e.layer) if e.layer else None,  # noqa: E731
                        "layers": [layer_name(l) for l in e.layers], "type": e.type, "desc": e.description,
                        "id": e.item.value}
        return {"unconnected": r.unconnected_count,
                "links": [{"net": l.net, "length": round(l.length_nm / NM, 3), "a": ep(l.a), "b": ep(l.b)} for l in r.links]}

    def probe(self, kind, start, end=None, layer="F.Cu", net="", width=0, via=(0, 0), radius=1.0, max_results=10):
        """Router clearance check for a hypothetical item: kind 'point' (track end of width), 'segment' (start-end)
        or 'via'. Returns ok, min_margin (mm, negative = violation) and the nearest obstacles."""
        cmd = rc.ProbeClearance(kind={"point": rc.PK_POINT, "segment": rc.PK_SEGMENT, "via": rc.PK_VIA}[kind],
                                layer=layer_id(layer), net=net or "", width=dist(width), via_diameter=dist(via[0]),
                                via_drill=dist(via[1]), search_radius=dist(radius), max_results=max_results)
        cmd.board.CopyFrom(self.doc)
        cmd.start.CopyFrom(v2(*start)); cmd.end.CopyFrom(v2(*(end or start)))
        r = self.kicad._client.send(cmd, rc.ProbeResult)
        return {"ok": r.ok, "min_margin": r.min_margin_nm / NM, "message": r.message,
                "obstacles": [{"kind": o.kind, "net": o.net, "desc": o.description, "id": o.item.value,
                               "distance": o.distance_nm / NM, "required": o.required_nm / NM,
                               "margin": o.margin_nm / NM, "layer": layer_name(o.layer) if o.layer else None}
                              for o in r.obstacles]}

    def clearance_at(self, x, y, layer, net="", width=0, radius=1.0):
        return self.probe("point", (x, y), layer=layer, net=net, width=width, radius=radius)

    def check_via(self, x, y, net="", via=(0, 0), radius=1.0):
        return self.probe("via", (x, y), net=net, via=via, radius=radius)

    def check_track(self, a, b, layer, net="", width=0, radius=1.0):
        return self.probe("segment", a, b, layer=layer, net=net, width=width, radius=radius)

    def zone_islands(self, nets=None, refill=False):
        """Per zone fill polygon: area, isolated / single-connection, items touching it, pads reachable."""
        if refill:
            self.board.refill_zones(block=True, max_poll_seconds=120)
        cmd = rc.GetZoneIslands(nets=[nets] if isinstance(nets, str) else list(nets or []))
        cmd.board.CopyFrom(self.doc)
        r = self.kicad._client.send(cmd, rc.ZoneIslandsResponse)
        return [{"zone": i.zone_name or i.zone.value[:8], "net": i.net, "layer": layer_name(i.layer), "index": i.index,
                 "area": round(i.area_mm2, 3), "isolated": i.isolated, "single_connection": i.single_connection,
                 "bbox": [i.bbox.position.x_nm / NM, i.bbox.position.y_nm / NM,
                          (i.bbox.position.x_nm + i.bbox.size.x_nm) / NM, (i.bbox.position.y_nm + i.bbox.size.y_nm) / NM],
                 "anchor": [i.anchor.x_nm / NM, i.anchor.y_nm / NM],
                 "direct": [d.description for d in i.direct], "pads": i.cluster_pads, "pad_names": list(i.pads)}
                for i in r.islands]

    # ---- editing helpers --------------------------------------------------------------------------------------
    def set_teardrops(self, enable=True, vias=True, pth_pads=True, smd_pads=True, track_to_track=False, nets=None):
        cmd = rc.SetTeardrops(enable=enable, vias=vias, pth_pads=pth_pads, smd_pads=smd_pads,
                              track_to_track=track_to_track, nets=list(nets or []))
        cmd.board.CopyFrom(self.doc)
        r = self.kicad._client.send(cmd, rc.TeardropsResponse)
        return {"items_changed": r.items_changed, "teardrop_zones": r.teardrop_zones}

    def update_from_schematic(self, schematic=None, dry_run=True, relink_by_reference=False, delete_unused=False,
                              replace_footprints=True, update_fields=True, override_locks=False):
        """Tools > Update PCB from Schematic, via a kicad-cli netlist. The schematic defaults to the board's own
        (or, for a work copy, the original's, recorded by pns_open copy_from). dry_run=True only reports."""
        sch = schematic or self.schematic_path()
        if not sch or not os.path.exists(sch):
            raise FileNotFoundError("schematic not found: %s" % sch)
        net = os.path.join(tempfile.mkdtemp(prefix="pnsnet_", dir=RUN_TMP if os.path.isdir(RUN_TMP) else None),
                           "board.net")
        r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch],
                           capture_output=True, text=True)
        if not os.path.exists(net):
            raise RuntimeError("netlist export failed: %s %s" % (r.stdout[-400:], r.stderr[-400:]))
        cmd = rc.UpdateFromNetlist(netlist_path=net, dry_run=dry_run, relink_by_reference=relink_by_reference,
                                   delete_unused_footprints=delete_unused, replace_footprints=replace_footprints,
                                   update_fields=update_fields, override_locks=override_locks)
        cmd.board.CopyFrom(self.doc)
        r = self.kicad._client.send(cmd, rc.UpdateFromNetlistResponse)
        routine = ("Processing symbol", "sheetname to", "sheetfile to", "unit metadata", "footprint filters to")
        changes = [l for l in r.report.splitlines() if l.strip() and not any(k in l for k in routine)]
        return {"applied": r.applied, "schematic": sch, "changes": changes, "report_lines": len(r.report.splitlines())}

    def schematic_path(self):
        b = self.board_path()
        sch = os.path.splitext(b)[0] + ".kicad_sch"
        if os.path.exists(sch):
            return sch
        src = os.path.join(os.path.dirname(b), "source.json")
        if os.path.exists(src):
            return os.path.splitext(json.load(open(src))["source"])[0] + ".kicad_sch"
        return None

    # ---- board helpers ----------------------------------------------------------------------------------------
    def tracks(self, net=None, layer=None, box=None):
        out = []
        lid = layer_id(layer) if layer else None
        for t in self.board.get_tracks():
            if net and t.net.name != net:
                continue
            if lid is not None and t.layer != lid:
                continue
            a, b = (t.start.x / NM, t.start.y / NM), (t.end.x / NM, t.end.y / NM)
            if box and not _in_box(a, box) and not _in_box(b, box):
                continue
            out.append(t)
        return out

    def vias(self, net=None, box=None):
        return [v for v in self.board.get_vias() if (not net or v.net.name == net)
                and (not box or _in_box((v.position.x / NM, v.position.y / NM), box))]

    def items_at(self, x, y, layer=None, radius=0.5, net=None):
        """Tracks and vias within radius of (x, y), nearest first."""
        hits = []
        for v in self.vias(net):
            d = math.hypot(v.position.x / NM - x, v.position.y / NM - y)
            if d <= radius + v.diameter / NM / 2:
                hits.append({"id": v.id.value, "type": "via", "net": v.net.name, "d": d,
                             "pos": [v.position.x / NM, v.position.y / NM]})
        for t in self.tracks(net, layer):
            d = _seg_dist(x, y, t.start.x / NM, t.start.y / NM, t.end.x / NM, t.end.y / NM)
            if d <= radius + t.width / NM / 2:
                hits.append({"id": t.id.value, "type": "track", "net": t.net.name, "d": d,
                             "layer": layer_name(t.layer), "start": [t.start.x / NM, t.start.y / NM],
                             "end": [t.end.x / NM, t.end.y / NM], "width": t.width / NM})
        return sorted(hits, key=lambda h: h["d"])

    def ripup_net(self, net, layer=None, box=None, vias=True):
        """Delete a net's tracks (optionally only on one layer / inside box=(x0, y0, x1, y1)) and its vias."""
        items = self.tracks(net, layer, box)
        if vias and not layer:
            items += self.vias(net, box)
        if items:
            self.board.remove_items(items)
        return {"removed": len(items)}

    def undo(self):
        r = self.kicad.run_action("common.Interactive.undo")
        return "ok" if getattr(r, "status", r) == 1 else str(r).strip()

    def save(self, path=None):
        if path:
            self.board.save_as(path, overwrite=True, include_project=True)
        else:
            self.board.save()
        return path or self.board_path()

    # ---- DRC --------------------------------------------------------------------------------------------------
    def drc_summary(self, refill=True, net=None, box=None, max_items=30, schematic_parity=False):
        """Save a temporary copy of the open board, run kicad-cli DRC on it, return counts + a filtered list."""
        tmp = tempfile.mkdtemp(prefix="pnsdrc_", dir=RUN_TMP if os.path.isdir(RUN_TMP) else None)
        name = os.path.basename(self.doc.board_filename) or "board.kicad_pcb"
        pcb = os.path.join(tmp, name)
        self.board.save_as(pcb, overwrite=True, include_project=True)
        src_dir = os.path.dirname(self.board_path())
        for ext in (".kicad_dru",):
            s = os.path.join(src_dir, os.path.splitext(name)[0] + ext)
            if os.path.exists(s):
                with open(s, "rb") as f, open(os.path.join(tmp, os.path.basename(s)), "wb") as g:
                    g.write(f.read())
        rpt = os.path.join(tmp, "drc.json")
        args = [KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all", "--units", "mm", "-o", rpt]
        if refill:
            args.append("--refill-zones")
        if schematic_parity:
            args.append("--schematic-parity")
        r = subprocess.run(args + [pcb], capture_output=True, text=True)
        if not os.path.exists(rpt):
            raise RuntimeError("kicad-cli DRC failed: %s %s" % (r.stdout[-500:], r.stderr[-500:]))
        return summarize_drc(json.load(open(rpt, encoding="utf-8")), net=net, box=box, max_items=max_items)

    # ---- plot -------------------------------------------------------------------------------------------------
    def plot_area(self, box, out_png, layers=("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"), zones=False, highlight=None,
                  px_per_mm=40, max_px=2400):
        """PNG of copper in box=(x0, y0, x1, y1): tracks, vias, pads, optional zone fills; highlight nets dim the
        rest. Read live from the open board."""
        return plot_area(self, box, out_png, layers, zones, highlight, px_per_mm, max_px)


def _in_box(p, box):
    x0, y0, x1, y1 = box
    return min(x0, x1) <= p[0] <= max(x0, x1) and min(y0, y1) <= p[1] <= max(y0, y1)


def summarize_drc(rep, net=None, box=None, max_items=30):
    counts, items = {}, []
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in rep.get(key, []):
            t = v.get("type", key)
            counts[t] = counts.get(t, 0) + 1
            its = v.get("items", [])
            if net and not any(("[%s]" % net) in i.get("description", "") for i in its):
                continue
            if box and not any(_in_box((i["pos"]["x"], i["pos"]["y"]), box) for i in its if "pos" in i):
                continue
            items.append({"type": t, "severity": v.get("severity"), "desc": v.get("description"),
                          "items": [{"desc": i.get("description"), "pos": [i["pos"]["x"], i["pos"]["y"]]}
                                    for i in its if "pos" in i]})
    errors = sum(1 for k in ("violations",) for v in rep.get(k, []) if v.get("severity") == "error")
    return {"errors": errors, "unconnected": len(rep.get("unconnected_items", [])),
            "counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "matching": len(items), "items": items[:max_items]}


COLORS = {"F.Cu": "#c83434", "In1.Cu": "#c8a832", "In2.Cu": "#c832c8", "B.Cu": "#3464c8"}


def _poly_xy(pl):
    pts = []
    for n in getattr(pl, "_proto", pl).nodes:
        if n.HasField("point"):
            pts.append((n.point.x_nm / NM, n.point.y_nm / NM))
        elif n.HasField("arc"):
            for q in (n.arc.start, n.arc.mid, n.arc.end):
                pts.append((q.x_nm / NM, q.y_nm / NM))
    return pts


def plot_area(p, box, out_png, layers, zones, highlight, px_per_mm, max_px):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle
    x0, x1 = sorted((box[0], box[2])); y0, y1 = sorted((box[1], box[3]))
    w, h = x1 - x0, y1 - y0
    scale = min(px_per_mm, max_px / max(w, h))
    dpi = 100
    fig = plt.figure(figsize=(w * scale / dpi, h * scale / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal"); ax.axis("off")
    fig.patch.set_facecolor("#101010")
    pt_per_mm = scale * 72.0 / dpi
    hl = set([highlight] if isinstance(highlight, str) else (highlight or []))
    alpha = lambda n: 1.0 if not hl or n in hl else 0.25          # noqa: E731
    pad_box = (x0 - 3, y0 - 3, x1 + 3, y1 + 3)
    for li, lname in enumerate(layers):
        lid, col = layer_id(lname), COLORS.get(lname, "#888888")
        if zones:
            for z in p.board.get_zones():
                if z.is_rule_area():
                    continue
                for poly in z.filled_polygons.get(lid, []):
                    pts = _poly_xy(poly.outline)
                    if pts:
                        ax.add_patch(Polygon(pts, closed=True, fc=col, ec="none", alpha=0.18 * alpha(z.net.name)))
        for t in p.tracks(layer=lname, box=pad_box):
            ax.plot([t.start.x / NM, t.end.x / NM], [t.start.y / NM, t.end.y / NM], color=col,
                    lw=t.width / NM * pt_per_mm, solid_capstyle="round", alpha=0.85 * alpha(t.net.name), zorder=2 + li)
    pads = [q for q in p.board.get_pads() if _in_box((q.position.x / NM, q.position.y / NM), pad_box)]
    for lname in ("F.Cu", "B.Cu"):
        if lname not in layers or not pads:
            continue
        cmd = board_commands_pb2.GetPadShapeAsPolygon(layer=layer_id(lname))
        cmd.board.CopyFrom(p.doc)
        cmd.pads.extend([q.id for q in pads])
        resp = p.kicad._client.send(cmd, board_commands_pb2.PadShapeAsPolygonResponse)
        net_of = {q.id.value: q.net.name for q in pads}
        for pid, poly in zip(resp.pads, resp.polygons):
            ax.add_patch(Polygon(_poly_xy(poly.outline), closed=True, fc=COLORS[lname], ec="#ffffff", lw=0.3,
                                 alpha=0.7 * alpha(net_of.get(pid.value, "")), zorder=10))
    for v in p.vias(box=pad_box):
        c = (v.position.x / NM, v.position.y / NM)
        ax.add_patch(Circle(c, v.diameter / NM / 2, fc="#d0d0d0", ec="none", alpha=alpha(v.net.name), zorder=20))
        ax.add_patch(Circle(c, v.drill_diameter / NM / 2, fc="#101010", ec="none", zorder=21))
    for s in p.board.get_shapes():
        if s.layer == board_types_pb2.BL_Edge_Cuts and hasattr(s, "start") and hasattr(s, "end"):
            ax.plot([s.start.x / NM, s.end.x / NM], [s.start.y / NM, s.end.y / NM], color="#e0e000", lw=1, zorder=30)
    fig.savefig(out_png, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_png


def copy_design(src, name=None, work=None):
    """Copy a board + its project files into work/<name>/ for editing. Project library tables get ${KIPRJMOD}
    rewritten to the original folder, and source.json records the original (for update_from_schematic)."""
    import shutil
    src = os.path.abspath(src)
    sdir = os.path.dirname(src)
    stem_src = os.path.splitext(os.path.basename(src))[0]
    stem = name or "%s_%s" % (stem_src, time.strftime("%Y%m%d_%H%M%S"))
    d = os.path.join(work or os.path.join(DEV, "work"), stem)
    os.makedirs(d, exist_ok=True)
    for ext in (".kicad_pcb", ".kicad_pro", ".kicad_prl", ".kicad_dru"):
        s = os.path.join(sdir, stem_src + ext)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(d, stem + ext))
    for tbl in ("fp-lib-table", "sym-lib-table"):
        s = os.path.join(sdir, tbl)
        if os.path.exists(s):
            open(os.path.join(d, tbl), "w").write(open(s).read().replace("${KIPRJMOD}", sdir.replace("\\", "/")))
    json.dump({"source": src}, open(os.path.join(d, "source.json"), "w"))
    return os.path.join(d, stem + ".kicad_pcb")


# ---- process management ---------------------------------------------------------------------------------------
def _dev_pcbnew_pids():
    exe = os.path.normcase(os.path.join(DEV_BIN, "pcbnew.exe"))
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-Process pcbnew -ErrorAction SilentlyContinue | ForEach-Object { \"$($_.Id)|$($_.Path)\" }"],
                       capture_output=True, text=True)
    pids = []
    for line in r.stdout.splitlines():
        pid, _, path = line.partition("|")
        if os.path.normcase(path.strip()) == exe:
            pids.append(int(pid))
    return pids


def ensure_config():
    """Private KICAD_CONFIG_HOME with the API server enabled (keeps the installed KiCad 10 settings untouched).
    Seeded once from the user's KiCad 10 settings so the first-run setup wizard does not block startup."""
    import shutil
    d = os.path.join(CONFIG, "10.0")
    user = os.path.join(os.environ["APPDATA"], "kicad", "10.0")
    if not os.path.exists(os.path.join(d, "pcbnew.json")) and os.path.isdir(user):
        shutil.copytree(user, d, dirs_exist_ok=True)
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(RUN_TMP, "kicad"), exist_ok=True)
    common = os.path.join(d, "kicad_common.json")
    cfg = json.load(open(common)) if os.path.exists(common) else {}
    cfg.setdefault("api", {})["enable_server"] = True
    dnsa = cfg.setdefault("do_not_show_again", {})
    dnsa["update_check_prompt"] = True
    dnsa["data_collection_prompt"] = True
    json.dump(cfg, open(common, "w"), indent=2)


def start_pcbnew(board_path):
    ensure_config()
    env = dict(os.environ, KICAD_CONFIG_HOME=CONFIG, TMP=RUN_TMP, TEMP=RUN_TMP)
    env.pop("KICAD_API_SOCKET", None); env.pop("KICAD_API_TOKEN", None)
    return subprocess.Popen([os.path.join(DEV_BIN, "pcbnew.exe"), os.path.abspath(board_path)], env=env,
                            cwd=os.path.dirname(os.path.abspath(board_path)),
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


if __name__ == "__main__":
    print("running:", PNS.running())
