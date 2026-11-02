# Floor plan v3 relocate (python): puts the given parts, one by one, at the legal, uncrowded spot on their side (anywhere on
# the board, any turn) that gives the lowest total wiring cost.   python place_v3_relocate.py U7 [U9 ...] [--side=F]
import sys as _s
REFS = [a for a in _s.argv[1:] if not a.startswith("--")]
LOOSE = "--loose" in _s.argv                          # --loose: crowding allowed (a refine sorts it out)
WANT_SIDE = next((a[7:] for a in _s.argv[1:] if a.startswith("--side=")), None)   # --side=F: may go to the other side
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/design/lib/place_v3_check.py").read().split("badh = ")[0])
import os as _os
for _r in _os.environ.get("NOT_BIG", "").split(","): BIG.discard(_r)       # NOT_BIG=U7: the normal 0.5 mm gap round these chips
import numpy as np
for r in REFS:
    x0, y0, a0, side = state[r]; best = None
    side = WANT_SIDE or side
    for x in np.arange(-38, 38.01, 0.5):
        for y in np.arange(-38, 38.01, 0.5):
            for a in (0, 90, 180, 270):
                st = (float(x), float(y), a, side)
                if not legal_hard(r, st): continue
                keep = (state[r], geoms[r]); state[r] = st; geoms[r] = (outline(r, st), side)
                if LOOSE or overlap_of(r, geoms) == 0:
                    c = cost_parts()
                    if best is None or c < best[0]: best = (c, st)
                state[r], geoms[r] = keep
    if best: state[r] = best[1]; geoms[r] = (outline(r, best[1]), side)
    print(r, "->", best[1] if best else "NO SPOT", "cost", round(best[0]) if best else "")
out = json.load(open(P + "placement_v3.json"))
for r in MOVE: out[r] = [round(state[r][0], 2), round(state[r][1], 2), state[r][2], state[r][3], 0]
json.dump(out, open(P + "placement_v3.json", "w"), indent=0)
