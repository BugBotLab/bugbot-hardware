# BugBot in FreeCAD: the main PCB outline and the motor cap, each its own body, driven by the same Params.
# Run after build_chassis.py:  python fusionflow/ffclient.py run mech/freecad/build_pcb_caps.py
import os, math
import Part, Sketcher
from fusionflow import params as P, helpers as H, extrude as X

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = _os.path.join(BB, "bugbot_freecad")
exec(open(os.path.join(OUT, "bugbot_params.py"), encoding="utf-8").read())
exec(open(os.path.join(OUT, "bb_lib.py"), encoding="utf-8").read())

doc = App.getDocument("BugBot_Base")
App.setActiveDocument("BugBot_Base")
P.set_params(PARAMS, doc)          # adds the new PCB / cap rows; existing rows keep their links
for name in ("MainPCB", "MotorCaps", "MotorCap", "MotorCapR"):   # rebuildable: drop the old bodies first
    old = doc.getObject(name)
    if old:
        old.removeObjectsFromDocument(); doc.removeObject(name)
doc.recompute()


def origin(b, role):
    return next(o for o in b.Origin.OriginFeatures if o.Role == role)


# ---------- main PCB ----------
body = H.body("MainPCB")
s = H.sketch(body, "XY", "PCBSketch")
s.setExpression(".AttachmentOffset.Base.z", "Params.pcb_z")
# outline: the big arc inside the wall, closed by the notch arc round the ball
R, rn, bx = ev("Params.pcb_r"), ev("Params.pcb_notch_r"), ev("Params.ball_x")
px = (R*R - rn*rn + bx*bx) / (2*bx); py = math.sqrt(R*R - px*px)
th = math.atan2(py, px); ph = math.atan2(py, bx - px)
o = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(), Vector(0, 0, 1), R), th, 2*math.pi - th), False)
n = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(bx, 0, 0), Vector(0, 0, 1), rn), math.pi - ph, math.pi + ph), False)
s.addConstraint([Sketcher.Constraint("Coincident", o, 3, -1, 1),
                 Sketcher.Constraint("PointOnObject", n, 3, -1),
                 Sketcher.Constraint("Coincident", o, 1, n, 1),
                 Sketcher.Constraint("Coincident", o, 2, n, 2)])
c0 = s.ConstraintCount
s.addConstraint([Sketcher.Constraint("Radius", o, R), Sketcher.Constraint("Radius", n, rn),
                 Sketcher.Constraint("DistanceX", -1, 1, n, 3, bx)])
dims(s, c0, ["pcb_R", "pcb_notch", "pcb_notch_x"],
     ["Params.pcb_r", "Params.pcb_notch_r", "Params.ball_x"])
# M2 holes for everything screwed to the board
holes = [(f"Params.boss_r * cos(Params.boss_a{k})", f"Params.boss_r * sin(Params.boss_a{k})") for k in range(1, 5)]
holes += [("Params.mast_screw_x", "-Params.mast_screw_y"), ("Params.mast_screw_x", "Params.mast_screw_y"),
          ("Params.deck_leg_x", "-Params.deck_leg_y"), ("Params.deck_leg_x", "Params.deck_leg_y"),
          ("Params.servo_x0 - 2.3 mm", "Params.ear_y + 2.15 mm"),
          ("Params.pivot_x - Params.hoopbr_dx", "Params.hoopbr_y"), ("Params.pivot_x + Params.hoopbr_dx", "Params.hoopbr_y"),
          ("Params.kb_front_x", "Params.kb_front_y"), ("Params.kb_rear_x", "Params.kb_rear_y")]
for k, (x, y) in enumerate(holes, 1):
    circ(s, f"hole{k}", x, y, "Params.pcb_hole_d")
# antenna lead hole removed for now (2026-10-20): to come back with the main board layout (params antenna_x / _y / _d kept)
# circ(s, "antenna", "Params.antenna_x", "Params.antenna_y", "Params.antenna_d")
doc.recompute()
f = X.extrude(s, "pcb_t", "Join"); f.Label = "Board"
body.ViewObject.ShapeColor = (0.10, 0.45, 0.25)
pcb = body

# ---------- motor cap: ONE body, in the drive unit (two per motor, screwed down onto the chassis saddles) ----------
# Local frame: X along the motor (radial, from the cap's inner end), Y across, Z up from the axle line.
exec(open(os.path.join(OUT, "bb_geo.py"), encoding="utf-8").read())
# Two clamp jaws (open top: the kick solenoid leaves no room for a crown over the motor); they stop mcap_gap above
# the saddle so the screws press the motor down into its groove. Front cap: both jaws; rear: one (+Y) jaw, the
# rear saddle's fixed hook holds the other side.
for nm, sides in (("MotorCap", (+1, -1)), ("MotorCapR", (+1,))):
    new_body(nm, (0.80, 0.80, 0.82))
    body.AllowCompound = True
    for sg in sides:
        t = 'P' if sg > 0 else 'N'
        # clamp lobe at full height beside the motor, the screw ear stepped down (the kick solenoid is 0.2 above the lobe)
        zbox(f"Lobe{t}", ("0 mm", "mcap_slot / 2" if sg > 0 else "-mcap_lobe", "mcap_gap"), ("saddle_l", "mcap_lobe - mcap_slot / 2", "mcap_t - mcap_gap"))
        zbox(f"Ear{t}", ("0 mm", "mcap_lobe - 0.01 mm" if sg > 0 else "-saddle_w / 2", "mcap_gap"), ("saddle_l", "saddle_w / 2 - mcap_lobe + 0.01 mm", "mcap_ear_top - mcap_gap"))
    xcyl("Groove", [("0 mm", "0 mm")], "-1 mm", "motor_d + 0.15 mm", "saddle_l + 2 mm", "cut", +1)   # meets the 6.15 gearbox ring; the 0.3 gap below makes it clamp
    zcyl("Holes", [("saddle_l / 2", f"{'' if sg > 0 else '-'}saddle_screw_y") for sg in sides], "-1 mm", "mcap_pilot_d", "mcap_t + 2 mm", "cut")
    if nm == "MotorCap":
        caps = body

bad = H.recompute(doc)
doc.save()
result = {"invalid": bad, "pcb": H.info(pcb), "caps": H.info(caps), 
          "allow_compound": getattr(caps, "AllowCompound", None)}
