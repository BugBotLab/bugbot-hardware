# Power switch v3 re-place, step 1b (plain Python + shapely): the corner placer worked from placement_v2.json, but some
# parts that stayed put had been nudged since (U9, C26, C27, C6, R10, U2 ...), so a few re-placed parts landed on them.
# This moves only the re-placed parts, each by the smallest step (0.05 mm grid, up to 3 mm) that clears every courtyard
# on its side (through-hole pads checked on both sides), stays on the board and out of the MCAD keepouts.
# Reads _place/board_geom.json (export_geom.py) with SW1 turned by SW_TURN deg about the board centre;
# writes _place/legalize.json {ref: [dx, dy]} (robot frame, mm) for apply_moves.py.
#   C:/Python312/python.exe design/lib/legalize_corner.py [sw_turn_deg] [extra refs allowed to move ...]
import sys, json, math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/schematics/Main/"
SW_TURN = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
GAP, R_MAX, STEP, REACH = 0.02, 38.6, 0.05, 3.0
g = json.load(open(D + "_place/board_geom.json")); F = {f["ref"]: f for f in g["fps"]}
moved = [r for r in json.load(open(D + "_route/corner_nets.json"))["moved"] if r != "SW1"]
moved += [r for r in sys.argv[2:] if r not in moved]        # small parts that stayed put but may step aside too
U = lambda ps: unary_union([Polygon(p).buffer(0) for p in ps if len(p) > 2]) if ps else Polygon()
geo = {}
for r, f in F.items():
    tht = unary_union([U(p["poly"]) for p in f["pads"] if p["tht"]])
    geo[r] = {"F": U(f["crtF"]), "B": U(f["crtB"]), "tht": tht}
    if r == "SW1":
        for k in geo[r]: geo[r][k] = affinity.rotate(geo[r][k], SW_TURN, origin=(0, 0))
keep = {"F": unary_union([U(z["poly"]) for z in g["rules"] if "F.Cu" in z["layers"]]),
        "B": unary_union([U(z["poly"]) for z in g["rules"] if "B.Cu" in z["layers"]])}
board = Point(0, 0).buffer(R_MAX, 256)
def shapes(r, d):
    s = F[r]["side"]; o = "F" if s == "B" else "B"
    m = lambda x: affinity.translate(x, *d)
    return s, o, m(geo[r][s]), m(geo[r]["tht"])
def bad(r, d):
    s, o, c, t = shapes(r, d)
    if c.is_empty: return 0
    pen = c.difference(board).area + c.intersection(keep[s]).area
    for q, gq in geo.items():
        if q == r: continue
        dq = off.get(q, (0, 0))
        other = affinity.translate(gq[s], *dq) if dq != (0, 0) else gq[s]
        if not other.is_empty and c.distance(other) < GAP: pen += c.buffer(GAP).intersection(other).area + 1e-3
        if not t.is_empty:                                       # my pins vs parts on the far side
            far = affinity.translate(gq[o], *dq) if dq != (0, 0) else gq[o]
            if not far.is_empty and t.intersects(far): pen += t.intersection(far).area + 1e-3
        if not gq["tht"].is_empty:                               # their pins vs me
            th = affinity.translate(gq["tht"], *dq) if dq != (0, 0) else gq["tht"]
            if c.intersects(th) and q not in ("H1", "H2", "H3", "H4"): pen += c.intersection(th).area + 1e-3
    return pen
off = {}
cands = sorted(((i * STEP, j * STEP) for i in range(-60, 61) for j in range(-60, 61) if math.hypot(i, j) * STEP <= REACH),
               key=lambda d: math.hypot(*d))
for it in range(4):
    todo = [r for r in moved if bad(r, off.get(r, (0, 0))) > 0]
    print("round", it, "overlapping:", todo, flush=True)
    if not todo: break
    for r in todo:
        base = off.get(r, (0, 0)); b0 = bad(r, base)
        best = None
        for d in cands:
            dd = (base[0] + d[0], base[1] + d[1]); p = bad(r, dd)
            if p == 0: best = dd; break
            if best is None or p < best[1]: best = (dd, p)
        if isinstance(best[1], float) and len(best) == 2 and isinstance(best[0], tuple): off[r] = best[0]; print(f"  {r}: best partial {best[0]} pen {best[1]:.3f} (was {b0:.3f})")
        else: off[r] = best; print(f"  {r}: moved {best[0]:+.2f}, {best[1]:+.2f}")
json.dump({r: list(v) for r, v in off.items()}, open(D + "_place/legalize.json", "w"), indent=1)
