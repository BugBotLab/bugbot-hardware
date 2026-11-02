# BugBot in FreeCAD: components, the BASE assembly and the class MODULES (Fusion-style hierarchy).
# This file is the master: the shared base robot (every style). The class parts (servo mount, gripper, kicker, ball) are MODULES:
# parametric components in the same file (they share the Params), outside the base assembly, in the "Modules" folder;
# each style is the base + its modules, built by its own script (build_scorpion.py, build_ant.py, ...; variants.py).
#   Base Assembly
#     Frame        chassis
#     DriveUnit:1..3  ONE drive-unit component (Wheel component + gearmotor + 2 x motor cap) placed three times, 120 deg apart
#     Kicker       solenoid, M3 thin nut, kick disc, kick bracket, storage capacitor
#     Electronics  main PCB, its components, front sensor board, LED ring, antenna
#     (the battery holder BT1 and its 16340 come with the KiCad main board)
#     SensorMast   mast, top deck, dome, deck standoffs, tag bar
#   Modules
#     GripperMount SG90 servo, servo block, pivot bracket + tube, their screws (the arm drive)
#     Gripper      both arms, front bar, TPU sleeve, servo horn: turns about the servo axis by grip_ang
#     NFC          antenna floor PCB, reader board, its tray and cable
#     Ball
# Every part is in exactly one component; repeated parts are links to one definition, so an edit shows everywhere.
# Run after the part scripts:  python fusionflow/ffclient.py run mech/freecad/build_structure.py
import JointObject
from fusionflow import helpers as H, extrude as X

doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
E = lambda s: X.expand(s, doc)

COMPONENTS = [
    ("Frame", ["Chassis"]),
    ("DriveUnit", ["Wheel", "Gearmotor", "MotorCap", "MotorCapR", "MotorCapScrews", "EncBoard"]),          # EncBoard: the KiCad wheel-encoder board (build_encoder.py)
    ("Kicker", ["Solenoid", "SolenoidCoil", "SolenoidPlunger", "SolenoidSpring", "M3ThinNut", "KickDisc", "KickBracket", "KickerScrews"]),   # MODULE; its capacitor (C1) is on the KiCad board
    ("Electronics", ["MainBoard", "MainPCB", "FrontSensorBoard", "FrontPCB", "LEDJewel", "LEDCable"]),   # the KiCad boards (MainPCB / FrontPCB, hidden, define their outlines); LEDJewel: the bought beacon
    ("SensorMast", ["Mast", "TopDeck", "Dome", "DeckStandoffs", "TagBar"]),   # TagBar: rear ID tag bar on the rear posts (tag_mounts.py)
    ("GripperMount", ["Servo", "ServoBlock", "HoopBracket", "PivotTube", "ServoMountScrews", "ServoMountPivotScrew"]),   # MODULE: the arm drive (not every style has an arm)
    ("Gripper", ["HoopArmL", "HoopArmR", "FrontBar", "BarScrew", "BarNut", "BarWashers", "PivotBushing", "HoopSleeve", "ServoHorn", "GripperScrews"]),
    ("NFC", ["NFCFloor", "NFCLinkCable"]),        # the floor tag reader: antenna + reader + underglow on one PCB (build_nfc.py)
    ("Fasteners", ["FastenersZinc", "FastenersNylon"]),   # (no black-oxide screws left: build_fasteners makes no FastenersBlack)          # every other screw and nut (build_fasteners.py)
]
MODULES = ("GripperMount", "Gripper", "Kicker")   # class modules: components outside the base assembly (+ the Ball body)

# ---------- clear an earlier structure (the parts themselves stay) ----------
for o in list(doc.Objects):
    if o.TypeId in ("Assembly::AssemblyObject", "Assembly::JointGroup") or (o.TypeId == "App::FeaturePython" and hasattr(o, "JointType")) \
            or (o.TypeId == "App::FeaturePython" and hasattr(o, "ObjectToGround")):
        pass
asm_old = doc.getObject("Assembly")
if asm_old:
    own = list(asm_old.Group)              # only the assembly's own occurrences and joints (not links inside components)
    for g in [o for o in own if o.isDerivedFrom("Assembly::JointGroup")]:
        own += list(g.Group)
    for o in own:
        try:                                 # (removing a joint group already removed its joints)
            if o.isDerivedFrom("App::Link") or o.TypeId == "App::FeaturePython" or o.isDerivedFrom("Assembly::JointGroup"):
                doc.removeObject(o.Name)
        except Exception:
            pass
    doc.removeObject("Assembly")
for name, parts in COMPONENTS:
    c = doc.getObject(name)
    if c and c.TypeId == "App::Part":
        for o in list(c.Group):
            try:
                if o.isDerivedFrom("App::Link"):
                    doc.removeObject(o.Name)
                elif not o.isDerivedFrom("App::Origin"):
                    c.removeObject(o)
            except Exception:                # an object that was deleted meanwhile
                pass
        doc.removeObject(c.Name)
for old in ("BoughtParts",):
    g = doc.getObject(old)
    if g:
        for o in list(g.Group): g.removeObject(o)
        doc.removeObject(old)
for o in doc.Objects:                      # gripper parts that an older version turned one by one: reset
    if o.isDerivedFrom("PartDesign::Body") and o.Name in dict(COMPONENTS)["Gripper"] and "Placement" in dict(o.ExpressionEngine):
        o.setExpression("Placement", None); o.Placement = App.Placement()
doc.recompute()

# ---------- components ----------
comp = {}
for name, parts in COMPONENTS:
    c = doc.addObject("App::Part", name)
    c.Label = name
    for p in parts:
        c.addObject(doc.getObject(p))
    comp[name] = c

# the drive unit is defined once in its own frame (X radial); the first cap sits on the front saddle, a link to it on the rear
cap = doc.getObject("MotorCap")
cap.setExpression("Placement", E("translationm(m_front - saddle_s1 - saddle_l; pinwheel_e; axle_z)"))
cap.Label = "MotorCap (front)"
cap2 = doc.getObject("MotorCapR")             # the rear one has a single jaw (the saddle's hook holds the other side)
cap2.Label = "MotorCap (rear)"
cap2.setExpression("Placement", E("translationm(m_front - saddle_s2 - saddle_l; pinwheel_e; axle_z)"))

# the gripper component turns about the servo axis (Y through the pivot); its parts are modelled closed, in place
comp["Gripper"].setExpression("Placement", E("translationm(pivot_x; 0 mm; pivot_z) * rotationy(-grip_ang) * translationm(-pivot_x; 0 mm; -pivot_z)"))
doc.recompute()

# ---------- the class modules: in a folder, outside the base assembly (hidden; show it to edit a module) ----------
mods = doc.getObject("Modules") or doc.addObject("App::DocumentObjectGroup", "Modules")
mods.Label = "Modules (class parts: not in the base)"
for name in MODULES:
    mods.addObject(comp[name])
mods.addObject(doc.getObject("Ball"))

# ---------- base assembly: one occurrence per BASE component, three of the drive unit ----------
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Label = "Base Assembly"
joints = asm.newObject("Assembly::JointGroup", "Joints")
occ = []
for name, _ in COMPONENTS:
    if name in MODULES:
        continue
    n = 3 if name == "DriveUnit" else 1
    for k in range(n):
        l = asm.newObject("App::Link", f"{name}_{k+1}")
        l.LinkedObject = comp[name]
        l.Label = f"{name}:{k+1}"
        if name == "DriveUnit":
            l.LinkTransform = False
            l.setExpression("LinkPlacement", E(f"placement(vector(0 mm; 0 mm; 0 mm); rotation(vector(0; 0; 1); wheel_ang1 + {k} * wheel_step))"))
        else:
            l.LinkTransform = True          # sits wherever the component is (the gripper turns by grip_ang)
        occ.append(l)
doc.recompute()                             # occurrences take their places first; each ground then holds its occurrence there
for l in occ:
    g = joints.newObject("App::FeaturePython", "Ground_" + l.Name)
    JointObject.GroundedJoint(g, l)
    g.setExpression("Placement", f"{l.Name}.Placement")   # parameters move grounded occurrences (the solver keeps them there)
    g.Label = "Ground " + l.Label
    JointObject.ViewProviderGroundedJoint(g.ViewObject)
joints.ViewObject.Visibility = False

# ---------- what shows: the assembly; the definitions stay in the tree for editing ----------
for c in comp.values():
    c.ViewObject.Visibility = False
doc.getObject("Ball").ViewObject.Visibility = False      # modules: hidden (show the Modules folder's parts to edit them)
for l in occ:
    l.ViewObject.Visibility = True
HIDDEN = {"MainPCB", "FrontPCB", "WheelFrame"}           # definitions shown through other parts
for c in comp.values():
    for o in c.Group:
        if hasattr(o, "ViewObject") and o.ViewObject and not o.isDerivedFrom("App::Origin"):
            o.ViewObject.Visibility = o.Name not in HIDDEN    # inside a component: shown through the occurrences
doc.recompute()
doc.save()
result = {"components": {n: [o.Label for o in c.Group if not o.isDerivedFrom("App::Origin")] for n, c in comp.items()},
          "occurrences": [l.Label for l in occ], "invalid": [o.Label for o in doc.Objects if hasattr(o, "isValid") and not o.isValid()]}
