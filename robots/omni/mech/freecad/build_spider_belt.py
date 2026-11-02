# BugBot "Spider" variant: gripper and kicker removed; a friction-roller tag dispenser in the old ball pocket.
# Builds a SEPARATE document BugBot_Spider (saved as mech/freecad/BugBot_Spider.FCStd) from static copies of the BugBot
# assembly's parts plus the dispenser parts below. The BugBot document is read only, never changed or saved.
#   python fusionflow/ffclient.py run mech/freecad/build_spider.py
# Approved 2D: mech/freecad/sketches/tag_roller.png. Tags: NTAG213 PVC coins 25 x 0.9 mm.
import math, json, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Spider.FCStd"
# ---------------- parameters (robot frame, mm) ----------------
T = dict(
    tag_d=25.0, tag_t=0.9, n_tags=20,
    roll_d=8.5, roll_w=10.0, roll_bot=3.0, grip=0.3,          # rubber-tyred roller (O-ring tyre); lowest point; pokes up through the floor window
    mag_c=47.0, mag_wall=1.6, mag_floor_t=1.6, mag_head=13.0, # magazine centre X (old ball pocket), walls, room above the stack (top meets the bracket)
    slot=1.35, gate_t=1.6,                                    # one-tag front slot; screw-set gate above it
    roll_dx=4.0,                                              # roller ahead of the magazine centre
    servo_x=51.0, servo_z=19.25, servo_y_end=17.0,           # SG90 beside the magazine (front left, where the gripper arm was), shaft -Y
    p_servo=12.0, p_roll=6.0, p_w=2.4, belt_d=1.5,            # pulleys (2:1) and O-ring belt cross-section
    mount_y=6.0, mount_z0=36.0, mount_z1=42.0,                # magazine bracket to the mast front plate (x 24), above the mast's own M2 screws
    follower_t=4.0,
)
roll_c = T["roll_bot"] + T["roll_d"] / 2
floor_top = roll_c + T["roll_d"] / 2 - T["grip"]
roll_x = T["mag_c"] + T["roll_dx"]
src = App.getDocument("BugBot_Base"); asm = src.getObject("Assembly"); P = src.Params
q = lambda n: P.get(n).Value
# ---------------- copy the parts that stay ----------------
drop_occ = ("Gripper:1/", "Kicker:1/", "Ball:1/")
drop_parts = ("GripperMount:1/HoopBracket", "GripperMount:1/PivotTube", "SensorMast:1/ServoBlock", "GripperMount:1/Servo")
# fastener solids that belonged to the gripper, its servo mount or the kicker (dropped by position)
pts = [(q("servo_x0") - 2.3, q("ear_y") + 2.15), (q("pivot_x") - q("hoopbr_dx"), q("hoopbr_y")), (q("pivot_x") + q("hoopbr_dx"), q("hoopbr_y")),
       (q("kb_front_x"), q("kb_front_y")), (q("kb_rear_x"), q("kb_rear_y")), (q("ear_x0"), q("ear_y") - 2.5), (q("ear_x1"), q("ear_y") - 2.5)]
def gone(so):
    c = so.BoundBox.Center
    if any(math.hypot(c.x - x, c.y - y) < 3.0 for x, y in pts): return True
    if abs(c.x - q("pivot_x")) < 4 and abs(c.z - q("pivot_z")) < 4: return True          # pivot screw / washer / nut
    sol_x0 = q("sol_x0"); return (sol_x0 - 3 < c.x < sol_x0 + q("sol_len") + 3 and c.z < 29 and abs(c.y) < 15 and so.BoundBox.ZMax < 29.5
                                  and "M3" in "")  # solenoid screws are in the Black group (handled below)
servo_src = None; keep = []
for occ in asm.Group:
    if not occ.isDerivedFrom("App::Link"): continue
    def walk(path, obj):
        global servo_src
        tgt = obj.getLinkedObject(True) if obj.isDerivedFrom("App::Link") else obj
        if tgt.isDerivedFrom("App::Part"):
            for c in tgt.Group:
                if c.isDerivedFrom("App::Origin") or not c.Visibility: continue
                walk(path + c.Name + ".", c)
        elif hasattr(tgt, "Shape") and not tgt.Shape.isNull():
            name = occ.Label + "/" + obj.Label
            sh = Part.getShape(asm, path, needSubElement=False, transform=True)
            try: col, sc = list(tgt.ViewObject.DiffuseColor), tuple(tgt.ViewObject.ShapeColor)
            except Exception: col, sc = None, (0.8, 0.8, 0.8)
            if name == "GripperMount:1/Servo": servo_src = (sh, col, sc); return
            if name.startswith(drop_occ) or name in drop_parts: return
            if name.startswith("Fasteners:1/"):
                if "black" in name.lower():
                    sols = [so for so in sh.Solids if not (so.BoundBox.ZMax < 29.5 and abs(so.BoundBox.Center.y) < 15 and -6 < so.BoundBox.Center.x < 24)]   # solenoid screws
                else:
                    sols = [so for so in sh.Solids if not gone(so)]
                if not sols: return
                sh = Part.makeCompound(sols); col = None
            keep.append((name, sh, col, sc))
    walk(occ.Name + ".", occ)
# ---------------- new parts ----------------
new = []
def add(name, shape, colour): new.append((name, shape, colour))
# servo moved into the old kicker bay
servo = servo_src[0].copy()
servo.rotate(V(q("pivot_x"), 0, q("pivot_z")), V(0, 0, 1), 180)       # shaft now points -Y
sb0 = servo.BoundBox
servo.translate(V(T["servo_x"] - q("pivot_x"), T["servo_y_end"] - sb0.YMin, T["servo_z"] - q("pivot_z")))
shaft_y = servo.BoundBox.YMin                                         # end of the output spline (facing the magazine)
add("Servo (SG90, moved)", servo, (0.23, 0.37, 0.66))
SX, SZ = T["servo_x"], T["servo_z"]
py1 = shaft_y + 0.2; py0 = py1 - T["p_w"]; belt_y = (py0 + py1) / 2   # pulleys sit between the tube and the servo
add("Servo pulley 12", Part.makeCylinder(T["p_servo"] / 2, T["p_w"], V(SX, py0, SZ), V(0, 1, 0)), (0.9, 0.49, 0.13))
# roller, its shaft and pulley
add("Roller (O-ring tyre)", Part.makeCylinder(T["roll_d"] / 2, T["roll_w"], V(roll_x, -T["roll_w"] / 2, roll_c), V(0, 1, 0)), (0.12, 0.12, 0.12))
add("Roller shaft 2 mm", Part.makeCylinder(1.0, py1 + 0.3 + 8.0, V(roll_x, -8.0, roll_c), V(0, 1, 0)), (0.75, 0.76, 0.8))
add("Roller pulley 6", Part.makeCylinder(T["p_roll"] / 2, T["p_w"], V(roll_x, py0, roll_c), V(0, 1, 0)), (0.9, 0.49, 0.13))
# O-ring belt: open-belt path (two tangent lines + two arcs) round the pulleys, swept circle
def belt_shape():
    r1, r2 = T["p_servo"] / 2 - 0.2, T["p_roll"] / 2 - 0.2
    c1, c2 = (SX, SZ), (roll_x, roll_c)
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]; Ld = math.hypot(dx, dz); a = math.atan2(dz, dx)
    b = math.acos((r1 - r2) / Ld)
    pt = lambda c, r, ang: V(c[0] + r * math.cos(ang), belt_y, c[1] + r * math.sin(ang))
    t1a, t1b = pt(c1, r1, a + b), pt(c2, r2, a + b)
    t2a, t2b = pt(c1, r1, a - b), pt(c2, r2, a - b)
    arc1 = Part.Arc(t2a, pt(c1, r1, a + math.pi), t1a).toShape()       # big pulley, far side
    arc2 = Part.Arc(t1b, pt(c2, r2, a), t2b).toShape()                  # small pulley, near side
    w = Part.Wire(Part.__sortEdges__([Part.LineSegment(t1a, t1b).toShape(), arc2, Part.LineSegment(t2b, t2a).toShape(), arc1]))
    e0 = w.OrderedEdges[0]; p0 = e0.valueAt(e0.FirstParameter); d0 = e0.tangentAt(e0.FirstParameter)
    prof = Part.Wire([Part.makeCircle(T["belt_d"] / 2, p0, d0)])
    return w.makePipeShell([prof], True, False)
try:
    add("O-ring belt", belt_shape(), (0.15, 0.15, 0.15))
except Exception as ex:
    print("belt sweep failed:", ex)
# magazine: round tube on a floor with a roller window, a one-tag front slot, bearing cheeks for the roller shaft
R_in = T["tag_d"] / 2 + 0.4; R_out = R_in + T["mag_wall"]
top = floor_top + T["n_tags"] * T["tag_t"] + T["mag_head"]
MC = T["mag_c"]
tube = Part.makeCylinder(R_out, top - floor_top, V(MC, 0, floor_top)).cut(Part.makeCylinder(R_in, top - floor_top + 1, V(MC, 0, floor_top - 0.5)))
tube = tube.cut(Part.makeBox(R_out + 1, 2 * R_in - 1.0, T["slot"], V(MC, -(R_in - 0.5), floor_top)))        # front slot
floor = Part.makeCylinder(R_out, T["mag_floor_t"], V(MC, 0, floor_top - T["mag_floor_t"]))
floor = floor.cut(Part.makeBox(T["roll_d"] + 0.8, T["roll_w"] + 0.8, 4, V(roll_x - T["roll_d"] / 2 - 0.4, -T["roll_w"] / 2 - 0.4, floor_top - 2)))
cheeks = Part.makeCompound([])
cheek_list = []
for y0 in (-T["roll_w"] / 2 - 2.4, T["roll_w"] / 2 + 0.4):
    ch = Part.makeBox(5.0, 2.0, floor_top - T["mag_floor_t"] - (roll_c - 2.2), V(roll_x - 2.5, y0, roll_c - 2.2))
    cheek_list.append(ch.cut(Part.makeCylinder(1.15, 5, V(roll_x, y0 - 1, roll_c), V(0, 1, 0))))
gate = Part.makeBox(4.0, 2 * R_in - 2.0, T["gate_t"], V(MC + R_in - 1.6, -(R_in - 1.0), floor_top + T["slot"]))
# bracket: a 3 mm plate flat on the mast front face (x 24) + two webs to the tube's back; two M2 x 6 screws at y +/-17,
# beside the tube, so a screwdriver reaches them from the front
bx0 = q("mast_x") + 3.0                                                   # mast front face
zc = (T["mount_z0"] + T["mount_z1"]) / 2
plate = Part.makeBox(3.0, 40.0, T["mount_z1"] - T["mount_z0"], V(bx0, -20.0, T["mount_z0"]))
webs = [Part.makeBox(MC - R_out + 1.0 - (bx0 + 3.0), 3.0, T["mount_z1"] - T["mount_z0"], V(bx0 + 3.0, y0, T["mount_z0"])) for y0 in (-7.0, 4.0)]
mag = tube.fuse([floor, gate] + cheek_list + [plate] + webs).removeSplitter()
for yy in (-17.0, 17.0):
    mag = mag.cut(Part.makeCylinder(1.15, 10, V(bx0 - 2.0, yy, zc), V(1, 0, 0)))
add("Magazine (printed)", mag, (0.93, 0.93, 0.96))
for yy in (-17.0, 17.0):
    screw = Part.makeCylinder(1.0, 6.0, V(bx0 - 3.0, yy, zc), V(1, 0, 0)).fuse(Part.makeCylinder(1.9, 1.3, V(bx0 + 3.0, yy, zc), V(1, 0, 0)))
    add(f"Magazine screw M2x6 (y {yy:+.0f})", screw, (0.77, 0.78, 0.81))
# tags + follower
for i in range(T["n_tags"]):
    add(f"Tag {i + 1}", Part.makeCylinder(T["tag_d"] / 2, T["tag_t"] - 0.05, V(MC, 0, floor_top + i * T["tag_t"])), (0.96, 0.96, 0.94) if i % 2 else (0.88, 0.88, 0.85))
add("Follower weight", Part.makeCylinder(T["tag_d"] / 2 - 1.0, T["follower_t"], V(MC, 0, floor_top + T["n_tags"] * T["tag_t"] + 0.05)), (0.6, 0.62, 0.66))
add("Tag mine on the field", Part.makeCylinder(T["tag_d"] / 2, T["tag_t"], V(MC + 40, 4, 0.0)), (0.96, 0.96, 0.94))
# servo cradle: two blocks under the servo's ear tabs, standing on the chassis floor plate (checked below)
sb = servo.BoundBox
# servo cradle: bottom plate + outer wall, hung from a bridge that passes OVER the belt and pulleys into the magazine wall
base_z = sb.ZMin
cradle = Part.makeBox(sb.XLength, sb.YMax - (py1 + 0.8), 1.6, V(sb.XMin, py1 + 0.8, base_z - 1.6))
cradle = cradle.fuse(Part.makeBox(sb.XLength, 1.6, sb.ZMax + 2.2 - (base_z - 1.6), V(sb.XMin, sb.YMax, base_z - 1.6)))
bz0 = max(sb.ZMax, SZ + T["p_servo"] / 2) + 0.6
bridge = Part.makeBox(12.0, sb.YMax + 1.6 - (R_in + 0.2), 1.8, V(roll_x - 6.0, R_in + 0.2, bz0))
cradle = cradle.fuse([bridge, Part.makeBox(12.0, 1.6, bz0 + 1.8 - (sb.ZMax), V(roll_x - 6.0, sb.YMax, sb.ZMax))]).removeSplitter()
cradle = cradle.cut(servo)
add("Servo holder (printed, part of the magazine)", cradle, (0.98, 0.80, 0.25))
# ---------------- checks ----------------
# exact booleans only for simple parts; the KiCad boards, fastener groups and the swept belt are screened by sampling
# points of the new part against the other part's solids (whole multi-solid booleans hang or give bogus volumes)
def pts_of(sh, n=800):
    P = []
    for e in sh.Edges:
        try: P += e.discretize(Number=12)
        except Exception: pass
    return P[::max(1, len(P) // n)]
def heavy(name): return ("KiCad" in name) or name.startswith("Fasteners") or name == "O-ring belt"
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
    try: v = a.common(b).Volume
    except Exception: return "boolean failed"
    return round(v, 2) if v > 0.01 else None
report = []
for nn, ns, _ in new:
    if nn.startswith(("Tag ", "Follower", "Tag mine")): continue
    ap = pts_of(ns)
    for kn, ks, _, _ in keep:
        r = clash(nn, ns, kn, ks, ap)
        if r: report.append([nn, kn, r])
for a_i in range(len(new)):
    for b_i in range(a_i + 1, len(new)):
        (an, a, _), (bn, b, _) = new[a_i], new[b_i]
        if any(n.startswith(("Tag", "Follower")) for n in (an, bn)): continue
        if ("pulley" in an or "pulley" in bn) and ("belt" in an or "belt" in bn): continue      # the belt sits on the pulleys
        if {"Roller shaft 2 mm"} & {an, bn} and ({"Roller (O-ring tyre)", "Roller pulley 6", "Magazine (printed)"} & {an, bn}): continue
        if {"Servo pulley 12", "Servo (SG90, moved)"} == {an, bn}: continue
        if "Magazine screw" in an + bn and "Magazine (printed)" in (an, bn): continue
        if {"Magazine (printed)", "Servo holder (printed, part of the magazine)"} == {an, bn}: continue
        r = clash(an, a, bn, b)
        if r: report.append([an, bn, r])
clear = {"servo bbox": [round(v, 1) for v in (sb.XMin, sb.XMax, sb.YMin, sb.YMax, sb.ZMin, sb.ZMax)],
         "belt plane y": round(belt_y, 2), "magazine floor top": round(floor_top, 2)}
# ---------------- document ----------------
if "BugBot_Spider" in App.listDocuments(): App.closeDocument("BugBot_Spider")
d = App.newDocument("BugBot_Spider")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot (static copy of BugBot, gripper + kicker removed)"
g_new = d.addObject("App::DocumentObjectGroup", "Dispenser"); g_new.Label = "Tag dispenser (Spider)"
objs = []
for kn, ks, col, sc in keep:
    o = d.addObject("Part::Feature", "B_" + "".join(ch if ch.isalnum() else "_" for ch in kn)[:48]); o.Label = kn; o.Shape = ks; g_base.addObject(o)
    objs.append((o, col, sc))
for nn, ns, colour in new:
    o = d.addObject("Part::Feature", "T_" + "".join(ch if ch.isalnum() else "_" for ch in nn)[:48]); o.Label = nn; o.Shape = ns; g_new.addObject(o)
    objs.append((o, None, colour))
d.recompute()
if App.GuiUp:
    for o, col, sc in objs:
        try:
            if col and len(col) == len(o.Shape.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
d.saveAs(OUTF)
App.setActiveDocument("BugBot_Base")
result = {"clashes": report, "clearances": clear, "parts": {"kept": len(keep), "new": len(new)}, "file": OUTF}
