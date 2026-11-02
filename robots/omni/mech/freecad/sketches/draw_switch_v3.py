# Power switch v3 for approval (user, 2026-10-25): keep the MOSFET (Q6) switching; SW1 becomes a hidden THROUGH-HOLE
# right-angle slide switch, the SK-12D07 type sold on Amazon UK (sourcingmap B00PDKEX1E; LCSC twin ROCPU SK-12D07-6,
# C16493666, whose footprint / STEP are used). Under the board at the switch angle, slider through a small slot in the
# wall, its tip 0.3 mm inside the wall's outer face (hidden, flush). Left: seen from below (bottom side, robot frame);
# right: section through the wall along the switch axis.
#   C:/Python312/python.exe mech/freecad/sketches/draw_switch_v3.py
import json, math, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, Wedge, Ellipse
HERE = os.path.dirname(os.path.abspath(__file__))
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
BM = BB + "/design/schematics/Main/_place/board_map.json"
R_IN, R_OUT, PCB_Z, PCB_T = 38.8, 40.6, 29.0, 1.6
ANG_NOW = 237.0
RECESS = 0.3                                            # slider tip inside the wall's outer face
KNOB_L, KNOB_W, KNOB_T = 4.0, 2.0, 2.0                   # slider sticks 4.0 out of the body face, 2 x 2
BODY_L, BODY_D, BODY_H = 8.6, 4.3, 4.0                   # along the wall, radial depth, below the board
TRAVEL = 2.0                                            # slider travel (check on the real part)
SLOT_W = KNOB_W + TRAVEL + 2 * 0.6                       # 0.6 mm clearance a side (print tolerance)
r_tip = R_OUT - RECESS
r_face = r_tip - KNOB_L                                  # body face toward the wall
r_pins = r_face - BODY_D / 2                             # pin row = body centre line (as the footprint)
bm = json.load(open(BM))
from shapely.geometry import Polygon as SP, Point as SPt


def frame(ang_deg):
    a = math.radians(ang_deg); t = (-math.sin(a), math.cos(a)); n = (math.cos(a), math.sin(a))
    return lambda u, v: (r_pins * n[0] + u * t[0] + v * n[0], r_pins * n[1] + u * t[1] + v * n[1])


def clear(ang_deg):
    """body (bottom) 0.3 mm clear of the bottom parts; pins and tabs (through the board) 0.3 mm clear of every part's outline"""
    Q = frame(ang_deg)
    body = SP([Q(-BODY_L / 2, -BODY_D / 2), Q(BODY_L / 2, -BODY_D / 2), Q(BODY_L / 2, BODY_D / 2), Q(-BODY_L / 2, BODY_D / 2)])
    pins = [SPt(*Q(u, 0)).buffer(0.8) for u in (-2, 0, 2)] + [SPt(*Q(u, 0)).buffer(1.0) for u in (-4, 4)]
    for f in bm["fps"]:
        if f["ref"].startswith("H") or not f["crt"] or f["ref"] in ("SW1",): continue
        g = SP(f["crt"]).buffer(0)
        if f["side"] == "B" and g.distance(body) < 0.3: return False
        if any(g.distance(p) < 0.3 for p in pins): return False
    return True


# 230-232 deg is blocked only by Q6, the switch's own MOSFET (SOT-23): the switch goes there and Q6 moves aside
from shapely import affinity
q6 = next(f for f in bm["fps"] if f["ref"] == "Q6")
q6_poly = SP(q6["crt"]).buffer(0)
ANG_DEG = 231.0


def q6_ok(poly, Q):
    body = SP([Q(-BODY_L / 2, -BODY_D / 2), Q(BODY_L / 2, -BODY_D / 2), Q(BODY_L / 2, BODY_D / 2), Q(-BODY_L / 2, BODY_D / 2)])
    pins = [SPt(*Q(u, 0)).buffer(0.8) for u in (-2, 0, 2)] + [SPt(*Q(u, 0)).buffer(1.0) for u in (-4, 4)]
    if poly.distance(body) < 0.3 or any(poly.distance(p) < 0.3 for p in pins): return False
    if math.hypot(*poly.centroid.coords[0]) > R_IN - 1.5: return False
    for f in bm["fps"]:
        if f["ref"] in ("Q6", "SW1") or f["ref"].startswith("H") or not f["crt"] or f["side"] != "B": continue
        if SP(f["crt"]).buffer(0).distance(poly) < 0.3: return False
    return True


Qa = frame(ANG_DEG)
Q6_MOVE = None
for rad in [k * 0.25 for k in range(1, 40)]:
    for th in range(0, 360, 15):
        dx, dy = rad * math.cos(math.radians(th)), rad * math.sin(math.radians(th))
        if q6_ok(affinity.translate(q6_poly, dx, dy), Qa): Q6_MOVE = (round(dx, 2), round(dy, 2)); break
    if Q6_MOVE: break

print("Q6 moves", Q6_MOVE)
ANG = math.radians(ANG_DEG)
t = (-math.sin(ANG), math.cos(ANG)); n = (math.cos(ANG), math.sin(ANG))      # tangent, outward normal
P = frame(ANG_DEG)
print(f"clear at {ANG_DEG} deg (now {ANG_NOW})")

fig = plt.figure(figsize=(18, 9.5))
ax = fig.add_axes([0.02, 0.06, 0.5, 0.86]); sx = fig.add_axes([0.55, 0.30, 0.43, 0.6])
c = P(0, 1.5)
ax.add_patch(Wedge((0, 0), R_OUT, 200, 280, width=R_OUT - R_IN, fc="#d8d8d8", ec="#888", lw=0.8))
ax.add_patch(Circle((0, 0), R_OUT, fc="none", ec="k", lw=1.2))
# slot in the wall
a0 = math.degrees(ANG) - math.degrees(SLOT_W / 2 / R_IN); a1 = math.degrees(ANG) + math.degrees(SLOT_W / 2 / R_IN)
ax.add_patch(Wedge((0, 0), R_OUT + 0.05, a0, a1, width=R_OUT - R_IN + 0.1, fc="white", ec="#c00", lw=1.0, ls="--"))
# other parts nearby (both sides)
for f in bm["fps"]:
    if f["ref"].startswith("H") or not f["crt"] or f["ref"] == "SW1": continue
    x, y = f["pos"]
    if math.dist((x, y), c) > 14: continue
    bot = f["side"] == "B"
    ax.add_patch(Polygon(f["crt"], fc="none", ec="#3060d0" if bot else "#d06060", lw=0.7, ls="-" if bot else ":"))
    ax.text(x, y, f["ref"], fontsize=7, ha="center", va="center", color="#3060d0" if bot else "#d06060")
if Q6_MOVE:
    g = affinity.translate(q6_poly, *Q6_MOVE)
    ax.add_patch(Polygon(list(g.exterior.coords), fc="#ffd24d", ec="k", lw=0.8, alpha=0.8))
    ax.text(*g.centroid.coords[0], f"Q6\nmoves\n{math.hypot(*Q6_MOVE):.1f} mm", fontsize=6.5, ha="center", va="center", weight="bold")
old = next(f for f in bm["fps"] if f["ref"] == "SW1")
ax.add_patch(Polygon(old["crt"], fc="none", ec="#999", lw=1.0, ls="--"))
ax.text(*old["pos"], "SW1 now\n(MSK12C02, SMD)", fontsize=7, ha="center", va="bottom", color="#777")
# new switch: body, slider (both positions), pads
body = [P(-BODY_L / 2, -BODY_D / 2), P(BODY_L / 2, -BODY_D / 2), P(BODY_L / 2, BODY_D / 2), P(-BODY_L / 2, BODY_D / 2)]
ax.add_patch(Polygon(body, fc="#c8ccd4", ec="k", lw=1.0, alpha=0.9))
for u0, col, lab in ((-TRAVEL / 2, "#202020", "OFF"), (TRAVEL / 2, "#606060", "ON")):
    k = [P(u0 - KNOB_W / 2, BODY_D / 2), P(u0 + KNOB_W / 2, BODY_D / 2), P(u0 + KNOB_W / 2, BODY_D / 2 + KNOB_L), P(u0 - KNOB_W / 2, BODY_D / 2 + KNOB_L)]
    ax.add_patch(Polygon(k, fc=col, ec="k", lw=0.6, alpha=0.85 if lab == "OFF" else 0.35))
for u, d, lab in ((-2, 1.524, "1 SW_ON"), (0, 1.524, "2 GND"), (2, 1.524, "3 nc")):
    ax.add_patch(Circle(P(u, 0), d / 2, fc="#e8b04a", ec="#8a5a00", lw=0.6)); ax.add_patch(Circle(P(u, 0), 0.457, fc="white", ec="none"))
    ax.annotate(lab, P(u, 0), P(u, -BODY_D / 2 - 2.2 - 0.9 * (u / 2)), fontsize=7, ha="center", arrowprops=dict(arrowstyle="-", lw=0.4))
for u in (-4, 4):
    q = P(u, 0); ax.add_patch(Ellipse(q, 1.6, 2.0, angle=math.degrees(ANG), fc="#e8b04a", ec="#8a5a00", lw=0.6))
ax.annotate("slider (2 x 2): tip 0.3 mm inside\nthe wall's outer face: hidden", P(0, BODY_D / 2 + KNOB_L), (c[0] + 9, c[1] - 7), fontsize=8,
            arrowprops=dict(arrowstyle="->", lw=0.6))
ax.annotate(f"new slot {SLOT_W:.1f} mm wide\n(now 7.8 mm)", P(0, BODY_D / 2 + KNOB_L + 1.2), (c[0] - 16, c[1] - 9), fontsize=8, color="#c00",
            arrowprops=dict(arrowstyle="->", lw=0.6, color="#c00"))
ax.set_xlim(c[0] - 16, c[0] + 16); ax.set_ylim(c[1] - 14, c[1] + 14); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title("Bottom side near 237 deg (robot frame, seen from below; blue = bottom parts, red dotted = top parts over\n"
             "the through-hole pins, grey dashed = the switch now). Pins 2.0 mm pitch, 2 shell tabs soldered for strength", fontsize=9)
# section through the wall (radius vs height)
sx.add_patch(Rectangle((r_pins - 8, PCB_Z), R_OUT - (r_pins - 8), PCB_T, fc="#2e6b2e", ec="k", lw=0.6))
sx.text(r_pins - 7.5, PCB_Z + 0.5, "main PCB (6 layers, 1.6)", fontsize=8, color="white")
sx.add_patch(Rectangle((R_IN, PCB_Z - 12), R_OUT - R_IN, 12, fc="#d8d8d8", ec="#888"))
sx.text(R_IN + 0.1, PCB_Z - 11.5, "wall", fontsize=8, rotation=90)
z_mid = PCB_Z - BODY_H / 2
sx.add_patch(Rectangle((r_face - BODY_D, PCB_Z - BODY_H), BODY_D, BODY_H, fc="#c8ccd4", ec="k"))
sx.add_patch(Rectangle((r_face, z_mid - KNOB_T / 2), KNOB_L, KNOB_T, fc="#202020", ec="k"))
slot_lo = z_mid - KNOB_T / 2 - 0.6
sx.add_patch(Rectangle((R_IN - 0.01, slot_lo), R_OUT - R_IN + 0.02, PCB_Z - slot_lo, fc="white", ec="#c00", ls="--"))
for xx in (r_pins,):
    sx.plot([xx, xx], [PCB_Z - 0.5, PCB_Z + PCB_T + 0.6], color="#8a5a00", lw=2)
sx.annotate(f"slider tip r {r_tip:.1f}\n(wall outside {R_OUT})", (r_tip, z_mid), (r_tip - 5, z_mid - 5), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.6))
sx.annotate(f"slot bottom z {slot_lo:.1f}\n(now {PCB_Z - 8.6:.1f})", (R_OUT, slot_lo), (R_OUT + 0.8, slot_lo - 3), fontsize=8, color="#c00",
            arrowprops=dict(arrowstyle="->", lw=0.6, color="#c00"))
sx.text(r_face - BODY_D / 2, PCB_Z - BODY_H - 0.8, f"body 8.6 x 4.3, {BODY_H:.0f} below the board", fontsize=8, ha="center")
sx.set_xlim(r_pins - 8, R_OUT + 5); sx.set_ylim(PCB_Z - 12, PCB_Z + 4); sx.set_aspect("equal"); sx.grid(alpha=0.2)
sx.set_xlabel("radius (mm)"); sx.set_ylabel("height above the floor (mm)")
sx.set_title("Section along the switch axis (radius vs height)", fontsize=9)
txt = ("Power switch v3 (keeps the MOSFET: Q6 SI2333 carries the battery current, the switch only pulls SW_ON to GND)\n"
       "  part: SK-12D07 right-angle slide switch, through-hole, SPDT;\n"
       "        Amazon UK sourcingmap B00PDKEX1E (100 pcs, GBP 9.99); LCSC twin ROCPU SK-12D07-6 (C16493666)\n"
       "        for the footprint and the 3D model; hand-soldered\n"
       f"  place: {ANG_DEG:.2f} deg (slot now at {ANG_NOW:.0f}), pin row at r {r_pins:.2f};\n"
       f"         slider through a {SLOT_W:.1f} mm slot, tip {RECESS} mm inside the wall: hidden,\n"
       "         pushed with a fingernail or a pen tip\n"
       "  schematic: unchanged (pin 2 = GND, pin 1 = SW_ON, pin 3 free)\n"
       "  FreeCAD: new switch model + smaller wall slot (after approval)")
fig.text(0.53, 0.03, txt, fontsize=8, family="monospace", va="bottom")
fig.suptitle("Power switch v3: hidden through-hole right-angle slide switch (to scale)", fontsize=13, weight="bold")
out = HERE + "/power_switch_v3.png"; fig.savefig(out, dpi=95); print(out, f"r_pins {r_pins:.2f}, slot {SLOT_W:.1f} mm, slot bottom z {slot_lo:.1f}")
