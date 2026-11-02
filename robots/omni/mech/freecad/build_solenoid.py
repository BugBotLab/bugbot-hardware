# BugBot in FreeCAD: the JF-0520B push solenoid, parametric, in four bodies so the plunger can move:
#   Solenoid         steel U-frame (M3 face + 2 end plates with the plunger holes) + the 2 leads     (fixed)
#   SolenoidCoil     the taped coil, bored for the plunger                                           (fixed)
#   SolenoidPlunger  plunger + tail, M3 stud, spring washer, e-clip  (moves with the kick disc and its nut)
#   SolenoidSpring   10 return-spring turns between the frame and the washer (they squeeze as it fires)
# From bugbot_parts.scad jf0520b() as fitted (nut="disc", cut=true), drawn retracted: the kick disc on the frame.
# Run after build_bought.py:  python fusionflow/ffclient.py run mech/freecad/build_solenoid.py
import os
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
STEEL, BLUE, SPRING = (0.72, 0.72, 0.75), (0.15, 0.3, 0.75), (0.82, 0.82, 0.84)

x0, L = "sol_x0", "sol_len"
y0 = "(-sol_depth / 2 - sol_dy)"                   # the M3 face (frame y = 0)
z0 = "(sol_z - sol_height / 2)"
PAX = [("-sol_dy", "sol_z")]                        # the plunger axis (y, z)

# ---- frame + leads ----
new_body("Solenoid", STEEL)
zbox("FacePlate", (x0, y0, z0), (L, "1 mm", "sol_height"))
zbox("RearPlate", (x0, y0, z0), ("1 mm", "sol_depth", "sol_height"))
zbox("FrontPlate", (f"{x0} + {L} - 1 mm", y0, z0), ("1 mm", "sol_depth", "sol_height"))
ycyl("M3Holes", [(f"{x0} + {L} / 2 - 5.5 mm", "sol_z"), (f"{x0} + {L} / 2 + 5.5 mm", "sol_z")], f"{y0} - 1 mm", "2.5 mm", "3 mm", "cut", +1)
xcyl("PlungerHoles", PAX, f"{x0} - 1 mm", "sol_hole_d", f"{L} + 2 mm", "cut")
ycyl("Leads", [(f"{x0} + {L} / 2 - 2 mm", f"{z0} + 1.5 mm"), (f"{x0} + {L} / 2", f"{z0} + 1.5 mm")],
     f"{y0} + sol_depth", "1.2 mm", "4 mm", "add", +1)
body.AllowCompound = True

# ---- coil ----
new_body("SolenoidCoil", BLUE)
xcyl("Coil", PAX, f"{x0} + 1.5 mm", "sol_coil_d", f"{L} - 3 mm")
xcyl("Bore", PAX, f"{x0} + 1 mm", "sol_hole_d", f"{L} - 2 mm", "cut")

# ---- plunger: rod + tail, M3 stud (the kick disc + thin nut sit on it), washer, e-clip ----
new_body("SolenoidPlunger", STEEL)
xcyl("Rod", PAX, f"{x0} - sol_tail", "sol_plunger_d", f"sol_tail + {L}")
xcyl("Stud", PAX, f"{x0} + {L}", "3 mm", "1.8 mm")
xcyl("Washer", PAX, f"{x0} - sol_washer_x", "9 mm", "0.5 mm")
xcyl("EClip", PAX, f"{x0} - sol_washer_x - 0.6 mm", "8 mm", "0.6 mm")

# ---- return spring: one ring per turn ----
new_body("SolenoidSpring", SPRING)
body.AllowCompound = True
n = int(round(float(doc.getObject("Params").get("sol_spring_n"))))
for i in range(n):
    s = sk(f"Turn{i + 1}Sketch", "YZ", f"{x0} - 0.7 mm - {i} * sol_spring_pitch")
    circle2d(s, f"to{i}", ("0 mm", "-sol_dy", "sol_z"), "8 mm")
    circle2d(s, f"ti{i}", ("0 mm", "-sol_dy", "sol_z"), "6.8 mm")
    ext(s, "add", "sol_spring_wire", +1, f"Turn{i + 1}")
doc.recompute()
result = {n: {"valid": doc.getObject(n).Shape.isValid(), "solids": len(doc.getObject(n).Shape.Solids),
              "volume": round(doc.getObject(n).Shape.Volume, 1),
              "bbox": [round(v, 2) for v in (lambda b: (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax))(doc.getObject(n).Shape.BoundBox)]}
          for n in ("Solenoid", "SolenoidCoil", "SolenoidPlunger", "SolenoidSpring")}
result["stroke_mm"] = float(doc.getObject("Params").get("sol_stroke").getValueAs("mm"))
