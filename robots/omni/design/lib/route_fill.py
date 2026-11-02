# Finishing the main board's routing 2/3: a small grid router (A*, 0.05 mm, layers F.Cu / In2.Cu / B.Cu, vias) for the links
# Freerouting left open, every existing track / via / pad fixed as an obstacle. Each link ends either on another copper item of
# its net or, for GND / VSYS, on a via down to its plane ("plane" goal). Reads _route/copper.json (route_fill_export.py),
# writes _route/fill.json for route_fill_apply.py.
#   C:/Python312/python.exe design/lib/route_fill.py
import json, math, heapq
import numpy as np
from scipy.ndimage import distance_transform_edt
from matplotlib.path import Path

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/_route/"
cu = json.load(open(R + "copper.json"))
RES, X0, Y0, N = 0.05, 58.0, 58.0, 1700
LAYERS = ["F", "I", "B"]
CLR, EDGE_CLR, HOLE_CLR = 0.19, 0.37, 0.29           # 0.15 rule + 0.035 (the 0.05 grid's worst case) + 0.005
VIA = {"default": (0.5, 0.25), "Camera": (0.45, 0.2), "USB": (0.45, 0.2)}

nets = sorted({t["net"] for t in cu["tracks"]} | {v["net"] for v in cu["vias"]} | {p["net"] for p in cu["pads"]})
NID = {n: i for i, n in enumerate(nets)}
grid = {l: np.full((N, N), -1, np.int32) for l in LAYERS}       # net id per cell (-1 free, -2 not-ours-ever)
xs = X0 + np.arange(N) * RES


def ij(x, y):
    return int(round((x - X0) / RES)), int(round((y - Y0) / RES))


def window(x0, y0, x1, y1, pad=0.0):
    i0, j0 = ij(min(x0, x1) - pad, min(y0, y1) - pad); i1, j1 = ij(max(x0, x1) + pad, max(y0, y1) + pad)
    return max(i0, 0), max(j0, 0), min(i1 + 1, N), min(j1 + 1, N)


def paint(l, mask_fn, box, nid):
    i0, j0, i1, j1 = box
    if i1 <= i0 or j1 <= j0: return
    X, Y = np.meshgrid(xs[i0:i1], Y0 + np.arange(j0, j1) * RES, indexing="ij")
    m = mask_fn(X, Y); g = grid[l][i0:i1, j0:j1]
    g[m & (g == -1)] = nid
    g[m & (g != -1) & (g != nid)] = -2                          # two nets in one cell: an obstacle for everyone


def capsule(x0, y0, x1, y1, r):
    dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy or 1e-12
    def f(X, Y):
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        return (X - x0 - t * dx) ** 2 + (Y - y0 - t * dy) ** 2 <= r * r
    return f


def disc(x, y, r):
    return lambda X, Y: (X - x) ** 2 + (Y - y) ** 2 <= r * r


def polygon(pts):
    p = Path(pts)
    return lambda X, Y: p.contains_points(np.c_[X.ravel(), Y.ravel()], radius=1e-6).reshape(X.shape)


def add_track(l, x0, y0, x1, y1, w, net):
    paint(l, capsule(x0, y0, x1, y1, w / 2), window(x0, y0, x1, y1, w), NID.setdefault(net, len(NID)))


def add_via(x, y, d, net):
    for l in LAYERS: paint(l, disc(x, y, d / 2), window(x, y, x, y, d), NID.setdefault(net, len(NID)))


for t in cu["tracks"]: add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
for v in cu["vias"]: add_via(v["x"], v["y"], v["d"], v["net"])
for p in cu["pads"]:
    if len(p["poly"]) < 3: continue
    xsp = [q[0] for q in p["poly"]]; ysp = [q[1] for q in p["poly"]]
    nid = NID[p["net"]] if p["net"] else -2                    # unconnected pads: obstacles for every net
    for l in p["layers"]:
        paint(l, polygon(p["poly"]), window(min(xsp), min(ysp), max(xsp), max(ysp), 0.1), nid if nid >= 0 else -2)
holes = np.zeros((N, N), bool)
for h in cu["holes"]:
    i0, j0, i1, j1 = window(h["x"], h["y"], h["x"], h["y"], h["d"])
    X, Y = np.meshgrid(xs[i0:i1], Y0 + np.arange(j0, j1) * RES, indexing="ij")
    holes[i0:i1, j0:j1] |= (X - h["x"]) ** 2 + (Y - h["y"]) ** 2 <= (h["d"] / 2) ** 2
# the board: inside the main circle, outside the front cut-out
X, Y = np.meshgrid(xs, Y0 + np.arange(N) * RES, indexing="ij")
inside = np.ones((N, N), bool)
for e in cu["edge"]:
    d2 = (X - e["cx"]) ** 2 + (Y - e["cy"]) ** 2
    inside &= (d2 <= e["r"] ** 2) if e["r"] > 30 else (d2 >= e["r"] ** 2)
edge_dist = distance_transform_edt(inside) * RES
hole_dist = distance_transform_edt(~holes) * RES


def clearance_maps(net):
    nid = NID[net]; out = {}
    for l in LAYERS:
        g = grid[l]; blocked = (g != -1) & (g != nid)
        out[l] = distance_transform_edt(~blocked) * RES
    return out


def route(net, start, goal, w, cls="default", in2_cost=1.6, via_cost=2.0):
    """start: (layer list, mask of own-net cells or point); goal: same, or ('plane',). Returns [(layer, [(x, y)...])], vias"""
    dist = clearance_maps(net); vd, vdrill = VIA.get(cls, VIA["default"])
    ok = {l: (dist[l] > w / 2 + CLR) & (edge_dist > w / 2 + EDGE_CLR) & (hole_dist > w / 2 + HOLE_CLR) for l in LAYERS}
    via_ok = np.ones((N, N), bool)
    for l in LAYERS: via_ok &= dist[l] > vd / 2 + CLR
    via_ok &= (edge_dist > vd / 2 + EDGE_CLR) & (hole_dist > vd / 2 + HOLE_CLR)
    nid = NID[net]
    def cells(spec):
        layers, pts = spec
        out = set()
        for l in layers:
            for (i, j) in pts: out.add((i, j, l))
        return out
    S = cells(start)
    G = None if goal[0] == "plane" else cells(goal)
    gi = None if G is None else (np.mean([c[0] for c in G]), np.mean([c[1] for c in G]))
    h = (lambda i, j: 0.0) if G is None else (lambda i, j: math.hypot(i - gi[0], j - gi[1]))
    openq, came, cost = [], {}, {}
    for c in S:
        cost[c] = 0.0; heapq.heappush(openq, (h(c[0], c[1]), c))
    steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    vc = via_cost / RES
    end = None; n = 0
    while openq and n < 3_000_000:
        f, c = heapq.heappop(openq); n += 1
        i, j, l = c
        if (G is not None and c in G) or (G is None and via_ok[i, j] and c not in S and n > 1):
            end = c; break
        base = cost[c]
        mult = in2_cost if l == "I" else 1.0
        for di, dj, s in steps:
            ni, nj = i + di, j + dj
            if not (0 <= ni < N and 0 <= nj < N): continue
            nc = (ni, nj, l)
            free = ok[l][ni, nj] or grid[l][ni, nj] == nid
            if not free: continue
            g2 = base + s * mult
            if g2 < cost.get(nc, 1e18):
                cost[nc] = g2; came[nc] = c; heapq.heappush(openq, (g2 + h(ni, nj), nc))
        if via_ok[i, j]:
            for l2 in LAYERS:
                if l2 == l: continue
                nc = (i, j, l2); g2 = base + vc
                if g2 < cost.get(nc, 1e18):
                    cost[nc] = g2; came[nc] = c; heapq.heappush(openq, (g2 + h(i, j), nc))
    if end is None:
        return None
    path = [end]
    while path[-1] in came: path.append(came[path[-1]])
    path.reverse()
    segs, vias, run = [], [], [path[0]]
    for a, b in zip(path, path[1:]):
        if a[2] != b[2]:
            segs.append((a[2], run)); vias.append((a[0], a[1])); run = [b]
        else:
            run.append(b)
    segs.append((run[0][2], run))
    if G is None: vias.append((end[0], end[1]))                 # the plane via
    def simplify(run):
        pts = [(X0 + c[0] * RES, Y0 + c[1] * RES) for c in run]
        out = [pts[0]]
        for k in range(1, len(pts) - 1):
            ax, ay = out[-1]; bx, by = pts[k]; cx, cy = pts[k + 1]
            if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) > 1e-9: out.append(pts[k])
        out.append(pts[-1]); return out
    res = [(l, simplify(r)) for l, r in segs if len(r) > 1]
    return res, [(X0 + i * RES, Y0 + j * RES) for i, j in vias], (vd, vdrill)


def pad_spec(ref, num):
    p = next(p for p in cu["pads"] if p["ref"] == ref and p["num"] == num)
    xsp = [q[0] for q in p["poly"]]; ysp = [q[1] for q in p["poly"]]
    i0, j0, i1, j1 = window(min(xsp), min(ysp), max(xsp), max(ysp))
    m = polygon(p["poly"])
    Xw, Yw = np.meshgrid(xs[i0:i1], Y0 + np.arange(j0, j1) * RES, indexing="ij")
    ii, jj = np.nonzero(m(Xw, Yw))
    return p["layers"], [(i0 + a, j0 + b) for a, b in zip(ii, jj)]


def track_end_spec(net, x, y, toward):
    best = None
    for t in cu["tracks"]:
        if t["net"] != net: continue
        for ex, ey in ((t["x0"], t["y0"]), (t["x1"], t["y1"])):
            d = math.hypot(ex - x, ey - y) + 0.01 * math.hypot(ex - toward[0], ey - toward[1])
            if best is None or d < best[0]: best = (d, t["l"], ex, ey)
    _, l, ex, ey = best
    return [l], [ij(ex, ey)]


def via_spec(net, x, y):
    v = min((v for v in cu["vias"] if v["net"] == net), key=lambda v: math.hypot(v["x"] - x, v["y"] - y))
    return LAYERS, [ij(v["x"], v["y"])]


W = {"Camera": 0.15, "USB": 0.2, "default": 0.2, "Power": 0.4, "Rail3V3": 0.4}
pad_xy = lambda r, n: next((p["x"], p["y"]) for p in cu["pads"] if p["ref"] == r and p["num"] == n)
JOBS = [  # net, class, start, goal  (from the DRC's unconnected list after the Freerouting pass)
    ("/CAM_PCLK", "Camera", pad_spec("U6", "75"), pad_spec("R46", "2")),
    ("/CAM_XCLK", "Camera", pad_spec("U6", "78"), track_end_spec("/CAM_XCLK", 114.99, 114.5, pad_xy("U6", "78"))),
    ("/CAM_XCLK_J", "Camera", pad_spec("J6", "13"), pad_spec("R45", "2")),
    ("/CAM_HREF", "Camera", pad_spec("U6", "77"), pad_spec("J6", "9")),
    ("/CAM_D2", "Camera", pad_spec("U6", "67"), track_end_spec("/CAM_D2", 119.66, 102.23, pad_xy("U6", "67"))),
    ("/USB_DP", "USB", pad_spec("J1", "B6"), pad_spec("J1", "A6")),
    ("/USB_DP", "USB", pad_spec("J1", "A6"), track_end_spec("/USB_DP", 83.64, 104.45, pad_xy("J1", "A6"))),
    ("/USB_DN", "USB", pad_spec("J1", "A7"), pad_spec("J1", "B7")),
    ("/USB_DN", "USB", pad_spec("J1", "B7"), track_end_spec("/USB_DN", 82.56, 102.55, pad_xy("J1", "B7"))),
    ("/CC1", "default", pad_spec("J1", "A5"), pad_spec("R8", "1")),
    ("/CC2", "default", pad_spec("J1", "B5"), pad_spec("R9", "1")),
    ("/U9_VCP", "default", pad_spec("U9", "11"), via_spec("/U9_VCP", 82.76, 96.07)),
    ("/5V", "Power", pad_spec("U5", "6"), track_end_spec("/5V", 86.86, 128.11, pad_xy("U5", "6"))),
    # plane drops: a short stub from the item to a via on its plane (VSYS on In2, GND on In1)
    ("/VSYS", "Power", pad_spec("U9", "12"), ("plane",)),
    ("/VSYS", "Power", pad_spec("U8", "12"), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 81.56, 109.55, (81.56, 109.55)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 89.52, 124.09, (89.52, 124.09)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 91.38, 129.63, (91.38, 129.63)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 92.14, 124.54, (92.14, 124.54)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 93.04, 100.18, (93.04, 100.18)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 109.56, 121.76, (109.56, 121.76)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 115.21, 118.99, (115.21, 118.99)), ("plane",)),
    ("/VSYS", "Power", track_end_spec("/VSYS", 122.0, 123.45, (122.0, 123.45)), ("plane",)),
    # (the two loose GND track ends near C40 are left to the GND stitching: a stub from there broke C40's clearance)
]
result = {"tracks": [], "vias": [], "failed": []}
for net, cls, s, g in JOBS:
    w = W.get(cls, 0.2)
    r = route(net, s, g, w, cls, via_cost=1.0 if g[0] == "plane" else 2.0)
    if r is None:
        print("FAILED", net, cls); result["failed"].append(net); continue
    segs, vias, (vd, vdr) = r
    for l, pts in segs:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            result["tracks"].append({"net": net, "l": l, "x0": ax, "y0": ay, "x1": bx, "y1": by, "w": w})
            add_track(l, ax, ay, bx, by, w, net)
    for vx, vy in vias:
        result["vias"].append({"net": net, "x": vx, "y": vy, "d": vd, "drill": vdr})
        add_via(vx, vy, vd, net)
    L = sum(math.hypot(t["x1"] - t["x0"], t["y1"] - t["y0"]) for t in result["tracks"] if t["net"] == net)
    print(f"routed {net:12s} {cls:8s}: {len(segs)} runs, {len(vias)} vias")
json.dump(result, open(R + "fill.json", "w"), indent=0)
print("failed:", result["failed"])
