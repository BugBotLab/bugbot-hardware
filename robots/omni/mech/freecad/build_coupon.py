# BugBot printer test coupon: small pieces cut from the real parts, so anyone can check their printer's fits in
# ~15 minutes before printing the whole robot. Also writes the drill-to-size list (fits that never rely on the printer).
#   python fusionflow/ffclient.py run mech/freecad/build_coupon.py     ->  mech/freecad/print/coupon/*.stl + FITS.md
import os, math
import Part, Mesh
V = App.Vector
doc = App.getDocument("BugBot_Base")
P = doc.Params
q = lambda e: float(P.evalExpression("Params." + e).Value)
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/print/coupon"
os.makedirs(OUT, exist_ok=True)


def piece(obj, region, name, note):
    sh = doc.getObject(obj).Shape.common(region)
    sh = sh.removeSplitter()
    m = Mesh.Mesh(); m.addFacets(sh.tessellate(0.02)); m.write(f"{OUT}/{name}.stl")
    return {"file": f"{name}.stl", "from": obj, "volume_mm3": round(sh.Volume, 1), "tests": note}


items = []
# 1 wheel: one roller pocket of the outer half (pocket clearance, pin hole to drill, screw counterbore)
ax = q("roller_axis_r")
items.append(piece("WheelFrameOne" if doc.getObject("WheelFrameOne") else "WheelHalfOuter", Part.makeBox(9, 16, 10, V(ax - 4.5, -8, -1)), "1_wheel_pocket",
                   "a TPU roller (with its brass liner) must spin freely in the pocket; drill the pin hole 0.95 and push a 1x12 pin in from the open end: it must hold by friction"))
items.append(piece("Roller", Part.makeBox(40, 40, 40, V(-20, -20, -20)), "1b_roller_tpu",
                   "print in TPU: must push onto the 2.0 brass tube (CA after the test)"))
# 2 bayonet: one notch + channel of the deck collar, and the matching lug on a piece of the dome rim
a0 = math.radians(q("bay_a0"))
cx, cy = 15.5 * math.cos(a0 + math.radians(15)), 15.5 * math.sin(a0 + math.radians(15))
reg = Part.makeBox(18, 18, 6, V(cx - 9, cy - 9, q("mast_top") + q("deck_t") - 2.2))
items.append(piece("TopDeck", reg, "2_bayonet_collar", "drop the dome lug in at the notch, turn: it must slide, then tighten on the ramp"))
items.append(piece("Dome", Part.makeBox(18, 18, 5, V(cx - 9, cy - 9, q("mast_top") + q("deck_t") - 0.7)), "2b_dome_lug",
                   "print in clear PLA, rim down (as the real dome)"))
# 3 arm R pivot boss: drill 5.0, press the 3x5x4 flanged bushing in, the 3 mm brass tube must turn in it
px, pz = q("pivot_x"), q("pivot_z")
items.append(piece("HoopArmR", Part.makeBox(14, 6, 14, V(px - 7, -27, pz - 7)), "3_pivot_boss",
                   "drill the hole 5.0, press the bushing in (flange in the recess); the tube must turn freely"))
# 4 motor saddle: the motor drops into the groove; the M2 pilots take the self-tappers
a = math.radians(q("wheel_ang1")); xs = q("m_front") - q("saddle_s1") - q("saddle_l") / 2; e = q("pinwheel_e")
sx, sy = xs * math.cos(a) - e * math.sin(a), xs * math.sin(a) + e * math.cos(a)
reg = Part.makeBox(20, 20, 10, V(sx - 10, sy - 10, q("plate_z")))
items.append(piece("Chassis", reg, "4_motor_saddle", "the 6 mm gearmotor drops in; an M2x6 self-tapper goes into a pilot by hand-driver"))
# 5 mast spigot + deck pocket: the deck corner drops over the spigot
mx, my = q("mast_x"), q("mast_w") / 2
items.append(piece("Mast", Part.makeBox(9, 8, 5, V(mx - 4.5, my - 8, q("mast_top") - 4)), "5_mast_spigot", "the deck corner must drop on without forcing"))
items.append(piece("TopDeck", Part.makeBox(9, 8, 3, V(mx - 4.5, my - 8, q("mast_top") - 0.5)), "5b_deck_corner", ""))
# 6 front-bar sleeve: a 10 mm slice must spin on the 4 mm brass tube
items.append(piece("HoopSleeve", Part.makeBox(20, 10, 20, V(q("grip_x") - 10, -5, q("grip_z") - 10)), "6_sleeve", "must spin freely on the 4 mm brass tube"))

DRILL = [
    ("Wheel frame pin holes (36)", "printed 0.9", "drill 1.0", "push the 1x12 dowel in, a drop of thin CA"),
    ("Wheel motor-half shaft bore (3)", "printed 1.8 (D)", "drill 2.0", "push onto the 2 mm D-shaft, 5-min epoxy"),
    ("Arm R pivot hole", "printed 4.8", "drill 5.0", "press the 3x5x4 flanged bronze bushing in"),
    ("TPU roller bore (18)", "printed 1.8", "-", "stretch onto the 2.0 brass liner, thin CA"),
    ("M2 self-tapping pilots (all)", "printed 1.6", "drill 1.6 if a screw is hard to start", "M2 pan-head self-tappers, snug only"),
    ("Front-bar sleeve bore", "printed 4.6", "drill 4.5-4.6 if it does not spin", "on the 4 mm brass tube"),
    ("Dome bayonet", "-", "-", "turn until it tightens on the ramp (where depends on your printer)"),
    ("Motor caps", "-", "-", "screws snug: the 0.5 mm gap under the jaws makes them clamp"),
    ("Arm R pivot", "-", "-", "M2x12 + washer + nyloc fully tight: the brass tube takes the clamp, the arm stays free"),
    ("Front bar", "-", "-", "M3x45 snug + medium threadlocker: the washers and tube take the clamp"),
]
with open(f"{OUT}/../FITS.md", "w", encoding="utf-8") as f:
    f.write("# BugBot fits that work on any printer\n\nPrint the coupon first (print/coupon/*.stl, PLA except where noted).\n\n")
    f.write("| Coupon piece | What it tests |\n|---|---|\n")
    for it in items:
        f.write(f"| {it['file']} | {it['tests']} |\n")
    f.write("\n## Drill to size / assembly fits\n\n| Feature | As printed | Then | Fit |\n|---|---|---|---|\n")
    for r in DRILL:
        f.write("| " + " | ".join(r) + " |\n")
    f.write("\nClearances in the model: moving parts >= 0.3 per side (roller pockets 0.4 / ends 0.35), locating fits 0.25 per side (fit_loc),\n"
            "M2 clearance holes 2.5, M3 3.4. Nothing relies on the printer for a press fit.\n")
result = {"pieces": items, "drill_rows": len(DRILL), "out": OUT}
