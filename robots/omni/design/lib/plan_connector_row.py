# Connector plan v4 (user, 2026-10-26: "neater, designed with purpose"): the five cable connectors in ONE aligned row on
# the west side, all side-entry JST-SH, the same turn, equal 1.0 mm gaps between bodies, squared to the board (row along y).
# Searched: the row's x, where it starts in y, and which way the plugs go in (toward the centre +x, or toward the wall -x).
# Each spot must have, as the single-connector planner: the body and its 7 mm plug lane on the board, out of the MCAD
# bottom keep-outs, clear of the parts that never move and of every through-hole pin, 3.6 mm free under the board for the
# body and the lane. Order along the row (south -> north) follows where the cables go. Score = total cable length.
# -> _place/connector_row.json
#   C:/Python312/python.exe design/lib/plan_connector_row.py
import json, math, itertools
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.prepared import prep
from matplotlib.path import Path as MPath
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
g = json.load(open(P + "board_geom.json")); fps = json.load(open(P + "jst_fps.json"))
d = np.load(P + "free_height.npz"); RES, H = float(d["res"]), float(d["half"]); BEL = d["below"]; N = BEL.shape[0]
U = lambda ps: unary_union([Polygon(p).buffer(0) for p in ps if len(p) > 2]) if ps else Polygon()
NFC_J1 = (-8.5 - 11.2 * math.cos(math.radians(117)), 19.5 - 11.2 * math.sin(math.radians(117)))
ROW = [("J15", "Motor 2", 2, (0.44, -8.67)), ("J17", "Underglow", 4, (0.0, -1.2)), ("J14", "Motor 1", 2, (-7.73, 3.95)),
       ("J20", "NFC reader", 8, NFC_J1), ("J16", "Motor 3", 2, (7.29, 4.72))]       # south -> north
MOVING = {r for r, *_ in ROW}
NEVER = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6", "J18", "J19", "J21", "J22", "SW2", "SW3", "LED1", "BZ1"}
obst = unary_union([U(f["crtB"]) for f in g["fps"] if f["crtB"] and (f["ref"] in NEVER or f["ref"].startswith("H"))])
obst = obst.union(unary_union([Point(p["pos"]).buffer(max(p["size"]) / 2 + 0.3) for f in g["fps"] if f["ref"] not in MOVING
                               for p in f["pads"] if p["tht"]]))
obst_p = prep(obst.buffer(0.3))
keep = prep(unary_union([U(z["poly"]) for z in g["rules"] if "B.Cu" in z["layers"]]))
board = prep(Point(0, 0).buffer(38.6, 128).difference(Point(41.5, 0).buffer(18.9, 128)))
def min_h(poly):
    x0, y0, x1, y1 = poly.bounds
    i0, i1 = max(int((x0 + H) / RES), 0), min(int((x1 + H) / RES) + 1, N); j0, j1 = max(int((y0 + H) / RES), 0), min(int((y1 + H) / RES) + 1, N)
    xs = -H + (np.arange(i0, i1) + 0.5) * RES; ys = -H + (np.arange(j0, j1) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    m = MPath(np.asarray(poly.exterior.coords)).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
    a = BEL[i0:i1, j0:j1][m]; return a.min() if a.size else 0
def place(poly, x, y, a):
    p = affinity.scale(poly, 1, -1, origin=(0, 0)); p = affinity.rotate(p, a, origin=(0, 0)); return affinity.translate(p, x, y)
FN = {n: f"JST_SH_SM0{n}B-SRSS-TB_1x0{n}-1MP_P1.00mm_Horizontal" for n in (2, 3, 4, 8)}
W = {n: Polygon(fps[FN[n]]["crt"]).bounds[2] * 2 for n in (2, 3, 4, 8)}            # body width (along the row)
GAP = 1.0
best = []
for rot, facing in ((90, "+x (plugs in toward the centre)"), (270, "-x (plugs in toward the wall)")):
    for X0 in np.arange(-36, -9.9, 0.25):
        for Y0 in np.arange(-30, 10.1, 0.25):
            y = Y0; spots = []; ok = True; cable = 0.0
            for ref, what, n, T in ROW:
                yc = y + W[n] / 2
                b0 = Polygon(fps[FN[n]]["crt"]).buffer(0); w = b0.bounds[2]
                body = place(b0, X0, yc, rot); lane = place(box(-w + 0.4, 3.27, w - 0.4, 10.27), X0, yc, rot)
                if not (board.contains(body) and board.contains(lane)) or obst_p.intersects(body) or obst_p.intersects(lane) \
                        or keep.intersects(body) or keep.intersects(lane) or min_h(body) < 3.6 or min_h(lane) < 3.6:
                    ok = False; break
                ex = place(Point(0, 7.27), X0, yc, rot).coords[0]
                cable += math.dist(ex, T); spots.append([ref, what, n, float(X0), float(yc), rot, FN[n], [round(ex[0], 2), round(ex[1], 2)], list(T)])
                y += W[n] + GAP
            if ok: best.append((round(cable, 1), facing, spots))
best.sort(key=lambda b: b[0])
print(len(best), "valid rows")
for c, f, sp in best[:5]: print(c, f, "x", sp[0][3], "y", round(sp[0][4], 2), "->", round(sp[-1][4], 2))
json.dump([{"cable": c, "facing": f, "spots": sp} for c, f, sp in best[:50]], open(P + "connector_row.json", "w"), indent=1)
