# 2D: rear ID tag plate v3 (user: slot it into the back and the top, for easy fitting and a smooth look).
# The plate is curved round the body (0.3 off it). TOP: a 7 mm tongue on its top edge slides into a slot in a new small boss
# under the deck's rear edge (no arms or screw heads on the deck). BACK: 2 round bosses on the plate's inside drop into 2
# shallow pockets in the wall's outside (on 2 new pads inside the wall, either side of the rear wheel) and take 2 radial M2
# screws. Fit: tongue into the slot, swing the plate down onto the wall, 2 screws. Side view (y 0), rear view, top view.
#   python draw_rear_tag_v3.py <rear.json> <rear2.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon as MP
from shapely.geometry import Polygon
from shapely.ops import unary_union

R = json.load(open(sys.argv[1])); R2 = json.load(open(sys.argv[2])); OUT = sys.argv[3]
BODY_R, WALL_IN, CAM_Z = 40.6, 38.8, 47.1
PCB_Z0 = 29.0
T, GAP = 2.0, 0.3                     # plate thickness; plate to the body
R_IN = BODY_R + GAP                   # plate inside radius
X_FACE = -(R_IN + T)                  # plate outside at y 0 (-42.9)
BOT_Z, TOP_Z = 10.0, 61.0             # plate bottom / top (top tucks under the deck's rear edge, deck bottom z 61.1)
# top: tongue + slot boss under the deck's rear edge
DECK_X = -18.5                        # deck rear edge
TONGUE_HW, TONGUE_Z0, TONGUE_Z1 = 3.5, 58.6, 60.6
TONGUE_IN = 3.5                       # tongue goes 3.5 into the slot
BOSS = dict(x0=-18.5, x1=-14.5, hw=5.5, z0=57.0, z1=61.1)   # new boss on the deck's underside (antenna 1.9, screw 1.7 away)
SLOT_FIT = 0.2                        # slot round the tongue, a side (locating fit)
# back: pads inside the wall + pockets outside + bosses on the plate
PAD_A, PAD_Z = 30.0, 17.0
PAD_W, PAD_H, PAD_D = 7.0, 10.0, 4.0
POCKET_D, POCKET_R = 0.6, 4.0         # pocket in the wall's outside at each pad; plate boss Ø7.5 x 0.9 drops in (0.25 a side)
TAG, TAG_Z = 20.0, CAM_Z
LAND_HW, LAND_Z0, LAND_Z1, LAND_X = 11.0, 36.0, 58.0, -43.4
FLAT_HW = 14.0
C_P = "#f2c200"; C_PE = "#7a6100"; C_B = "#8a8f98"
pad_xy = [(-WALL_IN * math.cos(math.radians(PAD_A)), s * WALL_IN * math.sin(math.radians(PAD_A))) for s in (1, -1)]
bot_hw = BODY_R * math.sin(math.radians(PAD_A + 9))

fig = plt.figure(figsize=(18, 16))
fig.suptitle("Rear ID tag plate v3 (2D, to scale) – slotted in at the top and the back", fontsize=17, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.915, "TOP: a 7 mm tongue on the plate's top edge slides into a slot in a new small boss under the deck's rear edge: nothing on top "
         "of the deck, deck screws unchanged.\nBACK: 2 round bosses on the plate's inside drop into 2 shallow pockets in the wall (on 2 new pads inside "
         "it) and take 2 radial M2 x 8 screws. Fit: tongue in, swing down, 2 screws.", fontsize=12, color="#333")

# ---------------- side view, y 0 ----------------
ax = fig.add_axes([0.04, 0.47, 0.55, 0.40])
for n, ws in R["side"].items():
    if "TopDeck" in n: continue
    for w in ws:
        ax.plot([p[0] for p in w], [p[1] for p in w], color=C_B, lw=0.6)
for w in R2["deck_side"]["13.5"]["SensorMast:1/TopDeck"]:
    pass
for n, ws in R["side"].items():
    if "TopDeck" in n:
        for w in ws:
            ax.plot([p[0] for p in w], [p[1] for p in w], color="#555", lw=0.8)
ax.axhline(0, color="k", lw=1.2)
ax.add_patch(Rectangle((X_FACE, BOT_Z), T, TOP_Z - BOT_Z, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((X_FACE, TONGUE_Z0), DECK_X + TONGUE_IN - X_FACE, TONGUE_Z1 - TONGUE_Z0, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((LAND_X, LAND_Z0), X_FACE - LAND_X, LAND_Z1 - LAND_Z0, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((LAND_X - 0.2, TAG_Z - TAG / 2), 0.2, TAG, fc="k"))
# deck boss with the slot
ax.add_patch(Rectangle((BOSS["x0"], BOSS["z0"]), BOSS["x1"] - BOSS["x0"], BOSS["z1"] - BOSS["z0"], fc="#ffcdd2", ec="#c62828"))
ax.add_patch(Rectangle((BOSS["x0"], TONGUE_Z0 - SLOT_FIT), TONGUE_IN + SLOT_FIT, TONGUE_Z1 - TONGUE_Z0 + 2 * SLOT_FIT, fc="white", ec="#c62828", ls="--"))
ax.add_patch(Rectangle((X_FACE, TONGUE_Z0), DECK_X + TONGUE_IN - X_FACE, TONGUE_Z1 - TONGUE_Z0, fc=C_P, ec=C_PE))
ax.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9); ax.text(-51, CAM_Z + 0.8, "other robots' camera z 47.1", color="#7b61ff", fontsize=9)
ax.axhline(PAD_Z, color="#c62828", ls=":", lw=0.9); ax.text(-51, PAD_Z + 0.8, "bottom screws z 17 (at ±30°)", color="#c62828", fontsize=9)
ax.annotate("new boss under the deck's rear edge (red),\nslot 2.4 x 7.4 x 3.7 deep; tongue 2 x 7 slides in", xy=(BOSS["x0"] + 1, 59.6), xytext=(-30, 74),
            fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("tongue 7 wide, under the deck level:\nnothing on top of the deck", xy=(-30, TONGUE_Z1), xytext=(-51, 66), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("plate 2 thick, curved round the body,\n0.3 off it; tag land + 20 mm ArUco sticker", xy=(X_FACE, 30), xytext=(-51, 22), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.set_title("SIDE VIEW – section at y 0", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-53, 10); ax.set_ylim(-1, 84); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- rear view ----------------
ax3 = fig.add_axes([0.62, 0.47, 0.36, 0.40])
ax3.add_patch(Rectangle((-BODY_R, 6.5), 2 * BODY_R, 22.5, fc="#f5f5f5", ec=C_B))
ax3.add_patch(Rectangle((-BODY_R, PCB_Z0), 2 * BODY_R, 1.5, fc="#cfe3d4", ec="#2e6b3f"))
ax3.add_patch(Rectangle((-20, 61.1), 40, 1.5, fc="none", ec=C_B))
ax3.add_patch(Wedge((0, 62.6), 15, 0, 180, fc="#eef", ec="#88a"))
outline = Polygon([(-bot_hw, BOT_Z), (bot_hw, BOT_Z), (bot_hw, 26.0), (FLAT_HW + 2.0, 33.0), (FLAT_HW + 2.0, TOP_Z),
                   (-FLAT_HW - 2.0, TOP_Z), (-FLAT_HW - 2.0, 33.0), (-bot_hw, 26.0)]).buffer(2.0, join_style=1).buffer(-2.0, join_style=1)
ax3.add_patch(MP(list(outline.exterior.coords), closed=True, fc=C_P, ec=C_PE, alpha=0.95))
ax3.add_patch(Rectangle((-TONGUE_HW, TONGUE_Z0), 2 * TONGUE_HW, TONGUE_Z1 - TONGUE_Z0, fc="none", ec=C_PE, ls="--"))
for s in (1, -1):
    y = s * pad_xy[0][1]
    ax3.add_patch(Circle((y, PAD_Z), POCKET_R, fc="none", ec="#c62828", ls="--"))
    ax3.add_patch(Circle((y, PAD_Z), 1.9, fc="#bbb", ec="k", lw=0.6)); ax3.add_patch(Circle((y, PAD_Z), 0.8, fc="#555"))
cell = TAG / 6
pat = ["111111", "101101", "110011", "100101", "101011", "111111"]
for i, row in enumerate(pat):
    for j, v in enumerate(row):
        ax3.add_patch(Rectangle((-TAG / 2 + j * cell, TAG_Z + TAG / 2 - (i + 1) * cell), cell, cell, fc="k" if v == "1" else "white", ec="none"))
ax3.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9)
ax3.annotate("2 x M2 x 8 radial; the plate's round bosses\nsit in Ø8 x 0.6 pockets in the wall (red dashed)", xy=(pad_xy[0][1], PAD_Z), xytext=(2, 1),
             fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax3.annotate("plate top tucks under the deck edge;\ntongue (dashed) into the deck boss", xy=(0, TONGUE_Z1), xytext=(-44, 72), fontsize=9,
             arrowprops=dict(arrowstyle="-", color="#666"))
ax3.set_title("REAR VIEW (looking forward)", fontsize=13, fontweight="bold", loc="left")
ax3.set_xlim(-45, 45); ax3.set_ylim(0, 82); ax3.set_aspect("equal")
ax3.grid(True, lw=0.25, color="#ddd"); ax3.set_xlabel("y (mm)"); ax3.set_ylabel("z (mm)")

# ---------------- top view: deck outline (z 61.5), boss, tongue, plate, wall pads ----------------
ax2 = fig.add_axes([0.04, 0.05, 0.55, 0.36])
for w in R2["deck_top"]["61.5"]:
    ax2.plot([p[0] for p in w], [p[1] for p in w], color="#555", lw=0.8)
for n, ws in R2["back"]["16.0"].items():
    for w in ws:
        ax2.plot([p[0] for p in w], [p[1] for p in w], color="r" if "Chassis" in n else ("b" if "EncBoard" in n else C_B), lw=0.6)
th = [math.radians(a) for a in range(0, 361, 1)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
a_lim = math.degrees(math.asin(bot_hw / BODY_R))
arc_o = [((R_IN + T) * math.cos(math.radians(a)), (R_IN + T) * math.sin(math.radians(a))) for a in [180 - a_lim + k for k in range(int(2 * a_lim) + 1)]]
arc_i = [(R_IN * math.cos(math.radians(a)), R_IN * math.sin(math.radians(a))) for a in [180 + a_lim - k for k in range(int(2 * a_lim) + 1)]]
ax2.add_patch(MP(arc_o + arc_i, closed=True, fc=C_P, ec=C_PE, alpha=0.9))
ax2.add_patch(Rectangle((X_FACE, -TONGUE_HW), DECK_X + TONGUE_IN - X_FACE, 2 * TONGUE_HW, fc=C_P, ec=C_PE, alpha=0.9))
ax2.add_patch(Rectangle((BOSS["x0"], -BOSS["hw"]), BOSS["x1"] - BOSS["x0"], 2 * BOSS["hw"], fc="#ffcdd2", ec="#c62828", alpha=0.8))
ax2.add_patch(Rectangle((-19.5, 4.0), 33.0, 8.0, fc="none", ec="#6a1b9a", ls=":"))
ax2.text(-5, 8, "antenna (under the deck)", fontsize=8, color="#6a1b9a", ha="center")
for (px, py) in pad_xy:
    ang = math.atan2(py, px)
    pad = Polygon([(WALL_IN * math.cos(ang) + d * math.cos(ang) + w * -math.sin(ang), WALL_IN * math.sin(ang) + d * math.sin(ang) + w * math.cos(ang))
                   for d, w in ((0.5, -PAD_W / 2), (0.5, PAD_W / 2), (-PAD_D, PAD_W / 2), (-PAD_D, -PAD_W / 2))])
    ax2.add_patch(MP(list(pad.exterior.coords), closed=True, fc="#ffcdd2", ec="#c62828"))
    ax2.plot([(BODY_R + 3) * math.cos(ang), (WALL_IN - 3.5) * math.cos(ang)], [(BODY_R + 3) * math.sin(ang), (WALL_IN - 3.5) * math.sin(ang)], color="k", lw=1.4)
ax2.annotate("new pads inside the wall (7 x 10, 4 deep):\n6.1 / 8.6 mm clear of the rear wheel", xy=pad_xy[1], xytext=(-35, -33),
             fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("deck boss (new): 1.9 from the antenna,\n1.7 from the deck screws", xy=(BOSS["x1"], -4), xytext=(-12, -22), fontsize=9,
             arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – deck outline, deck boss, tongue, plate; back wall at z 16", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-50, 5); ax2.set_ylim(-36, 36); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")

notes = ("• Screws: only 2 x M2 x 8 self-tapping (bottom). Top: tongue in a slot,\n   no screw. Deck screws stay M2 x 6.\n"
         "• Base changes (all robots carry the tag): deck gets a small boss\n   with a slot; chassis gets 2 inside pads + 2 shallow outside pockets.\n"
         "• Smooth look: no arms on the deck; plate hugs the body; only the\n   tag land stands 2.8 proud.\n"
         "• Fits (rough printer): slot 0.2 a side round the tongue; plate bosses\n   0.25 a side in the pockets.\n"
         "• Print the plate upright on its bottom edge, tongue last (short\n   bridge); PETG. Tag = sticker.")
fig.text(0.62, 0.10, notes, fontsize=11, color="#222")
plt.savefig(OUT, dpi=100)
print("saved", OUT)
