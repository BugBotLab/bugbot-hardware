# 2D: Beetle shield v2 (user mark-up on v1): tail block by the pivot removed; the plate redrawn as ONE clean outline
# (pivot end from the hoop arm, straight top bar, rounded outer corner, filleted inside corners, blended foot); the blade
# moved out 4 mm and given curved wings at both ends that sweep outward and back. Side view (left plate) + top view, to scale.
#   python draw_beetle_shield_v2.py <arm_zone.json> <base_low.json> <ram_sections.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, Circle
from shapely.geometry import Polygon, box, Point, LineString
from shapely.ops import unary_union, polygonize

ARM, LOW, RAM, OUT = sys.argv[1:5]
A = json.load(open(ARM)); LO = json.load(open(LOW)); R = json.load(open(RAM))
BODY_R = 40.6; PCB_TOP = 30.51; PIV = (8.0, 36.7)
# v1 (as built)
V1 = dict(leg_x0=35.1, leg_x1=41.5, run_z0=34.0, run_z1=40.0, toe_z0=7.5, toe_z1=13.0, blade_x1=56.6, foot=(27.0, 32.0), tail=(0.5, 3.4))
# v2
LOBE_CUT = 15.0                       # keep the hoop arm's pivot end behind this x (horn / bushing fits unchanged)
BAR_Z0, BAR_Z1 = 34.0, 40.0
LEG_X0, LEG_X1 = 35.1, 41.5
TOE_Z0, TOE_Z1 = 7.5, 13.0
TOE_X1 = 50.0                         # toes end just behind the U's back
TOE_Y0, TOE_Y1 = 21.25, 26.75         # toes 5.5 wide (the plates are 3.5): thickened outward
FIT = 0.25                            # locating clearance per side (fit_loc): blade to toes / legs
BOLTS = [(42.5, 12.0), (42.5, 21.0)]  # 2 x M3 x 50 through foot plate R, the U's middle block, foot plate L: two bolts, so the U can't pivot
BOLT = BOLTS[0]
FOOT_Z1 = 25.5                        # the plates' feet and the U's middle block rise to here: behind x 50 the stinger never reaches
BLOCK_X0 = 38.0                       # middle block back face: 0.8 clear of the Beetle's base-plate lip (x 37.18) and wall tips (35.04)
CB_D, CB_T = 6.0, 3.2                 # counterbore for the DIN 912 head (5.5 + 0.25 a side), in foot plate R
NUT_AF, NUT_T = 5.8, 2.6              # hex pocket for a DIN 934 M3 nut (5.5 AF + 0.15 a side, 2.4 thick), in foot plate L
# sasumata-style U (top view): a half ring round (U_CX, 0) + short prongs flared outward, all 6 thick
U_RI, U_T = 21.0, 6.0                 # inside radius 21 (a 40 mm ball fits in), 6 thick
U_BACK = 46.0                         # inside face of the U's back, on the centre line
U_CX = U_BACK + U_RI                  # 67.0
PRONG_L, PRONG_A = 6.0, 20.0          # prong tips: 6 long, flared 20 deg outward, round ends
FOOT = (26.0, 32.0)
R_OUT, R_IN = 4.0, 2.5                # outer corner round, inside fillets
WASP_TIP, WASP_FIRED, WASP_R = 35.04, 47.0, 40.6

def arm_outline(side_key):
    segs = []
    for w in A["side"][side_key]["Gripper:1/HoopArmL" if side_key == "23.0" else "Gripper:1/HoopArmR"]:
        segs += [LineString([w[i], w[i + 1]]) for i in range(len(w) - 1)]
    polys = list(polygonize(unary_union(segs)))
    outer = max(polys, key=lambda p: p.area)
    return Polygon(outer.exterior)

def plate(side_key):
    lobe = arm_outline(side_key).intersection(box(-30, PCB_TOP + 0.3, LOBE_CUT + 3, 80))
    parts = [lobe,
             box(LOBE_CUT - 2, BAR_Z0, LEG_X1, BAR_Z1),
             box(LEG_X0, TOE_Z0, LEG_X1, BAR_Z1),
             box(LEG_X0, TOE_Z0, TOE_X1, FOOT_Z1),
             box(FOOT[0], PCB_TOP, FOOT[1], BAR_Z0 + 0.5)]
    p = unary_union(parts)
    p = p.buffer(R_IN, join_style=1).buffer(-R_IN, join_style=1)          # inside fillets
    p = p.buffer(-R_OUT * 0.5, join_style=1).buffer(R_OUT * 0.5, join_style=1)   # round the outside corners a little
    p = p.intersection(unary_union([box(-30, PCB_TOP, 80, 80), box(LEG_X0 - 0.01, -10, 80, PCB_TOP)]))   # foot flat on the board top
    return p

def v1_plate(side_key):
    lobe = arm_outline(side_key).intersection(box(-30, PCB_TOP + 0.01, 35.0, 80))
    d = V1
    return unary_union([lobe, box(34.6, d["run_z0"], d["leg_x1"], d["run_z1"]), box(d["leg_x0"], d["toe_z0"], d["leg_x1"], d["run_z1"]),
                        box(d["leg_x0"], d["toe_z0"], d["blade_x1"], d["toe_z1"]), box(d["foot"][0], PCB_TOP, d["foot"][1], d["run_z0"] + 0.5),
                        box(d["tail"][0], PCB_TOP, d["tail"][1], PIV[1] + 1.0)])

def draw_poly(ax, p, **kw):
    geoms = getattr(p, "geoms", [p])
    for g in geoms:
        if g.geom_type != "Polygon" or g.area < 0.5:
            continue
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, **kw))

def outlines(ax, secs, col="#8a8f98", lw=0.6, skip=("Gripper", "Ball"), xf=None, yf=None):
    for n, ws in secs.items():
        if n.startswith(skip):
            continue
        for w in ws:
            xs = [p[0] for p in w]; ys = [p[1] for p in w]
            if xf: xs = [xf(x) for x in xs]
            if yf: ys = [yf(y) for y in ys]
            ax.plot(xs, ys, color=col, lw=lw)

# the U (blade) in the top view: half ring + flared prongs + the rib that sits between the toes
rc = U_RI + U_T / 2
ring = Point(U_CX, 0).buffer(U_RI + U_T, quad_segs=64).difference(Point(U_CX, 0).buffer(U_RI, quad_segs=64)).intersection(box(0, -60, U_CX, 60))
prongs = []
for s in (1, -1):
    a = math.radians(PRONG_A)
    p0 = (U_CX, s * rc); p1 = (U_CX + PRONG_L * math.cos(a), s * (rc + PRONG_L * math.sin(a)))
    prongs.append(LineString([p0, p1]).buffer(U_T / 2, cap_style=1, quad_segs=32))
# the middle bar between the toes runs solid into the U's back (no notches): everything between the toes from the legs up to
# the U's inside curve is one block, with the U's inside cut out of it
rib = box(BLOCK_X0, -(TOE_Y0 - FIT), U_CX, TOE_Y0 - FIT).difference(Point(U_CX, 0).buffer(U_RI, quad_segs=64))
blade = unary_union([ring, rib] + prongs).buffer(1.0, join_style=1, quad_segs=16).buffer(-1.0, join_style=1, quad_segs=16)
# toes: run forward until 0.25 off the U's outside, so their ends follow its curve (one even 0.25 line, no gaps)
U_OUT = Point(U_CX, 0).buffer(U_RI + U_T + FIT, quad_segs=64)
TOE_END = BOLT[0] + 5.0               # foot plates end 5 ahead of the bolts: >= 1.6 wall round the counterbore and hex pocket
toes_xy = {s: box(LEG_X0, min(s * TOE_Y0, s * TOE_Y1), TOE_END, max(s * TOE_Y0, s * TOE_Y1)).difference(U_OUT) for s in (1, -1)}
TOE_X1 = max(t.bounds[2] for t in toes_xy.values())   # the side profile runs this far; the 3D build cuts the curve
NOSE_X = blade.bounds[2]
# where a head-on Wasp stops: it comes in until its outline (round wall for |y| >= 20.5, its wheels / motors at x 27 inside
# the front opening; its base-plate lip is ignored, so this is the worst case) touches the U
def wasp_front_x(y):
    return math.sqrt(WASP_R ** 2 - y * y) if abs(y) >= 20.5 else 27.0
pts = [c for g in getattr(blade, "geoms", [blade]) for c in g.exterior.coords]
WASP_CX = max(px + wasp_front_x(py) for px, py in pts if abs(py) < WASP_R)
GAP = WASP_CX - WASP_FIRED - BODY_R

C_SH = "#f2c200"; C_SH_E = "#7a6100"; C_W = "#4a90d9"
fig = plt.figure(figsize=(17, 18))
fig.suptitle("Beetle shield v2d (2D, to scale) – middle block flush with the foot plates",
             fontsize=16, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.94, f"The U's middle block rises to z {FOOT_Z1:.1f} between two 5.5-wide foot plates (no toes), held by TWO M3 x 50 bolts one above the "
         f"other, so it can't pivot down.\nHeads sunk in counterbores, nuts in hex pockets: nothing sticks out. The tall part ends flush with the foot plates at x 47.5, "
         f"out of the stinger's reach (fired stinger ends {GAP:.1f} mm short). U as v2b, nose x {NOSE_X:.1f}.", fontsize=12, color="#333")

# ---------------- side view ----------------
ax = fig.add_axes([0.04, 0.50, 0.92, 0.40])
outlines(ax, A["side"]["23.0"])
ax.axhline(0, color="k", lw=1.5)
draw_poly(ax, v1_plate("23.0"), fc="none", ec="#c62828", ls="--", lw=1.0)
pl = plate("23.0")
draw_poly(ax, pl, fc=C_SH, ec=C_SH_E, lw=1.2)
ax.add_patch(Circle(PIV, 2.25, fc="white", ec="k", lw=0.6))
for z in (41.2, 45.2):
    ax.add_patch(Circle((8.0, z), 0.5, fc="white", ec="k", lw=0.5))
# blade + wings seen from the side (one height band)
ax.add_patch(Rectangle((LEG_X1 + 0.3, TOE_Z0), NOSE_X - LEG_X1 - 0.3, TOE_Z1 - TOE_Z0, fc=C_SH, ec=C_SH_E, alpha=0.6, lw=1.0, ls="--"))
blk = box(BLOCK_X0, TOE_Z0, TOE_END, FOOT_Z1).buffer(-R_OUT * 0.5, join_style=1).buffer(R_OUT * 0.5, join_style=1)   # flush with the foot plates, same corners
draw_poly(ax, blk, fc="none", ec="#c62828", ls="--", lw=1.4)
for b in BOLTS:
    ax.add_patch(Circle(b, CB_D / 2, fc="#c0c4c8", ec="k", lw=0.8)); ax.add_patch(Circle(b, 1.0, fc="#555", ec="k", lw=0.4))
ax.annotate("U middle block (red dashed): flush with the foot plates,\nfront x 47.5, top z 25.5, same rounded corner;\n13 mm out of the stinger's reach. 2 x M3 x 50: no pivot",
            xy=(BOLTS[1][0], BOLTS[1][1]), xytext=(55, 30), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
# Wasp ghost, fired, where the U stops it
xf = lambda x: WASP_CX - x
outlines(ax, R["side"]["-2.8"], col=C_W, lw=0.5, xf=xf)
cap_x = WASP_CX - WASP_FIRED
ax.add_patch(Rectangle((cap_x, 14.3), 6.0, 16.0, fc=C_W, alpha=0.35, ec=C_W))
ax.axvline(BODY_R, color="#999", lw=0.8, ls=":")
ax.annotate("", xy=(BODY_R, 24), xytext=(cap_x, 24), arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.5))
ax.text((BODY_R + cap_x) / 2, 25.2, f"{GAP:.1f} gap", color="#c62828", ha="center", fontsize=11, fontweight="bold")
ax.annotate("", xy=(NOSE_X, 4.0), xytext=(BODY_R, 4.0), arrowprops=dict(arrowstyle="<->", color=C_SH_E, lw=1.2))
ax.text((NOSE_X + BODY_R) / 2, 2.0, f"prong tips {NOSE_X - BODY_R:.0f} ahead of the body", color=C_SH_E, ha="center", fontsize=10)
ax.annotate("tail block removed\n(red dashed = v1 as built)", xy=(2.0, 33), xytext=(-19, 21), fontsize=10, color="#c62828",
            arrowprops=dict(arrowstyle="-", color="#c62828"))
ax.annotate("one clean outline: pivot end kept from the hoop arm,\nstraight top bar, rounded outer corner, filleted inside corners",
            xy=(LEG_X1 - 1, BAR_Z1 - 1), xytext=(22, 50), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("foot blended into the bar,\nflat on the board top (z 30.51)", xy=(29, PCB_TOP + 1.0), xytext=(-19, 47), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("U front, one part (dashed: its side)", xy=(NOSE_X - 4, TOE_Z1), xytext=(62, 42), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.set_title("SIDE VIEW – left plate (y +23); Wasp head-on, fired", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-20, 110); ax.set_ylim(-1, 56); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- top view ----------------
ax2 = fig.add_axes([0.04, 0.05, 0.92, 0.40])
outlines(ax2, LO["top"]["11.0"])
th = [math.radians(a) for a in range(0, 361, 2)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
for s in (1, -1):
    y0, y1 = sorted((s * TOE_Y0, s * TOE_Y1))
    draw_poly(ax2, toes_xy[s], fc=C_SH, ec=C_SH_E, lw=1.0)
draw_poly(ax2, blade, fc=C_SH, ec=C_SH_E, lw=1.2)
ax2.add_patch(Circle((U_CX, 0), 20.0, fc="#ff9a3c", alpha=0.25, ec="#c06000", ls="--"))
ax2.text(U_CX, 0, "40 mm ball\nfits in the U", ha="center", va="center", fontsize=9, color="#a04000")
ax2.plot([BOLT[0]] * 2, [-TOE_Y1 + CB_T, TOE_Y1 - NUT_T + 2.4], color="k", lw=1.5)
ax2.add_patch(Rectangle((BOLT[0] - 2.75, -TOE_Y1), 5.5, 3.0, fc="#c0c4c8", ec="k"))           # head, in its counterbore
ax2.add_patch(Rectangle((BOLT[0] - 2.75, TOE_Y1 - NUT_T), 5.5, 2.4, fc="#c0c4c8", ec="k"))    # nut, in its hex pocket
ax2.annotate("2 x M3 x 50 socket head (DIN 912) + M3 nut (DIN 934):\nheads sunk in foot plate R, nuts in hex pockets in foot plate L;\nnothing sticks out. Ø3.5 holes",
             xy=(BOLT[0], -TOE_Y1 - 2), xytext=(-40, -52), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
# Wasp head-on where the U stops it
outlines(ax2, {n: [[(WASP_CX - p[0], -p[1]) for p in w] for w in ws] for n, ws in R["top"]["17.5"].items() if "Chassis" in n}, col=C_W, lw=0.9)
ax2.text(WASP_CX, 0, "Wasp", color="#1f5d99", fontsize=12, ha="center")
ax2.annotate(f"sasumata U: inside R{U_RI:.0f}, {U_T:.0f} thick,\nprongs flared {PRONG_A:.0f}° with round tips; z 7.5–13",
             xy=(U_CX - U_RI - 3, 14), xytext=(-5, 47), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("the Wasp's wall lands on the prong tips", xy=(NOSE_X - 1, -27), xytext=(75, -50), fontsize=10,
             arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – z 11, Beetle base + shield; Wasp head-on (its chassis, mirrored)", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-45, 155); ax2.set_ylim(-58, 58); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")
fig.text(0.04, 0.012, "Right plate: same outline with the hoop arm R's pivot end (bushing). Print: plates flat, blade flat on its bottom face; PETG. "
         "Toes 5.5 wide in the toe region only.\nGap from model numbers (Wasp wall r 40.6, tips x 35.04, fired face 47.0), worst case: its base-plate lip ignored.",
         fontsize=10.5, color="#222")
plt.savefig(OUT, dpi=100)
# profiles for the 3D build (build_beetle.py): plate outlines in XZ (left: hoop arm L section at y +23, right: arm R at y -23),
# blade outline in XY
def ext(p):
    g = max([g for g in getattr(p, "geoms", [p]) if g.geom_type == "Polygon"], key=lambda g: g.area)
    return [list(c) for c in g.exterior.coords]
json.dump({"plate_L_xz": ext(plate("23.0")), "plate_R_xz": ext(plate("-23.0")), "blade_xy": ext(blade),
           "bolt_xz": BOLT, "bolts_xz": BOLTS, "u": [U_CX, U_RI], "block_x1": TOE_END, "corner_r": R_OUT * 0.5, "foot_z1": FOOT_Z1, "block_x0": BLOCK_X0, "cb": [CB_D, CB_T], "nut": [NUT_AF, NUT_T], "toe_z": [TOE_Z0, TOE_Z1], "lobe_cut": LOBE_CUT, "pcb_top": PCB_TOP, "nose_x": NOSE_X, "toe_y": [TOE_Y0, TOE_Y1], "gap": GAP},
          open(OUT.replace(".png", "_profiles.json"), "w"))
print("saved", OUT, "gap", round(GAP, 2), "plate bounds", [round(v, 1) for v in pl.bounds])
