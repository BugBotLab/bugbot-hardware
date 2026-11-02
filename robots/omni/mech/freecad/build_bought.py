# BugBot in FreeCAD: bought parts. Vendor shapes come in as solids from the STLs in bought/ (exported from the
# OpenSCAD part models, each in its own frame); their placements are expressions on the Params sheet, written like
# the OpenSCAD transform chain. Ball, front bar and servo horn are simple enough to model natively.
import os, traceback, Mesh
from fusionflow import params as P, helpers as H, extrude as X

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = _os.path.join(BB, "bugbot_freecad")
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
P.set_params(PARAMS, doc)

STEEL, BLACK, BLUE, GREEN, ORANGE, WHITE = (0.72, 0.72, 0.75), (0.15, 0.15, 0.17), (0.15, 0.3, 0.75), (0.1, 0.45, 0.25), (0.95, 0.55, 0.15), (1.0, 1.0, 0.95)
MAXF = 12000          # decimate big vendor meshes to about this many triangles


def solid_from_stl(path):
    m = Mesh.Mesh(path)
    if m.CountFacets > MAXF:
        m.decimate(0.02, 1 - MAXF / m.CountFacets)
    sh = Part.Shape(); sh.makeShapeFromMesh(m.Topology, 0.01); sh.sewShape()
    sols = []
    for s in sh.Shells:
        try:
            x = Part.Solid(s)
            if x.Volume < 0: x.reverse()
            sols.append(x)
        except Exception:
            sols.append(s)
    return Part.makeCompound(sols) if len(sols) > 1 else sols[0], m.CountFacets


grp = doc.getObject("BoughtParts") or doc.addObject("App::DocumentObjectGroup", "BoughtParts")
cache = {}


MESH_ONLY = {"Wheel", "PCBParts"}     # solids made from meshes: shown shaded, so their triangle edges do not show


def bought(name, src, placement, colour):
    """A bought part from bought/<src>.brep (made once, headless, by convert_bought.py: no OpenSCAD runs here)."""
    old = doc.getObject(name)
    if old: doc.removeObject(name)
    if src not in cache:
        cache[src] = Part.read(os.path.join(OUT, "bought", src + ".brep"))
    o = doc.addObject("Part::Feature", name)
    o.Shape = cache[src]
    o.addProperty("App::PropertyString", "Source", "BugBot", "where the shape comes from").Source = f"bought/{src}.brep"
    o.setExpression("Placement", E(placement))
    o.ViewObject.ShapeColor = colour
    o.ViewObject.DisplayMode = "Shaded" if src in MESH_ONLY else "Flat Lines"
    grp.addObject(o)
    return o


# the drive unit's frame: X out along the wheel's radial line, origin at the robot centre (DriveUnit turns it)
AXLE = "translationm(wf - wheel_w / 2; pinwheel_e; axle_z) * rotationy(90)"
report = {}
try:
    # the omni wheel is a parametric model of its own (build_wheel.py)
    bought("Gearmotor", "Gearmotor", AXLE + " * translationm(0 mm; 0 mm; -wheel_w / 2 - 0.3 mm)", BLACK)
    # the JF-0520B solenoid is parametric, with a moving plunger: build_solenoid.py
    bought("M3ThinNut", "M3ThinNut", "translationm(sol_x0 + sol_len; -sol_dy; sol_z) * rotationy(90)", STEEL)
    bought("Servo", "Servo", "translationm(pivot_x; 0 mm; pivot_z)", (0.15, 0.25, 0.65))
    # the 16340 now sits in BT1 (Keystone 1051 holder) on the KiCad board: it comes with the board
    # the main board's components (and the kicker capacitor) come from KiCad: build_ecad.py
    # the front sensor board comes from KiCad too: build_ecad.py
    # the LED ring is a KiCad board now (kicad/BugBot_LED): build_ledpcb.py + build_ecad.py
    # (the external FPC antenna under the top deck was removed on 2026-10-23, user request)
except Exception:
    report["error"] = traceback.format_exc()[-800:]

# native: ball, steel front bar (DIN 6325 3 x 45), SG90 single-arm horn
new_body("Ball", WHITE)
o = body.newObject("PartDesign::AdditiveSphere", "Sphere")
o.setExpression("Radius", E("ball_d / 2")); o.setExpression(".Placement.Base.x", E("ball_x")); o.setExpression(".Placement.Base.z", E("ball_d / 2"))
o = body.newObject("PartDesign::SubtractiveSphere", "BallShell")       # a real ball is a thin shell (mass + spin inertia)
o.setExpression("Radius", E("ball_d / 2 - ball_wall")); o.setExpression(".Placement.Base.x", E("ball_x")); o.setExpression(".Placement.Base.z", E("ball_d / 2"))
doc.recompute()
new_body("FrontBar", (0.79, 0.64, 0.30))          # the bar: a brass tube clamped between the arm tips by an M3 screw
ycyl("Tube", [("grip_x", "grip_z")], "-bar_tube_l / 2", "bar_tube_d", "bar_tube_l", "add", +1)
ycyl("TubeBore", [("grip_x", "grip_z")], "0 mm", "bar_tube_d - 2 * bar_tube_wall", "0", "cut", mid=True, kind="ThroughAll")
new_body("BarScrew", (0.17, 0.17, 0.18))           # M3 x 50 socket head (black oxide), head on arm R
ycyl("Head", [("grip_x", "grip_z")], "-(hoop_y + arm_t / 2 - bar_cb_h)", "bar_head_d", "bar_head_h", "add", -1)
ycyl("Shank", [("grip_x", "grip_z")], "-(hoop_y + arm_t / 2 - bar_cb_h)", "bar_screw_d", "bar_screw_l", "add", +1)
ycyl("Socket", [("grip_x", "grip_z")], "-(hoop_y + arm_t / 2 - bar_cb_h + bar_head_h)", "2.6 mm", "1.6 mm", "cut", +1)
new_body("BarWashers", STEEL)                      # M3 washers (7 x 3.2 x 0.5) between the tube ends and the arm tips
body.AllowCompound = True
for nm, y in (("L", "hoop_y - arm_t / 2 - tip_boss_l - bar_washer_t"), ("R", "-(hoop_y - arm_t / 2 - tip_boss_l)")):
    ycyl(f"Washer{nm}", [("grip_x", "grip_z")], y, "7 mm", "bar_washer_t", "add", +1)
ycyl("WasherHoles", [("grip_x", "grip_z")], "0 mm", "3.2 mm", "0", "cut", mid=True, kind="ThroughAll")
# arm R pivot: flanged sintered-bronze bushing (pressed into the arm) on a clamped 3 mm brass tube
yo = "(hoop_y + arm_t / 2)"
new_body("PivotBushing", (0.69, 0.48, 0.23))
ycyl("Flange", [("pivot_x", "pivot_z")], f"-{yo} - (bush_fl_t - bush_recess)", "bush_fl_d", "bush_fl_t", "add", +1)
ycyl("Body", [("pivot_x", "pivot_z")], f"-{yo} + bush_recess - 0.01 mm", "bush_d", "bush_l - bush_fl_t + 0.01 mm", "add", +1)
ycyl("Bore", [("pivot_x", "pivot_z")], "0 mm", "bush_id", "0", "cut", mid=True, kind="ThroughAll")
new_body("PivotTube", (0.79, 0.64, 0.30))
ycyl("Tube", [("pivot_x", "pivot_z")], f"-{yo} - 0.4 mm", "ptube_d", f"0.4 mm + bush_recess + (bush_l - bush_fl_t) + 0.15 mm", "add", +1)
ycyl("Bore", [("pivot_x", "pivot_z")], "0 mm", "ptube_id", "0", "cut", mid=True, kind="ThroughAll")
new_body("BarNut", STEEL)                           # M3 nut in arm L's hex pocket
s = sk("NutSketch", "XZ", "hoop_y + arm_t / 2 - bar_nut_depth")
hex2d(s, "nut", ("grip_x", 0, "grip_z"), "bar_nut_af")
ext(s, "add", "bar_nut_h", +1, "Nut")
ycyl("Thread", [("grip_x", "grip_z")], "0 mm", "bar_screw_d", "0", "cut", mid=True, kind="ThroughAll")
new_body("ServoHorn", (0.93, 0.92, 0.88))
s = sk("HornSketch", "XZ", "horn_y - 1.3 mm")
slot2d(s, "horn", ("pivot_x", 0, "pivot_z"), "3.5 mm", ("pivot_x", 0, "pivot_z + 14 mm"), "2 mm")
ext(s, "add", "1.3 mm", +1, "Horn")
for n in ("Ball", "FrontBar", "BarScrew", "BarNut", "BarWashers", "PivotBushing", "PivotTube", "ServoHorn"):
    grp.addObject(doc.getObject(n))

bad = H.recompute(doc)
for o in grp.Group:
    sh = o.Shape
    report[o.Label] = {"solids": len(sh.Solids), "vol": round(sh.Volume, 1), "bbox": [round(v, 1) for v in (sh.BoundBox.XMin, sh.BoundBox.YMin, sh.BoundBox.ZMin, sh.BoundBox.XMax, sh.BoundBox.YMax, sh.BoundBox.ZMax)]}
report["invalid"] = bad
doc.save()
result = report
