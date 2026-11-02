# Scorpion in the simulator (SimLink): the base + servo mount + gripper + kicker + ball. Run after build_scorpion.py.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_scorpion.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim
#         C:/Python312/python.exe simlink/SimLink/simlink/sim/viewer.py mech/freecad/sim
# Was build_sim.py on the old Scorpion master (joints by Params expressions). The Scorpion is now a static document rebuilt
# from the base (FusionFlow Variants), so the joints take their numbers from the base's Params when this runs; the
# Variants object reruns it after every rebuild. Masses: printed parts from their solids x density; bought parts from
# datasheets (ESTIMATES marked so: check them).
import os, sys, json
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
mod = os.path.join(App.getUserAppDataDir(), "Mod", "SimLink")
if mod not in sys.path:
    sys.path.append(mod)                       # (a FreeCAD started before SimLink was installed)
import importlib
import simlink, simlink.objects, simlink.export, simlink.live
for m in (simlink.objects, simlink.export, simlink.live):
    importlib.reload(m)
from simlink import objects, export

doc = App.getDocument("BugBot_Scorpion")
root = doc.getObject("Scorpion")
OUT = BB + "/mech/freecad/sim"
P = App.getDocument("BugBot_Base").getObject("Params")
q = lambda k: float(P.get(k).getValueAs("mm")) if hasattr(P.get(k), "getValueAs") else float(P.get(k))
try:                                           # the document is rebuilt from scratch: take the count from the last export
    prev_ver = int(json.load(open(OUT + "/robot.json"))["version"])
except Exception:
    prev_ver = 0
for o in list(doc.Objects):                    # rebuildable
    if type(getattr(o, "Proxy", None)).__name__ in ("SimRobot", "SimJoint", "SimWheel"):
        doc.removeObject(o.Name)
grp = doc.getObject("Simulation") or doc.addObject("App::DocumentObjectGroup", "Simulation")

r = objects.make_robot(doc, root, OUT)
r.RobotName = "Scorpion"
r.Version = prev_ver                           # keeps counting: an open viewer sees the new scene and reloads
r.AutoSync = False
r.WorldBodies = ["Ball:1"]
import sim_profile; importlib.reload(sim_profile)   # the base robot's sim parameters + sensor models (shared)
sim_profile.apply(r, q,
    masses={r"/M3ThinNut$": "0.6"},
    densities={r"^Ball:1": "1.37",            # 40+ ping-pong ball: 0.4 mm plastic shell -> 2.7 g
               r"/FrontBar$": "8.5", r"/BarScrew$": "7.85", r"/BarNut$": "7.85",   # brass tube, M3 screw + nut
               r"BarWashers": "7.85", r"/HoopSleeve$": "1.24",                     # PLA, printed solid
               r"/Solenoid$": "7.85", r"/SolenoidPlunger$": "7.85", r"/SolenoidSpring": "7.85",   # steel
               r"/SolenoidCoil$": "6.0"},      # copper winding + tape (ESTIMATE): the JF-0520B comes to ~20 g
    colliders={r"^Gripper:1/HoopArm": "precise", r"/KickBracket$": "precise",
               r"/Solenoid$": "solids", r"/SolenoidCoil$": "hull", r"/SolenoidPlunger$": "hull",
               r"BarWashers": "none",
               r"/MainBoard \(KiCad\)$": "board,precise"})   # the PCB split finely round the ball notch
r.PartFriction = {r"/HoopSleeve$": "0.35",     # PLA sleeve, free to spin on the brass tube (see the sleeve joint)
                  r"/FrontBar$": "0.15"}       # brass tube (the bar)
r.WorldRestitution = 0.85                      # a ping-pong ball bounces back ~0.85-0.9 of its speed off a hard surface
r.Timestep = 0.001                             # 1 ms (no thin tags): same results as 0.5 ms (checked), twice as fast
grp.addObject(r)

sim_profile.add_wheels(objects, r)             # 3 omni wheels: the base robot's (sim_profile.py)

g = objects.make_joint(r, "gripper", "gripper", ["Gripper:1"], "revolute",
                       Axis=App.Vector(0, -1, 0), Lower=0.0, Upper=105.0, Actuator="position",
                       Effort=0.18, MaxVelocity=10.5, Kp=0.6, Kv=0.004, Damping=0.0005)   # SG90: 1.8 kg cm, 0.1 s/60 deg
g.Origin = App.Vector(q("pivot_x"), 0, q("pivot_z"))
g.CadPosition = float(P.get("grip_ang").Value)                 # the CAD model may show it lifted (deg)

# front-bar sleeve: free to spin on the brass tube (clearance fit), so a ball pressed by the bar rolls in under it
sl = objects.make_joint(r, "sleeve", "sleeve", ["Gripper:1/HoopSleeve"], "continuous", ParentLink="gripper",
                        Axis=App.Vector(0, 1, 0), Actuator="none", Damping=1e-6, FrictionLoss=2e-5, Armature=1e-8)
sl.Origin = App.Vector(q("grip_x"), 0, q("grip_z"))

kk = objects.make_joint(r, "kicker", "kicker", ["Kicker:1/KickDisc", "Kicker:1/M3ThinNut", "Kicker:1/SolenoidPlunger"], "prismatic",
                        Axis=App.Vector(1, 0, 0), Lower=0.0, Upper=q("sol_stroke"), Actuator="motor",   # 6.4 mm: the spring goes solid
                        Effort=4.0, MaxVelocity=2.0, Stiffness=60.0, Damping=0.05,  # JF-0520B: 4 N at 12 V / 300 mA (seller data)
                        Drive="capacitor", CoilResistance=40.0, ForcePerAmp=13.3,     # 12 V / 0.3 A; 4 N / 0.3 A (MEASURE the coil)
                        Capacitance=330.0, ChargeVoltage=24.0, MaxVoltage=35.0)       # kicker cap 330 uF 35 V, boost to 24 V (design choice)
kk.Origin = App.Vector(q("sol_tip_x"), -q("sol_dy"), q("sol_z"))
kk.SpringParts = ["Kicker:1/SolenoidSpring"]   # the return spring squeezes between the frame and the plunger's washer
kk.SpringFixed = App.Vector(q("sol_x0"), -q("sol_dy"), q("sol_z"))
doc.recompute()
s = export.export(r)                           # the scene build runs separately (Variants "After"; first time: convex decomposition)
result = {"export": s}
