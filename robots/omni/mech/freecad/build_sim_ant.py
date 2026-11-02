# Ant in the simulator (SimLink): the base + servo mount + gripper + ball, no kicker. Run after build_ant.py.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_ant.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim_ant
# Same robot, gripper and sleeve joints as the Scorpion (sim_style.py); the ball is a world body.
import sys, importlib
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import sim_style as S; importlib.reload(S)
doc = App.getDocument("BugBot_Ant")
r = S.robot(doc, doc.getObject("Ant"), BB + "/mech/freecad/sim_ant", "Ant", world_bodies=["Ball:1"])
S.gripper(r, ["Gripper:1"])
S.sleeve(r)
result = {"export": S.finish(r)}
