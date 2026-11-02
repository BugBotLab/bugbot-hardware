# Rebuild the whole BugBot in FreeCAD from scratch: Params, chassis, PCB + motor caps, printed parts, bought parts, assembly.
# Run:  python fusionflow/ffclient.py run mech/freecad/build_all.py      (takes a few minutes)
import os
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad"
steps = {}
for f in ("build_chassis.py", "build_pcb_caps.py", "build_printed.py", "build_bought.py", "build_solenoid.py", "build_wheel.py", "build_frontpcb.py", "build_ledpcb.py", "build_ecad.py", "build_encoder.py", "build_nfc.py", "build_cable.py", "build_fasteners.py", "build_structure.py", "apply_colours.py"):
    g = dict(globals()); g.pop("ONLY", None); g.pop("result", None)
    exec(open(os.path.join(OUT, f), encoding="utf-8").read(), g)
    steps[f] = g.get("result")
result = steps
