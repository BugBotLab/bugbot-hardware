# Beetle in the simulator (SimLink): the base + servo mount + the passive shield. Run after build_beetle.py.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_beetle.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim_beetle
# The shield is NOT driven (the SG90 stays fitted but unpowered): a passive "shield" hinge on the servo axis. Its feet rest on
# the main board (contact holds it at 0); a push from below lifts it and gravity drops it back. Upper 30 deg: ESTIMATE.
import sys, importlib
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import sim_style as S; importlib.reload(S)
doc = App.getDocument("BugBot_Beetle")
r = S.robot(doc, doc.getObject("Beetle"), BB + "/mech/freecad/sim_beetle", "Beetle",
            densities={r"^U screws": "7.85", r"^U nuts": "7.85"},
            colliders={r"^ShieldPlate|^Shield U front": "precise", r"^U screws|^U nuts": "none"})
sh = S.objects.make_joint(r, "shield", "shield",
                          ["ShieldPlateL (PETG)", "ShieldPlateR (PETG)", "Shield U front (PETG)", "U screws 2x M3x50 DIN912 (black)",
                           "U nuts 2x M3 DIN934 (zinc)", "Gripper:1/ServoHorn", "Gripper:1/Gripper screws", "Gripper:1/PivotBushing"],
                          "revolute", Axis=S.App.Vector(0, -1, 0), Lower=-2.0, Upper=30.0, Actuator="none",
                          Damping=0.0005, FrictionLoss=0.002)       # the unpowered SG90's gear train drags a little (ESTIMATE)
sh.Origin = S.App.Vector(S.q("pivot_x"), 0, S.q("pivot_z"))
result = {"export": S.finish(r)}
