# Floor plan v3 kick (python): each chip still breaking a hard rule moves with its small parts, as one block, to the nearest
# spot where the whole block keeps the hard rules (crowding allowed); a refine pass then makes room round it.
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
seen = set()
for r in [q for q in MOVE if not legal_hard(q, state[q])]:
    grp = group_of(r)
    if grp[0] in seen: continue
    seen.add(grp[0]); old = {k: state[k] for k in grp}; found = None
    for rad in [k * 0.25 for k in range(1, 161)]:
        for t in range(0, 360, 10):
            dx, dy = rad * math.cos(math.radians(t)), rad * math.sin(math.radians(t))
            new = {k: (round((old[k][0] + dx) / 0.05) * 0.05, round((old[k][1] + dy) / 0.05) * 0.05, old[k][2], old[k][3]) for k in grp}
            if all(legal_hard(k, v) for k, v in new.items()): found = (rad, new); break
        if found: break
    if found:
        for k, v in found[1].items(): state[k] = v
    if not found:                                  # the block cannot move: the chip alone (any turn); its parts follow in the refine
        x, y, a, side = state[r]
        for rad in [k * 0.25 for k in range(1, 161)]:
            for t in range(0, 360, 10):
                for a2 in (a, (a + 90) % 360, (a + 180) % 360, (a + 270) % 360):
                    st = (round((x + rad * math.cos(math.radians(t))) / 0.05) * 0.05, round((y + rad * math.sin(math.radians(t))) / 0.05) * 0.05, a2, side)
                    if legal_hard(r, st): found = (rad, {r: st}); break
                if found: break
            if found: break
        if found: state[r] = found[1][r]; grp = [r]
    print(grp, "->", f"{found[0]:.2f} mm" if found else "NO SPOT")
out = json.load(open(P + "placement_v3.json"))
for r in MOVE: out[r] = [round(state[r][0], 2), round(state[r][1], 2), state[r][2], state[r][3], 0]
json.dump(out, open(P + "placement_v3.json", "w"), indent=0)
