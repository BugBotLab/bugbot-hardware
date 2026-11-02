# Shared SimLink setup for the style sims (build_sim_ant / wasp / beetle / base.py): the same robot settings, joint names
# and actuators as build_sim_scorpion.py, so one robot API drives every style ("gripper", "sleeve", "kicker", wheel<k>_drive).
# Joint numbers come from the base master's Params (BugBot_Base) when the script runs.
import os, sys, json
import FreeCAD as App

MOD = os.path.join(App.getUserAppDataDir(), "Mod", "SimLink")
if MOD not in sys.path:
    sys.path.append(MOD)
import importlib
import simlink, simlink.objects, simlink.export, simlink.live
for _m in (simlink.objects, simlink.export, simlink.live):
    importlib.reload(_m)
from simlink import objects, export
import sim_profile; importlib.reload(sim_profile)

P = App.getDocument("BugBot_Base").getObject("Params")


def q(k):
    v = P.get(k)
    return float(v.getValueAs("mm")) if hasattr(v, "getValueAs") else float(v)


DENSITIES = {r"^Ball:1": "1.37",            # 40+ ping-pong ball: 0.4 mm plastic shell -> 2.7 g
             r"/FrontBar$": "8.5", r"/BarScrew$": "7.85", r"/BarNut$": "7.85",   # brass tube, M3 screw + nut
             r"BarWashers": "7.85", r"/HoopSleeve$": "1.24",                     # PLA, printed solid
             r"/Solenoid$": "7.85", r"/SolenoidPlunger$": "7.85", r"/SolenoidSpring": "7.85",   # steel
             r"/SolenoidCoil$": "6.0"}      # copper winding + tape (ESTIMATE): the JF-0520B comes to ~20 g
COLLIDERS = {r"^Gripper:1/HoopArm": "precise", r"/KickBracket$": "precise",
             r"/Solenoid$": "solids", r"/SolenoidCoil$": "hull", r"/SolenoidPlunger$": "hull",
             r"BarWashers": "none",
             r"/MainBoard \(KiCad\)$": "board,precise"}   # the PCB split finely round the ball notch


def robot(doc, root, out, name, world_bodies=(), densities=None, colliders=None, friction=None):
    """a fresh SimRobot for `doc` (old sim objects removed), the base's sim profile + the style's own extras, the 3 wheels"""
    try:                                       # the style documents are rebuilt from scratch: keep the scene version counting
        ver = int(json.load(open(out + "/robot.json"))["version"])
    except Exception:
        ver = 0
    for o in list(doc.Objects):
        if type(getattr(o, "Proxy", None)).__name__ in ("SimRobot", "SimJoint", "SimWheel"):
            doc.removeObject(o.Name)
    grp = doc.getObject("Simulation") or doc.addObject("App::DocumentObjectGroup", "Simulation")
    r = objects.make_robot(doc, root, out)
    r.RobotName = name
    r.Version = ver                            # an open viewer sees the new scene and reloads
    r.AutoSync = False
    r.WorldBodies = list(world_bodies)
    sim_profile.apply(r, q, masses={r"/M3ThinNut$": "0.6"}, densities={**DENSITIES, **(densities or {})},
                      colliders={**COLLIDERS, **(colliders or {})})
    r.PartFriction = {r"/HoopSleeve$": "0.35", r"/FrontBar$": "0.15", **(friction or {})}
    r.WorldRestitution = 0.85                  # a ping-pong ball bounces back ~0.85-0.9 of its speed off a hard surface
    r.Timestep = 0.001
    grp.addObject(r)
    sim_profile.add_wheels(objects, r)         # wheel1..3 (+ wheel<k>_drive actuators): the base robot's
    return r


def gripper(r, parts, lower=0.0, upper=105.0):
    """the SG90 arm joint, as the Scorpion's: 0 = down, + = up (deg)"""
    g = objects.make_joint(r, "gripper", "gripper", parts, "revolute",
                           Axis=App.Vector(0, -1, 0), Lower=lower, Upper=upper, Actuator="position",
                           Effort=0.18, MaxVelocity=10.5, Kp=0.6, Kv=0.004, Damping=0.0005)   # SG90: 1.8 kg cm, 0.1 s/60 deg
    g.Origin = App.Vector(q("pivot_x"), 0, q("pivot_z"))
    g.CadPosition = float(P.get("grip_ang").Value)
    return g


def sleeve(r):
    """the front-bar sleeve, free to spin on the brass tube"""
    sl = objects.make_joint(r, "sleeve", "sleeve", ["Gripper:1/HoopSleeve"], "continuous", ParentLink="gripper",
                            Axis=App.Vector(0, 1, 0), Actuator="none", Damping=1e-6, FrictionLoss=2e-5, Armature=1e-8)
    sl.Origin = App.Vector(q("grip_x"), 0, q("grip_z"))
    return sl


def kicker(r, parts):
    """the JF-0520B solenoid on its 330 uF capacitor, as the Scorpion's; `parts` = what the plunger carries"""
    kk = objects.make_joint(r, "kicker", "kicker", parts, "prismatic",
                            Axis=App.Vector(1, 0, 0), Lower=0.0, Upper=q("sol_stroke"), Actuator="motor",
                            Effort=4.0, MaxVelocity=2.0, Stiffness=60.0, Damping=0.05,
                            Drive="capacitor", CoilResistance=40.0, ForcePerAmp=13.3,
                            Capacitance=330.0, ChargeVoltage=24.0, MaxVoltage=35.0)
    kk.Origin = App.Vector(q("sol_tip_x"), -q("sol_dy"), q("sol_z"))
    kk.SpringParts = ["Kicker:1/SolenoidSpring"]
    kk.SpringFixed = App.Vector(q("sol_x0"), -q("sol_dy"), q("sol_z"))
    return kk


def finish(r):
    r.Document.recompute()
    return export.export(r)                    # the scene build runs separately (Variants "After")
