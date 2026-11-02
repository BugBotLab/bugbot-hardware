# Floor plan v3: which parts crowd which (needed gap vs actual distance) in _place/placement_v3.json.
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/design/lib/place_v3_check.py").read().split("badh = ")[0])
for r in MOVE:
    g, side = geoms[r]
    for o in MOVE:
        if o <= r: continue
        og, oside = geoms[o]
        if not (sides_of(r, side) & sides_of(o, oside)): continue
        need = pair_gap(r, o); dist = g.distance(og)
        if dist < need - 0.01: print(f"{r:5s} {o:5s} gap {dist:.2f} need {need:.2f}  ({shapes[r]['fp'].split(':')[-1][:22]} / {shapes[o]['fp'].split(':')[-1][:22]})")
