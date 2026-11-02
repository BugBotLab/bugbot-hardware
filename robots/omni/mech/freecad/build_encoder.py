# BugBot in FreeCAD: the wheel encoders (approved 2D sketch: mech/freecad/sketches/wheel_encoder_v3.png).
# Run after build_wheel.py / build_chassis.py / build_ecad.py, before build_structure.py (re-runnable: replaces its own parts).
#   MagnetRing   printed ring on the wheel's outer hub face (part of WheelFrameOne): holds the 6 x 2.5 magnet, glued
#   EncMagnet    the diametric NdFeB magnet (in the Wheel component, turns with it)
#   EncBoard     the KiCad encoder board (kicad/BugBot_Enc), in the DriveUnit component: it shows on all 3 wheels.
#                It hangs from a 1x4 1.27 mm socket on the main board's underside; its bottom edge sits in a plate slot.
#   Chassis      per wheel: EncSlot (plate slot, 0.2 a side), EncSeat (flat seat where the curved wall would touch the board),
#                EncLeads (pocket for the header's clipped leads), EncSocket (wall-top notch under the main board socket),
#                EncRingRelief (plate relief under the magnet ring, which turns 0.1 mm into the plate otherwise),
#                EncGuideL/R + EncGuideSlotL/R: card guides (approved 2D: sketches/enc_retention_v1.png): a rib each side of the
#                board with a 1.2 groove (0.2 a side, 0.8 deep: its lip covers 0.5 of the board edge, clear of the MT6701's
#                pads 1.15 in); the board slides down in from above and is held on 3 edges; the socket only connects
# Drive-unit frame: X radial, axle at y = pinwheel_e (8), z = axle_z (12); the hub face is at x = wf (32.55).
import math, os
import Part
from fusionflow import ecad
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
K = BB + "/design"
ev = lambda s: float(doc.Params.evalExpression(s.replace("Params.", "")).Value) if hasattr(doc.Params.evalExpression(s.replace("Params.", "")), "Value") else float(doc.Params.evalExpression(s))
E_, AZ, WF, WW = ev("pinwheel_e"), ev("axle_z"), ev("wf"), ev("wheel_w")
MAG_D, MAG_T, RING_RI, RING_RO, RING_H = 6.0, 2.5, 3.2, 4.0, 1.2
X_BACK = 37.97                   # encoder board back face (its front, with the chip, faces the wheel: 1.4 mm gap to the magnet)
PCB_T = 0.8
X_FRONT = X_BACK - PCB_T
BY0, BY1 = 3.0, 11.0             # board edges (chip on the axle at y 8)
BZ0, BZ1 = 7.5, 24.2             # board bottom / top
log = {}

def drop(name):
    o = doc.getObject(name)
    if o:
        if hasattr(o, "Proxy") and o.TypeId == "Part::FeaturePython" and hasattr(o, "KicadPcb"):
            try: ecad.stop(o)
            except Exception: pass
        for p in list(o.InList):
            if hasattr(p, "removeObject") and o in getattr(p, "Group", []): p.removeObject(o)
        doc.removeObject(name)

# ---------- 1. magnet ring on the wheel's outer hub face (Wheel local: axle = Z, outer face at z = +wheel_w / 2) ----------
wf1 = doc.getObject("WheelFrameOne")
for n in ("MagnetPocket", "MagnetRing"):
    o = doc.getObject(n)
    if o:
        if wf1.Tip == o: wf1.Tip = o.BaseFeature
        wf1.removeObject(o); doc.removeObject(n)
doc.recompute()
ring = wf1.newObject("PartDesign::AdditiveCylinder", "MagnetRing")
ring.Radius = RING_RO; ring.Height = RING_H
ring.Placement = App.Placement(V(0, 0, WW / 2), App.Rotation())
pkt = wf1.newObject("PartDesign::SubtractiveCylinder", "MagnetPocket")
pkt.Radius = RING_RI; pkt.Height = RING_H + 0.1                    # 0.2 a side round the 6 mm magnet: glued, any printer
pkt.Placement = App.Placement(V(0, 0, WW / 2), App.Rotation())
for f_ in (ring, pkt): f_.Refine = False                     # Refine fails on this frame ("Removing splitter failed")
wf1.Tip = pkt
doc.recompute()
bad = [f_.Name for f_ in (ring, pkt) if f_.Shape.isNull() or "Invalid" in f_.State]
assert not bad, f"magnet ring features failed: {bad}"      # the body stays 'valid' on its last good shape, so check each feature
log["ring_top_z"] = round(wf1.Shape.BoundBox.ZMax, 3)

# ---------- 2. the magnet (in the Wheel component, turns with the wheel) ----------
drop("EncMagnet")
mag = doc.addObject("Part::Cylinder", "EncMagnet")
mag.Radius = MAG_D / 2; mag.Height = MAG_T
mag.Placement = App.Placement(V(0, 0, WW / 2), App.Rotation())
mag.ViewObject.ShapeColor = (0.75, 0.15, 0.12)
doc.getObject("Wheel").addObject(mag)

# ---------- 3. the encoder board (KiCad link) in the DriveUnit component ----------
drop("EncBoard")
eb = ecad.make(doc, "EncBoard", K + "/schematics/Enc/BugBot_Enc.kicad_pcb")
eb.Label = "EncBoard (KiCad)"
eb.SubstrateColour = (0.11, 0.40, 0.22)
# KiCad board frame (STEP: X across, Y up = -KiCad Y, Z = top-side normal; origin = chip centre, z 0 = back face)
#   -> drive-unit frame: X_s -> -y, Y_s -> +z, Z_s -> -x; origin at (X_BACK, pinwheel_e, axle_z)
m = App.Matrix(0, 0, -1, X_BACK, -1, 0, 0, E_, 0, 1, 0, AZ, 0, 0, 0, 1)
eb.Placement = App.Placement(m)
du = doc.getObject("DriveUnit")
if du: du.addObject(eb)
ecad.sync(eb, wait=True)
bb = eb.Shape.BoundBox
log["board_bbox"] = [round(v, 2) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)]

# ---------- 4. chassis: per wheel, subtractive boxes in the drive-unit frame turned to that wheel ----------
ch = doc.getObject("Chassis")
for o in [o for o in ch.Group if o.Name.startswith("Enc")]:
    pass
old = [o for o in ch.Group if o.Label.startswith("Enc") and o.TypeId in ("PartDesign::SubtractiveBox", "PartDesign::AdditiveBox")]
if old:
    first = old[0]
    ch.Tip = first.BaseFeature
    for o in old:
        ch.removeObject(o); doc.removeObject(o.Name)
    doc.recompute()
R_BODY = ev("body_r")
GUIDE_X1 = lambda y0, y1: min(39.0, math.sqrt(R_BODY ** 2 - max(abs(y0), abs(y1)) ** 2) - 0.4)
BOXES = [  # label, x0, x1, y0, y1, z0, z1
    ("EncSlot", X_FRONT - 0.2, X_BACK + 0.2, BY0 - 0.3, BY1 + 0.3, BZ0 - 0.2, 10.6),     # plate slot 1.2 x 8.6, floor 0.8 (z 7.3)
    ("EncSeat", 36.6, X_BACK + 0.2, BY0 - 0.3, BY1 + 0.3, 8.1, BZ1 + 0.4),              # wall cut flat 0.2 behind the board
    ("EncLeads", X_BACK - 0.1, 38.7, 4.6, 9.4, 22.4, 29.01),                             # clipped header leads (<= 0.5 mm): a channel up to
                                                                                         # the wall top, so they pass the wall as the board drops into its guides
    ("EncRingRelief", 33.3, 34.3, 3.4, 12.6, 7.4, 8.2),                                  # plate under the turning magnet ring: 0.6 below it, 0.9 floor left
    ("EncSocket", 35.0, 38.1, 3.85, 10.15, 24.4, 29.01),                                 # wall top under the main board socket (THT, body +-1.0 round x 36.12: 0.4+ all round)
    # the board's way in from above: its full width (+ the guides' play) cut through the wall top over the seat (the wall
    # curves in over the board's outer edge: without this the board cannot drop past it into the guides)
    ("EncDrop", X_FRONT - 0.2, X_BACK + 0.2, BY0 - 0.3, BY1 + 0.3, 24.0, 29.01),
    # card guides: ribs (added) from the plate top to just under the board top, 1.0 lip in front of the board, into the wall
    # (each rib stops 0.4 inside the OUTER wall face at its far corner: the wall curves away, a straight box poked out)
    ("+EncGuideL", X_FRONT - 1.2, GUIDE_X1(BY0 - 0.3 - 1.4, BY0 + 0.5), BY0 - 0.3 - 1.4, BY0 + 0.5, 8.0, 24.0),
    ("+EncGuideR", X_FRONT - 1.2, GUIDE_X1(BY1 - 0.5, BY1 + 0.3 + 1.4), BY1 - 0.5, BY1 + 0.3 + 1.4, 8.0, 24.0),
    # ... and their grooves, open at the top so the board drops in (floor = the plate slot's, z 7.3)
    ("EncGuideSlotL", X_FRONT - 0.2, X_BACK + 0.2, BY0 - 0.3, BY0 + 0.5, 7.3, 24.1),
    ("EncGuideSlotR", X_FRONT - 0.2, X_BACK + 0.2, BY1 - 0.5, BY1 + 0.3, 7.3, 24.1),
]
a1, step = ev("wheel_ang1"), ev("wheel_step")
for k in range(3):
    th = a1 + k * step; c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    for lab, x0, x1, y0, y1, z0, z1 in BOXES:
        add = lab.startswith("+"); lab = lab.lstrip("+")
        bx = ch.newObject("PartDesign::AdditiveBox" if add else "PartDesign::SubtractiveBox", f"{lab}{k + 1}")
        bx.Label = f"{lab}{k + 1}"
        bx.Length, bx.Width, bx.Height = x1 - x0, y1 - y0, z1 - z0
        bx.Placement = App.Placement(V(x0 * c - y0 * s, x0 * s + y0 * c, z0), App.Rotation(V(0, 0, 1), th))
        ch.Tip = bx
doc.recompute()
log["chassis_valid"] = ch.isValid()
# wall left beside each cut: outer radius minus the cut's outer face, at its corners
R_OUT = ev("body_r")
walls = []
for lab, x0, x1, y0, y1, z0, z1 in BOXES:
    if lab.startswith("+"):
        continue
    for y in (y0, y1):
        walls.append((lab, round(math.sqrt(R_OUT ** 2 - y ** 2) - x1, 2)))
log["wall_left_at_cut_corners"] = walls
doc.recompute()
# new features reset the chassis / wheel colours to grey: put the colour scheme back
_g = dict(globals()); exec(open(os.path.join(os.path.dirname(K), "bugbot_freecad", "apply_colours.py"), encoding="utf-8").read(), _g)
doc.save()
result = log
