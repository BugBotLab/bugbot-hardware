# Floor plan v3 group fix (python): a chip that breaks a rule moves with its own small parts, as one block, to the nearest legal spot (25 mm).
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/design/lib/place_v3_check.py").read().split("badh = ")[0])
import math
def group_of(r):
    ch = chip_of.get(r, r)
    if ch not in state: ch = r
    return [ch] + [q for q, c in chip_of.items() if c == ch and q in state and q != ch]
done_groups = set()
for r in [q for q in MOVE if not legal_hard(q, state[q]) or overlap_of(q, geoms) > 0]:
    grp = group_of(r)
    if grp[0] in done_groups: continue
    done_groups.add(grp[0])
    print("group", grp)
    old = {k: state[k] for k in grp}; oldg = {k: geoms[k] for k in grp}
    found = None
    for rad in [k * 0.25 for k in range(0, 101)]:
        for t in (range(0, 360, 10) if rad else [0]):
            dx, dy = rad * math.cos(math.radians(t)), rad * math.sin(math.radians(t))
            new = {k: (round((old[k][0] + dx) / 0.05) * 0.05, round((old[k][1] + dy) / 0.05) * 0.05, old[k][2], old[k][3]) for k in grp}
            if not all(legal_hard(k, v) for k, v in new.items()): continue
            for k, v in new.items(): state[k] = v; geoms[k] = (outline(k, v), v[3])
            if all(overlap_of(k, geoms, skip=grp) == 0 for k in grp): found = (rad, t); break
            for k in grp: state[k] = old[k]; geoms[k] = oldg[k]
        if found: break
    print("  ->", f"moved {found[0]:.2f} mm" if found else "NO SPOT for the whole group")
out = json.load(open(P + "placement_v3.json"))
for r in MOVE: out[r] = [round(state[r][0], 2), round(state[r][1], 2), state[r][2], state[r][3], 0]
json.dump(out, open(P + "placement_v3.json", "w"), indent=0)
print("cost", round(cost_parts()))
