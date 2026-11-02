# BugBot fasteners: every screw, nut and pin the build needs, modelled at its real size and finish, in the component
# it moves with, so the assembly shows what goes where and the interference check proves each one fits.
#   python fusionflow/ffclient.py run mech/freecad/build_fasteners.py        (build_all.py runs it before build_structure)
# Threads are modelled at their root diameter (M2 1.6, M3 2.5, M1.2 0.9): a self-tapping screw then fills its pilot
# without showing as a clash; anything the check still reports is a real one.
# Positions come from the same Params as the holes (evaluated here), so a parameter change moves them on the next rebuild.
import math
import Part
V = App.Vector
doc = App.getDocument("BugBot_Base")
P = doc.Params
q = lambda e: float(P.evalExpression(e if e.startswith("Params.") or not e[0].isalpha() else "Params." + e).Value) \
    if not isinstance(e, (int, float)) else float(e)

# ---------- shapes (local frame: the head's bearing face at z = 0, the shank along +z into the hole) ----------
SIZES = {   # d, root, socket head D x H, hex key, pan head D x H
    "M1.2": (1.2, 0.9, None, None, (2.2, 0.8)),
    "M2": (2.0, 1.6, (3.8, 2.0), 1.5, (3.8, 1.4)),
    "M3": (3.0, 2.5, (5.5, 3.0), 2.5, (5.6, 1.8)),
}


def hexprism(af, h, z0=0.0):
    r = af / math.sqrt(3)
    w = Part.makePolygon([V(r * math.cos(math.radians(30 + 60 * k)), r * math.sin(math.radians(30 + 60 * k)), z0) for k in range(7)])
    return Part.Face(w).extrude(V(0, 0, h))


def screw(size, length, head="socket", low=False):
    d, root, sock, key, pan = SIZES[size]
    shank = Part.makeCylinder(root / 2, length, V(0, 0, 0))
    if head == "socket":
        D, H = sock
        if low:
            H = H * 2 / 3                                           # DIN 7984 low head
        h = Part.makeCylinder(D / 2, H, V(0, 0, -H))
        h = h.cut(hexprism(key, H * 0.6, -H - 0.01))
    elif head == "button":                                          # ISO 7380 button head, hex socket
        D, H = (5.7, 1.65) if size == "M3" else (3.5, 1.3)
        h = Part.makeCylinder(D / 2, H, V(0, 0, -H))
        try:
            h = h.makeFillet(H * 0.6, [e for e in h.Edges if abs(e.BoundBox.ZMin + H) < 1e-6 and e.Curve.TypeId == "Part::GeomCircle"])
        except Exception:
            pass
        h = h.cut(hexprism(key, H * 0.6, -H - 0.01))
    else:                                                           # pan head, cross recess
        D, H = pan
        h = Part.makeCylinder(D / 2, H, V(0, 0, -H))
        try:
            h = h.makeChamfer(H * 0.4, [e for e in h.Edges if abs(e.BoundBox.ZMin + H) < 1e-6 and e.Curve.TypeId == "Part::GeomCircle"])
        except Exception:
            pass
        s = D * 0.45
        h = h.cut(Part.makeBox(s, s / 4, H * 0.6, V(-s / 2, -s / 8, -H - 0.01))).cut(Part.makeBox(s / 4, s, H * 0.6, V(-s / 8, -s / 2, -H - 0.01)))
    return h.fuse(shank).removeSplitter()


def nut(size, h, af, nyloc=False):
    d, root = SIZES[size][:2]
    n = hexprism(af, h).cut(Part.makeCylinder(root / 2, h + 1, V(0, 0, -0.5)))
    if nyloc:                                                       # the nylon insert shows as a ring on top
        n = n.cut(Part.makeCylinder(af * 0.45, h * 0.35, V(0, 0, h * 0.65)).cut(Part.makeCylinder(root / 2 + 0.2, h, V(0, 0, 0))))
    return n


def washer(di, do, t):
    return Part.makeCylinder(do / 2, t).cut(Part.makeCylinder(di / 2, t + 1, V(0, 0, -0.5)))


def place(shape, at, direction):
    """local +z -> direction, local origin -> at"""
    s = shape.copy()
    rot = App.Rotation(V(0, 0, 1), V(*direction))
    s.Placement = App.Placement(V(*at), rot)
    return s


# ---------- the list: (group, label, shape, head point, direction into the hole) ----------
G = {}
def add(group, label, shp, at, direction):
    G.setdefault(group, []).append((label, place(shp, at, direction)))


ZT, ZB = q("pcb_top"), q("pcb_z")
UP, DOWN = (0, 0, 1), (0, 0, -1)
# board to the chassis posts: pan-head self-tappers from the top of the board
for k in range(1, 5):
    a = math.radians(q(f"boss_a{k}")); r = q("boss_r")
    add("Zinc", f"Post screw {k} M2x6", screw("M2", 6, "pan"), (r * math.cos(a), r * math.sin(a), ZT), DOWN)
# mast base, servo block, hoop bracket: from under the board, up into the part
mx, my = q("mast_screw_x"), q("mast_screw_y")
for sg in (1, -1):
    add("Zinc", f"Mast base screw M2x6 ({'+' if sg > 0 else '-'}Y)", screw("M2", 6, "pan"), (mx, sg * my, ZB), UP)
add("Mount", "Servo block screw M2x6", screw("M2", 6, "pan"), (q("servo_x0") - 2.3, q("ear_y") + 2.15, ZB), UP)
for sg in (1, -1):
    add("Mount", f"Hoop bracket screw M2x6 ({'+' if sg > 0 else '-'})", screw("M2", 6, "pan"), (q("pivot_x") + sg * q("hoopbr_dx"), q("hoopbr_y"), ZB), UP)
# kick bracket tabs: through the board from the top
for nm in ("rear", "front"):                    # (kicker module: in the Kicker component, not the base's fasteners)
    add("Kick", f"Kick bracket screw M2x5 ({nm})", screw("M2", 5, "pan"), (q(f"kb_{nm}_x"), q(f"kb_{nm}_y"), ZT), DOWN)
# top deck: into the mast, and machine screws into the two brass standoffs (top + bottom)
ZD = q("mast_top") + q("deck_t")
for sg in (1, -1):
    add("Zinc", f"Deck-to-mast screw M2x6 ({'+' if sg > 0 else '-'}Y)", screw("M2", 6, "pan"), (mx, sg * my, ZD), DOWN)
    lx, ly = q("deck_leg_x"), sg * q("deck_leg_y")
    add("Zinc", f"Standoff screw top M2x6 ({'+' if sg > 0 else '-'}Y)", screw("M2", 6, "pan"), (lx, ly, ZD), DOWN)      # into the printed standoff
    add("Zinc", f"Standoff screw bottom M2x6 ({'+' if sg > 0 else '-'}Y)", screw("M2", 6, "pan"), (lx, ly, ZB), UP)
# SG90 ears (its own screws), 2.5 mm ears  (servo block, hoop bracket, ears, pivot: the GripperMount module's screws)
ear_face = q("ear_y") - 2.5
for nm, x in (("rear", q("ear_x0")), ("front", q("ear_x1"))):
    add("Mount", f"Servo ear screw M2x8 ({nm})", screw("M2", 8, "pan"), (x, ear_face, q("pivot_z")), (0, 1, 0))
# front sensor board: from behind, through the board into the mast front
for y in (q("fsb_y0") + 2,):                                   # one screw is enough (the header holds the bottom)
    add("Zinc", f"Front board screw M2x4 (y {y:+.1f})", screw("M2", 4, "pan"), (q("fsb_x"), y, q("fsb_z0") + q("fsb_h") - 2), (1, 0, 0))
# solenoid: low-head M3 through the bracket's side plate
y0 = -q("sol_depth") / 2 - q("sol_dy")
for dx in (-5.5, 5.5):
    add("Kick", f"Solenoid screw M3x4 ({'rear, DIN 7984 low head' if dx < 0 else 'front, ISO 7380 button head'})", screw("M3", 4, low=True) if dx < 0 else screw("M3", 4, "button"),
        (q("sol_x0") + q("sol_len") / 2 + dx, y0 - q("kb_t") + (0.5 if dx > 0 else 0.0), q("sol_z")), (0, 1, 0))   # front: button head sunk 0.5
# gripper pivot (arm R): M2x10 through the bracket post and the arm, nyloc on the arm's inside
y_post = -(q("hoop_y") + q("arm_t") / 2 + 0.4 + 3.2)
add("MountBlack", "Pivot screw M2x12", screw("M2", 12), (q("pivot_x"), y_post, q("pivot_z")), (0, 1, 0))
y_tube_end = -(q("hoop_y") + q("arm_t") / 2) + q("bush_recess") + (q("bush_l") - q("bush_fl_t")) + 0.15     # the clamped brass tube ends here
add("Mount", "Pivot washer M2", washer(2.2, 5.0, 0.3), (q("pivot_x"), y_tube_end, q("pivot_z")), (0, 1, 0))
add("Mount", "Pivot nyloc nut M2", nut("M2", 2.8, 4.0, True), (q("pivot_x"), y_tube_end + 0.3, q("pivot_z")), (0, 1, 0))
# --- the gripper (moves with it) ---
px, pz, hy = q("pivot_x"), q("pivot_z"), q("horn_y")
add("GripZinc", "Horn screw (SG90, centre) M2x4", screw("M2", 4, "pan"), (px, hy, pz), (0, -1, 0))
for dz in (4.5, 8.5):
    add("GripZinc", f"Horn-to-arm screw M1.2x4 (+{dz})", screw("M1.2", 4, "pan"), (px, hy - 1.3, pz + dz), (0, 1, 0))
# --- each drive unit (drive frame: X along the motor, the axle at y = pinwheel_e, z = axle_z) ---
e, ztop = q("pinwheel_e"), q("axle_z") + q("mcap_ear_top")       # on the stepped-down screw ear
xf = q("m_front") - q("saddle_s1") - q("saddle_l") / 2; xr = q("m_front") - q("saddle_s2") - q("saddle_l") / 2
sy = q("saddle_screw_y")
for nm, x, ys in (("front", xf, (e + sy, e - sy)), ("rear", xr, (e + sy,))):
    for y in ys:
        add("Drive", f"Motor cap screw M2x6 ({nm}, y {y - e:+.1f})", screw("M2", 6, "pan"), (x, y, ztop), DOWN)
# --- each wheel (wheel frame: z along the axle, the outer half z 0..w_half): M2x10 socket heads in the counterbores ---
zc = q("w_half") - q("w_head_h")
for k in range(0 if float(getattr(P.get("w_one_piece"), "Value", P.get("w_one_piece"))) > 0.5 else 3):        # one-piece wheel frame: no screws
    a = math.radians(30 + 120 * k + 0); r = q("w_screw_r")
    pt = (r * math.cos(math.radians(-90 + 120 * k)), r * math.sin(math.radians(-90 + 120 * k)), zc)
    add("Wheel", f"Wheel screw M2x10 button head ({k + 1})", screw("M2", 10, "button"), pt, DOWN)

# (the LED beacon is a bought jewel on a foam pad since 2026-10-31: no screws; build_ledpcb.py)

# --- the NFC floor PCB (nfc_layout.py): 3 nylon M2x5 from below hold it under the floor (the reader is on it: no tray screws) ---
if doc.Params.getCellFromAlias("nfc_ang") is not None:
    import os as _os                                  # repo-relative paths: see .bugbot-root
    _d = _os.path.dirname(_os.path.abspath(__file__))
    while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
    BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
    exec(open(BB + "/mech/freecad/nfc_layout.py", encoding="utf-8").read())
    for k, (x, y) in enumerate(CLAMPS):
        add("Nylon", f"NFC antenna board screw M2x5 nylon pan ({k + 1})", screw("M2", 5, "pan"), (x, y, PLATE_Z - 1.6), UP)   # through the 1.6 antenna PCB

# --- the rear ID tag (tag_mounts.py): the bar snaps on, so screw_points() is empty (it was 2 M2x6 for the old tag plate) ---
if doc.getObject("TagBar") is not None or doc.getObject("TagPlate") is not None:
    import sys as _sys, importlib as _il
    _sys.path.insert(0, BB + "/mech/freecad")
    import tag_mounts as _tm; _il.reload(_tm)
    for (at, dirn), nm in zip(_tm.screw_points(doc), ("+Y", "-Y")):
        add("Zinc", f"Tag plate screw M2x6 ({nm})", screw("M2", 6, "pan"), at, dirn)

# ---------- objects: one per finish and component, so the colours and the assembly come out right ----------
GROUPS = {   # group: (object name, label, colour)
    "Zinc": ("FastenersZinc", "Fasteners (zinc)", (0.77, 0.78, 0.81)),
    "Black": ("FastenersBlack", "Fasteners (black oxide)", (0.17, 0.17, 0.18)),
    "Nylon": ("FastenersNylon", "Fasteners (nylon)", (0.77, 0.78, 0.81)),   # shown steel grey like the other screws
    "GripZinc": ("GripperScrews", "Gripper screws", (0.77, 0.78, 0.81)),
    "Drive": ("MotorCapScrews", "Motor cap screws", (0.77, 0.78, 0.81)),
    "Wheel": ("WheelScrews", "Wheel screws", (0.17, 0.17, 0.18)),
    "Kick": ("KickerScrews", "Kicker screws", (0.77, 0.78, 0.81)),          # the kicker module's own screws
    "Mount": ("ServoMountScrews", "Servo mount screws", (0.77, 0.78, 0.81)),        # the GripperMount module's screws
    "MountBlack": ("ServoMountPivotScrew", "Servo mount pivot screw", (0.17, 0.17, 0.18)),
}
COMPONENT = {"FastenersZinc": "Fasteners", "FastenersBlack": "Fasteners", "FastenersNylon": "Fasteners",   # put each object
             "GripperScrews": "Gripper", "MotorCapScrews": "DriveUnit", "KickerScrews": "Kicker",
             "ServoMountScrews": "GripperMount", "ServoMountPivotScrew": "GripperMount"}                                  # back in its component
report = {}
for g, (name, _, _) in GROUPS.items():    # an empty group (no wheel screws on a one-piece frame; no black screws in the base
    old = doc.getObject(name)             # since the pivot screw went to the servo mount): drop its old object
    if g not in G and old:
        for p in list(old.InList):
            if hasattr(p, "removeObject"): p.removeObject(old)
        doc.removeObject(name)
for g, items in G.items():
    name, label, col = GROUPS[g]
    old = doc.getObject(name)
    if old:
        for p in list(old.InList):
            if hasattr(p, "removeObject"):
                p.removeObject(old)
        doc.removeObject(name)
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.makeCompound([s for _, s in items])
    o.Label = label
    o.addProperty("App::PropertyStringList", "Items", "Fasteners", "what is in it")
    o.Items = [n for n, _ in items]
    if App.GuiUp:
        o.ViewObject.ShapeColor = col
    comp = doc.getObject(COMPONENT.get(name, ""))              # run on its own, this used to leave the screws outside
    if comp is not None and comp.TypeId == "App::Part":        # their components (and the variants lost them)
        comp.addObject(o)
    report[name] = len(items)
wheel = doc.getObject("Wheel")
if wheel and doc.getObject("WheelScrews"):
    wheel.addObject(doc.getObject("WheelScrews"))
doc.recompute()
result = {"objects": report, "total": sum(report.values()) + 3 * (report.get("MotorCapScrews", 0) + report.get("WheelScrews", 0)) - report.get("MotorCapScrews", 0) - report.get("WheelScrews", 0)}
