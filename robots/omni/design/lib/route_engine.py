# Lane-aware grid router for the main board (routing plan v1, approved 2026-10-25). The plan decides; this carries it out.
#  - layers F.Cu / In2.Cu / B.Cu (In1 is the solid GND plane, never routed); In2 may carry signals only inside the plan's
#    "In2 signal" areas, elsewhere it stays the VSYS pour (hard rule)
#  - each net is grown as a tree: from its first pad, the nearest unconnected pad is routed to the tree, and so on
#  - lanes: each net prefers its plan lane (outside costs LANE_PENALTY x); not a wall, so a net can still reach its pads
#  - GND / VSYS pads: a short stub to a plane via (or to an existing via of the net); VSYS vias only where the In2 pour is
#  - windowed: each connection is searched in a box round its ends (fast); the result is string-pulled into straight runs
#  - clearance: 0.15 mm rule + margin for the 0.05 mm grid; KiCad's DRC checks every stage
# Used by route_stage.py. KiCad mm coordinates (x right, y down); the plan's robot coordinates convert with
# X = x - 100, Y = 100 - y.
import json, math, heapq, re
import numpy as np
from scipy.ndimage import distance_transform_edt, label
from matplotlib.path import Path

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/_route/"
RES = 0.05
LAYERS = ["F", "I2", "I3", "B"]     # plan v2: In2 / In3 are signal layers; In1 (GND) and In4 (VSYS islands + GND) planes
CLR, EDGE_CLR, HOLE_CLR = 0.22, 0.37, 0.29   # 0.15 rule + 2 x 0.035 grid rounding (seen 0.1415 at 0.19)
LANE_PENALTY = 3.0
HEUR_W = 1.6        # weighted A*: the search runs many times faster; paths stay within a few % of the shortest
# neat traces: each inner layer has a direction (In2 front-back = KiCad x, In3 left-right = KiCad y); steps along it
# cost 1, diagonal DIAG_COST, across ACROSS_COST. Outer layers cost OUTER_COST per step (kept for fan-outs and power).
DIR = {"I2": (1, 0), "I3": (0, 1)}
DIAG_COST, ACROSS_COST, OUTER_COST = 1.25, 2.5, 1.15
# noise immunity (plan v2): switching nodes and sensitive lines keep NOISE_GAP mm apart on the same layer; the USB pair and
# camera lines never run on B over an In4 VSYS island (their reference there is In4: it must be GND)
NOISY = {"/SW33A", "/SW33B", "/SW5", "/KSW", "/M1_A", "/M1_B", "/M2_A", "/M2_B", "/M3_A", "/M3_B", "/SOL_N", "/BUZ_N"}
SENSITIVE = {"/VBAT_SENSE", "/SERVO_ISENSE", "/KICK_VSENSE", "/ISENSE_RAW", "/USB_DP", "/USB_DN", "/CAM_PCLK",
             "/CAM_PCLK_J", "/CAM_XCLK", "/CAM_XCLK_J", "/IMU_INT1", "/IMU_INT2", "/I2C_SDA", "/I2C_SCL", "/FB33", "/FB5", "/KFB"}
NOISE_GAP = 1.0
OUTER_ONLY = {"Battery", "Power", "Local"}       # these classes stay on F / B (inner layers are 0.5 oz); 3V3 may go inside
GND_REF = re.compile(r"/USB_D[PN]|/CAM_.*")      # need GND under them on B, and a GND via beside each of their vias
# tapered tracks: a track necks to fit only where it must (searches cost NECK_COST x through cells where the full
# width does not fit), and every 0.5 mm piece is then widened as far as its clearance allows, up to the class width;
# power classes may go wider still (W_MAX) where that leaves SPARE mm of room for later nets
NECK_COST, PIECE, SPARE = 3.0, 0.5, 0.4
W_MAX = {"Battery": 1.0, "Power": 0.8, "Rail3V3": 0.6, "Local": 0.5}
RIP_COST, NO_RIP, MAX_RIPS = 25.0, set(), 3
PLANES = {"/GND": "GND", "/VSYS": "VSYS"}         # plane nets are never ripped whole: only their vias / stubs in the way   # rip-up: cost per cell through other nets' tracks
ESC = 0.2         # extra keep-off round other nets' still-unrouted pads, so tracks leave room for their escapes

# net classes (as route_main.py)
CLASSES = [("Battery", r"/BAT_.*|/VBAT_P|/VBAT_SW|/BAT_F|/FS_D", 0.6, (0.6, 0.3)),
           ("Local", r"/SW33[AB]|/SW5", 0.3, (0.5, 0.25)),
           ("Rail3V3", r"/3V3", 0.4, (0.6, 0.3)),
           ("Power", r"/VBUS|/5V|/SERVO_5V|/M\d_[AB]|/KICK_HV|/KICK_BOOST|/KSW|/SOL_N|/BUZ_N|/VSYS|/GND", 0.4, (0.6, 0.3)),
           ("USB", r"/USB_D[PN]", 0.2, (0.45, 0.2)),
           ("Camera", r"/CAM_.*", 0.15, (0.45, 0.2))]


def net_class(net):
    for name, pat, w, via in CLASSES:
        if re.fullmatch(pat, net): return name, w, via
    return "Default", 0.2, (0.45, 0.2)


def K(X, Y):                                   # robot -> KiCad mm
    return (100 + X, 100 - Y)


# the plan's In2 signal areas (robot coords; draw_routing_plan.py IN2_SIGNALS)
IN2_AREAS_V1 = [[(-7.5, 31.5), (17.5, 31.5), (17.5, 6.5), (-7.5, 6.5)],
             [(0.5, 6.5), (5, 6.5), (6.5, -24), (2, -24)],
             [(17.5, 16), (22.5, 16), (22.5, -11), (16, -25), (11, -35), (8, -33), (16, -12), (17.5, 6.5)],
             [(-7.5, 6.6), (-3.5, 6.6), (-3.5, -10.0), (-7.5, -10.0)]]   # added: U6's SW corner down past U8 / U9's input pins


class Board:
    def __init__(self, copper_json=R + "copper.json", rippable=False):
        # rippable: the board's existing tracks / vias may be ripped up and re-routed too (save() then holds them all)
        cu = json.load(open(copper_json))
        self.cu = cu
        xs = [e["cx"] - e["r"] for e in cu["edge"]] + [e["cx"] + e["r"] for e in cu["edge"]]
        self.X0, self.Y0 = 57.0, 57.0
        self.N = int(88 / RES)
        N = self.N
        self.nets = {}
        self.grid = {l: np.full((N, N), -1, np.int32) for l in LAYERS}
        self.xs = self.X0 + np.arange(N) * RES
        self.ys = self.Y0 + np.arange(N) * RES
        if not rippable:
            for t in cu["tracks"]: self.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
            for v in cu["vias"]: self.add_via(v["x"], v["y"], v["d"], v["net"])
        self.pads = cu["pads"]
        padmask = np.zeros((N, N), bool)
        self.padnet = {l: np.full((N, N), -1, np.int32) for l in ("F", "B")}
        for p in self.pads:
            if len(p["poly"]) < 3: continue
            nid = self.nid(p["net"]) if p["net"] and not p["net"].startswith("unconnected") else -2
            box = self.window(*self.bbox(p["poly"]), 0.1)
            for l in p["layers"]:
                self.paint(l, self.polygon(p["poly"]), box, nid)
            i0, j0, i1, j1 = box
            Xw, Yw = np.meshgrid(self.xs[i0:i1], self.ys[j0:j1], indexing="ij")
            m = self.polygon(p["poly"])(Xw, Yw)
            padmask[i0:i1, j0:j1] |= m
            for l in p["layers"]:
                if l in self.padnet: self.padnet[l][i0:i1, j0:j1][m] = nid
        X, Y = np.meshgrid(self.xs, self.ys, indexing="ij")
        inside = np.ones((N, N), bool)
        for e in cu["edge"]:
            d2 = (X - e["cx"]) ** 2 + (Y - e["cy"]) ** 2
            inside &= (d2 <= e["r"] ** 2) if e["r"] > 30 else (d2 >= e["r"] ** 2)
        self.edge_dist = distance_transform_edt(inside) * RES
        self.pad_dist = distance_transform_edt(~padmask) * RES
        holes = np.zeros((N, N), bool)
        for h in cu["holes"]:
            if h.get("pth"): continue                    # plated: its pad copper is the obstacle
            i0, j0, i1, j1 = self.window(h["x"], h["y"], h["x"], h["y"], h["d"])
            Xw, Yw = np.meshgrid(self.xs[i0:i1], self.ys[j0:j1], indexing="ij")
            holes[i0:i1, j0:j1] |= (Xw - h["x"]) ** 2 + (Yw - h["y"]) ** 2 <= (h["d"] / 2) ** 2
        self.hole_dist = distance_transform_edt(~holes) * RES
        self.island = np.zeros((N, N), bool)              # In4 VSYS islands (plan_v2.py -> _route/vsys_islands.json)
        for poly in json.load(open(R + "vsys_islands.json")):
            pts = [K(*q) for q in poly]
            self.island |= Path(pts).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(N, N)
        self.out_tracks, self.out_vias = [], []
        self.necked = []
        routed = {self.nets[t["net"]] for t in cu["tracks"]} | {self.nets[v["net"]] for v in cu["vias"]}
        self.pending = np.array(sorted(set(range(len(self.nets))) - routed), np.int32)   # nets whose pads still need escapes
        self.tree = {}                                   # net -> set of (i, j, layer) cells joined so far
        self.noisy_ids = np.array([self.nid(n) for n in NOISY], np.int32)
        self.sensitive_ids = np.array([self.nid(n) for n in SENSITIVE], np.int32)
        self.hard = {l: self.grid[l].copy() for l in LAYERS}    # pads + copper that was on the board before this run
        if rippable:
            for t in cu["tracks"]:
                self.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"]); self.out_tracks.append(dict(t))
            for v in cu["vias"]:
                self.add_via(v["x"], v["y"], v["d"], v["net"]); self.out_vias.append(dict(v, drill=v.get("drill", net_class(v["net"])[2][1])))
        self.lanes, self.rips = {}, {}
        self.extra, self.on_plane = {}, set()
        self.failed, self.dropped, self.replane = set(), set(), set()         # nets with open connections; pads given their plane via            # fan-out stubs per pad; pads already tied to their plane

    # ---- painting
    def nid(self, net):
        if net not in self.nets: self.nets[net] = len(self.nets)
        return self.nets[net]

    def ij(self, x, y):
        return int(round((x - self.X0) / RES)), int(round((y - self.Y0) / RES))

    def xy(self, i, j):
        return self.X0 + i * RES, self.Y0 + j * RES

    @staticmethod
    def bbox(pts):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def window(self, x0, y0, x1, y1, pad=0.0):
        i0, j0 = self.ij(min(x0, x1) - pad, min(y0, y1) - pad); i1, j1 = self.ij(max(x0, x1) + pad, max(y0, y1) + pad)
        return max(i0, 0), max(j0, 0), min(i1 + 1, self.N), min(j1 + 1, self.N)

    def paint(self, l, fn, box, nid, cells=None):
        i0, j0, i1, j1 = box
        if i1 <= i0 or j1 <= j0: return
        Xw, Yw = np.meshgrid(self.xs[i0:i1], self.ys[j0:j1], indexing="ij")
        m = fn(Xw, Yw); g = self.grid[l][i0:i1, j0:j1]
        g[m & (g == -1)] = nid
        g[m & (g != -1) & (g != nid)] = -2
        if cells is not None:
            ii, jj = np.nonzero(m)
            cells.update((i0 + a, j0 + b, l) for a, b in zip(ii, jj))

    @staticmethod
    def capsule(x0, y0, x1, y1, r):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy or 1e-12
        def f(X, Y):
            t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
            return (X - x0 - t * dx) ** 2 + (Y - y0 - t * dy) ** 2 <= r * r
        return f

    @staticmethod
    def disc(x, y, r):
        return lambda X, Y: (X - x) ** 2 + (Y - y) ** 2 <= r * r

    @staticmethod
    def polygon(pts):
        p = Path(pts)
        return lambda X, Y: p.contains_points(np.c_[X.ravel(), Y.ravel()], radius=1e-6).reshape(X.shape)

    def add_track(self, l, x0, y0, x1, y1, w, net, tree=None):
        self.paint(l, self.capsule(x0, y0, x1, y1, w / 2), self.window(x0, y0, x1, y1, w), self.nid(net), tree)

    def add_via(self, x, y, d, net, tree=None):
        for l in LAYERS: self.paint(l, self.disc(x, y, d / 2), self.window(x, y, x, y, d), self.nid(net), tree)

    # ---- pads
    def pads_of(self, net):
        return [p for p in self.pads if p["net"] == net and len(p["poly"]) >= 3]

    def pad_cells(self, p):
        i0, j0, i1, j1 = self.window(*self.bbox(p["poly"]))
        Xw, Yw = np.meshgrid(self.xs[i0:i1], self.ys[j0:j1], indexing="ij")
        ii, jj = np.nonzero(self.polygon(p["poly"])(Xw, Yw))
        return {(i0 + a, j0 + b, l) for a, b in zip(ii, jj) for l in p["layers"]} | self.extra.get((p["ref"], p["num"]), set())

    def fanout(self, ref, ep="17", inward=("/GND",), lengths=(1.3, 0.5), wmax=0.3):
        """fixed escape stubs for a fine-pitch IC, laid before anything else: each signal pin gets a straight stub out
        along its pad (alternately long and short, so vias can stagger); the pins of `inward` nets get a stub into the
        exposed pad instead. The stubs count as the pad's own copper and are never ripped up."""
        pins = [p for p in self.pads if p["ref"] == ref and p["num"] != ep and len(p["poly"]) >= 3]
        cx = np.mean([p["x"] for p in pins]); cy = np.mean([p["y"] for p in pins])
        cols = {}
        for p in pins:
            x0, y0, x1, y1 = self.bbox(p["poly"])
            horiz = (x1 - x0) > (y1 - y0)
            side = (np.sign(p["x"] - cx), 0) if horiz else (0, np.sign(p["y"] - cy))
            cols.setdefault(side, []).append((p, (x1 - x0) / 2 if horiz else (y1 - y0) / 2))
        for (dx, dy), col in cols.items():
            col.sort(key=lambda q: q[0]["y"] if dx else q[0]["x"])
            for k, (p, half) in enumerate(col):
                net = p["net"]
                if not net or net.startswith("unconnected"): continue
                w = min(net_class(net)[1], wmax)
                cells = set()
                if net in inward:
                    a, b = p["x"], p["y"]; L = half + 0.9      # pad centre -> into the exposed pad
                    e = (a - dx * L, b - dy * L)
                    self.on_plane.add((ref, p["num"]))
                else:
                    a, b = p["x"], p["y"]; L = half + lengths[k % 2]
                    e = (a + dx * L, b + dy * L)
                l = p["layers"][0]
                same = lambda t: (t["net"] == net and t["l"] == l and abs(t["x0"] - a) < 1e-3 and abs(t["y0"] - b) < 1e-3
                                  and abs(t["x1"] - e[0]) < 1e-3 and abs(t["y1"] - e[1]) < 1e-3)
                self.out_tracks = [t for t in self.out_tracks if not same(t)]
                self.out_tracks.append({"net": net, "l": l, "x0": a, "y0": b, "x1": e[0], "y1": e[1], "w": w})
                self.add_track(l, a, b, e[0], e[1], w, net, cells)
                for (i, j, L2) in cells: self.hard[L2][i, j] = self.grid[L2][i, j]
                self.extra[(ref, p["num"])] = cells

    # ---- search
    def done_net(self, net):
        self.pending = self.pending[self.pending != self.nid(net)]

    def search(self, net, starts, goals, w, via, lane=None, plane=None, margin=5.0, via_cost=2.0, box=None, esc=ESC, soft=False, w_full=None):
        """starts / goals: sets of (i, j, layer) cells. plane: 'GND' or 'VSYS' -> goal = a cell where a plane via fits
        (or any existing via of the net). lane: {layer: bool mask over the board} preferred cells. Returns path or None."""
        nid = self.nid(net); vd = via[0]
        pts = [c for c in starts] + ([c for c in goals] if goals else [])
        ii = [c[0] for c in pts]; jj = [c[1] for c in pts]
        m = int(margin / RES)
        if box is None:
            i0, i1 = max(min(ii) - m, 0), min(max(ii) + m + 1, self.N); j0, j1 = max(min(jj) - m, 0), min(max(jj) + m + 1, self.N)
        else:
            i0, j0, i1, j1 = box
        pad = int(1.0 / RES)                              # obstacles just outside the box still count
        a0, b0, a1, b1 = max(i0 - pad, 0), max(j0 - pad, 0), min(i1 + pad, self.N), min(j1 + pad, self.N)
        ok, dist, busy = {}, {}, {}
        for l in LAYERS:
            g = self.grid[l][a0:a1, b0:b1]
            d = distance_transform_edt((g == -1) | (g == nid)) * RES
            if soft:                                      # soft: only the hard copper blocks; this run's other tracks cost
                gh = self.hard[l][a0:a1, b0:b1]
                busy[l] = d <= w / 2 + CLR
                d = distance_transform_edt((gh == -1) | (gh == nid)) * RES
            dist[l] = d
            ok[l] = ((d > w / 2 + CLR) & (self.edge_dist[a0:a1, b0:b1] > w / 2 + EDGE_CLR)
                     & (self.hole_dist[a0:a1, b0:b1] > w / 2 + HOLE_CLR))
        if GND_REF.fullmatch(net): ok["B"] &= ~self.island[a0:a1, b0:b1]
        if net_class(net)[0] in OUTER_ONLY or net in NOISY:     # power on the 35 um outer copper, not the 15 um inner
            for l in ("I2", "I3"): ok[l][:] = False
        if net in NOISY or net in SENSITIVE:              # keep switching nodes and sensitive lines apart (same layer)
            other = self.noisy_ids if net in SENSITIVE else self.sensitive_ids
            for l in LAYERS:
                g = self.grid[l][a0:a1, b0:b1]
                o = np.isin(g, other)
                if o.any(): ok[l] &= distance_transform_edt(~o) * RES > w / 2 + NOISE_GAP
        wide = None
        if w_full and w_full > w:                         # cells where the full width would fit (no neck needed)
            wide = {l: (dist[l] > w_full / 2 + CLR) & (self.edge_dist[a0:a1, b0:b1] > w_full / 2 + EDGE_CLR)
                    & (self.hole_dist[a0:a1, b0:b1] > w_full / 2 + HOLE_CLR) for l in LAYERS}
        via_ok = np.ones((a1 - a0, b1 - b0), bool)
        if esc > 0:
            for l in ("F", "B"):
                pn = self.padnet[l][a0:a1, b0:b1]
                pend = np.isin(pn, self.pending) & (pn != nid)
                if pend.any():
                    dp = distance_transform_edt(~pend) * RES
                    ok[l] &= dp > w / 2 + CLR + esc
                    via_ok &= dp > vd / 2 + CLR + esc
        for l in LAYERS: via_ok &= dist[l] > vd / 2 + CLR
        via_ok &= (self.edge_dist[a0:a1, b0:b1] > vd / 2 + EDGE_CLR) & (self.hole_dist[a0:a1, b0:b1] > vd / 2 + HOLE_CLR)
        # plan v2: vias are epoxy filled & capped, so one may sit inside a pad of its own net (via-in-pad); never touching another
        own_pad = (self.padnet["F"][a0:a1, b0:b1] == nid) | (self.padnet["B"][a0:a1, b0:b1] == nid)
        via_ok &= (self.pad_dist[a0:a1, b0:b1] > vd / 2 + 0.1) | own_pad
        plane_ok = None
        if plane == "VSYS":                               # the via must land in the VSYS pour, not in an In2 signal area
            plane_ok = via_ok & self.island[a0:a1, b0:b1]          # a VSYS via must land in an In4 VSYS island
        elif plane == "GND":
            plane_ok = via_ok
        lane_w = None
        if lane is not None:
            lane_w = {l: np.where(lane[l][a0:a1, b0:b1], 1.0, LANE_PENALTY) for l in LAYERS}
        inside = lambda i, j: i0 <= i < i1 and j0 <= j < j1
        okc = lambda c: inside(c[0], c[1]) and ok[c[2]][c[0] - a0, c[1] - b0]
        S = {c for c in starts if okc(c)}                 # only pad / tree cells a track of this width may end on
        G = {c for c in goals if okc(c)} if goals else set()
        if not S or (goals and not G): return None
        if G:
            gs = np.array(list(G))[:, :2][:: max(1, len(G) // 40)].astype(float)
            def h(i, j):                                  # octile distance to the nearest goal, weighted (faster, near-shortest)
                dx = np.abs(gs[:, 0] - i); dy = np.abs(gs[:, 1] - j)
                return float(np.min(dx + dy - 0.5858 * np.minimum(dx, dy))) * HEUR_W
        else:
            h = lambda i, j: 0.0
        openq, came, cost = [], {}, {}
        for c in S:
            cost[c] = 0.0; heapq.heappush(openq, (h(c[0], c[1]), c))
        steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        vc = via_cost / RES
        end, n = None, 0
        while openq and n < getattr(self, "node_cap", 2_000_000):
            f, c = heapq.heappop(openq); n += 1
            i, j, l = c
            if f > cost.get(c, 1e18) + h(i, j) + 1e-6: continue
            li, lj = i - a0, j - b0
            if G and c in G: end = c; break
            if plane_ok is not None and c not in S and (plane_ok[li, lj] or self._own_via(i, j, nid)):
                end = c; break
            base = cost[c]
            for di, dj, s in steps:
                ni, nj = i + di, j + dj
                if not inside(ni, nj): continue
                if not ok[l][ni - a0, nj - b0]: continue
                if l in DIR:
                    ax_, ay_ = DIR[l]
                    mult = DIAG_COST if (di and dj) else (1.0 if (di and ax_) or (dj and ay_) else ACROSS_COST)
                else:
                    mult = OUTER_COST
                mult *= lane_w[l][ni - a0, nj - b0] if lane_w else 1.0
                if soft and busy[l][ni - a0, nj - b0]: mult += RIP_COST
                if wide is not None and not wide[l][ni - a0, nj - b0]: mult *= NECK_COST
                g2 = base + s * mult
                nc = (ni, nj, l)
                if g2 < cost.get(nc, 1e18):
                    cost[nc] = g2; came[nc] = c; heapq.heappush(openq, (g2 + h(ni, nj), nc))
            if via_ok[li, lj]:
                for l2 in LAYERS:
                    if l2 == l or not ok[l2][li, lj]: continue
                    nc = (i, j, l2); g2 = base + vc
                    if g2 < cost.get(nc, 1e18):
                        cost[nc] = g2; came[nc] = c; heapq.heappush(openq, (g2 + h(i, j), nc))
        if end is None: return None
        path = [end]
        while path[-1] in came: path.append(came[path[-1]])
        path.reverse()
        return path, ok, (a0, b0), plane is not None and not (G and end in G), dist

    def blockers(self, net, path, w, vd):
        """nets of this run whose copper sits within clearance of a path (found by a soft search)"""
        nid = self.nid(net); out = set()
        r = int(math.ceil((max(w, vd) / 2 + CLR) / RES))
        for i, j, l in path:
            for L in LAYERS:
                g = self.grid[L][max(i - r, 0):i + r + 1, max(j - r, 0):j + r + 1]
                h = self.hard[L][max(i - r, 0):i + r + 1, max(j - r, 0):j + r + 1]
                out.update(int(v) for v in np.unique(g[(g != h) & (g >= 0) & (g != nid)]))
        inv = {v: k for k, v in self.nets.items()}
        return {inv[v] for v in out}

    def rip_near(self, net, path, w, vd):
        """remove only this plane net's tracks / vias within clearance of the path; its pads get re-dropped later"""
        r = max(w, vd) / 2 + CLR + 0.6
        pts = np.array([self.xy(i, j) for i, j, _ in path])
        def near(x, y): return np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y)) < r
        gt = [t for t in self.out_tracks if t["net"] == net and (near(t["x0"], t["y0"]) or near(t["x1"], t["y1"]))]
        gv = [v for v in self.out_vias if v["net"] == net and near(v["x"], v["y"])]
        if not gt and not gv: return
        ids = {id(t) for t in gt} | {id(v) for v in gv}
        self.out_tracks = [t for t in self.out_tracks if id(t) not in ids]
        self.out_vias = [v for v in self.out_vias if id(v) not in ids]
        xs = [t["x0"] for t in gt] + [t["x1"] for t in gt] + [v["x"] for v in gv]
        ys = [t["y0"] for t in gt] + [t["y1"] for t in gt] + [v["y"] for v in gv]
        self._rebuild(min(xs), min(ys), max(xs), max(ys))
        self.dropped = {k for k in self.dropped if not any(p["ref"] == k[0] and p["num"] == k[1] and math.hypot(p["x"] - x, p["y"] - y) < 3
                                                             for p in self.pads_of(net) for x, y in zip(xs, ys))}
        self.replane.add(net)

    def _rebuild(self, xa, ya, xb, yb):
        i0, j0, i1, j1 = self.window(xa, ya, xb, yb, 1.0)
        for l in LAYERS: self.grid[l][i0:i1, j0:j1] = self.hard[l][i0:i1, j0:j1]
        x0, y0 = self.xy(i0, j0); x1, y1 = self.xy(i1, j1)
        for t in self.out_tracks:
            if (max(t["x0"], t["x1"]) + 1 >= x0 and min(t["x0"], t["x1"]) - 1 <= x1
                    and max(t["y0"], t["y1"]) + 1 >= y0 and min(t["y0"], t["y1"]) - 1 <= y1):
                self.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
        for v in self.out_vias:
            if x0 - 1 <= v["x"] <= x1 + 1 and y0 - 1 <= v["y"] <= y1 + 1: self.add_via(v["x"], v["y"], v["d"], v["net"])

    def plane_connected(self, p, nid):
        """is this SMD pad already joined (on its layer) to a via of its net?"""
        l = p["layers"][0]
        i0, j0, i1, j1 = self.window(p["x"], p["y"], p["x"], p["y"], 6.0)
        m = self.grid[l][i0:i1, j0:j1] == nid
        lab, _ = label(m)
        pc = [(i - i0, j - j0) for i, j, L in self.pad_cells(p) if L == l and i0 <= i < i1 and j0 <= j < j1]
        ids = {lab[a, b] for a, b in pc} - {0}
        if not ids: return False
        via = np.ones_like(m)
        for L in LAYERS: via &= self.grid[L][i0:i1, j0:j1] == nid
        return bool(np.isin(lab[via], list(ids)).any())

    def rip(self, net):
        nid = self.nid(net)
        gone = [t for t in self.out_tracks if t["net"] == net]; gv = [v for v in self.out_vias if v["net"] == net]
        self.out_tracks = [t for t in self.out_tracks if t["net"] != net]; self.out_vias = [v for v in self.out_vias if v["net"] != net]
        xs = [t["x0"] for t in gone] + [t["x1"] for t in gone] + [v["x"] for v in gv]
        ys = [t["y0"] for t in gone] + [t["y1"] for t in gone] + [v["y"] for v in gv]
        self.tree[net] = set(); self.rips[net] = self.rips.get(net, 0) + 1
        if nid not in self.pending: self.pending = np.append(self.pending, nid)
        if not xs: return
        i0, j0, i1, j1 = self.window(min(xs), min(ys), max(xs), max(ys), 1.0)
        for l in LAYERS: self.grid[l][i0:i1, j0:j1] = self.hard[l][i0:i1, j0:j1]
        x0, y0 = self.xy(i0, j0); x1, y1 = self.xy(i1, j1)
        for t in self.out_tracks:
            if (max(t["x0"], t["x1"]) + 1 >= x0 and min(t["x0"], t["x1"]) - 1 <= x1
                    and max(t["y0"], t["y1"]) + 1 >= y0 and min(t["y0"], t["y1"]) - 1 <= y1):
                self.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
        for v in self.out_vias:
            if x0 - 1 <= v["x"] <= x1 + 1 and y0 - 1 <= v["y"] <= y1 + 1: self.add_via(v["x"], v["y"], v["d"], v["net"])

    def rip_for(self, net, pc, goals, w, via, lane, plane=None, margin=15.0):
        """soft-search past this run's other tracks and rip the nets in the way; returns them (empty: nothing done)"""
        r = self.search(net, pc, goals, w, via, lane, plane=plane, margin=margin, esc=0.0, soft=True,
                        via_cost=0.5 if plane else 2.0)
        if r is None: return set()
        bl = self.blockers(net, r[0], w, via[0])
        pl = bl & set(PLANES); bl -= pl
        if not (bl or pl) or bl & NO_RIP or any(self.rips.get(b, 0) >= MAX_RIPS for b in bl): return set()
        for b in bl: self.rip(b)
        for b in pl: self.rip_near(b, r[0], w, via[0])
        print(f"   ripped {sorted(bl)} + {sorted(pl)} vias/stubs for {net}")
        return bl | {"(plane)"} if pl and not bl else bl

    def _own_via(self, i, j, nid):
        return all(self.grid[l][i, j] == nid for l in LAYERS)

    # ---- commit
    def fit_width(self, l, x0, y0, x1, y1, dist, off, w, w_full, w_max):
        """widest track (0.05 mm steps) that fits along this piece: up to w_full where it clears, beyond (to w_max)
        only with SPARE mm to spare"""
        a0, b0 = off
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / RES) + 2)
        d = 1e9
        for t in np.linspace(0, 1, n):
            i, j = self.ij(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            li, lj = i - a0, j - b0
            if not (0 <= li < dist[l].shape[0] and 0 <= lj < dist[l].shape[1]): return w
            d = min(d, dist[l][li, lj], self.edge_dist[i, j] - (EDGE_CLR - CLR), self.hole_dist[i, j] - (HOLE_CLR - CLR))
        best = w
        for wt in np.arange(round(w, 2) + 0.05, w_max + 1e-6, 0.05):
            need = wt / 2 + CLR + (SPARE if wt > w_full + 1e-6 else 0.0)
            if d > need: best = round(float(wt), 2)
        return best

    def commit(self, net, path, ok, off, w, via, plane_via, tree, dist=None, w_full=None):
        a0, b0 = off
        w_full = w_full or w
        w_max = max(w_full, W_MAX.get(net_class(net)[0], w_full))
        runs, vias, run = [], [], [path[0]]
        for a, b in zip(path, path[1:]):
            if a[2] != b[2]:
                runs.append(run); vias.append((a[0], a[1])); run = [b]
            else:
                run.append(b)
        runs.append(run)
        if plane_via and not self._own_via(path[-1][0], path[-1][1], self.nid(net)):
            vias.append((path[-1][0], path[-1][1]))
        for run in runs:
            if len(run) < 2: continue
            l = run[0][2]
            pts = self.pull(run, ok[l], off)
            pieces = []
            for (i, j), (k, m) in zip(pts, pts[1:]):
                x0, y0 = self.xy(i, j); x1, y1 = self.xy(k, m)
                if dist is None or w_max <= w:
                    pieces.append((x0, y0, x1, y1, w)); continue
                n = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / PIECE)))
                for q in range(n):
                    xa, ya = x0 + (x1 - x0) * q / n, y0 + (y1 - y0) * q / n
                    xb, yb = x0 + (x1 - x0) * (q + 1) / n, y0 + (y1 - y0) * (q + 1) / n
                    wq = self.fit_width(l, xa, ya, xb, yb, dist, off, w, w_full, w_max)
                    if pieces and pieces[-1][4] == wq and pieces[-1][2:4] == (xa, ya) and q > 0:
                        pieces[-1] = (pieces[-1][0], pieces[-1][1], xb, yb, wq)       # same width, same line: merge
                    else:
                        pieces.append((xa, ya, xb, yb, wq))
            for x0, y0, x1, y1, wq in pieces:
                self.out_tracks.append({"net": net, "l": l, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": wq})
                self.add_track(l, x0, y0, x1, y1, wq, net, tree)
        for i, j in vias:
            x, y = self.xy(i, j)
            self.out_vias.append({"net": net, "x": x, "y": y, "d": via[0], "drill": via[1]})
            self.add_via(x, y, via[0], net, tree)
            if GND_REF.fullmatch(net): self.return_via(x, y)

    def stitch_edge(self, spacing=5.0, inset=1.1):
        """GND stitching vias every `spacing` mm round the board edge (and the ball cut-out), `inset` mm in"""
        big = max(self.cu["edge"], key=lambda e: e["r"]); cut = min(self.cu["edge"], key=lambda e: e["r"])
        pts = []
        r = big["r"] - inset; n = int(2 * math.pi * r / spacing)
        for k in range(n):
            a = 2 * math.pi * k / n; x, y = big["cx"] + r * math.cos(a), big["cy"] + r * math.sin(a)
            if math.hypot(x - cut["cx"], y - cut["cy"]) > cut["r"] + inset: pts.append((x, y))
        r = cut["r"] + inset; n = int(2 * math.pi * r / spacing)
        for k in range(n):
            a = 2 * math.pi * k / n; x, y = cut["cx"] + r * math.cos(a), cut["cy"] + r * math.sin(a)
            if math.hypot(x - big["cx"], y - big["cy"]) < big["r"] - inset: pts.append((x, y))
        before = len(self.out_vias)
        for x, y in pts: self.return_via(x, y, rmax=1.5)
        return len(self.out_vias) - before, len(pts)

    def return_via(self, x, y, rmax=1.0):
        """a GND via within rmax mm of a USB / camera via, so the return current changes layer with the signal"""
        nid = self.nid("/GND"); vd, dr = 0.45, 0.2
        i0, j0, i1, j1 = self.window(x, y, x, y, rmax + 1.5)
        ok = np.ones((i1 - i0, j1 - j0), bool)
        for l in LAYERS:
            g = self.grid[l][i0:i1, j0:j1]
            ok &= distance_transform_edt((g == -1) | (g == nid)) * RES > vd / 2 + CLR
        ok &= (self.edge_dist[i0:i1, j0:j1] > vd / 2 + EDGE_CLR) & (self.pad_dist[i0:i1, j0:j1] > vd / 2 + 0.1)
        ok &= self.hole_dist[i0:i1, j0:j1] > vd / 2 + HOLE_CLR
        best = None
        for a, b in zip(*np.nonzero(ok)):
            px, py = self.xy(i0 + a, j0 + b); d = math.hypot(px - x, py - y)
            if d <= rmax and (best is None or d < best[0]): best = (d, px, py)
        if best:
            self.out_vias.append({"net": "/GND", "x": best[1], "y": best[2], "d": vd, "drill": dr})
            self.add_via(best[1], best[2], vd, "/GND")

    def pull(self, run, okl, off):
        """45-degree string-pull: from each point, the farthest later point reachable by a straight 0 / 45 / 90 degree
        piece, or by two (a 45-degree run and a straight one) through a free corner; then collinear pieces merged"""
        a0, b0 = off
        pts = [(int(c[0]), int(c[1])) for c in run]
        sgn = lambda v: int(v > 0) - int(v < 0)
        out, k, n = [pts[0]], 0, len(pts)
        while k < n - 1:
            step = max(1, (n - k) // 80)
            cand = list(range(n - 1, k + 1, -step))
            got = None
            for m in cand:
                p, q = pts[k], pts[m]
                dx, dy = q[0] - p[0], q[1] - p[1]
                if dx == 0 or dy == 0 or abs(dx) == abs(dy):
                    if self._los(p, q, okl, a0, b0): got = (m, [q]); break
                    continue
                d = min(abs(dx), abs(dy))
                for c in ((p[0] + sgn(dx) * d, p[1] + sgn(dy) * d), (q[0] - sgn(dx) * d, q[1] - sgn(dy) * d)):
                    if self._los(p, c, okl, a0, b0) and self._los(c, q, okl, a0, b0): got = (m, [c, q]); break
                if got: break
            if got is None: got = (k + 1, [pts[k + 1]])
            out += got[1]; k = got[0]
        # merge collinear pieces
        merged = [out[0]]
        for i in range(1, len(out)):
            if len(merged) >= 2:
                (x0, y0), (x1, y1), (x2, y2) = merged[-2], merged[-1], out[i]
                if (x1 - x0) * (y2 - y1) == (y1 - y0) * (x2 - x1) and (x1 - x0) * (x2 - x1) + (y1 - y0) * (y2 - y1) >= 0:
                    merged[-1] = out[i]; continue
            if out[i] != merged[-1]: merged.append(out[i])
        return merged

    @staticmethod
    def _los(p, q, okl, a0, b0):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) * 2 + 1
        for t in np.linspace(0, 1, n):
            i = int(round(p[0] + (q[0] - p[0]) * t)) - a0; j = int(round(p[1] + (q[1] - p[1]) * t)) - b0
            if not okl[i, j]: return False
        return True

    # ---- whole nets
    def route_net(self, net, lane=None, margin=5.0, order_from=None, depth=0):
        self.lanes[net] = lane
        cls, w, via = net_class(net)
        pads = self.pads_of(net)
        if len(pads) < 2: return 0, 0
        tree = self.tree.setdefault(net, set())
        if not tree:
            first = pads[0] if order_from is None else min(pads, key=lambda p: math.dist((p["x"], p["y"]), order_from))
            tree |= self.pad_cells(first)
        left = [p for p in pads if not (self.pad_cells(p) & tree)]
        done = fail = 0
        ripped = set()
        while left:
            tx = np.mean([c[0] for c in tree]); ty = np.mean([c[1] for c in tree])
            # nearest pad to the tree (by centre distance to the nearest tree cell, sampled)
            sample = list(tree)[:: max(1, len(tree) // 400)]
            def dpad(p):
                pi, pj = self.ij(p["x"], p["y"])
                return min(math.hypot(pi - c[0], pj - c[1]) for c in sample)
            p = min(left, key=dpad)
            left.remove(p)
            pc = self.pad_cells(p)
            pi, pj = self.ij(p["x"], p["y"])
            tl = list(tree); dd = np.hypot([c[0] - pi for c in tl], [c[1] - pj for c in tl])
            near = {c for c, d in zip(tl, dd) if d <= dd.min() + 4.0 / RES}   # tree cells within 4 mm of the nearest
            r, wu = None, w
            widths = [w] + [x for x in (0.25, 0.2, 0.15) if x < w]   # neck down only where the full width cannot leave a pad
            for wu, e in [(x, ESC) for x in widths] + [(x, 0.0) for x in widths]:   # last resort: ignore the escape keep-off
                r = self.search(net, pc, near, wu, via, lane, margin=margin, esc=e, w_full=w)
                if r is None: r = self.search(net, pc, near, wu, via, lane, margin=margin * 3, esc=e, w_full=w)
                if r is not None: break
            if r is None and depth < 2:                    # rip-up: lift the nets in the way, route this, re-route them
                for wu in widths:
                    bl = self.rip_for(net, pc, near, wu, via, lane)
                    if bl:
                        ripped |= bl
                        r = self.search(net, pc, near, wu, via, lane, margin=margin * 3, esc=0.0, w_full=w)
                        break
            if r is None:
                fail += 1; self.failed.add(net); print(f"   FAILED {net}: {p['ref']}.{p['num']}"); continue
            if wu < w: print(f"   tapered {net}: {p['ref']}.{p['num']} down to {wu} mm where tight"); self.necked.append((net, p["ref"], p["num"], wu))
            path, ok, off, _, dist = r
            self.commit(net, path, ok, off, wu, via, False, tree, dist, w)
            tree |= pc; done += 1
        self.done_net(net)
        for b in sorted(ripped - {"(plane)"}):
            d2, f2 = self.route_net(b, self.lanes.get(b), depth=depth + 1)
            print(f"   re-routed {b}: joined {d2} failed {f2}"); fail += f2
        if depth == 0:
            for pn in sorted(self.replane):
                self.replane.discard(pn); d2, f2 = self.plane_drops(pn, PLANES[pn])
                print(f"   re-dropped {pn}: {d2} vias, failed {f2}")
        return done, fail

    def plane_drops(self, net, plane, skip_refs=()):
        cls, w, via = net_class(net)
        w = min(w, 0.3)
        done = fail = 0
        for p in self.pads_of(net):
            if p["ref"] in skip_refs or len(p["layers"]) != 1: continue      # through-hole pads reach the planes already
            if (p["ref"], p["num"]) in self.on_plane | self.dropped: continue    # tied into its exposed pad, or done already
            if self.plane_connected(p, self.nid(net)): self.dropped.add((p["ref"], p["num"])); continue
            pc = self.pad_cells(p)
            r = self.search(net, pc, set(), w, via, None, plane=plane, margin=2.5, via_cost=0.5)
            if r is None: r = self.search(net, pc, set(), w, via, None, plane=plane, margin=5.0, via_cost=0.5)
            if r is None:                                  # no room for a via: join the nearest copper of the net instead
                nid = self.nid(net); pi, pj = self.ij(p["x"], p["y"]); m = int(6 / RES)
                i0, j0 = max(pi - m, 0), max(pj - m, 0)
                near = {(i0 + a, j0 + c, l) for l in LAYERS
                        for a, c in zip(*np.nonzero(self.grid[l][i0:pi + m, j0:pj + m] == nid))} - pc
                r = self.search(net, pc, near, w, via, None, margin=3.0) if near else None
                if r is None:
                    bl = self.rip_for(net, pc, set(), w, via, None, plane=plane, margin=3.0)
                    r2 = None
                    if bl:
                        r2 = self.search(net, pc, set(), w, via, None, plane=plane, margin=3.0, via_cost=0.5)
                        if r2 is not None:
                            self.commit(net, r2[0], r2[1], r2[2], w, via, True, None); done += 1; self.dropped.add((p["ref"], p["num"]))
                        for b in sorted(bl):
                            d2, f2 = self.route_net(b, self.lanes.get(b), depth=1)
                            print(f"   re-routed {b}: joined {d2} failed {f2}"); fail += f2
                    if r2 is not None: continue
                    fail += 1; self.failed.add(net); print(f"   FAILED plane via {net}: {p['ref']}.{p['num']}"); continue
                print(f"   {net}: {p['ref']}.{p['num']} joined to nearby {net} copper (no room for a via)")
                self.commit(net, r[0], r[1], r[2], w, via, False, None); done += 1; self.dropped.add((p["ref"], p["num"])); continue
            path, ok, off, pv, dist = r
            self.commit(net, path, ok, off, w, via, True, None, dist)
            done += 1; self.dropped.add((p["ref"], p["num"]))
        self.done_net(net)
        return done, fail

    def lane_mask(self, lanes):
        """lanes: [(layer, robot polyline, width)] -> {layer: mask}"""
        N = self.N
        X, Y = np.meshgrid(self.xs, self.ys, indexing="ij")
        out = {l: np.zeros((N, N), bool) for l in LAYERS}
        for l, pts, wd in lanes:
            kp = [K(*q) for q in pts]
            for (x0, y0), (x1, y1) in zip(kp, kp[1:]):
                i0, j0, i1, j1 = self.window(x0, y0, x1, y1, wd)
                Xw, Yw = X[i0:i1, j0:j1], Y[i0:i1, j0:j1]
                out[l][i0:i1, j0:j1] |= self.capsule(x0, y0, x1, y1, wd / 2)(Xw, Yw)
        return out

    def save(self, path):
        json.dump({"tracks": self.out_tracks, "vias": self.out_vias}, open(path, "w"))


# ---- completing nets after a local re-placement (power switch v3, 2026-10-25)
def _components(self, net):
    """the net's copper split into connected pieces (layers stacked; a via / through-hole pad joins them)"""
    from scipy.ndimage import label
    nid = self.nid(net)
    stack = np.stack([self.grid[l] == nid for l in LAYERS])
    # layers join ONLY where a via or a through-hole pad of the net is (2026-10-26: stacking every overlap joined an In3
    # track end to an In2 one with no via between them, so open nets were reported done)
    joint = np.zeros(stack.shape[1:], bool)
    for v in list(self.cu.get("vias", [])) + list(self.out_vias):
        if v["net"] != net: continue
        i, j = self.ij(v["x"], v["y"]); r = max(1, int(v["d"] / 2 / RES))
        joint[max(i - r, 0):i + r + 1, max(j - r, 0):j + r + 1] = True
    for p in self.pads:
        if p["net"] == net and len(p["layers"]) > 1:
            for i, j, l in self.pad_cells(p): joint[i, j] = True
    st2 = np.zeros((3, 3, 3), bool); st2[1, 1, :] = st2[1, :, 1] = True           # in-plane only
    lab, n = label(stack, structure=st2)
    parent = list(range(n + 1))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    ii, jj = np.nonzero(joint & (stack.sum(axis=0) > 1))
    for i, j in zip(ii, jj):
        ls = [int(lab[k, i, j]) for k in range(len(LAYERS)) if lab[k, i, j]]
        for a in ls[1:]: parent[find(a)] = find(ls[0])
    roots = {}
    for a in range(1, n + 1): roots.setdefault(find(a), len(roots) + 1)
    remap = np.zeros(n + 1, np.int32)
    for a in range(1, n + 1): remap[a] = roots[find(a)]
    return remap[lab], len(roots)


def complete_net(self, net, lane=None, margin=4.0):
    """join every piece of the net to its biggest piece (the one with most pads), nearest piece first"""
    cls, w, via = net_class(net)
    joined = failed = 0
    for _ in range(40):
        lab, n = self._components(net)
        if n <= 1: break
        pads = self.pads_of(net)
        count = {}
        for p in pads:
            i, j = self.ij(p["x"], p["y"])
            for k, l in enumerate(LAYERS):
                c = lab[k, i, j]
                if c: count[c] = count.get(c, 0) + 1; break
        if not count: break
        main = max(count, key=count.get)
        mk, mi, mj = np.nonzero(lab == main)
        others = [c for c in range(1, n + 1) if c != main and (lab == c).sum() > 4]
        if not others: break
        # the piece nearest the main one
        def dist_to_main(c):
            ck, ci, cj = np.nonzero(lab == c); s = slice(None, None, max(1, len(ci) // 60))
            return min(np.min(np.hypot(mi[::max(1, len(mi) // 400)] - a, mj[::max(1, len(mj) // 400)] - b)) for a, b in zip(ci[s], cj[s]))
        c = min(others, key=dist_to_main)
        ck, ci, cj = np.nonzero(lab == c)
        starts = {(int(a), int(b), LAYERS[k]) for k, a, b in zip(ck, ci, cj)}
        cx, cy = ci.mean(), cj.mean()
        dd = np.hypot(mi - cx, mj - cy); near = dd <= dd.min() + 4.0 / RES
        goals = {(int(a), int(b), LAYERS[k]) for k, a, b in zip(mk[near], mi[near], mj[near])}
        r = None
        for wu in [w] + [x for x in (0.25, 0.2, 0.15) if x < w]:
            r = self.search(net, starts, goals, wu, via, lane, margin=margin, esc=0.0, w_full=w)
            if r is None: r = self.search(net, starts, goals, wu, via, lane, margin=margin * 3, esc=0.0, w_full=w)
            if r: break
        if r is None:
            failed += 1; print(f"   FAILED to join a piece of {net} at ({self.xy(int(cx), int(cy))[0]:.1f}, {self.xy(int(cx), int(cy))[1]:.1f})")
            # mark it so the loop does not retry it: paint nothing, just stop after repeated failures
            if failed > 3: break
            continue
        self.commit(net, r[0], r[1], r[2], wu, via, False, None, r[4], w); joined += 1
    return joined, failed


Board._components = _components
Board.complete_net = complete_net
