# Power switch v3 near 231 deg (user, 2026-10-25): the switch (shared C&K OS102011MA1QN1 / SK-12D07 footprint) at a
# given angle, and the parts round it (3V3 converter U4 group, Q6 group) pushed the least that clears it: repeated passes,
# each part in conflict moving to the nearest legal spot (0.15 mm courtyard gaps, holes 0.3, robot keep-outs).
# Writes _place/sw1_room.json (angle, moves) for the drawing and the apply step.
import json, math, sys
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
bm = json.load(open(P + "board_map.json"))
bot = {f["ref"]: Polygon(f["crt"]).buffer(0) for f in bm["fps"] if f["crt"] and f["side"] == "B" and f["ref"] != "SW1" and not f["ref"].startswith("H")}
holes = [Point(*f["pos"]).buffer(1.15) for f in bm["fps"] if f["ref"].startswith("H")]
kz = [g for g in (Polygon(p).buffer(0) for z in bm["zones"] if "keepout bottom" in z["name"] for p in z["polys"]) if g.is_valid and g.area > 0.01]
MOVABLE = [r for r in ["Q6", "R6", "R47", "R48", "L1", "C9", "C8", "C10", "C7", "U4", "R12", "R13"] if r in bot]   # (R47 / R48 are on top)
R_TIP, GAP = 40.3, 0.15


def sw(pos):
    a = math.radians(pos); V = (math.cos(a), math.sin(a)); U = (V[1], -V[0])
    c = ((R_TIP - 6.5) * V[0], (R_TIP - 6.5) * V[1])
    L = lambda x, y: (c[0] + x * U[0] + y * V[0], c[1] + x * U[1] + y * V[1])
    return unary_union([Polygon([L(-5.3, -2.5), L(5.3, -2.5), L(5.3, 2.5), L(-5.3, 2.5)]),
                        Polygon([L(-2.25, 2.4), L(2.25, 2.4), L(2.25, 6.5), L(-2.25, 6.5)])])


def solve(pos, passes=8, maxr=3.0):
    s = sw(pos)
    if min(h.distance(s) for h in holes) < 0.3: return None
    cur = dict(bot); total = {r: (0.0, 0.0) for r in MOVABLE}
    bad = lambda r, g: g.distance(s) < GAP or any(g.distance(o) < GAP for q, o in cur.items() if q != r)
    for _ in range(passes):
        moved = False
        for r in sorted(MOVABLE, key=lambda q: cur[q].distance(s)):
            if not bad(r, cur[r]): continue
            g0 = cur[r]; found = None
            for rad in [k * 0.05 for k in range(1, int(maxr / 0.05) + 1)]:
                for th in range(0, 360, 10):
                    dx, dy = rad * math.cos(math.radians(th)), rad * math.sin(math.radians(th))
                    g = affinity.translate(g0, dx, dy)
                    if bad(r, g) or any(g.intersection(k).area > 0.01 for k in kz) or any(g.distance(h) < 0.3 for h in holes): continue
                    found = (dx, dy); break
                if found: break
            if not found: continue
            cur[r] = affinity.translate(g0, *found); total[r] = (total[r][0] + found[0], total[r][1] + found[1]); moved = True
        if not any(bad(r, cur[r]) for r in cur if r in MOVABLE or cur[r].distance(s) < GAP): break
        if not moved: break
    if any(g.distance(s) < GAP for g in cur.values()) or any(bad(r, cur[r]) for r in MOVABLE): return None
    return {r: (round(v[0], 2), round(v[1], 2)) for r, v in total.items() if math.hypot(*v) > 0.001}


if __name__ == "__main__":
    best = None
    for pos in [232.5 + 0.25 * k for k in range(0, 9)]:
        m = solve(pos)
        if m is None: print(pos, "no solution"); continue
        tot = sum(math.hypot(*v) for v in m.values()); print(pos, m, f"total {tot:.2f} mm, biggest {max(math.hypot(*v) for v in m.values()):.2f}")
        if best is None or tot < best[1]: best = (pos, tot, m)
    if best:
        json.dump({"angle": best[0], "moves": best[2]}, open(P + "sw1_room.json", "w"), indent=1); print("chosen", best[0])
