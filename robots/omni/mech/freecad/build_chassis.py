# BugBot rebuilt in FreeCAD through FusionFlow: master parameters (the 'Params' sheet) and the chassis body.
# Run with:  python fusionflow/ffclient.py run mech/freecad/build_chassis.py
# Port of bugbot_chassis.scad: every size is bound to a parameter, so Change Parameters drives the model.
import os
from fusionflow import params as P, helpers as H, extrude as X

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = _os.path.join(BB, "bugbot_freecad")

exec(open(os.path.join(OUT, "bugbot_params.py"), encoding="utf-8").read())   # PARAMS: the master list


exec(open(os.path.join(OUT, "bb_lib.py"), encoding="utf-8").read())   # ev, dims, rect, circ, rotated_sketch, frame_sketch, pocket


# ---------- document + master parameters ----------
if "BugBot_Base" in App.listDocuments():
    App.closeDocument("BugBot_Base")
doc = H.new_doc("BugBot_Base")
P.set_params(PARAMS, doc)

# ---------- chassis ----------
body = H.body("Chassis")
zaxis = next(o for o in body.Origin.OriginFeatures if o.Role == "Z_Axis")

# base plate
s = H.sketch(body, "XY", "PlateSketch")
circ(s, "plate", "0 mm", "0 mm", "2 * Params.body_r")
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z")
doc.recompute()
f = X.extrude(s, "plate_t", "Join"); f.Label = "Plate"

# wall
s = H.sketch(body, "XY", "WallSketch")
circ(s, "wall_out", "0 mm", "0 mm", "2 * Params.body_r")
circ(s, "wall_in", "0 mm", "0 mm", "2 * Params.r_inner")
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z")
doc.recompute()
f = X.extrude(s, "pcb_z - plate_z", "Join"); f.Label = "Wall"

# PCB posts
s = H.sketch(body, "XY", "PostSketch")
for k in range(1, 5):
    a = f"Params.boss_a{k}"
    circ(s, f"post{k}", f"Params.boss_r * cos({a})", f"Params.boss_r * sin({a})", "Params.boss_d")
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z")
doc.recompute()
f = X.extrude(s, "pcb_z - plate_z", "Join"); f.Label = "Posts"

# inside fillet where the wall meets the base plate (revolved), before the wheel windows so they cut it where the wheels pass
import math, Part as _Part
s = H.sketch(body, "XZ", "WallFilletSketch")
ri, pt, fr = ev("Params.r_inner"), ev("Params.plate_z + Params.plate_t"), ev("Params.wall_fillet")
l1 = s.addGeometry(_Part.LineSegment(Vector(ri, pt, 0), Vector(ri - fr, pt, 0)), False)
ar = s.addGeometry(_Part.ArcOfCircle(_Part.Circle(Vector(ri - fr, pt + fr, 0), Vector(0, 0, 1), fr), -math.pi / 2, 0), False)
l2 = s.addGeometry(_Part.LineSegment(Vector(ri, pt + fr, 0), Vector(ri, pt, 0)), False)
doc.recompute()
import Sketcher as _Sk
s.addConstraint([_Sk.Constraint("Coincident", l1, 2, ar, 1), _Sk.Constraint("Coincident", ar, 2, l2, 1), _Sk.Constraint("Coincident", l2, 2, l1, 1)])
doc.recompute()
rv = body.newObject("PartDesign::Revolution", "WallFillet")
rv.Profile = s; rv.ReferenceAxis = (s, ["V_Axis"]); rv.Angle = 360
doc.recompute(); H.settle_sketch(s); s.ViewObject.Visibility = False

# wheel 1 frame: X radial toward the wheel, Z up; every wheel feature below is patterned x3 round Z
lcs = body.newObject("PartDesign::CoordinateSystem", "WheelFrame")
lcs.AttachmentSupport = [(next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane"), "")]
lcs.MapMode = "ObjectXY"
lcs.AttachmentOffset = App.Placement(Vector(), App.Rotation(Vector(0, 0, 1), 40))
lcs.setExpression(".AttachmentOffset.Rotation.Angle", "Params.wheel_ang1")
doc.recompute()

wheel_feats = []
for k, sv in ((1, "Params.saddle_s1"), (2, "Params.saddle_s2")):
    # saddle profile across the radial line (sketch X = sideways, Y = up), padded outward toward the wheel.
    # front: symmetric; rear: its low side stays short (the next motor's tail is there)
    s = frame_sketch(body, lcs, f"Saddle{k}Sketch", "ObjectYZ", f"Params.m_front - {sv} - Params.saddle_l")
    lo = "Params.saddle_w / 2" if k == 1 else "Params.saddle_rlo"
    rect(s, f"sad{k}", f"Params.pinwheel_e - {lo}", "Params.plate_z + Params.plate_t",
         f"{lo} + Params.saddle_w / 2", "Params.axle_z - Params.plate_z - Params.plate_t")
    doc.recompute()
    f = X.extrude(s, "saddle_l", "Join"); f.Label = f"Saddle{k}"
    wheel_feats.append(f)
    if k == 2:     # the fixed hook on the rear saddle's low side: the motor rolls in under it, one jaw clamps the other side
        s = frame_sketch(body, lcs, "HookSketch", "ObjectYZ", f"Params.m_front - {sv} - Params.saddle_l")
        rect(s, "hook", "Params.pinwheel_e - Params.saddle_rlo", "Params.axle_z",
             "Params.saddle_rlo - Params.mcap_slot / 2 - 1 mm", "Params.mcap_t")
        doc.recompute()
        f = X.extrude(s, "saddle_l", "Join"); f.Label = "RearHook"
        wheel_feats.append(f)

# (drop skids under the saddles removed at the user's request: they made the chassis harder to print)

s = frame_sketch(body, lcs, "MotorGrooveSketch", "ObjectYZ", "Params.m_front - (Params.saddle_s1 + Params.saddle_s2 + Params.saddle_l) / 2")
circ(s, "groove", "Params.pinwheel_e", "Params.axle_z", "Params.motor_d + 0.4 mm")   # the gearbox ring is 6.15: 0.12 per side, drops in on any printer
doc.recompute()
wheel_feats.append(pocket(s, "Length", "Params.saddle_s2 + Params.saddle_l - Params.saddle_s1 + 2 mm", mid=True, label="MotorGroove"))

s = frame_sketch(body, lcs, "SaddlePilotSketch", "ObjectXY", "Params.plate_z + Params.saddle_pilot_floor")
for k, sv in ((1, "Params.saddle_s1"), (2, "Params.saddle_s2")):
    for j, sg in (((1, "+"), (2, "-")) if k == 1 else ((1, "+"),)):
        circ(s, f"pil{k}{j}", f"Params.m_front - {sv} - Params.saddle_l / 2", f"Params.pinwheel_e {sg} Params.saddle_screw_y", "Params.pilot_d")
doc.recompute()
wheel_feats.append(pocket(s, reverse=True, label="SaddlePilots"))   # blind: up from inside the plate, saddle_pilot_floor stays closed

s = frame_sketch(body, lcs, "WheelWindowSketch", "ObjectXY", "0 mm")
rect(s, "win", "Params.wf - Params.wheel_w - 1 mm", "Params.pinwheel_e - Params.wheel_r - 1 mm",
     "Params.wheel_w + 2 mm", "2 * Params.wheel_r + 2 mm")
doc.recompute()
wheel_feats.append(pocket(s, mid=True, label="WheelWindow"))

pp = body.newObject("PartDesign::PolarPattern", "WheelPattern")
pp.Originals = wheel_feats
pp.Axis = (zaxis, [""])
pp.Angle = 360
pp.Occurrences = 3
body.Tip = pp
doc.recompute()

# the wheel windows stop at the wall's inside face: put the full wall back (the wheels are 0.6 inside it)
s = H.sketch(body, "XY", "WallRestoreSketch")
circ(s, "wr_out", "0 mm", "0 mm", "2 * Params.body_r")
circ(s, "wr_in", "0 mm", "0 mm", "2 * Params.r_inner")
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z")
doc.recompute()
f = X.extrude(s, "pcb_z - plate_z", "Join"); f.Label = "WallRestore"

# PCB posts joined to the wall: a web per post, 3 wide at the post, 7 at the wall, full height; R1 into the wall, R1.5 round the foot
s = H.sketch(body, "XY", "PostWebSketch")
ri, br = ev("Params.r_inner"), ev("Params.boss_r")
webs = []
for k in range(1, 5):
    a_ = math.radians(ev(f"Params.boss_a{k}")); u_ = Vector(math.cos(a_), math.sin(a_), 0); t_ = Vector(-math.sin(a_), math.cos(a_), 0)
    pts = [u_ * br + t_ * 1.5, u_ * (ri + 0.3) + t_ * 3.5, u_ * (ri + 0.3) - t_ * 3.5, u_ * br - t_ * 1.5]
    L = [s.addGeometry(_Part.LineSegment(pts[i], pts[(i + 1) % 4]), False) for i in range(4)]
    s.addConstraint([_Sk.Constraint("Coincident", L[i], 2, L[(i + 1) % 4], 1) for i in range(4)])
    webs.append((u_, t_))
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z")
doc.recompute()
f = X.extrude(s, "pcb_z - plate_z", "Join"); f.Label = "PostWebs"
doc.recompute()
# post feet: a 1.5 mm 45-degree flare (a cone per post). A PartDesign fillet on the whole chassis hung FreeCAD.
for k in range(1, 5):
    a_ = math.radians(ev(f"Params.boss_a{k}"))
    cn = body.newObject("PartDesign::AdditiveCone", f"PostFoot{k}")
    cn.Radius1 = ev("Params.boss_d") / 2 + 1.5; cn.Radius2 = ev("Params.boss_d") / 2; cn.Height = 1.5
    cn.Placement = App.Placement(Vector(br * math.cos(a_), br * math.sin(a_), ev("Params.plate_z + Params.plate_t")), App.Rotation())
doc.recompute()

# ball pocket: a 1 mm-clearance ball hull open to the front, plus the round cut in the base plate
sp = body.newObject("PartDesign::SubtractiveSphere", "BallPocket")
sp.setExpression("Radius", "Params.ball_d / 2 + 1 mm")
sp.setExpression(".Placement.Base.x", "Params.ball_x")
sp.setExpression(".Placement.Base.z", "Params.ball_d / 2")
cy = body.newObject("PartDesign::SubtractiveCylinder", "BallRun")
cy.Placement = App.Placement(Vector(41.5, 0, 20), App.Rotation(Vector(0, 1, 0), 90))
cy.setExpression("Radius", "Params.ball_d / 2 + 1 mm")
cy.setExpression("Height", "Params.pocket_run")
cy.setExpression(".Placement.Base.x", "Params.ball_x")
cy.setExpression(".Placement.Base.z", "Params.ball_d / 2")
doc.recompute()

s = H.sketch(body, "XY", "PlatePocketSketch")
circ(s, "ppk", "Params.ball_x", "0 mm", "2 * Params.pocket_r")
s.setExpression(".AttachmentOffset.Base.z", "Params.plate_z + Params.plate_t")
doc.recompute()
pocket(s, "Length", "50 mm", reverse=True, label="PlatePocket")   # upward only: the plate under the pocket stays

# switch and USB slots through the wall (open at the top, print without support)
s = rotated_sketch(body, "SwitchSlotSketch", "Params.sw_ang", "Params.sw_slot_z")
rect(s, "sw", "Params.r_inner - 1 mm", "-Params.sw_slot_w / 2", "Params.wall_t + 2 mm", "Params.sw_slot_w")
doc.recompute()
pocket(s, "Length", "9 mm", reverse=True, label="SwitchSlot")

s = rotated_sketch(body, "UsbSlotSketch", "Params.usb_ang", "Params.usb_slot_z")
rect(s, "usb", "Params.r_inner - 1 mm", "-Params.usb_slot_w / 2", "Params.wall_t + 2 mm", "Params.usb_slot_w")
doc.recompute()
pocket(s, "Length", "6 mm", reverse=True, label="UsbSlot")

# (no floor-sensor window: the PAA5100JE optical-flow sensor was dropped on 2026-10-21)

# PCB post pilots (M2 self-tapping), 6 mm deep from the post tops
s = H.sketch(body, "XY", "PostPilotSketch")
for k in range(1, 5):
    a = f"Params.boss_a{k}"
    circ(s, f"ppil{k}", f"Params.boss_r * cos({a})", f"Params.boss_r * sin({a})", "Params.pilot_d")
s.setExpression(".AttachmentOffset.Base.z", "Params.pcb_z - 6 mm")
doc.recompute()
pocket(s, "Length", "7 mm", reverse=True, label="PostPilots")

# rear ID tag: the bar needs nothing in the chassis; this only removes the old tag plate's wall features (tag_mounts.py)
import sys as _sys
_sys.path.insert(0, OUT)
import tag_mounts as _tm
_tm.chassis_features(doc, body)

for o in (lcs,):
    o.ViewObject.Visibility = False
bad = H.recompute(doc)
H.view("iso")
doc.saveAs(os.path.join(OUT, "BugBot_Base.FCStd"))
result = {"invalid": bad, "chassis": H.info(body), "features": [o.Label for o in body.Group]}
