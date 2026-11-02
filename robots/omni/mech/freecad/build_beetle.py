# BugBot "Beetle" variant, shield v2c: a passive front shield, no gripper and no kicker. Two rigid side plates on the gripper's
# pivot mounts (their pivot ends cut from the BugBot's hoop arms, so the horn / bushing fits are the same) drop just ahead of
# the wall and end in 5.5-wide foot plates. Between them sits the sasumata-style U front: its middle block rises to z 25.5
# (behind x 50, out of the Wasp's stinger reach) and is held by TWO M3 bolts one above the other, so it can't pivot down; the
# U itself stays low (z 7.5-13) under the stinger, prong tips 35 mm ahead of the body. A Wasp is caught on the prong tips and
# its fired ram ends ~20 mm short of the Beetle; a 40 mm ball fits in the U. A foot on each plate rests on the main board;
# gravity holds it there (a lift only raises the shield, it drops back). The servo stays fitted but unpowered.
# Built from plain boxes and cylinders with real fillets (sizes from the approved 2D, sketches/draw_beetle_shield_v2.py);
# the U's middle block is flush with the foot plates (v2d: same front, top and rounded corner).
# Builds a SEPARATE document BugBot_Beetle (saved as mech/freecad/BugBot_Beetle.FCStd): the shared base robot
# (variants.py) + the shield. The BugBot_Base document is read only.
#   python fusionflow/ffclient.py run mech/freecad/build_beetle.py
# Approved 2D: mech/freecad/sketches/beetle_shield_v2c.png (+ v2d alignment, beetle_shield_v2d.png).
# Screws (also in BEETLE_PARTS.md):
#   U front:   2 x M3 x 50 socket head DIN 912 (heads sunk in foot plate R) + 2 x M3 nut DIN 934 (in hex pockets in foot
#              plate L), through foot plate R + the U's middle block + foot plate L (Ø3.5 holes); nothing sticks out
#   R plate:   the gripper's pivot axle, M2 x 8 + M2 nyloc, through the pivot bracket and bushing (tightened: nothing swings)
#   L plate:   the servo horn's own 2 x M1.4 x 4 self-tapping screws into the plate's horn pad (as the gripper arm)
#   bracket:   2 x M2 x 6 self-tapping from under the board (base, unchanged)
import sys, importlib, math, json, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Beetle.FCStd"
PROF = BB + "/mech/freecad/sketches/beetle_shield_v2c_profiles.json"
src = App.getDocument("BugBot_Base"); P = src.Params
q = lambda n: P.get(n).Value
J = json.load(open(PROF))
# ---------------- parameters (robot frame, mm) ----------------
S = dict(
    m3_clear=3.5,                    # printed M3 clearance (holes come out small on a rough printer)
    head_d=5.5, head_t=3.0,          # DIN 912 M3 socket head
    screw_l=50.0,                    # M3 x 50: ends flush with the nut's outer face
    nut_af=5.5, nut_t=2.4,           # DIN 934 M3
)
# ---------------- shield geometry: plain boxes and cylinders, real fillets (robot frame, mm) ----------------
G = dict(
    bar_x0=13.0, bar_z0=34.0, bar_z1=40.0,           # top bar, from inside the hoop arm's pivot end to the leg
    leg_x0=35.1, leg_x1=41.5,                        # leg: >= 0.4 ahead of the wall / board edge at the plate's inner face
    foot_x1=47.5, foot_z0=7.5, foot_z1=25.5,         # foot plate (5.5 wide) that carries the U; its front / top = the U block's
    pad_x0=25.0, pad_x1=30.5,                        # pad under the bar, resting on the board top (4.6 to the leg: room for both fillets)
    block_x0=38.0,                                   # U middle block back face (0.8 clear of the Beetle's base-plate lip)
    u_cx=67.0, u_ri=21.0, u_t=6.0,                   # U: half ring round (u_cx, 0), inside R21 (a 40 mm ball fits), 6 thick
    u_z0=7.5, u_z1=13.0,                             # the U stays below the Wasp's stinger (z 14.3)
    prong_l=6.0, prong_a=20.0,                       # prongs: 6 long, flared 20 deg outward, round ends
    r_out=3.0, r_in=2.0, r_pad=1.0,                  # fillets: outside corners, inside corners, the pad's
)
PCB_TOP = q("pcb_z") + 1.51                             # the KiCad board's real top (1.51 thick): the pads sit on it
ARM_IN, ARM_T = q("arm_in"), q("arm_t")
FOOT_W = 5.5                                           # foot plates 5.5 wide (the plates are ARM_T), widened outward
BOLTS = [(42.5, 12.0), (42.5, 21.0)]                   # 2 x M3 x 50, one above the other: the U can't pivot
CB_D, CB_T = 6.0, 3.2                                  # counterbore for the DIN 912 heads (foot plate R)
POCKET_AF, POCKET_T = 5.8, 2.6                         # hex pocket for the DIN 934 nuts (foot plate L)
CUT = 15.0                                             # the hoop arm's pivot end is kept behind this x
FIT = 0.25                                             # U block to the foot plates, a side
GAP = J["gap"]                                         # stinger gap, worst case, from the approved 2D (same U)
# ---------------- the base robot + the arm pieces the plates reuse ----------------
sys.path.insert(0, BB + "/mech/freecad")
import variants; importlib.reload(variants)
keep = variants.base_parts(src)                        # base (servo mount, arm, kicker, ball: modules)
keep += variants.module_leaves(src, "GripperMount")    # the servo mount module (SG90, servo block, pivot bracket + screws)
grip = variants.parts_of(src, "Gripper:1")
for n in ("Gripper:1/ServoHorn", "Gripper:1/Gripper screws", "Gripper:1/PivotBushing"):   # the plates sit on these
    keep.append((n,) + grip[n])
new = []
fillet_log = {}
def box(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def cyl_z(cx, cy, r, z0, z1): return Part.makeCylinder(r, z1 - z0, V(cx, cy, z0))
def hex_y(cx, cz, af, y0, t):
    """hex prism along +y from y0, flats top and bottom"""
    r = af / 2 / math.cos(math.radians(30))
    return Part.Face(Part.makePolygon([V(cx + r * math.cos(math.radians(60 * k)), y0, cz + r * math.sin(math.radians(60 * k)))
                                       for k in range(7)])).extrude(V(0, t, 0))
def fillet_y(shape, pts, r, tag):
    """fillet the straight edges running along y whose (x, z) is one of pts"""
    es = [e for e in shape.Edges if e.Curve.TypeId == "Part::GeomLine" and abs(e.Curve.Direction.y) > 0.999
          and any(abs(e.Vertexes[0].X - x) < 0.02 and abs(e.Vertexes[0].Z - z) < 0.02 for x, z in pts)]
    if not es:
        fillet_log[tag] = "no edges"; return shape
    try:
        out = shape.makeFillet(r, es)
        fillet_log[tag] = f"{len(es)} edges r{r}"
        return out
    except Exception as ex:
        fillet_log[tag] = f"FAILED ({len(es)} edges): {ex}"
        return shape
holes = Part.makeCompound([Part.makeCylinder(S["m3_clear"] / 2, 80, V(bx, -40, bz), V(0, 1, 0)) for bx, bz in BOLTS])
y_out = ARM_IN + FOOT_W                                # outer faces of the foot plates: +-26.75
g = G
plates = {}
for side, arm_n in ((1, "Gripper:1/HoopArmL"), (-1, "Gripper:1/HoopArmR")):
    y0, y1 = (ARM_IN, ARM_IN + ARM_T) if side > 0 else (-ARM_IN - ARM_T, -ARM_IN)        # the plate
    f0, f1 = (ARM_IN, y_out) if side > 0 else (-y_out, -ARM_IN)                          # the foot plate (wider)
    bar = box(g["bar_x0"], g["leg_x1"], y0, y1, g["bar_z0"], g["bar_z1"])
    leg = box(g["leg_x0"], g["leg_x1"], y0, y1, g["foot_z0"], g["bar_z1"])
    foot = box(g["leg_x0"], g["foot_x1"], f0, f1, g["foot_z0"], g["foot_z1"])
    pad = box(g["pad_x0"], g["pad_x1"], y0, y1, PCB_TOP, g["bar_z0"])
    pl = bar.fuse([leg, foot, pad]).removeSplitter()
    pl = fillet_y(pl, [(g["pad_x0"], g["bar_z0"]), (g["pad_x1"], g["bar_z0"]), (g["leg_x0"], g["bar_z0"])], g["r_in"],
                  f"plate{side} inside")                                      # inside corners in one go (separately OCC refuses)
    pl = fillet_y(pl, [(g["leg_x1"], g["bar_z1"]), (g["foot_x1"], g["foot_z1"]),
                       (g["leg_x0"], g["foot_z0"])], g["r_out"], f"plate{side} outside")
    pl = fillet_y(pl, [(g["pad_x0"], PCB_TOP), (g["pad_x1"], PCB_TOP)], g["r_pad"], f"plate{side} pad feet")
    lobe = grip[arm_n][0].common(box(-30, CUT, -60, 60, PCB_TOP + 0.3, 80))   # pivot end with its horn pad / bushing fit
    pl = lobe.fuse(pl).removeSplitter().cut(holes)
    for bx, bz in BOLTS:
        if side < 0:                                                         # counterbores for the heads, from the outer face
            pl = pl.cut(Part.makeCylinder(CB_D / 2, CB_T + 1, V(bx, -y_out - 1, bz), V(0, 1, 0)))
        else:                                                                # hex pockets for the nuts, from the outer face
            pl = pl.cut(hex_y(bx, bz, POCKET_AF, y_out - POCKET_T, POCKET_T + 1))
    plates[side] = pl
    new.append(("ShieldPlate" + ("L" if side > 0 else "R") + " (PETG)", pl, "printed"))
# U front: middle block flush with the foot plates (front x 47.5, top z 25.5) + the low half ring + two stadium prongs
cx, ri, ro = g["u_cx"], g["u_ri"], g["u_ri"] + g["u_t"]
z0, z1 = g["u_z0"], g["u_z1"]
ring = cyl_z(cx, 0, ro, z0, z1).cut(cyl_z(cx, 0, ri, z0 - 1, z1 + 1)).common(box(0, cx, -60, 60, z0, z1))
rc, a = ri + g["u_t"] / 2, math.radians(g["prong_a"])
prongs = []
for s in (1, -1):
    p0 = V(cx, s * rc, z0); d = V(math.cos(a), s * math.sin(a), 0); p1 = p0 + d * g["prong_l"]
    slab = Part.makeBox(g["prong_l"], g["u_t"], z1 - z0, V(0, -g["u_t"] / 2, 0))
    slab.rotate(V(0, 0, 0), V(0, 0, 1), s * g["prong_a"]); slab.translate(p0)
    prongs += [slab, cyl_z(p0.x, p0.y, g["u_t"] / 2, z0, z1), cyl_z(p1.x, p1.y, g["u_t"] / 2, z0, z1)]
block = box(g["block_x0"], g["foot_x1"], -ARM_IN + FIT, ARM_IN - FIT, g["foot_z0"], g["foot_z1"])
block = fillet_y(block, [(g["foot_x1"], g["foot_z1"])], g["r_out"], "block front-top")      # same round as the foot plates
blade = block.fuse([ring] + prongs).removeSplitter().cut(cyl_z(cx, 0, ri, z0 - 1, g["foot_z1"] + 1)).cut(holes)
new.append(("Shield U front (PETG)", blade, "printed"))
# 2 x M3 x 50 DIN 912, heads seated at the counterbore floors (foot plate R) + 2 x DIN 934 nuts at the pocket floors (L)
y_head = -y_out + CB_T                                # head seat
y_nut = y_out - POCKET_T                              # nut seat
screws, nuts = [], []
for bx, bz in BOLTS:
    h = Part.makeCylinder(S["head_d"] / 2, S["head_t"], V(bx, y_head - S["head_t"], bz), V(0, 1, 0))
    h = h.cut(Part.makeCylinder(1.25, 2.0, V(bx, y_head - S["head_t"] - 0.01, bz), V(0, 1, 0)))     # 2.5 hex key socket (round, for looks)
    screws.append(h.fuse(Part.makeCylinder(1.5, S["screw_l"], V(bx, y_head, bz), V(0, 1, 0))))
    nuts.append(hex_y(bx, bz, S["nut_af"], y_nut, S["nut_t"]).cut(Part.makeCylinder(1.5, 10, V(bx, y_nut - 5, bz), V(0, 1, 0))))
new.append(("U screws 2x M3x50 DIN912 (black)", Part.makeCompound(screws), "black"))
new.append(("U nuts 2x M3 DIN934 (zinc)", Part.makeCompound(nuts), "zinc"))
# ---------------- checks (bounding-box filtered, one solid pair at a time) ----------------
# designed contacts: the feet on the main board; the plates' pivot ends on the horn, horn screws and bushing; screw head and
# nut on the toes' outer faces. The right pivot end overlaps the bushing by 3.5 mm3 and is 0.35 from the pivot screw exactly
# as the BugBot's HoopArmR (its press fit, copied unchanged): reported, not counted.
contact_ok = {"Electronics:1/MainBoard (KiCad)", "Gripper:1/ServoHorn", "Gripper:1/Gripper screws", "Gripper:1/PivotBushing"}
clash, near = [], []
for nn, ns, _ in new:
    for kn, ks, _, _ in keep:
        kb = ks.BoundBox; kb.enlarge(2)
        if not ns.BoundBox.intersect(kb):
            continue
        ov = variants.common_volume(ns, ks) if ks.Solids else 0.0   # (cached while both shapes are unchanged)
        if ov > 1e-3 and not (kn == "Gripper:1/PivotBushing" and abs(ov - 3.541) < 0.01):
            clash.append((nn, kn, round(ov, 3)))
        elif kn not in contact_ok:
            near.append((round(variants.distance(ns, ks), 2), nn, kn))
near.sort()
# fits between the shield's own parts: printed-to-printed >= 0.25 a side, screw in its holes, head / nut seated
fits = {}
for i, (an, a, _) in enumerate(new):
    for bn, b, _ in new[i + 1:]:
        if not a.BoundBox.intersect(b.BoundBox):
            continue
        fits[an + " / " + bn] = (round(variants.common_volume(a, b), 3), round(variants.distance(a, b), 2))
mb = [s for n, s, _, _ in keep if n == "Electronics:1/MainBoard (KiCad)"][0]
seat = {nn: round(variants.distance(ns, mb), 3) for nn, ns, _ in new if nn.startswith("ShieldPlate")}
wasp_tip, wasp_fired = 35.04, q("body_r") + q("sol_stroke")
gap = J["gap"]                                          # worst case from the 2D (Wasp wall on the prong tips)
tip_y = y_head + S["screw_l"]                         # screw tip vs the nut's outer face and the foot plate's outer face
bolt = {"tip_vs_nut_face": round(tip_y - (y_nut + S["nut_t"]), 2), "tip_below_plate_face": round(y_out - tip_y, 2)}
mass = {nn: round(ns.Volume / 1000 * 1.27, 2) for nn, ns, k in new if k == "printed"}
# ---------------- document ----------------
if "BugBot_Beetle" in App.listDocuments(): App.closeDocument("BugBot_Beetle")
d = App.newDocument("BugBot_Beetle")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot (static copy of BugBot; ball, kicker, hoop arms + front bar removed)"
g_new = d.addObject("App::DocumentObjectGroup", "Shield"); g_new.Label = "Passive shield v2c, sasumata U, 2 flush bolts (Beetle)"
root = d.addObject("App::DocumentObjectGroup", "Beetle"); root.Label = "Beetle"; root.addObject(g_base); root.addObject(g_new)   # render root
yellow = tuple(grip["Gripper:1/HoopArmL"][2][:3]); zinc = (0.75, 0.76, 0.78); black = (0.12, 0.12, 0.13)
objs = []
for kn, ks, col, sc in keep:
    o = d.addObject("Part::Feature", "B_" + "".join(ch if ch.isalnum() else "_" for ch in kn)[:48]); o.Label = kn; o.Shape = ks; g_base.addObject(o)
    objs.append((o, col, sc))
for nn, ns, kind in new:
    o = d.addObject("Part::Feature", "S_" + "".join(ch if ch.isalnum() else "_" for ch in nn)[:48]); o.Label = nn; o.Shape = ns; g_new.addObject(o)
    objs.append((o, None, {"printed": yellow, "zinc": zinc, "black": black}[kind]))
d.recompute()
if App.GuiUp:
    for o, col, sc in objs:
        try:
            if col and len(col) == len(o.Shape.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read()); recolour(d, "Beetle")   # this style's printed colour
d.saveAs(OUTF)
variants.save_checks()
App.setActiveDocument("BugBot_Base")
result = {"fillets": fillet_log, "clashes": clash, "nearest": near[:8], "fits": fits, "board_seat_mm": seat, "stinger_gap_mm": round(gap, 2),
          "bolts": bolt, "mass_g": mass,
          "valid": [ns.isValid() for _, ns, _ in new], "solids": [len(ns.Solids) for _, ns, _ in new], "file": OUTF}
