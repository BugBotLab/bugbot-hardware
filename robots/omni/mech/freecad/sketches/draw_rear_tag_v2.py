# 2D: rear ID tag plate v2 (user: v1 hung from the deck alone was not secure; fix it to the back of the body AND the top).
# A plate on the outside of the chassis' back wall: its curved bottom hugs the wall and takes 2 radial M2 screws into 2 new
# pads moulded inside the wall (150 and 210 deg, clear of the rear wheel); it rises behind the battery with the 20 mm ArUco
# tag at another robot's camera height (z 47), and two arms run forward over the deck onto the deck's two rear screws.
# Side view (y 0), rear view, top view, to scale.
#   python draw_rear_tag_v2.py <rear.json> <base_low.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon as MP
from shapely.geometry import Point, box, Polygon
from shapely.ops import unary_union

R = json.load(open(sys.argv[1])); LO = json.load(open(sys.argv[2])); OUT = sys.argv[3]
BODY_R, WALL_IN, CAM_Z = 40.6, 38.8, 47.1
PCB_Z0, PCB_TOP = 29.0, 30.51
SCREW_TOP = (-11.5, 15.5)             # rear deck screws, +-y (M2 x 6 -> M2 x 8)
LUG_TOP = 62.6
T = 2.0                               # plate / arm thickness
GAP = 0.3                             # plate to the body's outside
PAD_A, PAD_Z = 30.0, 17.0             # pads at 180 +- 30 deg (x -35.2, y +-20.3), screw height z 17
PAD_W, PAD_H, PAD_D = 7.0, 10.0, 4.0  # pad inside the wall: 7 wide, 10 tall, 4 deep (wall 1.8 -> 5.8 there)
BOT_Z = 10.0                          # plate bottom
TAG, TAG_Z = 20.0, CAM_Z
FLAT_HW = 14.0                        # upper plate half width (the plate is curved round the body, r 40.9..42.9)
LAND_HW, LAND_Z0, LAND_Z1, LAND_X = 11.0, 36.0, 58.0, -43.4   # flat land for the tag on the outer face
ARM_Y0, ARM_Y1 = 13.5, 17.5           # arms on the deck (0.7 clear of the LED board)
TOP_Z = LUG_TOP + T
C_P = "#f2c200"; C_PE = "#7a6100"; C_B = "#8a8f98"

r_out = BODY_R + GAP                  # plate inside radius (bottom, round the wall)
x_flat = -(BODY_R + GAP)              # flat part's inside face, behind the board edge
x_face = x_flat - T                   # tag face x
pad_xy = [(-WALL_IN * math.cos(math.radians(PAD_A)), s * WALL_IN * math.sin(math.radians(PAD_A))) for s in (1, -1)]
bot_hw = BODY_R * math.sin(math.radians(PAD_A + 9))     # curved bottom reaches past the screws

fig = plt.figure(figsize=(18, 16))
fig.suptitle("Rear ID tag plate v2 (2D, to scale) – fixed to the back of the body AND the top deck", fontsize=17, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.915, "Bottom: the plate, curved round the body, hugs the back wall and takes 2 x M2 x 8 radial screws into 2 new pads inside the wall "
         "(150° and 210°, either side of the rear wheel).\nTop: 2 arms run forward over the deck onto the deck's 2 rear screws (M2 x 6 -> M2 x 8). "
         "Fixed at both ends: no wobble. The pads are a chassis (base) change: every robot carries the tag.", fontsize=12, color="#333")

# ---------------- side view, y 0 ----------------
ax = fig.add_axes([0.04, 0.47, 0.55, 0.40])
for n, ws in R["side"].items():
    for w in ws:
        ax.plot([p[0] for p in w], [p[1] for p in w], color=C_B, lw=0.6)
ax.axhline(0, color="k", lw=1.2)
# plate: vertical from BOT_Z to TOP_Z just outside the body, then the arms forward on the deck (arm drawn dashed: it's at y 15.5)
ax.add_patch(Rectangle((x_face, BOT_Z), T, TOP_Z - BOT_Z, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((x_face, LUG_TOP), SCREW_TOP[0] + 3.2 - x_face, T, fc=C_P, ec=C_PE, ls="--", alpha=0.6))
ax.add_patch(Rectangle((LAND_X, LAND_Z0), x_face - LAND_X, LAND_Z1 - LAND_Z0, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((LAND_X - 0.2, TAG_Z - TAG / 2), 0.2, TAG, fc="k"))
ax.plot([SCREW_TOP[0]] * 2, [56.6, TOP_Z + 0.6], color="#555", lw=2.5)
ax.add_patch(Rectangle((SCREW_TOP[0] - 1.9, TOP_Z), 3.8, 1.3, fc="#bbb", ec="k", lw=0.6))
ax.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9); ax.text(-50, CAM_Z + 0.8, "other robots' camera z 47.1", color="#7b61ff", fontsize=9)
ax.axhline(PAD_Z, color="#c62828", ls=":", lw=0.9); ax.text(-50, PAD_Z + 0.8, "bottom screws z 17 (at ±30°, not in this section)", color="#c62828", fontsize=9)
ax.annotate("arm (at y ±15.5) on the deck,\nunder the rear deck screw", xy=(-20, TOP_Z), xytext=(-30, 76), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("plate 2 thick, 0.3 off the back of the body;\n20 mm ArUco sticker, centre z 47", xy=(x_face, 40), xytext=(-50, 22),
            fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.set_title("SIDE VIEW – section at y 0", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-52, 10); ax.set_ylim(-1, 84); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- rear view, looking forward ----------------
ax3 = fig.add_axes([0.62, 0.47, 0.36, 0.40])
ax3.add_patch(Rectangle((-BODY_R, 6.5), 2 * BODY_R, 22.5, fc="#f5f5f5", ec=C_B))
ax3.add_patch(Rectangle((-BODY_R, PCB_Z0), 2 * BODY_R, 1.5, fc="#cfe3d4", ec="#2e6b3f"))
ax3.add_patch(Rectangle((-20, 57.0), 40, 5.6, fc="none", ec=C_B))
ax3.add_patch(Wedge((0, 62.0), 15, 0, 180, fc="#eef", ec="#88a"))
# plate outline: wide curved foot (|y| <= bot_hw, z BOT_Z..30) narrowing to the flat tag face (|y| <= FLAT_HW) up to TOP_Z
outline = Polygon([(-bot_hw, BOT_Z), (bot_hw, BOT_Z), (bot_hw, 26.0), (FLAT_HW + 2.0, 33.0), (FLAT_HW + 2.0, TOP_Z),
                   (-FLAT_HW - 2.0, TOP_Z), (-FLAT_HW - 2.0, 33.0), (-bot_hw, 26.0)]).buffer(2.0, join_style=1).buffer(-2.0, join_style=1)
ax3.add_patch(MP(list(outline.exterior.coords), closed=True, fc=C_P, ec=C_PE, alpha=0.95))
for s in (1, -1):
    ax3.add_patch(Circle((s * pad_xy[0][1], PAD_Z), 1.1, fc="white", ec="k")); ax3.add_patch(Circle((s * pad_xy[0][1], PAD_Z), 1.9, fc="none", ec="k", lw=0.6))
    ax3.add_patch(Rectangle((s * pad_xy[0][1] - PAD_W / 2, PAD_Z - PAD_H / 2), PAD_W, PAD_H, fc="none", ec="#c62828", ls="--"))
cell = TAG / 6
pat = ["111111", "101101", "110011", "100101", "101011", "111111"]
for i, row in enumerate(pat):
    for j, v in enumerate(row):
        ax3.add_patch(Rectangle((-TAG / 2 + j * cell, TAG_Z + TAG / 2 - (i + 1) * cell), cell, cell, fc="k" if v == "1" else "white", ec="none"))
ax3.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9)
ax3.annotate("2 x M2 x 8 self-tapping, radial,\ninto new pads inside the wall (red dashed)", xy=(pad_xy[0][1], PAD_Z), xytext=(4, 2),
             fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax3.set_title("REAR VIEW (looking forward)", fontsize=13, fontweight="bold", loc="left")
ax3.set_xlim(-45, 45); ax3.set_ylim(0, 82); ax3.set_aspect("equal")
ax3.grid(True, lw=0.25, color="#ddd"); ax3.set_xlabel("y (mm)"); ax3.set_ylabel("z (mm)")

# ---------------- top view: inside the back wall at z 13.5 + the plate ----------------
ax2 = fig.add_axes([0.04, 0.05, 0.55, 0.36])
for n, ws in LO["top"]["13.5"].items():
    for w in ws:
        ax2.plot([p[0] for p in w], [p[1] for p in w], color="r" if "Chassis" in n else C_B, lw=0.6)
th = [math.radians(a) for a in range(0, 361, 1)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
a_lim = math.degrees(math.asin(bot_hw / BODY_R))
arc_o = [((r_out + T) * math.cos(math.radians(a)), (r_out + T) * math.sin(math.radians(a))) for a in [180 - a_lim + k for k in range(int(2 * a_lim) + 1)]]
arc_i = [(r_out * math.cos(math.radians(a)), r_out * math.sin(math.radians(a))) for a in [180 + a_lim - k for k in range(int(2 * a_lim) + 1)]]
ax2.add_patch(MP(arc_o + arc_i, closed=True, fc=C_P, ec=C_PE, alpha=0.9))
land = Polygon([(LAND_X, -LAND_HW), (-math.sqrt((r_out + T) ** 2 - LAND_HW ** 2), -LAND_HW), (-(r_out + T), 0),
                (-math.sqrt((r_out + T) ** 2 - LAND_HW ** 2), LAND_HW), (LAND_X, LAND_HW)])
ax2.add_patch(MP(list(land.exterior.coords), closed=True, fc=C_P, ec=C_PE, ls="--"))
ax2.annotate("flat 22 mm land for the tag\n(z 36-58), 0.5 proud", xy=(LAND_X, 6), xytext=(-62, 2), fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
for (px, py) in pad_xy:
    ang = math.atan2(py, px)
    pad = Polygon([(WALL_IN * math.cos(ang) + d * math.cos(ang) + w * -math.sin(ang), WALL_IN * math.sin(ang) + d * math.sin(ang) + w * math.cos(ang))
                   for d, w in ((0.5, -PAD_W / 2), (0.5, PAD_W / 2), (-PAD_D, PAD_W / 2), (-PAD_D, -PAD_W / 2))])
    ax2.add_patch(MP(list(pad.exterior.coords), closed=True, fc="#ffcdd2", ec="#c62828"))
    ax2.plot([(BODY_R + 3) * math.cos(ang), (WALL_IN - 3.5) * math.cos(ang)], [(BODY_R + 3) * math.sin(ang), (WALL_IN - 3.5) * math.sin(ang)], color="k", lw=1.4)
ax2.annotate("new pad inside the wall (7 x 10, 4 deep),\nM2 pilot; clear of the rear wheel and encoder board\n(check in 3D)", xy=pad_xy[1], xytext=(-30, -32),
             fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("plate curved round the body,\n0.3 off it", xy=(-r_out - 1, 8), xytext=(-62, 20), fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – inside the back wall at z 13.5 (rear wheel, encoder board), plate foot", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-62, -5); ax2.set_ylim(-36, 36); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")

notes = ("• Screws: 2 x M2 x 8 self-tapping (bottom, new pads) +\n   the 2 rear deck screws M2 x 6 -> M2 x 8 (top).\n"
         "• Chassis change (base, all robots): 2 pads inside the back wall.\n"
         "• The plate is curved round the body (0.3 off it, 2 thick): no corners\n   stick out; only the flat tag land stands 2.8 proud.\n"
         "• Arms 0.7 clear of the LED board; battery and its cradle\n   untouched (the plate is behind the board edge).\n"
         "• Print upside down: arms flat on the bed, the curved plate\n   standing up (no supports); PETG. Tag = sticker.")
fig.text(0.62, 0.12, notes, fontsize=11, color="#222")
plt.savefig(OUT, dpi=100)
print("saved", OUT, "pads", [tuple(round(v, 1) for v in p) for p in pad_xy], "foot half width", round(bot_hw, 1))
