# Floor plan v3 last fix (python): each part still overlapping / breaking a rule goes to the nearest legal spot (15 mm, any turn).
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/design/lib/place_v3_check.py").read().split("badh = ")[0])
import math
for rnd in range(3):
    bad = [r for r in MOVE if not legal_hard(r, state[r]) or overlap_of(r, geoms) > 0]
    print("round", rnd, "bad:", bad)
    if not bad: break
    for r in sorted(bad, key=lambda q: outline(q).area):
        if legal_hard(r, state[r]) and overlap_of(r, geoms) == 0: continue
        x, y, a, side = state[r]; done = False
        for rad in [k * 0.1 for k in range(1, 151)]:
            for t in range(0, 360, 10):
                for a2 in (a, (a + 90) % 360, (a + 180) % 360, (a + 270) % 360):
                    st = (round((x + rad * math.cos(math.radians(t))) / 0.05) * 0.05, round((y + rad * math.sin(math.radians(t))) / 0.05) * 0.05, a2, side)
                    if not legal_hard(r, st): continue
                    keep = (state[r], geoms[r]); state[r] = st; geoms[r] = (outline(r, st), side)
                    if overlap_of(r, geoms) == 0: done = True; break
                    state[r], geoms[r] = keep
                if done: break
            if done: break
        print(" ", r, "moved %.1f mm" % rad if done else "NO SPOT")
out = json.load(open(P + "placement_v3.json"))
for r in MOVE: out[r] = [round(state[r][0], 2), round(state[r][1], 2), state[r][2], state[r][3], 0]
json.dump(out, open(P + "placement_v3.json", "w"), indent=0)
print("cost", round(cost_parts()))
