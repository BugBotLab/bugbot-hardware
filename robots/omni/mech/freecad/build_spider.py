# BugBot "Spider" variant v3: the gripper arm carries the tag magazine and a TPU ground roller.
# Same servo, pivot and horn as the gripper. v3: magazine moved back into the ball notch (short arm), 10 tags, no follower
# weight (gravity feeds the stack), kicker removed (its 10 mm stroke would reach the magazine). Arm down -> roller on the floor; driving forward turns it and
# its top drags the bottom tag out of a one-tag front slot. Servo lifts the arm a few degrees to park (roller off the floor).
# Builds a SEPARATE document BugBot_Spider (saved as mech/freecad/BugBot_Spider.FCStd): the shared base robot
# (variants.py, the same base as BugBot_Base.FCStd) + the new parts below. The BugBot document is read only.
# Rebuilt automatically when BugBot is saved (FusionFlow Variants object in BugBot_Base.FCStd).
#   python fusionflow/ffclient.py run mech/freecad/build_spider.py
# Approved 2D: mech/freecad/sketches/spider_arm.png + spider_back.png (option A). Tags: NTAG213 PVC coins 25 x 0.9 mm.
# (Previous servo + belt version: build_spider_belt.py / BugBot_Spider_belt.FCStd.)
import Part, math
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Spider.FCStd"
# ---------------- parameters (robot frame, mm) ----------------
T = dict(
    tag_d=25.0, tag_t=0.9, n_tags=10,
    roll_d=16.0, roll_w=20.0, roll_x=48.5, grip=0.3,          # TPU ground roller; axle x; pokes this far through the floor
    hub_d=11.0, axle_d=3.0,                                   # printed hub inside the TPU tyre; 3 mm steel axle
    mag_dx=-6.0, mag_wall=1.6, mag_floor_t=1.6, mag_head=3.0, # magazine centre = roller x - 6 (contact ahead of the centre)
    slot=1.35, gate_t=1.6, follower_t=0.0,                  # (the weighted lid rides on the stack, in the head room)
    lid_rise=3.5,                                             # magazine 3.5 mm taller for the weighted lid (board still 4.4 mm away)
    lid_d=24.6, lid_h=3.0, lug_a=75.0, twist=30.0, lug_w=1.6, lug_h=1.6, slot_w=2.2,   # lid + its twist lock
    plate_y0=21.2, plate_y1=24.8,                             # arm plates (old hoop arm side plates, kept)
    run_z0=4.0, run_z1=12.0, run_x0=37.5,                     # new lower run of each plate, to the axle
    park_deg=4.0,                                             # servo lift to park
)
RR = T["roll_d"] / 2; RX = T["roll_x"]; RZ = RR                # arm lowered: roller on the floor
floor_top = T["roll_d"] - T["grip"]
MC = RX + T["mag_dx"]
R_in = T["tag_d"] / 2 + 0.4; R_out = R_in + T["mag_wall"]
top_ref = floor_top + T["n_tags"] * T["tag_t"] + T["follower_t"] + T["mag_head"]   # 27.7: tabs + screws stay where they were
top = top_ref + T["lid_rise"]                                                       # 31.2: tube top
src = App.getDocument("BugBot_Base"); asm = src.getObject("Assembly"); P = src.Params
q = lambda n: P.get(n).Value
PX, PZ = q("pivot_x"), q("pivot_z")
# ---------------- the base robot (variants.py: one definition for every variant) + what the Spider reuses ----------------
import sys, importlib
sys.path.insert(0, BB + "/mech/freecad")
import variants; importlib.reload(variants)
keep = variants.base_parts(src)                               # base (servo mount, arm, kicker, ball: modules)
keep += variants.module_leaves(src, "GripperMount")    # the servo mount module (SG90, servo block, pivot bracket + screws)
grip = variants.parts_of(src, "Gripper:1")                    # the BugBot arm: the Spider keeps its pivot end + horn
arm_old = {n: (grip[n][0], grip[n][2]) for n in ("Gripper:1/HoopArmL", "Gripper:1/HoopArmR")}
arm_keep = ["Gripper:1/ServoHorn", "Gripper:1/Gripper screws", "Gripper:1/PivotBushing"]   # ride on the arm
for n in arm_keep:
    keep.append((n,) + grip[n])
# ---------------- new parts ----------------
new = []
def add(name, shape, colour, on_arm=True): new.append((name, shape, colour, on_arm))
# arm plates: one clean L (constant width, rounded bends, round axle end) on the old hoop arms' pivot ends (servo-horn fit)
import sys, importlib
sys.path.insert(0, BB + "/mech/freecad")
import spider_parts as tp; importlib.reload(tp)
FNS = {"App": App, "Part": Part, "math": math, "V": V}                  # the BugBot's own screw models (build_fasteners.py)
_ft = open(BB + "/mech/freecad/build_fasteners.py", encoding="utf-8").read()
exec(_ft[:_ft.index("# ---------- the list")], FNS)
AX_CLR, AX_PILOT = 1.65, 1.25                                           # M3 axle screw: clearance (L, head side), pilot (R)
for nm, side in (("Gripper:1/HoopArmL", 1), ("Gripper:1/HoopArmR", -1)):
    sh, sc = arm_old[nm]
    y0 = T["plate_y0"] if side > 0 else -T["plate_y1"]
    plate = tp.plate(sh, y0, y0 + T["plate_y1"] - T["plate_y0"], RX, RZ, run_z=(T["run_z0"], T["run_z1"]))
    plate = plate.cut(Part.makeCylinder(AX_CLR if side > 0 else AX_PILOT, 60, V(RX, -30, RZ), V(0, 1, 0)))
    add("Arm plate " + ("L" if side > 0 else "R") + " (printed)", plate, (1.0, 0.769, 0.0))   # printed yellow, like the chassis
# roller: TPU tyre on a printed hub, 3 mm axle, printed spacers to the plates
add("Roller tyre (TPU)", Part.makeCylinder(RR, T["roll_w"], V(RX, -T["roll_w"] / 2, RZ), V(0, 1, 0)).cut(
    Part.makeCylinder(T["hub_d"] / 2, T["roll_w"] + 2, V(RX, -T["roll_w"] / 2 - 1, RZ), V(0, 1, 0))), (0.13, 0.13, 0.13))
add("Roller hub (printed)", Part.makeCylinder(T["hub_d"] / 2, T["roll_w"], V(RX, -T["roll_w"] / 2, RZ), V(0, 1, 0)).cut(
    Part.makeCylinder(AX_CLR, T["roll_w"] + 2, V(RX, -T["roll_w"] / 2 - 1, RZ), V(0, 1, 0))), (0.35, 0.35, 0.38))
add("Axle screw M3x50 socket (steel)", FNS["place"](FNS["screw"]("M3", 50, "socket"), (RX, T["plate_y1"], RZ), (0, -1, 0)), (0.17, 0.17, 0.18))   # threads into plate R
for s in (1, -1):
    y0 = T["roll_w"] / 2 + 0.3 if s > 0 else -T["plate_y0"] + 0.3
    add(f"Axle spacer {'L' if s > 0 else 'R'}", Part.makeCylinder(2.6, T["plate_y0"] - T["roll_w"] / 2 - 0.6, V(RX, y0, RZ), V(0, 1, 0)).cut(
        Part.makeCylinder(AX_CLR, 30, V(RX, -15, RZ), V(0, 1, 0))), (0.8, 0.8, 0.82))
# magazine: tube + floor + a lip that follows the tube over the slot + one tab per side (filleted into the tube; flat
# outer faces against the arm plates), then the slot, roller window, bore, roller clearance and screw pilots are cut
mag, n_fil = tp.magazine(MC, R_in, R_out, floor_top - T["mag_floor_t"], top, floor_top, T["slot"], lip_t=T["gate_t"],
                         tab_x=(36.5, 42.5), tab_y=(11.0, T["plate_y0"] - 0.2), r_tab_out=0.0, tab_top=top_ref - 1.7)   # flush with the drop of the arm plate
mag = mag.cut(Part.makeBox(R_out + 3, 2 * R_in - 1.0, T["slot"], V(MC, -(R_in - 0.5), floor_top)))           # front slot
win_half = math.sqrt(RR ** 2 - (floor_top - T["mag_floor_t"] - RZ) ** 2) + 0.6
# roller window open to the front (no floor ledge ahead of the roller): a tag tips out as soon as it passes the roller,
# instead of being cantilevered with its tail pinned under the next tag (sim/spider/dispense_test.py: ledge -> jams)
window = Part.makeBox(MC + R_out + 1.0 - (RX - win_half), T["roll_w"] + 1.0, T["mag_floor_t"] + 3, V(RX - win_half, -T["roll_w"] / 2 - 0.5, floor_top - T["mag_floor_t"] - 2.5))
mag = mag.cut(window).cut(Part.makeCylinder(R_in, top, V(MC, 0, floor_top)))
mag = mag.cut(Part.makeCylinder(RR + 0.8, T["roll_w"] + 1.0, V(RX, -T["roll_w"] / 2 - 0.5, RZ), V(0, 1, 0)))   # roller clearance
SCREWS = [(39.5, 18.0), (39.5, top_ref - 4.7)]                 # two M2x8 pan heads per side through the plate's drop
screws = []
for sd in (1, -1):
    for sx, sz in SCREWS:
        yp = T["plate_y1"] if sd > 0 else -T["plate_y1"]
        screws.append((f"Magazine screw M2x8 pan ({'L' if sd > 0 else 'R'}, z {sz:.0f})", FNS["place"](FNS["screw"]("M2", 8, "pan"), (sx, yp, sz), (0, -sd, 0)), sx, sz))
for nm, sc_, sx, sz in screws:
    mag = mag.cut(Part.makeCylinder(0.8, 30, V(sx, -15, sz), V(0, 1, 0)).fuse(Part.makeCylinder(0.8, 30, V(sx, 15, sz), V(0, -1, 0))))
# twist lock for the weighted lid: a vertical slot through the wall at +-lug_a, turning twist deg sideways at the top to
# an entry notch (both lugs turn the same way: +75 -> +105, -75 -> -45). Lift to the top + twist to take the lid out.
LID_ZB = floor_top + T["n_tags"] * (T["tag_t"] + 0.01) + 0.02             # lid bottom with a full stack
SL_Z0 = floor_top + T["lid_h"] / 2 - T["lug_h"] / 2 - 0.5                  # slot bottom: the lug with no tags left
J_Z0, J_Z1 = top - 2.6, top - 0.4                                          # the sideways part of the J
r0_, r1_ = R_in - 0.3, R_out + 0.5
def radial_box(ang, z0, z1, w):
    b = Part.makeBox(r1_ - r0_, w, z1 - z0, V(r0_, -w / 2, z0))
    b.rotate(V(0, 0, 0), V(0, 0, 1), ang); b.translate(V(MC, 0, 0)); return b
def sector(a0, a1, z0, z1):
    c = Part.makeCylinder(r1_, z1 - z0, V(0, 0, z0), V(0, 0, 1), a1 - a0).cut(Part.makeCylinder(r0_, z1 - z0 + 1, V(0, 0, z0 - 0.5)))
    c.rotate(V(0, 0, 0), V(0, 0, 1), a0); c.translate(V(MC, 0, 0)); return c
hw_deg = math.degrees(T["slot_w"] / 2 / R_out)
for la in (T["lug_a"], -T["lug_a"]):
    ea = la + T["twist"]
    mag = mag.cut(radial_box(la, SL_Z0, J_Z1, T["slot_w"]))
    mag = mag.cut(sector(min(la, ea) - hw_deg, max(la, ea) + hw_deg, J_Z0, J_Z1))
    mag = mag.cut(radial_box(ea, J_Z0, top + 1.0, T["slot_w"]))
add("Magazine (printed)", mag, (1.0, 0.769, 0.0))   # printed yellow, like the chassis + arms
# screw clearance holes in the plates
for i, (n, s, c, o) in enumerate(new):
    if n.startswith("Arm plate"):
        for nm, sc_, sx, sz in screws:
            s = s.cut(Part.makeCylinder(1.1, 60, V(sx, -30, sz), V(0, 1, 0)))
        new[i] = (n, s, c, o)
for nm, sc_, sx, sz in screws: add(nm, sc_, (0.77, 0.78, 0.81))
# tags + follower (printed)
for i in range(T["n_tags"]):
    add(f"Tag {i + 1}", Part.makeCylinder(T["tag_d"] / 2, T["tag_t"], V(MC, 0, floor_top + i * (T["tag_t"] + 0.01))), (0.62, 0.3, 0.85) if i % 2 else (0.52, 0.22, 0.75))   # purple tags
# weighted lid: printed cup (base 0.6, rim, centre boss, 2 lugs) holding an M10 washer (DIN 125: 20 x 10.5 x 2, steel)
zb = LID_ZB
cup = Part.makeCylinder(T["lid_d"] / 2, T["lid_h"], V(MC, 0, zb)).cut(Part.makeCylinder(10.2, T["lid_h"], V(MC, 0, zb + 0.6)))
cup = cup.fuse(Part.makeCylinder(4.65, 1.4, V(MC, 0, zb + 0.6)))
lug_r0, lug_r1 = T["lid_d"] / 2 - 0.4, R_out + 0.3
for la in (T["lug_a"], -T["lug_a"]):
    lg = Part.makeBox(lug_r1 - lug_r0, T["lug_w"], T["lug_h"], V(lug_r0, -T["lug_w"] / 2, zb + T["lid_h"] / 2 - T["lug_h"] / 2))
    lg.rotate(V(0, 0, 0), V(0, 0, 1), la); lg.translate(V(MC, 0, 0)); cup = cup.fuse(lg)
cup = cup.removeSplitter()
washer = Part.makeCylinder(10.0, 2.0, V(MC, 0, zb + 0.6)).cut(Part.makeCylinder(5.25, 3, V(MC, 0, zb)))
add("Lid/cup (printed)", cup, (1.0, 0.769, 0.0))
add("Lid/washer M10 (steel)", washer, (0.72, 0.74, 0.78))
# ---------------- checks ----------------
def pts_of(sh, n=800):
    Pp = []
    for e in sh.Edges:
        try: Pp += e.discretize(Number=12)
        except Exception: pass
    return Pp[::max(1, len(Pp) // n)]
def heavy(name): return ("KiCad" in name) or name.startswith("Fasteners")
def clash(an, a, bn, b, ap=None):
    if not a.BoundBox.intersect(b.BoundBox): return None
    if heavy(an) or heavy(bn):
        ap = ap if ap is not None else pts_of(a)
        hits = 0
        for so in (b.Solids or [b]):
            bb = so.BoundBox
            if not bb.intersect(a.BoundBox): continue
            hits += sum(1 for p in ap if bb.isInside(p) and so.isInside(p, 0.05, False))
        return f"{hits} sample points inside" if hits else None
    try: v = variants.common_volume(a, b)     # (cached while both shapes are unchanged)
    except Exception: return "boolean failed"
    return round(v, 2) if v > 0.01 else None
def parked(sh):
    s = sh.copy(); s.rotate(V(PX, 0, PZ), V(0, 1, 0), -T["park_deg"]); return s     # nose up
allowed = [({"Axle screw M3x50 socket (steel)"}, ("Roller hub", "Arm plate", "Axle spacer")),
           ({"Roller tyre (TPU)"}, ("Roller hub",))]
def ok_pair(an, bn):
    for s1, pref in allowed:
        if (an in s1 and bn.startswith(pref)) or (bn in s1 and an.startswith(pref)): return True
    if "Magazine screw" in an + bn and ("Magazine (printed)" in (an, bn) or "Arm plate" in an + bn): return True
    if an.startswith("Lid/") and bn.startswith("Lid/"): return True
    if "Arm plate" in an + bn and ("Gripper:1/" in an + bn or "Fasteners" in an + bn and "Gripper" in an + bn): return True
    return False
report = {"lowered": [], "parked": []}
fixed = [(kn, ks) for kn, ks, _, _ in keep if kn not in arm_keep]
for mode in ("lowered", "parked"):
    movers = [(n, parked(s) if (mode == "parked" and o) else s) for n, s, c, o in new if not n.startswith(("Tag ", "Follower"))]
    for nn, ns in movers:
        if nn.startswith("Tag mine"): continue
        ap = pts_of(ns)
        for kn, ks in fixed + [(k, parked(s) if mode == "parked" else s) for k, s, _, _ in keep if k in arm_keep]:
            if ok_pair(nn, kn): continue
            r = clash(nn, ns, kn, ks, ap)
            if r: report[mode].append([nn, kn, r])
    if mode == "lowered":
        for i in range(len(movers)):
            for j in range(i + 1, len(movers)):
                (an, a), (bn, b) = movers[i], movers[j]
                if ok_pair(an, bn): continue
                r = clash(an, a, bn, b)
                if r: report[mode].append([an, bn, r])
def gap(a, b):
    try: return round(variants.distance(a, b), 2)
    except Exception: return None
G = {n: s for n, s, c, o in new}
K = {n: s for n, s in fixed}
pk = {n: parked(s) for n, s, c, o in new if o}
clear = {
    "magazine top z lowered / parked": [round(G["Magazine (printed)"].BoundBox.ZMax, 1), round(pk["Magazine (printed)"].BoundBox.ZMax, 1)],
    "camera z": round(q("pcb_top") + 17, 1),
    "roller bottom z parked": round(pk["Roller tyre (TPU)"].BoundBox.ZMin, 2),
    "lowest arm plate z lowered": round(min(G["Arm plate L (printed)"].BoundBox.ZMin, G["Arm plate R (printed)"].BoundBox.ZMin), 2),
    "lid - magazine (lugs in their slots)": gap(G["Lid/cup (printed)"], G["Magazine (printed)"]),
    "magazine - main board (tube top raised)": gap(G["Magazine (printed)"], K["Electronics:1/MainBoard (KiCad)"]),
    "plate L - chassis": gap(G["Arm plate L (printed)"], K["Frame:1/Chassis"]),
    "plate R - chassis": gap(G["Arm plate R (printed)"], K["Frame:1/Chassis"]),
    "magazine - chassis": gap(G["Magazine (printed)"], K["Frame:1/Chassis"]),
    "magazine - main board (lowered / parked)": [gap(G["Magazine (printed)"], K["Electronics:1/MainBoard (KiCad)"]), gap(pk["Magazine (printed)"], K["Electronics:1/MainBoard (KiCad)"])],
    "magazine - front board (parked)": gap(pk["Magazine (printed)"], K["Electronics:1/FrontSensorBoard (KiCad)"]),
    "magazine - mast (parked)": gap(pk["Magazine (printed)"], K["SensorMast:1/Mast"]),
    "plate L - wheel 1 frame": gap(G["Arm plate L (printed)"], next(v for k, v in K.items() if k.startswith("DriveUnit:1/") and k.endswith("/WheelFrameOne"))),
    "plate R - wheel 3 frame": gap(G["Arm plate R (printed)"], next(v for k, v in K.items() if k.startswith("DriveUnit:3/") and k.endswith("/WheelFrameOne"))),
}
dens = {"(printed)": 1.24 * 0.6, "TPU": 1.2, "steel": 7.85, "spacer": 1.24}
mass = {}
for n, s, c, o in new:
    if not o: continue
    if n.startswith("Tag "): mass[n] = s.Volume * 1.4e-3; continue
    dd = next((v for k, v in dens.items() if k in n), 1.24 * 0.6)
    if "screw" in n: dd = 7.85
    mass[n] = s.Volume * dd * 1e-3
m_tot = sum(mass.values())
def com_x(sh):
    so = sh.Solids or [sh]; vv = sum(x.Volume for x in so)
    return sum(x.Volume * x.CenterOfMass.x for x in so) / vv
cx = sum(mass[n] * com_x(G[n]) for n in mass) / m_tot if m_tot else 0
clear["arm payload g (est.)"] = round(m_tot, 1)
clear["payload torque kg.cm"] = round(m_tot * (cx - PX) / 10 / 1000, 2)
clear["payload CoM x"] = round(cx, 1)
# ---------------- document ----------------
if "BugBot_Spider" in App.listDocuments(): App.closeDocument("BugBot_Spider")
d = App.newDocument("BugBot_Spider")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot (static copy of BugBot; ball, kicker, hoop arms + front bar removed)"
g_new = d.addObject("App::DocumentObjectGroup", "Dispenser"); g_new.Label = "Tag dispenser on the arm (Spider v3)"
root = d.addObject("App::DocumentObjectGroup", "Spider"); root.Label = "Spider"; root.addObject(g_base); root.addObject(g_new)   # render root
objs = []
for kn, ks, col, sc in keep:
    o = d.addObject("Part::Feature", "B_" + "".join(ch if ch.isalnum() else "_" for ch in kn)[:48]); o.Label = kn; o.Shape = ks; g_base.addObject(o)
    objs.append((o, col, sc))
for nn, ns, colour, _ in new:
    o = d.addObject("Part::Feature", "T_" + "".join(ch if ch.isalnum() else "_" for ch in nn)[:48]); o.Label = nn; o.Shape = ns; g_new.addObject(o)
    objs.append((o, None, colour))
# the magazine's colliders for the simulator (SimLink ColliderShapes): convex pieces, so the one-tag slot stays exact:
# 36 wall segments (inner faces on R_in; the front ones start above the slot) + the floor round the roller window
cs = []
NSEG = 36
for k in range(NSEG):
    a = math.radians(T["lug_a"] % 10 + 360.0 * k / NSEG)
    if min(abs((math.degrees(a) - la + 180) % 360 - 180) for la in (T["lug_a"], -T["lug_a"])) < 1:
        continue                                                     # the lugs' slots
    hw = (R_in + T["mag_wall"]) * math.tan(math.pi / NSEG) * 1.08
    front = math.cos(a) > 0 and abs(R_in * math.sin(a)) < R_in - 0.5 + hw
    z0 = floor_top + T["slot"] if front else floor_top - T["mag_floor_t"]
    b = Part.makeBox(T["mag_wall"], 2 * hw, top - z0, V(R_in, -hw, z0))
    b.rotate(V(0, 0, 0), V(0, 0, 1), math.degrees(a)); b.translate(V(MC, 0, 0))
    cs.append(b)
zf = floor_top - T["mag_floor_t"]; wy = T["roll_w"] / 2 + 0.5
xw0, xw1 = RX - win_half, MC + R_out                                  # window open to the front
cs.append(Part.makeBox(xw0 - (MC - R_out), 2 * R_out, T["mag_floor_t"], V(MC - R_out, -R_out, zf)))
if MC + R_out - xw1 > 0.2:
    cs.append(Part.makeBox(MC + R_out - xw1, 2 * R_out, T["mag_floor_t"], V(xw1, -R_out, zf)))
for sd in (1, -1):
    cs.append(Part.makeBox(xw1 - xw0, R_out - wy, T["mag_floor_t"], V(xw0, wy if sd > 0 else -R_out, zf)))
mc = d.addObject("Part::Feature", "MagazineCollider"); mc.Label = "MagazineCollider (sim only)"; mc.Shape = Part.makeCompound(cs)
mc.Visibility = False
lc = Part.makeCompound([Part.makeCylinder(T["lid_d"] / 2, T["lid_h"], V(MC, 0, zb))] +
                       [radial_box(la, zb + T["lid_h"] / 2 - T["lug_h"] / 2, zb + T["lid_h"] / 2 + T["lug_h"] / 2, T["lug_w"]).common(
                           Part.makeCylinder(lug_r1, 10, V(MC, 0, zb - 2)).cut(Part.makeCylinder(lug_r0, 12, V(MC, 0, zb - 3))))
                        for la in (T["lug_a"], -T["lug_a"])])
lo = d.addObject("Part::Feature", "LidCollider"); lo.Label = "LidCollider (sim only)"; lo.Shape = lc; lo.Visibility = False
d.recompute()
if App.GuiUp:
    for o, col, sc in objs:
        try:
            if col and len(col) == len(o.Shape.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read()); recolour(d, "Spider")   # this style's printed colour
d.saveAs(OUTF)
variants.save_checks()
App.setActiveDocument("BugBot_Base")
result = {"fillets": n_fil, "clashes": report, "clearances": clear, "mass": {k: round(v, 2) for k, v in mass.items() if not k.startswith("Tag ")},
          "parts": {"kept": len(keep), "new": len(new)}, "file": OUTF}
