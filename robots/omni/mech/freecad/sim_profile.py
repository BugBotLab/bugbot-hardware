# The base robot's simulation parameters: ONE place for every variant (like variants.py for the geometry).
#   apply(r, P)        masses, materials, colliders, friction, floor, timestep, lights and SENSORS (with their models)
#   add_wheels(r)      the three omni drive wheels (gearmotors, rollers)
# A variant's sim script (build_sim.py = BugBot, build_sim_spider.py = Spider) calls both, then adds only its own
# parts (arm, kicker, ball, dispenser, tags ...) and may override a value. Change a base value here and every variant's
# next sim build (FusionFlow Variants, on save of BugBot) picks it up.
# Sensor lines: "kind name x y z dx dy dz [numbers] [key=value ...]"; the key=value model parameters reach robot_io /
# the viewer unchanged (build_scene writes them into the scene as 'sensor_params').
import re

def _fmt(kv):
    return " ".join(f"{k}={v}" for k, v in kv.items())


# ---- sensor models (shared by every robot) ----
NFC = dict(                                    # WS1850S reader board (kicad/BugBot_NFC) + the antenna floor PCB (kicad/BugBot_NFCfloor)
    ant="d79",                                 # the 3-turn loop round the floor edge as one circle (r ~39.5; 2.42 uH)
    range_mm=27,                               # on-axis read range before detune (21 mm with it), flat NTAG213: CALCULATED (design/lib/nfc_floor_calc.py:
                                               # WS1850S datasheet TX 25 ohm at 3.3 V -> matching -> loop -> Biot-Savart) with the
                                               # reader RETUNED for the big loop (done 2026-10-23: C6/C12 10 pF, C8+C9 / C13+C11 47+47 pF); spread 0-28 mm.
                                               # As built (tuned for the old 22 mm coil) it would not read at all (0.59 x the field)
    h_min=1.5,                                 # A/m: ISO 14443 minimum operating field
    tag_coil=21,                               # NTAG213 25 mm coin: its coil (mm): ESTIMATE
    detune=0.8,                                # the gearmotors 1.6 mm behind the coil lower its range: ESTIMATE
    poll_ms=10, txn_ms=5)                      # firmware poll period; REQA + anticollision + SELECT + READ
NFC_POS = (0.0, 0.0, 6.45)                     # the loop: top copper of the floor PCB, against the floor underside (z 6.5)
CAMERA = dict(                                 # OV2640 (kept over the SC035HGS), CIF at 60 fps: the trackball session's model
    res="352x288", fps=60, fov_v=66,           # 66 deg top to bottom, measured on the distorted image
    k1=-0.28, k2=0.08, p1=0, p2=0, k3=0,       # small M12-style barrel lens: PLACEHOLDER until calibrated (checkerboard)
    noise=3,                                   # (its full model: shot ~375 e- at 1 ms, 4 e- read, 1 % FPN, 20 % 100 Hz flicker)
    shutter="rolling", exposure_ms=1, readout_ms=14)   # rows read over 14 ms

# ---- underglow (NFC floor PCB, kicad/BugBot_NFCfloor): 7 x WS2812B-4020 SIDE-view, lens facing OUT, white board ----
UNDERGLOW = dict(r=9.0, n=7, a0=318.77,        # LED line radius; first LED's angle (deg), then every 360/n counter-clockwise (= data order)
                 side=1, size="4.0x1.66x1.7",  # side-emitting package (along x across x tall, mm); its body sits inwards of the line
                 glow_r=38, spill_r=46)        # the light under the robot reaches the rim (white board + table bounce it out),
                                               # and a little spills past it onto the table (looks only)
UNDERGLOW_Z = 4.05                             # LED centres: board underside 4.9 - half the LED (1.7)

FLOOR = dict(friction=1.0, rolling=0.0004)     # matte rough silicone mat (the play field)

MASSES = {                                     # grams: bought parts from datasheets (ESTIMATES marked in build_sim.py)
    r"/Servo$": "9", r"/Gearmotor$": "1.25",
    r"/MainBoard \(KiCad\)$": "40", r"/FrontSensorBoard \(KiCad\)$": "4",
    r"/LEDJewel$": "1.5", r"/LEDCable$": "0.4", r"/Antenna$": "1"}   # jewel: Adafruit's 1.5 g (the reader is on the NFC floor PCB now)
DENSITIES = {                                  # g/cm3
    r"Roller": "1.21",                         # TPU, printed solid
    r"Fasteners \(nylon\)": "1.14", r"WheelPin": "7.85",
    r"Fasteners|Screws|screw": "7.85",
    r"BrassLiner|PivotTube|PivotBushing": "8.5", r"DeckStandoffs": "1.0", r"ServoHorn": "1.14",
    r"NFC antenna floor PCB": "1.85"}          # FR4 (the board + its LEDs: ~10.5 g)
COLLIDERS = {
    r"^SensorMast:1/": "hull", r"/LEDJewel$": "hull",
    r"/EncBoard \(KiCad\)$": "board", r"/NFC reader cable": "none", r"/LEDCable$": "none", r"/Antenna$": "none",   # board: only the bare PCB collides
    r"/NFC antenna floor PCB": "none",          # thin board right under the chassis floor (which collides precisely): no own collider,
    r"/NFC antenna cable$": "none",             # so no convex decomposition of it on every board change; the cable: looks only
    r"/Wheel/WheelHalf|/Wheel/WheelFrameOne": "hull",
    r"/MainBoard \(KiCad\)$": "board", r"/FrontSensorBoard \(KiCad\)$": "board",
    r"^Frame:1/Chassis$": "precise",
    r"(?i)fasteners|screws|BrassLiner|PivotTube|PivotBushing": "none",   # (any case: "Kicker screws", "Motor cap screws" were colliding)
    r"/Gearmotor$": "hull", r"/MotorCap": "hull", r"^GripperMount:1/Servo$": "hull", r"/ServoHorn$": "hull"}


def sensors(q):
    """The base robot's sensors (q: the BugBot Params in mm)."""
    x, y, z = NFC_POS
    return [
        f"imu imu 0 0 {q('pcb_top') + 1:.2f}",
        f"tof8x8 tof {q('mast_x') + 3.1:.2f} 0 {q('tof_z'):.2f} 1 0 0 60",
        f"camera camera {q('mast_x') + 3.1:.2f} 0 {q('cam_z'):.2f} 1 0 0 66 {_fmt(CAMERA)}",
        f"nfc nfc {x} {y} {z} 0 0 -1 {_fmt(NFC)}",
        f"underglow underglow 0 0 {UNDERGLOW_Z} 0 0 -1 {_fmt(UNDERGLOW)}",     # robot_io.Underglow, viewer UNDERGLOW panel
    ]


CABLES = re.compile(r"/(MotorCable\d|UnderglowCable|ServoCable|SolenoidCable)$")


def apply(r, q, masses=None, densities=None, colliders=None):
    """Base parameters onto a SimRobot; a variant passes its own extra masses / densities / colliders (they win)."""
    r.Masses = {**MASSES, **(masses or {})}
    r.Densities = {**DENSITIES, **(densities or {})}   # (a PropertyMap keeps keys sorted: patterns must not overlap)
    r.DefaultDensity = 0.8                              # PLA with walls + infill
    r.Colliders = {**COLLIDERS, **(colliders or {})}
    r.Friction = 0.35
    r.FloorFriction = FLOOR["friction"]; r.FloorRolling = FLOOR["rolling"]; r.AirDrag = True
    r.Timestep = 0.0005
    r.Emissive = {r"/Dome$": "0.55"}
    r.Lights = [f"ledring 0 0 {q('mast_top') + q('deck_t') + 3:.2f} 1 1 1"]
    r.Sensors = sensors(q)
    # the routed cables (build_cables.py) stay out of the sims: their sweeps mesh to 0.5-1M faces at any useful tolerance
    # (MuJoCo's STL limit is 200k; 2026-10-27) and they are looks only, ~1-2 g in all
    r.Exclude = sorted(o.Label for o in r.Document.Objects if CABLES.search(o.Label))
    return r


def add_wheels(objects, r):
    """Pololu #2358-class 136:1 sub-micro gearmotors (now the AliExpress 6 mm planetary ones) at the 3.7 V cell."""
    for k in (1, 2, 3):
        objects.make_wheel(r, f"wheel{k}", f"DriveUnit:{k}/Wheel", Motor="dc", Encoder=False, GearFriction=0.11 * 0.0565 * 3.7 / 6,
                           StallTorque=0.0565 * 3.7 / 6, MaxSpeed=500 * 2 * 3.14159265 / 60 * 3.7 / 6, MaxTorque=0.025,
                           RollerFriction=1.0, RollerDamping=2e-7, RollerArmature=1e-9, RollerAxleFriction=0.15 * 0.5 * 0.0005)
