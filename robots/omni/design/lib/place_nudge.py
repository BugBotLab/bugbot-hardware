# Placement nudge (routing <-> placement loop): where the router could not connect a pad, the movable parts next to the
# jam are shifted a little (0.25 mm steps, at most MAX_SHIFT mm, same side and turn) away from it, if they still obey the
# floor plan's rules: inside the board, 0.5 mm between courtyards (1 mm round the bigger chips), clear of the module's
# escape ring, the hard keep-outs (every style's arms, kicker, ball: from FreeCAD) and the height limits.
# Fixed parts (module, connectors in the walls, battery, switch, USB, front board socket) never move.
# Reads _place/{shapes.json, free_area.pkl, board_map.json, placement.json}, _route/nets.json and the router's log;
# writes _place/nudge.json (the moves) and nudge_v1.png (old / new outlines, to scale) for approval. place_apply.py
# then applies placement_nudged.json.
#   C:/Python312/python.exe design/lib/place_nudge.py design/schematics/Main/_route/stagefix.out [U8,U9,...]
import json, pickle, math, re, sys
from shapely.geometry import Polygon, Point
from shapely import affinity

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
RT = BB + "/design/schematics/Main/_route/"
MAX_SHIFT, STEP, NEAR = 1.5, 0.25, 7.0
shapes = json.load(open(P + "shapes.json"))
free = pickle.load(open(P + "free_area.pkl", "rb"))
placed = json.load(open(P + "placement.json"))
bmap = {f["ref"]: f for f in json.load(open(P + "board_map.json"))["fps"]}
SIDE = {"top": "F", "bottom": "B"}
FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"}
GAP, BIG_GAP, RING = 0.5, 1.0, 2.5
BIG = {"U4", "U5", "U7", "U8", "U9", "U11"}
margin = lambda ref: BIG_GAP if ref in BIG else GAP
board = Point(0, 0).buffer(40.6 - 0.8, 128).difference(Point(41.5, 0).buffer(18.6 + 0.8, 128))
hard = {SIDE[k]: board.difference(v[0]).buffer(0) for k, v in free.items()}
limits = {SIDE[k]: v[1] for k, v in free.items()}
HEIGHT = [("HTSSOP", 1.2), ("TSSOP", 1.2), ("SOT", 1.45), ("0402", 0.55), ("0603", 0.9), ("0805", 1.35), ("1206", 1.8)]
height = lambda fp: next((h for k, h in HEIGHT if k in fp), 3.0)


def outline(ref, x=None, y=None):
    if ref in FIXED: return Polygon(bmap[ref]["crt"]).buffer(0)
    px, py, rot, side, _ = placed[ref]
    return affinity.translate(Polygon(shapes[ref]["v"][f"{side}{int(rot)}"]), px if x is None else x, py if y is None else y)


def side_of(ref): return shapes[ref]["placed"][3] if ref in FIXED else placed[ref][3]


def through(ref):                                   # parts whose leads / holes block the other side too
    s = shapes[ref]
    return (s["tht"] and "ThermalVias" not in s["fp"]) or ref in ("SW1", "J1")


def blockers(ref):
    """everything a part must keep clear of, on its own side (and the other side for through-hole parts)"""
    sides = {side_of(ref)} | ({"F", "B"} if through(ref) else set())
    out = []
    for o in set(placed) | FIXED:
        if o == ref: continue
        so = {side_of(o)} | ({"F", "B"} if through(o) else set())
        if o == "BT1": so = {"F"}                     # only its pins come through
        if sides & so:
            out.append((outline(o), max(margin(ref), margin(o))))
            if o == "U6": out.append((outline(o).buffer(RING - 0.25), 0.0))
    if "B" in sides:
        for px, py, r in ((-23.8, -18.91, 1.6), (-23.8, 18.91, 1.6), (-31.9, -18.91, 1.3)):
            out.append((Point(px, py).buffer(r), GAP))
    return out, sides


def fits(ref, g):
    obs, sides = blockers(ref)
    if not board.contains(g): return False
    h = height(shapes[ref]["fp"])
    for s in sides:
        if g.buffer(0.1).intersects(hard[s]): return False
        for mh, poly in limits[s].items():
            if h + 0.3 > mh and g.intersects(poly) and g.intersection(poly).area > 0.01: return False
    return all(g.distance(o) >= m - 1e-6 for o, m in obs)


# the jams: each failed pad and the nearest other pad of its net (robot frame)
nets = {n: pads for grp in json.load(open(RT + "nets.json")).values() for n, pads in grp.items()}
log = open(sys.argv[1]).read() if len(sys.argv) > 1 else open(RT + "stagefix.out").read()
fails = sorted(set(re.findall(r"FAILED (/\S+): (\w+)\.(\w+)", log)))
jams = []
for net, ref, num in fails:
    pads = nets.get(net, [])
    me = next((p for p in pads if p["ref"] == ref and p["pad"] == num), None)
    if not me: continue
    others = [p for p in pads if p is not me]
    if not others: continue
    o = min(others, key=lambda p: math.dist(p["xy"], me["xy"]))
    jams.append((net, me["xy"], o["xy"]))
print("jams:", [(n, a, b) for n, a, b in jams])
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

# each movable part near a jam's line moves away from it, as far as it may (largest shift first, then turned +-20/40 deg)
def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy), (ax + t * dx, ay + t * dy)

moves = {}
cands = sorted({r for r in placed if r not in FIXED and (only is None or r in only)})
for ref in cands:
    px, py = placed[ref][0], placed[ref][1]
    near = [(seg_dist((px, py), a, b), n) for n, a, b in jams]
    near = [(d, c, n) for (d, c), n in near if d < NEAR]
    if not near: continue
    # push direction: away from the jams it is near, weighted by closeness
    vx = sum((px - c[0]) / max(d, 0.5) ** 2 for d, c, _ in near); vy = sum((py - c[1]) / max(d, 0.5) ** 2 for d, c, _ in near)
    L = math.hypot(vx, vy)
    if L < 1e-9: continue
    vx, vy = vx / L, vy / L
    best = None
    for k in range(int(MAX_SHIFT / STEP), 0, -1):
        s = k * STEP
        for da in (0, 20, -20, 40, -40):
            c, sn = math.cos(math.radians(da)), math.sin(math.radians(da))
            dx, dy = s * (vx * c - vy * sn), s * (vx * sn + vy * c)
            dx, dy = round(dx / 0.05) * 0.05, round(dy / 0.05) * 0.05
            if fits(ref, outline(ref, px + dx, py + dy)):
                best = (dx, dy); break
        if best: break
    if best:
        moves[ref] = {"from": [px, py], "by": [round(best[0], 2), round(best[1], 2)], "near": sorted({n for _, _, n in near})}
        placed[ref] = [px + best[0], py + best[1]] + placed[ref][2:]       # later parts see this move
        print(f"{ref:5s} moves {best[0]:+.2f}, {best[1]:+.2f} mm  (for {moves[ref]['near']})")
    else:
        print(f"{ref:5s} cannot move (boxed in by the rules)")
json.dump(moves, open(P + "nudge.json", "w"), indent=1)
json.dump(placed, open(P + "placement_nudged.json", "w"), indent=0)

# drawing for approval
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Circle
orig = json.load(open(P + "placement.json"))
fig, ax = plt.subplots(figsize=(13, 11))
ax.add_patch(Circle((0, 0), 40.6, fc="#f6f6f2", ec="k")); ax.add_patch(Circle((41.5, 0), 18.6, fc="white", ec="k"))
for k, v in hard.items():
    for g in getattr(v, "geoms", [v]):
        if g.area > 0.5: ax.add_patch(MP(list(g.exterior.coords), fc="#f0c0c0" if k == "F" else "#c0c8f0", ec="none", alpha=0.25))
for ref in set(placed) | FIXED:
    g = outline(ref)
    col = "#a03030" if side_of(ref) == "F" else "#3050a0"
    if ref in moves:
        g0 = affinity.translate(Polygon(shapes[ref]["v"][f"{orig[ref][3]}{int(orig[ref][2])}"]), orig[ref][0], orig[ref][1])
        ax.add_patch(MP(list(g0.exterior.coords), fc="none", ec="#888", lw=0.8, ls="--"))
        ax.add_patch(MP(list(g.exterior.coords), fc="#ffd24d", ec="k", lw=1.0, alpha=0.8))
        m = moves[ref]["by"]; ax.annotate(f"{ref}\n{m[0]:+.2f},{m[1]:+.2f}", g.centroid.coords[0], fontsize=7, ha="center", va="center", weight="bold")
    else:
        ax.add_patch(MP(list(g.exterior.coords), fc="none", ec=col, lw=0.4))
for n, a, b in jams:
    ax.plot([a[0], b[0]], [a[1], b[1]], color="#e07000", lw=1.5, ls=":")
ax.set_xlim(-34, 4); ax.set_ylim(-16, 34); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title("Placement nudge v1 (seen from above): yellow = moved part (dashed = where it was), orange dotted = connections the\n"
             "router could not make; blue = bottom-side parts, red = top; shaded = keep-outs (every style), to scale, mm", fontsize=9)
fig.savefig(BB + "/design/schematics/Main/nudge_v1.png", dpi=100)
print(BB + "/design/schematics/Main/nudge_v1.png")
