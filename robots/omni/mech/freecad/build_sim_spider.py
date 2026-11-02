# Spider in the simulator (SimLink): the BugBot base + the tag-dispenser arm. Run after build_spider.py.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_spider.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim_spider
#         C:/Python312/python.exe simlink/SimLink/simlink/sim/viewer.py mech/freecad/sim_spider
# Same drive, masses and sensors as build_sim.py (BugBot); the gripper joint is the dispenser arm (same SG90 + pivot), the
# TPU roller spins free on it, the 10 NTAG213 coins and the tag already on the field are free bodies. No kicker.
# Viewer: 1 = arm down / parked, arrows nudge 1 deg, T = drop a tag (arm down, drive 30 mm, park), KICK greyed out.
import os, sys
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
mod = os.path.join(App.getUserAppDataDir(), "Mod", "SimLink")
if mod not in sys.path:
    sys.path.append(mod)
import importlib
import simlink, simlink.objects, simlink.export, simlink.live
for m in (simlink.objects, simlink.export, simlink.live):
    importlib.reload(m)
from simlink import objects, export

doc = App.getDocument("BugBot_Spider")
root = doc.getObject("Spider")
OUT = BB + "/mech/freecad/sim_spider"
P = App.getDocument("BugBot_Base").getObject("Params")
q = lambda k: float(P.get(k).getValueAs("mm")) if hasattr(P.get(k), "getValueAs") else float(P.get(k))
import json
try:                                           # the Spider document is rebuilt from scratch: take the count from the last export
    prev_ver = int(json.load(open(OUT + "/robot.json"))["version"])
except Exception:
    prev_ver = 0
for o in list(doc.Objects):                    # rebuildable
    if type(getattr(o, "Proxy", None)).__name__ in ("SimRobot", "SimJoint", "SimWheel"):
        doc.removeObject(o.Name)
grp = doc.getObject("Simulation") or doc.addObject("App::DocumentObjectGroup", "Simulation")

labels = [o.Label for o in doc.Objects]
tags = sorted([l for l in labels if l.startswith("Tag ") and l[4:].isdigit()], key=lambda l: int(l[4:]))
r = objects.make_robot(doc, root, OUT)
r.RobotName = "Spider"
r.Version = prev_ver                           # keeps counting: an open viewer sees the new scene and reloads
r.AutoSync = False
r.WorldBodies = tags + ["Lid"]               # the weighted lid (cup + washer): one free body
import sim_profile; importlib.reload(sim_profile)   # the base robot's sim parameters + sensor models (shared)
sim_profile.apply(r, q,
    densities={r"^Tag ": "1.38",                    # NTAG213 PVC coin: 25 x 0.9 mm -> 0.6 g
               r"tyre \(TPU\)": "1.21", r"Axle spacer": "1.24", r"washer": "7.85"},
    colliders={r"^Tag ": "cylinder,thin",           # exact thin discs, firm contact, torsional friction
               r"^Roller tyre": "cylinder",         # the TPU tyre: an exact cylinder
               r"^Roller hub|^Axle|^Magazine screw|^Lid/washer": "none",
               r"^Arm plate": "hull"})
r.ColliderShapes = {r"^Magazine \(printed\)$": "MagazineCollider", r"^Lid/cup": "LidCollider"}   # convex pieces from build_spider.py
r.PartFriction = {r"^Tag ": "0.4", r"^Lid/": "0.35",             # PVC on PVC / on PLA
                  r"^Roller tyre": "0.9",      # TPU on the floor and on a tag (MuJoCo uses the larger of the two)
                  r"^Magazine": "0.35"}
r.WorldRestitution = 0.85                      # (spheres only: none here)
r.DropDrive = 18.0                             # mm driven (+ ~7 mm coast, roller down), then the viewer backs 5 mm with the roller still down: the next tag goes back in. 1 tag every drop, next tag within 1 mm after 9 (works for 17-20 mm with 3-8 mm back)
r.DropSpeed = 0.1
grp.addObject(r)

sim_profile.add_wheels(objects, r)             # same drive as every variant

arm_parts = ["Gripper:1", "Arm plate L (printed)", "Arm plate R (printed)", "Magazine (printed)",
             "Axle screw M3x50 socket (steel)", "Axle spacer L", "Axle spacer R"] + [l for l in labels if l.startswith("Magazine screw")]
g = objects.make_joint(r, "gripper", "gripper", arm_parts, "revolute",
                       Axis=App.Vector(0, -1, 0), Lower=-3.0, Upper=25.0, Actuator="position",   # 0 = roller on the floor, + = up
                       Effort=0.18, MaxVelocity=10.5, Kp=0.6, Kv=0.004, Damping=0.0005)          # SG90 (MG90S: same size)
g.Origin = App.Vector(q("pivot_x"), 0, q("pivot_z"))
g.Presets = ["Down 0", "Park 4", "Lift 15"]
rl = objects.make_joint(r, "roller", "roller", ["Roller tyre (TPU)", "Roller hub (printed)"], "continuous", ParentLink="gripper",
                        Axis=App.Vector(0, 1, 0), Actuator="none", Damping=1e-6,
                        FrictionLoss=0.3 * 0.15 * 0.0015,   # PLA hub on the M3 shank: mu 0.3 x ~0.15 N x 1.5 mm
                        Armature=1e-8)
rl.Origin = App.Vector(48.5, 0, 8.0)
doc.recompute()
s = export.export(r)
result = {"export": s}
