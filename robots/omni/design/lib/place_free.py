# Placement map 2/2: free area per side (board less keep-outs, holes, placed courtyards) and the height-limited parts of it
#   C:/Python312/python.exe design/lib/place_free.py   -> schematics/Main/_place/free_area.pkl
import json, re
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
S = BB + "/design/schematics/Main/_place/"
d = json.load(open(S + "board_map.json"))
txt = [(t[1], t[2]) for t in d["texts"]]
board = Point(0, 0).buffer(40.6 - 0.6, 128).difference(Point(41.5, 0).buffer(18.6 + 0.6, 128))   # front cut-out
out = {}
FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"}          # parts placed by hand (the rest is the placer's)
for side in ("top", "bottom"):
    hard, low = [], {}
    for z in d["zones"]:
        if side in z["name"]:
            for p in z["polys"]: hard.append(Polygon(p).buffer(0))
    for ln, shp, pts in d["shapes"]:
        if len(pts) < 3: continue
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        t = min(txt, key=lambda q: (q[1][0] - cx) ** 2 + (q[1][1] - cy) ** 2)[0]
        m = re.match(r"(top|bottom): max ([\d.]+) mm", t)
        if m and m.group(1) == side:
            h = float(m.group(2)); g = Polygon(pts).buffer(0)
            if h < 1.2: hard.append(g)
            else: low.setdefault(h, []).append(g)
    for f in d["fps"]:
        if f["pos"][0] > 45: continue
        if f["ref"].startswith("H"): hard.append(Point(f["pos"]).buffer(3.0)); continue
        if f["ref"] in FIXED and f["crt"] and ((f["side"] == "F") == (side == "top")): hard.append(Polygon(f["crt"]).buffer(0.2))
    free = board.difference(unary_union(hard))
    lim = {h: unary_union(g).intersection(free) for h, g in low.items()}
    out[side] = (free, lim)
    print(side, "free area", round(free.area), "mm2;", "limited by height:", {h: round(g.area) for h, g in sorted(lim.items()) if g.area > 5})
import pickle; pickle.dump(out, open(S + "free_area.pkl", "wb"))
