# Client-side helpers built on the private KiCad API (pns_client.PNS): footprint fan-out, stitching vias, footprint move
# with push, congestion map, MCAD height regions. Every check goes through the router's own clearance probe, so nothing
# here re-implements DRC. All units mm; layers by name ("F.Cu").
import math, os

from kipy.board_types import Via
from kipy.geometry import Vector2
from kipy.proto.board import board_types_pb2 as bt
from kipy.proto.common.types.base_types_pb2 import KIID

from pns_client import NM, layer_name

CU = {bt.BL_F_Cu: "F.Cu", bt.BL_B_Cu: "B.Cu"}


def _path(poly_proto):
    from matplotlib.path import Path
    pts = []
    for n in poly_proto.nodes:
        if n.HasField("point"):
            pts.append((n.point.x_nm / NM, n.point.y_nm / NM))
        elif n.HasField("arc"):
            pts += [(q.x_nm / NM, q.y_nm / NM) for q in (n.arc.start, n.arc.mid, n.arc.end)]
    return Path(pts) if len(pts) > 2 else None


def _fills(p, net=None, exclude_net=None):
    """{layer name: [(outline Path, [hole Paths])]} of zone fills of a net (or of every net but exclude_net)."""
    out = {}
    for z in p.board.get_zones():
        if z.is_rule_area():
            continue
        n = z.net.name if z.net else ""
        if (net is not None and n != net) or (exclude_net is not None and n == exclude_net):
            continue
        for lid, polys in z.filled_polygons.items():
            for poly in polys:
                o = _path(poly._proto.outline)
                if o is not None:
                    out.setdefault(layer_name(lid), []).append((o, [h for h in (_path(x) for x in poly._proto.holes) if h]))
    return out


def _inside(fills, pt):
    return any(o.contains_point(pt) and not any(h.contains_point(pt) for h in holes) for o, holes in fills)


def _circle(pt, r, n=8):
    return [(pt[0] + r * math.cos(2 * math.pi * k / n), pt[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def footprint(p, ref):
    for f in p.board.get_footprints():
        if f.reference_field.text.value == ref:
            return f
    raise ValueError("no footprint %s" % ref)


def copper_pads(fp):
    """The footprint's real pads (with a number and a copper layer), as (pad, layer name or 'all')."""
    out = []
    for q in fp.definition.pads:
        layers = set(q.padstack.layers)
        if not q.number:
            continue
        if bt.BL_F_Cu in layers and bt.BL_B_Cu in layers:
            out.append((q, "all"))
        elif bt.BL_F_Cu in layers or bt.BL_B_Cu in layers:
            out.append((q, "F.Cu" if bt.BL_F_Cu in layers else "B.Cu"))
    return out


# ---- fan-out ----------------------------------------------------------------------------------------------------------
def fanout_footprint(p, ref, via=(0, 0), pads=None, skip_nets=("",), lengths=(0.0, 0.2, 0.4, 0.7, 1.0, 1.4),
                     only_unconnected=True, dry_run=False):
    """Stub + via for each SMD pad of a footprint (default every pad with a net that has no track yet). For each pad the
    escape point is tried straight out from the footprint centre, then at +-45 deg, at growing distances; the via spot
    is checked with the router's clearance probe and the stub is routed (shove mode) and committed with its via."""
    fp = footprint(p, ref)
    cx, cy = fp.position.x / NM, fp.position.y / NM
    tracks = list(p.board.get_tracks())
    results = []
    for q, side in copper_pads(fp):
        net = q.net.name if q.net else ""
        if net in skip_nets or (pads and q.number not in pads) or side == "all":
            continue
        px, py = q.position.x / NM, q.position.y / NM
        bb = p.board.get_item_bounding_box(q)
        hx, hy = bb.size.x / NM / 2, bb.size.y / NM / 2
        if only_unconnected and any(t.net.name == net and any(abs(e.x / NM - px) <= hx + 0.05 and abs(e.y / NM - py) <= hy + 0.05
                                                              for e in (t.start, t.end)) for t in tracks):
            results.append({"pad": q.number, "net": net, "status": "already connected"}); continue
        ang = math.atan2(py - cy, px - cx)
        base = round(ang / (math.pi / 2)) * (math.pi / 2)                  # straight out of the package side
        other = "B.Cu" if side == "F.Cu" else "F.Cu"
        done = None
        for L in lengths:
            for a in (base, base + math.pi / 4, base - math.pi / 4):
                ux, uy = math.cos(a), math.sin(a)
                edge = abs(ux) * hx + abs(uy) * hy                          # pad half-extent along the direction
                dvia = (via[0] or 0.45) / 2
                d = edge + dvia + 0.15 + L
                pt = (round(px + ux * d, 4), round(py + uy * d, 4))
                c = p.check_via(pt[0], pt[1], net=net, via=via, radius=0.6)
                if not c["ok"]:
                    continue
                if dry_run:
                    done = {"pad": q.number, "net": net, "status": "would place", "via": pt}
                    break
                r = p.route_track(net, [(px, py), (pt[0], pt[1], other)], layer=side, via=via)
                if r["committed"]:
                    done = {"pad": q.number, "net": net, "status": "ok", "via": pt, "margin": round(c["min_margin"], 3)}
                    break
            if done:
                break
        results.append(done or {"pad": q.number, "net": net, "status": "no room"})
    return {"ref": ref, "placed": sum(r["status"] in ("ok", "would place") for r in results), "pads": results}


# ---- stitching vias ---------------------------------------------------------------------------------------------------
def add_stitching_vias(p, net="/GND", area=None, pitch=1.5, via=(0, 0), layers=None, margin=0.1, max_vias=400,
                       avoid_other_zones=True, dry_run=False):
    """Grid of through vias inside the net's zone fills (on every layer in 'layers', default all layers the net is
    poured on), each checked with the router's clearance probe and kept off other nets' pours."""
    fills = _fills(p, net=net)
    if not fills:
        raise ValueError("no zone fills for %s (refill zones first?)" % net)
    need = layers or sorted(fills)
    others = {l: f for l, f in _fills(p, exclude_net=net).items()} if avoid_other_zones else {}
    allf = [x for l in need for x in fills.get(l, [])]
    xs = [v[0] for o, _ in allf for v in o.vertices]; ys = [v[1] for o, _ in allf for v in o.vertices]
    x0, y0, x1, y1 = area or (min(xs), min(ys), max(xs), max(ys))
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1))
    r = (via[0] or 0.45) / 2 + margin
    existing = [(v.position.x / NM, v.position.y / NM) for v in p.board.get_vias()]
    placed, rejected = [], 0
    y = y0 + pitch / 2
    while y < y1 and len(placed) < max_vias:
        x = x0 + pitch / 2
        while x < x1 and len(placed) < max_vias:
            ring = _circle((x, y), r) + [(x, y)]
            if all(all(_inside(fills.get(l, []), q) for q in ring) for l in need) \
                    and not any(_inside(f, q) for f in others.values() for q in ring) \
                    and all(math.dist((x, y), e) > pitch * 0.6 for e in existing):
                c = p.check_via(x, y, net=net, via=via, radius=0.5)
                if c["ok"]:
                    placed.append((round(x, 4), round(y, 4)))
                else:
                    rejected += 1
            x += pitch
        y += pitch
    if placed and not dry_run:
        netobj = [n for n in p.board.get_nets() if n.name == net][0]
        vias = []
        for (x, y) in placed:
            v = Via()
            v.position = Vector2.from_xy(int(x * NM), int(y * NM))
            v.net = netobj
            if via[0]:
                v.diameter = int(via[0] * NM)
            if via[1]:
                v.drill_diameter = int(via[1] * NM)
            vias.append(v)
        p.board.create_items(vias)
    return {"net": net, "layers": need, "placed": len(placed), "rejected_by_probe": rejected, "vias": placed,
            "note": "refill zones to see them connected" if placed and not dry_run else ""}


# ---- footprint move with push -----------------------------------------------------------------------------------------
def _courtyard_box(fp):
    crt = bt.BL_B_CrtYd if fp.layer == bt.BL_B_Cu else bt.BL_F_CrtYd
    pts = []
    for s in fp.definition.shapes:
        if s.layer != crt:
            continue
        for attr in ("start", "end", "top_left", "bottom_right", "center"):
            v = getattr(s, attr, None)
            if v is not None and hasattr(v, "x"):
                pts.append((v.x / NM, v.y / NM))
        if hasattr(s, "polygons"):
            for poly in s.polygons:
                pts += [(n.point.x / NM, n.point.y / NM) for n in poly.outline.nodes if n.has_point]
    if not pts:                                                       # no courtyard: pads + 0.25
        for q, _ in copper_pads(fp):
            pts.append((q.position.x / NM, q.position.y / NM))
        if not pts:
            return None
        xs, ys = zip(*pts)
        return [min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5]
    xs, ys = zip(*pts)
    return [min(xs), min(ys), max(xs), max(ys)]


def move_footprint(p, ref, xy=None, rotation=None, push=True, clearance=0.2, max_moves=60, dry_run=False):
    """Move (and/or rotate) a footprint; with push, neighbours on the same side whose courtyards would come closer than
    'clearance' are pushed out along the shortest axis, cascading (locked parts are never moved; they are reported).
    Tracks are not dragged: re-route the moved parts' connections afterwards (ratsnest stays)."""
    fps = {f.reference_field.text.value: f for f in p.board.get_footprints()}
    me = fps[ref]
    if me.locked:
        raise ValueError("%s is locked" % ref)
    boxes = {r: _courtyard_box(f) for r, f in fps.items()}
    side = {r: f.layer for r, f in fps.items()}
    old = (me.position.x / NM, me.position.y / NM)
    turn = 0.0
    if rotation is not None:
        turn = (rotation - me.orientation.degrees) % 180.0
        from kipy.geometry import Angle
        me.orientation = Angle.from_degrees(rotation)
    if xy:
        me.position = Vector2.from_xy(int(xy[0] * NM), int(xy[1] * NM))
    b = boxes[ref]
    if b is not None:                                                  # my courtyard box at the new place
        cx, cy = (b[0] + b[2]) / 2 + (xy[0] - old[0] if xy else 0), (b[1] + b[3]) / 2 + (xy[1] - old[1] if xy else 0)
        w, h = b[2] - b[0], b[3] - b[1]
        if abs(turn - 90.0) < 1:
            w, h = h, w
        boxes[ref] = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    if (xy or rotation is not None) and not dry_run:
        p.board.update_items(me)
    moved, blocked = {}, []
    queue = [ref]
    n = 0
    while queue and n < max_moves:
        a = queue.pop(0); A = boxes[a]
        if not push or A is None:
            break
        for b, B in boxes.items():
            if b == a or B is None or side[b] != side[a]:
                continue
            ox = min(A[2], B[2]) - max(A[0], B[0]) + clearance
            oy = min(A[3], B[3]) - max(A[1], B[1]) + clearance
            if ox <= 0 or oy <= 0:
                continue
            if fps[b].locked or b == ref:
                blocked.append({"ref": b, "against": a}); continue
            ca, cb = ((A[0] + A[2]) / 2, (A[1] + A[3]) / 2), ((B[0] + B[2]) / 2, (B[1] + B[3]) / 2)
            if ox < oy:
                d = (ox + 0.01) * (1 if cb[0] >= ca[0] else -1); dx, dy = d, 0.0
            else:
                d = (oy + 0.01) * (1 if cb[1] >= ca[1] else -1); dx, dy = 0.0, d
            boxes[b] = [B[0] + dx, B[1] + dy, B[2] + dx, B[3] + dy]
            m = moved.setdefault(b, [0.0, 0.0]); m[0] += dx; m[1] += dy
            queue.append(b); n += 1
    if moved and not dry_run:
        items = []
        for b, (dx, dy) in moved.items():
            f = fps[b]
            f.position = Vector2.from_xy(int(f.position.x + dx * NM), int(f.position.y + dy * NM))
            items.append(f)
        p.board.update_items(items)
    return {"moved": {b: [round(d[0], 3), round(d[1], 3)] for b, d in moved.items()}, "blocked": blocked,
            "note": "tracks are not dragged; re-route the moved parts" if moved else ""}


# ---- congestion map ---------------------------------------------------------------------------------------------------
def congestion_map(p, area=None, cell=1.0, out_png=None, pad_weight=0.5):
    """Routing demand per cell: straight ratsnest lines of every open link (each link counts once per cell) plus pads.
    Returns the grid statistics and the hottest cells; optional PNG heatmap with the board outline and pads."""
    import numpy as np
    links = p.get_unrouted()["links"]
    pads = [(q.position.x / NM, q.position.y / NM) for q in p.board.get_pads() if q.number]
    edge = [s for s in p.board.get_shapes() if s.layer == bt.BL_Edge_Cuts]
    if area is None:
        bbs = [p.board.get_item_bounding_box(s) for s in edge]
        bbs = [b for b in bbs if b is not None]
        area = (min(b.pos.x for b in bbs) / NM, min(b.pos.y for b in bbs) / NM,
                max(b.pos.x + b.size.x for b in bbs) / NM, max(b.pos.y + b.size.y for b in bbs) / NM) if bbs else             (min(x for x, _ in pads), min(y for _, y in pads), max(x for x, _ in pads), max(y for _, y in pads))
    x0, x1 = sorted((area[0], area[2])); y0, y1 = sorted((area[1], area[3]))
    nx, ny = max(1, int(math.ceil((x1 - x0) / cell))), max(1, int(math.ceil((y1 - y0) / cell)))
    g = np.zeros((ny, nx))
    for l in links:
        (ax, ay), (bx, by) = l["a"]["pos"], l["b"]["pos"]
        k = max(2, int(math.dist((ax, ay), (bx, by)) / (cell / 3)) + 1)
        cells = set()
        for t in np.linspace(0, 1, k):
            i, j = int((ay + (by - ay) * t - y0) / cell), int((ax + (bx - ax) * t - x0) / cell)
            if 0 <= i < ny and 0 <= j < nx:
                cells.add((i, j))
        for i, j in cells:
            g[i, j] += 1
    for x, y in pads:
        i, j = int((y - y0) / cell), int((x - x0) / cell)
        if 0 <= i < ny and 0 <= j < nx:
            g[i, j] += pad_weight
    hot = sorted(((g[i, j], x0 + (j + 0.5) * cell, y0 + (i + 0.5) * cell) for i in range(ny) for j in range(nx)),
                 reverse=True)[:15]
    if out_png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 8 * (y1 - y0) / max(1e-6, x1 - x0)), dpi=110)
        im = ax.imshow(g, extent=(x0, x0 + nx * cell, y0 + ny * cell, y0), cmap="inferno", interpolation="nearest")
        ax.scatter([x for x, _ in pads], [y for _, y in pads], s=1, c="#33ccff", alpha=0.5)
        for s in edge:
            pts = [v for v in (getattr(s, "start", None), getattr(s, "mid", None), getattr(s, "end", None)) if v is not None]
            if len(pts) == 3:                                         # arc: draw it through its mid point
                import numpy as _np
                (ax_, ay_), (bx_, by_), (cx_, cy_) = [(v.x / NM, v.y / NM) for v in pts]
                d = 2 * (ax_ * (by_ - cy_) + bx_ * (cy_ - ay_) + cx_ * (ay_ - by_))
                if abs(d) > 1e-9:
                    ux = ((ax_**2 + ay_**2) * (by_ - cy_) + (bx_**2 + by_**2) * (cy_ - ay_) + (cx_**2 + cy_**2) * (ay_ - by_)) / d
                    uy = ((ax_**2 + ay_**2) * (cx_ - bx_) + (bx_**2 + by_**2) * (ax_ - cx_) + (cx_**2 + cy_**2) * (bx_ - ax_)) / d
                    R = math.hypot(ax_ - ux, ay_ - uy)
                    a0, a1, am = (math.atan2(y - uy, x - ux) for x, y in ((ax_, ay_), (cx_, cy_), (bx_, by_)))
                    span = (a1 - a0) % (2 * math.pi)
                    if not (0 <= (am - a0) % (2 * math.pi) <= span):
                        span -= 2 * math.pi
                    tt = _np.linspace(a0, a0 + span, 90)
                    ax.plot(ux + R * _np.cos(tt), uy + R * _np.sin(tt), color="#e0e000", lw=0.8)
            elif len(pts) == 2:
                ax.plot([pts[0].x / NM, pts[1].x / NM], [pts[0].y / NM, pts[1].y / NM], color="#e0e000", lw=0.8)
        ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, shrink=0.7, label="open links + %.1f x pads per %.1f mm cell" % (pad_weight, cell))
        ax.set_title("Routing demand (%d open links)" % len(links))
        fig.savefig(out_png, bbox_inches="tight"); plt.close(fig)
    return {"cell": cell, "area": [x0, y0, x1, y1], "max": float(g.max()), "mean": round(float(g.mean()), 3),
            "p95": float(np.percentile(g, 95)), "open_links": len(links),
            "hottest": [{"demand": round(float(v), 1), "at": [round(x, 2), round(y, 2)]} for v, x, y in hot],
            "png": out_png}


# ---- 3D: STEP export, height check, collisions ------------------------------------------------------------------------
def _origin_dir(p):
    import json as _json
    b = p.board_path()
    src = os.path.join(os.path.dirname(b), "source.json")
    return os.path.dirname(_json.load(open(src))["source"]) if os.path.exists(src) else os.path.dirname(b)


def export_step(p, out_step, user_origin=None, components=True):
    """Save a temp copy of the open board and export it with kicad-cli (3D models included). ${KIPRJMOD}/../lib model
    paths keep working through a 'lib' junction next to the temp folder."""
    import subprocess, tempfile, shutil
    from pns_client import RUN_TMP, KICAD_CLI
    base = os.path.join(RUN_TMP, "p3d")
    os.makedirs(base, exist_ok=True)
    lib = os.path.join(base, "lib")
    src_lib = os.path.normpath(os.path.join(_origin_dir(p), "..", "lib"))
    if os.path.isdir(src_lib) and not os.path.exists(lib):
        subprocess.run(["cmd", "/c", "mklink", "/J", lib, src_lib], capture_output=True)
    d = tempfile.mkdtemp(dir=base)
    pcb = os.path.join(d, "board.kicad_pcb")
    p.board.save_as(pcb, overwrite=True, include_project=True)
    args = [KICAD_CLI, "pcb", "export", "step", "-f", "-o", out_step]
    if user_origin:
        args += ["--user-origin", "%gx%gmm" % tuple(user_origin)]
    if not components:
        args.append("--no-components")
    r = subprocess.run(args + [pcb], capture_output=True, text=True)
    shutil.rmtree(d, ignore_errors=True)
    if not os.path.exists(out_step):
        raise RuntimeError("STEP export failed: %s %s" % (r.stdout[-400:], r.stderr[-400:]))
    return out_step


def _run3d(*args):
    import subprocess, sys as _sys
    r = subprocess.run([_sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pns_3d.py")] +
                       [str(a) for a in args], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError("pns_3d failed: " + r.stderr[-800:])


def height_check(p, regions=None, step=None):
    """Every component's 3D height (from the real models, exported by kicad-cli) vs. the MCAD max-height regions on
    the user layer. Returns violations plus each component's height and side."""
    import json as _json, tempfile
    from pns_client import RUN_TMP
    regions = regions if regions is not None else mcad_regions(p)
    d = tempfile.mkdtemp(dir=RUN_TMP)
    step = step or export_step(p, os.path.join(d, "board.step"))
    rj, oj = os.path.join(d, "regions.json"), os.path.join(d, "heights.json")
    _json.dump(regions, open(rj, "w"))
    _run3d("heights", step, rj, oj)
    out = _json.load(open(oj))
    out["regions"] = len(regions)
    return out


def collision_3d(p, external_step, user_origin=(100.0, 100.0), board_z=None, gap=0.5, skip=(), step=None):
    """Board components (exported with --user-origin, then lifted to board_z) vs. an external STEP in the robot frame
    (e.g. the robot assembly from FreeCAD): overlapping volumes and gaps under 'gap' mm. Defaults match BugBot:
    origin 100x100 mm, board underside at mcad.json's board_z (29 mm)."""
    import json as _json, tempfile
    from pns_client import RUN_TMP
    if board_z is None:
        mj = os.path.join(_origin_dir(p), "mcad.json")
        board_z = _json.load(open(mj)).get("board_z", 0.0) if os.path.exists(mj) else 0.0
    d = tempfile.mkdtemp(dir=RUN_TMP)
    step = step or export_step(p, os.path.join(d, "board_robot.step"), user_origin=user_origin)
    oj, rj = os.path.join(d, "opts.json"), os.path.join(d, "collide.json")
    _json.dump({"gap": gap, "board_z": board_z, "skip": list(skip)}, open(oj, "w"))
    _run3d("collide", step, external_step, oj, rj)
    out = _json.load(open(rj))
    out.update({"board_z": board_z, "user_origin": list(user_origin)})
    return out


# ---- MCAD height regions ----------------------------------------------------------------------------------------------
def mcad_regions(p, layer=bt.BL_User_1):
    """Closed outlines on the MCAD user layer paired with the label inside them: 'top|bottom: max X mm | part'."""
    import re
    from matplotlib.path import Path
    polys = []
    for s in p.board.get_shapes():
        if s.layer != layer:
            continue
        if hasattr(s, "polygons"):
            for poly in s.polygons:
                pts = [(n.point.x / NM, n.point.y / NM) for n in poly.outline.nodes if n.has_point]
                if len(pts) > 2:
                    polys.append(pts)
        elif hasattr(s, "top_left") and hasattr(s, "bottom_right"):
            a, b = s.top_left, s.bottom_right
            polys.append([(a.x / NM, a.y / NM), (b.x / NM, a.y / NM), (b.x / NM, b.y / NM), (a.x / NM, b.y / NM)])
    labels = []
    for t in p.board.get_text():
        if getattr(t, "layer", None) != layer:
            continue
        m = re.match(r"\s*(top|bottom)\s*:\s*max\s*([\d.]+)\s*mm\s*\|?\s*(.*)", t.value)
        if m:
            labels.append(((t.position.x / NM, t.position.y / NM), m.group(1), float(m.group(2)), m.group(3).strip()))
    regions = []
    for pos, side, hmax, part in labels:
        inside = [pl for pl in polys if Path(pl).contains_point(pos)]
        if inside:                                                     # the smallest outline around the label
            pl = min(inside, key=lambda q: abs(sum(q[i][0] * q[i - 1][1] - q[i - 1][0] * q[i][1] for i in range(len(q)))))
            regions.append({"side": side, "max": hmax, "part": part, "label_at": list(pos), "polygon": pl})
    return regions
