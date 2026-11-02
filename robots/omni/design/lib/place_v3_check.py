# Floor plan v3 check (python): parts that break a hard rule (with the reason) or overlap in _place/placement_v3.json.
import sys, json
sys.argv = ["x", "1"]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
src = open(BB + "/design/lib/place_v3.py").read()
marker = 'exec(compile(src, "place_v2(v3)", "exec"))'
src = src.replace(marker, "src = src.split('geoms = {r: (outline(r)')[0]\nexec(compile(src, 'v3', 'exec'))")
exec(src)
v3 = json.load(open(P + "placement_v3.json"))
for r in MOVE: state[r] = (v3[r][0], v3[r][1], int(v3[r][2]), v3[r][3])
geoms = {r: (outline(r), state[r][3]) for r in MOVE}
badh = [r for r in MOVE if not legal_hard(r, state[r])]
bado = [r for r in MOVE if overlap_of(r, geoms) > 0]
print("hard-illegal:", badh)
print("overlapping:", bado)
# why: which rule
for r in badh:
    x, y, a, side = state[r]; g = outline(r, state[r]); why = []
    if not board.contains(g): why.append("board edge")
    for s in sides_of(r, side):
        if g.buffer(0.1).intersects(hard[s]): why.append(f"keepout {s}")
        h = height(shapes[r]["fp"])
        for mh, poly in limits[s].items():
            if h + 0.3 > mh and g.intersects(poly) and g.intersection(poly).area > 0.01: why.append(f"height {mh} {s}")
        for k in stat_tree[s].query(g.buffer(1.5)):
            o, mo, ro = static[s][k]
            if g.distance(o) < max(margin(r), mo) - 1e-6: why.append(f"near {ro}")
    for zr, (zg, who) in CH_ZONE.items():
        if "B" in sides_of(r, side) and (who == "all" or height(shapes[r]["fp"]) > 1.0) and g.intersects(zg): why.append(f"zone {zr}")
    print(" ", r, sorted(set(why)))
