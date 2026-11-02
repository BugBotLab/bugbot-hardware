# Wasp in the simulator (SimLink): the base + the kicker with its striker ram, no servo or gripper. Run after build_wasp.py.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_wasp.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim_wasp
# The "kicker" joint is the Scorpion's (sim_style.py); the plunger carries the ram + its TPU cap instead of the kick disc.
import sys, importlib
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import sim_style as S; importlib.reload(S)
doc = App.getDocument("BugBot_Wasp")
r = S.robot(doc, doc.getObject("Wasp"), BB + "/mech/freecad/sim_wasp", "Wasp",
            densities={r"^Ram \(PETG\)": "1.27", r"^Ram cap": "1.21"},     # printed solid: PETG ram, TPU 95A cap
            colliders={r"^Ram": "hull"},
            friction={r"^Ram cap": "0.9"})                                  # TPU face
S.kicker(r, ["Ram (PETG)", "Ram cap (TPU 95A)", "Kicker:1/M3ThinNut", "Kicker:1/SolenoidPlunger"])
result = {"export": S.finish(r)}
