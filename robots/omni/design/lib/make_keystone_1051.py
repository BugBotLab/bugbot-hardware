# Keystone 1051 (THM CR123A / 16340 holder) for the BugBot KiCad library: 3D model (STEP) + footprint.
# Built from Keystone drawing 1051 rev C (Downloads/1051.PDF): the outlines were read straight out of the PDF's
# vector data (drawn 2:1), view by view:
#   side view : end walls 4.13 thick, full 15.24 high, outer face drafted (0.15 by 8.89, 0.24 by 14.25), R1 top edge;
#               inner face down to 8.89, R1.6 into the side rails, rails 6.99 high; window 5.59 x 3.81 low in each rail
#   end view  : 18.29 wide up to 8.89, tapering to 14.22 at the top; a 3.81 slot (open at the top) down the outer
#               face for the contact; lead 0.97 on the centre line; peg 1.27 dia, 8.10 off the centre line
#   top view  : rails 1.10 thick; slot 2.35 deep; the cradle: a cylinder (cell axis 9.78 above the board) between
#               the rails with a flat 6.6 strip down the middle (the + mark)
#   3D view   : + end: contact plate with a dimple in a pocket of the end wall; - end: a bent leaf spring
#   pad layout: contacts 37.82 apart (holes 1.19), peg hole 1.98 beside the + contact, 8.10 off the line
# Model axes: X along the holder (+ end at -X), Y across (KiCad 3D +Y = footprint -y), Z up from the board.
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_keystone_1051.py
import math
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib"
L, W, H = 42.93, 18.29, 15.24
WALL, RAIL_H, RAIL_T = 4.13, 6.99, 1.10
END_Z = 8.89                                   # end walls full width / undrafted up to here
TOP_W = 14.22                                  # end wall width at the top
SLOT_W, SLOT_D = 3.81, 2.35
WIN_L, WIN_H = 5.59, 3.81
ZC, R_SEAT, FLAT_W = 9.78, 8.6, 6.6
PIN, LEAD_W, LEAD_T, LEAD_L = 37.82, 0.97, 0.31, 3.56
PEG_D, PEG_L, PEG_Y = 1.27, 1.27, 8.10          # model +Y (= footprint -y)
X0 = L / 2
XI = X0 - WALL                                 # inner face of an end wall


def prism_xz(pts, y0, y1):
    """Polygon in the XZ plane, extruded along Y from y0 to y1."""
    w = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(w).extrude(V(0, y1 - y0, 0))


def prism_yz(pts, x0, x1):
    w = Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, pts[0][0], pts[0][1])])
    return Part.Face(w).extrude(V(x1 - x0, 0, 0))


def end_wall(s):
    """s = -1 (+ end, -X) or +1 (- end, +X)"""
    o = s * X0; i = s * XI
    side = [(o, 0), (o - s * 0.15, END_Z), (o - s * 0.24, H - 1.0), (o - s * 1.24, H), (i, H), (i, 0)]     # side view
    a = prism_xz(side, -W / 2 - 1, W / 2 + 1)
    hw, ht = W / 2, TOP_W / 2
    endv = [(-hw, 0), (hw, 0), (hw, END_Z), (ht + 0.32, H - 1.0), (ht, H), (-ht, H), (-ht - 0.32, H - 1.0), (-hw, END_Z)]
    b = prism_yz(endv, min(o, i) - 1, max(o, i) + 1)
    wall = a.common(b)
    # the R1 round on the outer top edge (as drawn): cut a corner and put back a quarter cylinder
    corner = Part.makeBox(1.0, W + 2, 1.0, V(o - (1.0 if s > 0 else 0), -W / 2 - 1, H - 1.0))
    q = Part.makeCylinder(1.0, W + 2, V(o - s * 1.0, -W / 2 - 1, H - 1.0), V(0, 1, 0))
    wall = wall.cut(corner.cut(q))
    slot = Part.makeBox(SLOT_D + 0.5, SLOT_W, H + 2, V(o - s * SLOT_D - (0.5 if s < 0 else 0) - (SLOT_D if s > 0 else 0) + (SLOT_D if s > 0 else 0), -SLOT_W / 2, -1))
    slot = Part.makeBox(SLOT_D + 0.5, SLOT_W, H + 2, V((o - SLOT_D) if s > 0 else (o - 0.5), -SLOT_W / 2, -1))
    return wall.cut(slot)


# side rails + floor block between the end walls, then the cradle cut out of it
mid = Part.makeBox(2 * XI + 0.02, W, RAIL_H, V(-XI - 0.01, -W / 2, 0))
seat = Part.makeCylinder(R_SEAT, 2 * XI + 2, V(-XI - 1, 0, ZC), V(1, 0, 0))
inner = Part.makeBox(2 * XI + 2, W - 2 * RAIL_T, RAIL_H, V(-XI - 1, -(W / 2 - RAIL_T), 0))
flat = Part.makeBox(2 * XI + 2, FLAT_W, ZC - math.sqrt(R_SEAT ** 2 - (FLAT_W / 2) ** 2), V(-XI - 1, -FLAT_W / 2, 0))
mid = mid.cut(seat.common(inner).cut(flat))
# the window low in the middle of each rail
for s in (-1, 1):
    mid = mid.cut(Part.makeBox(WIN_L, RAIL_T + 1, WIN_H, V(-WIN_L / 2, s * (W / 2 - RAIL_T / 2) - (RAIL_T + 1) / 2, -0.01)))
# R1.6 where each end wall's inner face runs down into the rails (side view), on the rails only
fil = []
for s in (-1, 1):
    for t in (-1, 1):
        y0 = (W / 2 - RAIL_T) if t > 0 else -W / 2
        blk = Part.makeBox(1.6, RAIL_T, 1.6, V(s * XI - (1.6 if s > 0 else 0), y0, RAIL_H))
        cyl = Part.makeCylinder(1.6, RAIL_T + 0.2, V(s * XI - s * 1.6, y0 - 0.1, RAIL_H + 1.6), V(0, 1, 0))
        fil.append(blk.cut(cyl))
body = mid.fuse([end_wall(-1), end_wall(1)] + fil)
# + end: the contact sits in a pocket of the inner face (3D view)
pocket = Part.makeBox(0.6, 9.0, 9.0, V(-XI - 0.01, -4.5, ZC - 4.5))
body = body.cut(pocket)
peg = Part.makeCylinder(PEG_D / 2, PEG_L + 0.3, V(-PIN / 2, PEG_Y, -PEG_L), V(0, 0, 1))
body = body.fuse(peg).removeSplitter()

# contacts (stainless, tin-nickel): + = flat plate with a dimple, - = bent leaf; each with its strip down the slot to a lead
def lead(x):
    return Part.makeBox(LEAD_W, LEAD_T, LEAD_L + 1.2, V(x - LEAD_W / 2, -LEAD_T / 2, -LEAD_L))
plus = Part.makeBox(0.31, 8.4, 8.4, V(-XI + 0.25, -4.2, ZC - 4.2))
plus = plus.fuse(Part.makeCylinder(1.5, 0.6, V(-XI + 0.56, 0, ZC), V(1, 0, 0)))                       # the dimple
plus = plus.fuse(Part.makeBox(0.31, SLOT_W - 0.3, ZC + 4.8, V(-X0 + 0.4, -(SLOT_W - 0.3) / 2, 0.2)))     # strip in the slot
plus = plus.fuse(Part.makeBox(X0 - XI - 0.1, SLOT_W - 0.3, 0.31, V(-X0 + 0.4, -(SLOT_W - 0.3) / 2, ZC + 4.8)))   # over the top
plus = plus.fuse(lead(-PIN / 2)).removeSplitter()
leaf = Part.makeBox(0.31, 6.0, 8.0, V(0, -3.0, 0)); leaf.rotate(V(), V(0, 1, 0), -25)   # leans in towards the cell
leaf.translate(V(XI - 0.4, 0, RAIL_H + 0.2))
minus = leaf.fuse(Part.makeBox(0.31, SLOT_W - 0.3, ZC + 4.8, V(X0 - 0.71, -(SLOT_W - 0.3) / 2, 0.2)))
minus = minus.fuse(Part.makeBox(X0 - XI - 0.1, SLOT_W - 0.3, 0.31, V(XI - 0.3, -(SLOT_W - 0.3) / 2, ZC + 4.8)))
minus = minus.fuse(lead(PIN / 2)).removeSplitter()

holder = Part.makeCompound([body, plus, minus])
holder.exportStep(f"{D}/3dmodels/BatteryHolder_Keystone_1051_1xCR123A.step")
bb = holder.BoundBox
print("model", round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZMax, 2), "below board", round(-bb.ZMin, 2), "valid", body.isValid())

x0, x1, y0, y1 = -L / 2, L / 2, -W / 2, W / 2
fp = f'''(footprint "BatteryHolder_Keystone_1051_1xCR123A"
  (version 20240108)
  (generator "bugbot")
  (layer "F.Cu")
  (descr "Keystone 1051 THM holder, 1x CR123A / 16340, from drawing 1051 rev C: body 42.93 x 18.29 x 15.24 mm, contacts 37.82 apart (holes 1.19), locating peg hole 1.98 beside the + contact, 8.10 off the contact line")
  (tags "battery holder CR123A 16340 Keystone 1051")
  (attr through_hole)
  (property "Reference" "REF**" (at 0 {y1 + 1.5:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "Keystone_1051" (at 0 {y1 + 3.0:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_rect (start {x0 - 0.12:.3f} {y0 - 0.12:.3f}) (end {x1 + 0.12:.3f} {y1 + 0.12:.3f}) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
  (fp_rect (start {x0 - 0.5:.3f} {y0 - 0.5:.3f}) (end {x1 + 0.5:.3f} {y1 + 0.5:.3f}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
  (fp_text user "+" (at {-PIN / 2 + 3:.2f} 0 0) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))
  (fp_text user "-" (at {PIN / 2 - 3:.2f} 0 0) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))
  (pad "1" thru_hole rect (at {-PIN / 2:.3f} 0) (size 2.2 2.2) (drill 1.19) (layers "*.Cu" "*.Mask"))
  (pad "2" thru_hole circle (at {PIN / 2:.3f} 0) (size 2.2 2.2) (drill 1.19) (layers "*.Cu" "*.Mask"))
  (pad "" np_thru_hole circle (at {-PIN / 2:.3f} {-PEG_Y:.3f}) (size 1.98 1.98) (drill 1.98) (layers "*.Cu" "*.Mask"))
  (model "${{KIPRJMOD}}/../lib/3dmodels/BatteryHolder_Keystone_1051_1xCR123A.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
  (model "${{KIPRJMOD}}/../lib/3dmodels/Cell_16340_unprotected.step" (offset (xyz 0 0 CELLDZ)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
cell = Part.read(f"{D}/3dmodels/Cell_16340_unprotected.step")
cz = (cell.BoundBox.ZMin + cell.BoundBox.ZMax) / 2
fp = fp.replace("CELLDZ", f"{ZC - cz:.3f}")
open(f"{D}/BugBot.pretty/BatteryHolder_Keystone_1051_1xCR123A.kicad_mod", "w").write(fp)
print("footprint ok, cell offset", round(ZC - cz, 3))
