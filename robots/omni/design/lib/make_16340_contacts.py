# 16340 on the board between a pair of PCB end contacts: Keystone 595 (positive, brass dimple) and 628 (negative,
# spring), 36.5 mm apart (JIATEL cross-reference data: plate 9.69 x 13.97 x 0.4 mm, 3 PC pins, holes 1.8 mm,
# pins 9.29 mm span + 2.99 mm offset, triangular). VERIFY pin positions against Keystone's 595 / 628 drawings.
# One footprint holds both contacts; the cell is a second, 3D-only model.
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_16340_contacts.py
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib"
SPAN, PW, PH, PT = 36.5, 9.69, 13.97, 0.4
CELL_D, CELL_L = 16.6, 34.5                     # unprotected 16340 (the board has its own protection, U5)
ZC = CELL_D / 2 + 0.3                           # cell axis height: cell 0.3 mm clear of the board
PIN_SPAN, PIN_OFF = 9.29, 2.99
parts = []
for s in (-1, 1):                               # -1: negative (628, spring) at -x, +1: positive (595, dimple) at +x
    x0 = s * SPAN / 2
    plate = Part.makeBox(PT, PW, PH, V(x0 - PT / 2, -PW / 2, 0))
    parts.append(plate)
    if s < 0:                                   # conical spring towards the cell
        spr = Part.makeCone(3.2, 1.6, 2.6, V(x0 + PT / 2, 0, ZC), V(1, 0, 0))
        parts.append(spr.cut(Part.makeCone(2.9, 1.3, 2.6, V(x0 + PT / 2, 0, ZC), V(1, 0, 0))))
    else:
        parts.append(Part.makeSphere(1.6, V(x0 - PT / 2, 0, ZC)).common(Part.makeBox(3, 4, 4, V(x0 - PT / 2 - 3, -2, ZC - 2))))
    for (px, py) in ((x0, -PIN_SPAN / 2), (x0, PIN_SPAN / 2), (x0 + s * PIN_OFF, 0)):
        parts.append(Part.makeCylinder(0.45, 3.05, V(px, py, -3.05)))
contacts = Part.makeCompound(parts)
contacts.exportStep(f"{D}/3dmodels/BatteryContacts_Keystone_595_628_16340.step")
cell = Part.makeCylinder(CELL_D / 2, CELL_L, V(-CELL_L / 2, 0, ZC), V(1, 0, 0))
cell = cell.fuse(Part.makeCylinder(3, 0.8, V(CELL_L / 2, 0, ZC), V(1, 0, 0))).removeSplitter()     # + cap
cell.exportStep(f"{D}/3dmodels/Cell_16340_unprotected.step")
pads = []
n = 0
for s, sign in ((-1, "-"), (1, "+")):
    x0 = s * SPAN / 2
    for (px, py) in ((x0, -PIN_SPAN / 2), (x0, PIN_SPAN / 2), (x0 + s * PIN_OFF, 0)):
        n += 1
        pads.append(f'  (pad "{1 if s > 0 else 2}" thru_hole circle (at {px:.3f} {py:.3f}) (size 2.6 2.6) (drill 1.8) (layers "*.Cu" "*.Mask"))')
cx0, cx1 = -SPAN / 2 - PIN_OFF - 1.6, SPAN / 2 + PIN_OFF + 1.6
fp = f'''(footprint "BatteryContacts_Keystone_595_628_16340"
  (version 20240108)
  (generator "bugbot")
  (layer "F.Cu")
  (descr "1x 16340 between Keystone 595 (+) and 628 (-) PCB contacts, 36.5 mm apart. Pins from cross-reference data: VERIFY against Keystone drawings.")
  (tags "battery contact 16340 CR123A Keystone 595 628")
  (attr through_hole)
  (property "Reference" "REF**" (at 0 {-CELL_D / 2 - 1.5:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "16340 + Keystone 595/628" (at 0 {CELL_D / 2 + 1.5:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {-CELL_L / 2:.2f} {-CELL_D / 2:.2f}) (end {CELL_L / 2:.2f} {CELL_D / 2:.2f}) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_rect (start {-SPAN / 2 - PT:.2f} {-PW / 2:.2f}) (end {-SPAN / 2 + PT:.2f} {PW / 2:.2f}) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
  (fp_rect (start {SPAN / 2 - PT:.2f} {-PW / 2:.2f}) (end {SPAN / 2 + PT:.2f} {PW / 2:.2f}) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
  (fp_rect (start {cx0:.2f} {-CELL_D / 2 - 0.5:.2f}) (end {cx1:.2f} {CELL_D / 2 + 0.5:.2f}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
  (fp_text user "+" (at {SPAN / 2 - 3:.2f} 0 0) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))
  (fp_text user "-" (at {-SPAN / 2 + 3:.2f} 0 0) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))
{chr(10).join(pads)}
  (model "${{KIPRJMOD}}/../lib/3dmodels/BatteryContacts_Keystone_595_628_16340.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
  (model "${{KIPRJMOD}}/../lib/3dmodels/Cell_16340_unprotected.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
open(f"{D}/BugBot.pretty/BatteryContacts_Keystone_595_628_16340.kicad_mod", "w").write(fp)
print("ok", round(cx1 - cx0, 2), "mm long courtyard,", round(CELL_D + 1, 2), "wide; cell axis", ZC, "mm above the board")
