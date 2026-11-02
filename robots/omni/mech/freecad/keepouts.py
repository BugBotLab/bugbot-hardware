# Mechanical keep-outs for the KiCad boards: where the robot's 3D-PRINTED parts touch each board (FreeCAD -> KiCad).
# Since the master is base-only (2026-10-22) the class modules sit outside the assembly: the MAIN board's keep-outs take
# the Scorpion's modules too (GripperMount, Gripper, Kicker: it carries every add-on; user, 2026-10-23), including their
# bought parts that are not KiCad footprints (the servo, the solenoid, their screws). extra_keepouts() adds "max height"
# outlines (MCAD layer only) for every part within REACH mm of the main board that does not touch it (the NFC reader
# board, the gearmotors, the wheels...). Connectors and other KiCad parts are placed in KiCad, so they are not sent.
# Used as the boards' KeepoutHook by ecad.push(); see design/README.md.
import json, math, sys, time
from fusionflow import helpers as H, params as P, ecad
import Part
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import variants as _V
doc = App.getDocument("BugBot_Base")
asm = doc.getObject("Assembly")
t0 = time.time()


SCORPION_MODULES = ("GripperMount", "Gripper", "Kicker")
# every style's own add-ons (built into its document by build_<style>.py, not in the master): the Beetle's shield, the
# Spider's arms / magazine / tags, the Wasp's ram... (2026-10-24: the main board's parts were hitting them)
STYLE_DOCS = ("BugBot_Scorpion", "BugBot_Ant", "BugBot_Wasp", "BugBot_Beetle", "BugBot_Spider")
SHARED = ("Frame:", "DriveUnit:", "Electronics:", "SensorMast:", "NFC:", "Fasteners:", "GripperMount:", "Gripper:", "Kicker:", "Ball")


def style_leaves():
    out = []
    for dn in STYLE_DOCS:
        try:
            sd = App.getDocument(dn)
        except Exception:
            continue                                  # that style's document is not open
        for o in sd.Objects:
            if o.TypeId not in ("PartDesign::Body", "Part::Feature", "Part::FeaturePython") or not o.Visibility:
                continue
            if o.Label.startswith(SHARED) or "(KiCad)" in o.Label:
                continue
            try:
                s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
            except Exception:
                continue
            if s.Solids:
                out.append((f"{dn.replace('BugBot_', '')}:1/{o.Label}", s))
    return out
REACH = 15.0                                   # mm: parts this close to a main-board face limit the parts' height there


def leaves(with_modules=True):
    out = list(H.assembly_leaves(asm))
    if with_modules:
        for m in SCORPION_MODULES:
            out += [(n, s) for n, s, *_ in _V.module_leaves(doc, m)]
        out += style_leaves()
    return out


def gripper_sweep(step=15, top=105):
    g0 = P.sheet(doc).getContents([f"B{r}" for r in range(2, 300) if P.sheet(doc).getAlias(f"B{r}") == "grip_ang"][0])
    shapes = []
    try:
        for a in range(0, top + 1, step):
            P.set_param("grip_ang", f"{a} deg"); doc.recompute()
            shapes += [("Gripper swing 0-105 deg", s.copy()) for n, s in leaves() if n.startswith("Gripper:")]
    finally:
        P.set_param("grip_ang", g0.lstrip("=")); doc.recompute()
    return shapes                              # every arm position; the outlines are merged per name


ADDON_BOUGHT = {"Servo", "Solenoid", "SolenoidCoil", "SolenoidPlunger", "SolenoidSpring", "M3ThinNut", "ServoHorn", "PivotBushing",
                "Servo mount screws", "Servo mount pivot screw", "Kicker screws", "Gripper screws"}
PRINTED = {"PivotTube", "TagBar", "Chassis", "MotorCap (front)", "MotorCap (rear)", "WheelHalfOuter", "WheelHalfMotor", "WheelFrameOne", "KickBracket", "KickDisc",
           "BattCradle", "Mast", "TopDeck", "Dome", "ServoBlock", "HoopBracket", "HoopArmL", "HoopArmR", "HoopSleeve"}


def board_shapes(board_name):
    own = {"MainBoard": "Electronics:1/MainBoard (KiCad)", "FrontSensorBoard": "Electronics:1/FrontSensorBoard (KiCad)"}
    groups = {}                               # one shape per part (a whole wheel counts as one part)
    wanted = PRINTED | (ADDON_BOUGHT if board_name == "MainBoard" else set())
    for n, s in leaves(with_modules=(board_name == "MainBoard")):
        style_part = n.split(":")[0] in [d.replace("BugBot_", "") for d in STYLE_DOCS]
        if n.startswith("Electronics:1/") or (n.split("/")[-1] not in wanted and not (style_part and board_name == "MainBoard")):
            continue                              # printed parts (+ the add-ons' bought bodies on the main board)
        key = n.split("/")[0] + "/" + n.split("/")[-1]
        groups.setdefault(key, []).append(s)
    out = [(k, v[0] if len(v) == 1 else Part.makeCompound(v)) for k, v in groups.items()]
    return out


def extra_keepouts(board):
    """'max height' outlines for the main board: every part within REACH of a board face that does not touch it."""
    if board.Name != "MainBoard":
        return []
    inv = board.Placement.inverse()
    t = P.sheet(doc).get("pcb_t").Value if hasattr(P.sheet(doc).get("pcb_t"), "Value") else 1.6
    groups = {}
    for n, s in leaves():
        last = n.split("/")[-1]
        if n.startswith("Electronics:1/") or "EncBoard" in last or n.startswith("Ball"):
            continue                              # the board itself, its plug-in boards, the encoder boards (their sockets)
        groups.setdefault(n.split("/")[0] + "/" + last, []).append(s)
    # the board's outline as a face in its own frame (underside at z = 0), as ecad.keepouts() builds it
    sk = board.OutlineSketch
    outer = max(sk.Shape.Wires, key=lambda w: w.BoundBox.DiagonalLength).copy()
    outer.Placement = sk.getGlobalPlacement(); outer.transformShape(inv.toMatrix(), True)
    face = Part.Face(outer); face.translate(App.Vector(0, 0, -face.BoundBox.ZMin))
    prism = {"F": face.copy().translate(App.Vector(0, 0, t)).extrude(App.Vector(0, 0, REACH)),
             "B": face.copy().translate(App.Vector(0, 0, -REACH)).extrude(App.Vector(0, 0, REACH))}
    out = []
    for key, ss in groups.items():
        sh = ss[0] if len(ss) == 1 else Part.makeCompound(ss)
        b = sh.copy(); b.transformShape(inv.toMatrix(), True)
        for side in ("F", "B"):
            # only the part of it over (or under) the board counts: long parts reach round the board's edge
            # (the Spider's arm plates, the gripper's arms), so their whole box says nothing about the gap
            if not b.BoundBox.intersect(prism[side].BoundBox):
                continue
            try:
                over = b.common(prism[side])
            except Exception:
                continue
            if not over.Solids or over.Volume < 1e-3:
                continue
            gap = over.BoundBox.ZMin - t if side == "F" else -over.BoundBox.ZMax
            if not (0.05 < gap <= REACH):
                continue                          # touching (a hard keep-out already) or too far to matter
            # (0.05, not 0.3: the gripper's left arm rides exactly 0.3 above the board, which the touch test (< 0.3)
            # missed too; such a part now gets a 'max 0.3 mm' outline, which nothing fits under)
            back = over.copy(); back.transformShape(board.Placement.toMatrix(), True)
            kos = ecad.keepouts(board, [(key, back)], touch=REACH)
            for k in kos:
                if k["side"] == side:
                    k["gap"] = math.floor(gap * 10) / 10
                    out.append(k)
    return out


def shapes_for(board):
    """KeepoutHook for the BugBot boards: every mechanical part + the gripper's whole swing."""
    return board_shapes(board.Name)


if globals().get("RUN_ALL", True):             # run directly: write both boards' keep-outs to design/schematics/*/keepouts.json
    result = {}
    for bname in ("MainBoard", "FrontSensorBoard"):
        b = doc.getObject(bname)
        ko = ecad.keepouts(b, board_shapes(bname)) + extra_keepouts(b)
        json.dump(ko, open(BB + f"/design/schematics/{'Main' if bname == 'MainBoard' else 'Front'}/keepouts.json", "w"))
        result[bname] = [(k["name"], k["side"], k["area"]) for k in ko]
    result["seconds"] = round(time.time() - t0, 1)
