# BugBot in the simulator (SimLink): the robot's links, joints, masses and sensors.
#   python fusionflow/ffclient.py run mech/freecad/build_sim.py
# Joints follow the Params sheet (expressions), so a parameter change moves them in the simulator too.
# Masses: printed parts from their solids x density; bought parts from datasheets (ESTIMATES marked so: check them).
import os, sys
mod = os.path.join(App.getUserAppDataDir(), "Mod", "SimLink")
if mod not in sys.path:
    sys.path.append(mod)                       # (a FreeCAD started before SimLink was installed)
import importlib
import simlink, simlink.objects, simlink.export, simlink.live
for m in (simlink.objects, simlink.export, simlink.live):
    importlib.reload(m)
from simlink import objects, live, export

doc = App.getDocument("BugBot")
asm = doc.getObject("Assembly")
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/sim"
for o in list(doc.Objects):                    # rebuildable
    if type(getattr(o, "Proxy", None)).__name__ in ("SimRobot", "SimJoint", "SimWheel"):
        doc.removeObject(o.Name)
grp = doc.getObject("Simulation") or doc.addObject("App::DocumentObjectGroup", "Simulation")

r = objects.make_robot(doc, asm, OUT)
r.RobotName = "BugBot"
r.AutoSync = False                             # switched on at the end
r.WorldBodies = ["Ball:1"]
r.Masses = {                                   # grams
    r"/Servo$": "9",                           # SG90
    r"/Gearmotor$": "1.25",                    # Pololu #2358 (Pololu specs)
    r"/MainBoard \(KiCad\)$": "40",            # PCB 1.6 mm + Keystone 1051 + 16340 cell + parts (ESTIMATE)
    r"/FrontSensorBoard \(KiCad\)$": "4",
    r"/LEDBoard \(KiCad\)$": "1.6", r"/LEDCable$": "0.4", r"/Antenna$": "1", r"/M3ThinNut$": "0.6"}
r.Densities = {r"^Ball:1": "1.37",            # 40+ ping-pong ball: 0.4 mm plastic shell -> 2.7 g
               r"Roller": "1.21",              # TPU, printed solid
               r"Fasteners \(nylon\)": "1.14",  # nylon screws (before the steel rule)
               r"WheelPin": "7.85",            # steel
               r"/FrontBar$": "8.5", r"/BarScrew$": "7.85", r"/BarNut$": "7.85",   # brass tube, M3 screw + nut
               r"Fasteners|Screws": "7.85",    # every other screw and nut (steel)
               r"BrassLiner|PivotTube|PivotBushing": "8.5", r"BarWashers": "7.85",
               r"DeckStandoffs": "1.0",        # aluminium
               r"ServoHorn": "1.14",           # nylon
               r"/HoopSleeve$": "1.24",        # PLA, printed solid
               r"/Solenoid$": "7.85", r"/SolenoidPlunger$": "7.85", r"/SolenoidSpring": "7.85",   # steel
               r"/SolenoidCoil$": "6.0"}       # copper winding + tape (ESTIMATE): the JF-0520B comes to ~20 g
r.DefaultDensity = 0.8                         # PLA with walls + infill
r.Colliders = {                                # only what the floor or the ball can touch needs its true (concave) shape
    r"^SensorMast:1/": "hull", r"/LEDBoard \(KiCad\)$": "hull", r"/LEDCable$": "none", r"/Antenna$": "none",
    r"/Wheel/WheelHalf|/Wheel/WheelFrameOne": "hull",                # inside the rollers' rolling circle: never touches the floor
    r"/MainBoard \(KiCad\)$": "solids,precise",  # every component its own hull, the PCB split finely round the ball notch
    r"/FrontSensorBoard \(KiCad\)$": "solids",
    r"^Frame:1/Chassis$": "precise",            # the ball pocket
    r"^Gripper:1/HoopArm": "precise", r"/KickBracket$": "precise",
    r"/Solenoid$": "solids", r"/SolenoidCoil$": "hull", r"/SolenoidPlunger$": "hull",
    r"Fasteners|Screws|BrassLiner|PivotTube|PivotBushing|BarWashers": "none",                # screws: mass only, nothing touches them
    r"/Gearmotor$": "hull", r"/MotorCap": "hull", r"^GripperMount:1/Servo$": "hull", r"/ServoHorn$": "hull"}
r.Friction = 0.35                              # PLA on the celluloid ball (the floor and the ball set their own)
r.PartFriction = {r"/HoopSleeve$": "0.35",     # PLA sleeve, free to spin on the brass tube (see the sleeve joint)
                  r"/FrontBar$": "0.15"}       # brass tube (the bar)
r.FloorFriction = 0.5; r.FloorRolling = 0.0001; r.AirDrag = True       # hard floor; carpet: FloorRolling ~0.0006
r.WorldRestitution = 0.85                      # a ping-pong ball bounces back ~0.85-0.9 of its speed off a hard surface
r.Timestep = 0.001                             # 1 ms: same results as 0.5 ms (checked), twice as fast
P = doc.getObject("Params")
q = lambda k: float(P.get(k).getValueAs("mm")) if hasattr(P.get(k), "getValueAs") else float(P.get(k))
r.Emissive = {r"/Dome$": "0.55"}               # diffuse white dome over the LED ring: it glows
r.Lights = [f"ledring 0 0 {q('mast_top') + q('deck_t') + 3:.2f} 1 1 1"]   # 6 x WS2812B-2020 under the dome
r.Sensors = [
    f"imu imu 0 0 {q('pcb_top') + 1:.2f}",
    f"flow flow -17 25 {q('pcb_z') - 3:.2f} 0 0 -1",                        # PAA5100JE-Q under the board
    f"tof8x8 tof {q('mast_x') + 3.1:.2f} 0 {q('tof_z'):.2f} 1 0 0 60",     # VL53L5CX in the mast: 8 x 8 zones, 63 deg diagonal
    f"camera camera {q('mast_x') + 3.1:.2f} 0 {q('cam_z'):.2f} 1 0 0 66",      # OV2640 / OV5640 24-pin module (66 deg lens), straight ahead
]
grp.addObject(r)

for k in (1, 2, 3):                            # 3 omni wheels: hub joint + 6 free rollers each
    # Pololu #2358 136:1 sub-micro planetary gearmotor: 500 rpm / 0.0565 N m (8 oz in) at 6 V (Pololu specs),
    # scaled to the 3.7 V cell: 32 rad/s, 0.035 N m. Gearbox: keep peaks under ~0.025 N m (Pololu family guidance).
    # no encoder on the 2358: the firmware drives it open loop and corrects with the floor sensor + gyro.
    # gearbox friction from Pololu's no-load current (45 of 400 mA at 6 V): ~0.11 x stall torque (ESTIMATE)
    w = objects.make_wheel(r, f"wheel{k}", f"DriveUnit:{k}/Wheel", Motor="dc", Encoder=False, GearFriction=0.11 * 0.0565 * 3.7 / 6,
                           StallTorque=0.0565 * 3.7 / 6, MaxSpeed=500 * 2 * 3.14159265 / 60 * 3.7 / 6, MaxTorque=0.025,
                           RollerFriction=1.0, RollerDamping=2e-7, RollerArmature=1e-9,
                           RollerAxleFriction=0.15 * 0.5 * 0.0005)   # brass liner on a steel pin: mu 0.15 x ~0.5 N x 0.5 mm

g = objects.make_joint(r, "gripper", "gripper", ["Gripper:1"], "revolute",
                       Axis=App.Vector(0, -1, 0), Lower=0.0, Upper=105.0, Actuator="position",
                       Effort=0.18, MaxVelocity=10.5, Kp=0.6, Kv=0.004, Damping=0.0005)   # SG90: 1.8 kg cm, 0.1 s/60 deg
g.setExpression(".Origin.x", "Params.pivot_x"); g.setExpression(".Origin.z", "Params.pivot_z")
g.setExpression("CadPosition", "Params.grip_ang / 1 deg")     # the CAD model may show it lifted

# front-bar sleeve: free to spin on the brass tube (clearance fit), so a ball pressed by the bar rolls in under it
sl = objects.make_joint(r, "sleeve", "sleeve", ["Gripper:1/HoopSleeve"], "continuous", ParentLink="gripper",
                        Axis=App.Vector(0, 1, 0), Actuator="none", Damping=1e-6, FrictionLoss=2e-5, Armature=1e-8)
sl.setExpression(".Origin.x", "Params.grip_x"); sl.setExpression(".Origin.z", "Params.grip_z")

kk = objects.make_joint(r, "kicker", "kicker", ["Kicker:1/KickDisc", "Kicker:1/M3ThinNut", "Kicker:1/SolenoidPlunger"], "prismatic",
                        Axis=App.Vector(1, 0, 0), Lower=0.0, Upper=6.4, Actuator="motor",          # stop: spring solid (6 mm) behind the washer
                        Effort=4.0, MaxVelocity=2.0, Stiffness=60.0, Damping=0.05,  # JF-0520B: 4 N at 12 V / 300 mA (seller data)
                        Drive="capacitor", CoilResistance=40.0, ForcePerAmp=13.3,     # 12 V / 0.3 A; 4 N / 0.3 A (MEASURE the coil)
                        Capacitance=330.0, ChargeVoltage=24.0, MaxVoltage=35.0)       # kicker cap 330 uF 35 V, boost to 24 V (design choice)
kk.setExpression(".Origin.x", "Params.sol_tip_x"); kk.setExpression(".Origin.y", "-Params.sol_dy"); kk.setExpression(".Origin.z", "Params.sol_z")
kk.SpringParts = ["Kicker:1/SolenoidSpring"]   # the return spring squeezes between the frame and the plunger's washer
kk.setExpression(".SpringFixed.x", "Params.sol_x0"); kk.setExpression(".SpringFixed.y", "-Params.sol_dy"); kk.setExpression(".SpringFixed.z", "Params.sol_z")
kk.setExpression("Upper", "Params.sol_stroke / 1 mm")      # 6.4 mm: the spring goes solid
doc.recompute()
s = export.export(r)                           # the scene build runs separately (first time: convex decomposition)
live.watch(doc)
result = {"export": s, "python": r.Python}
