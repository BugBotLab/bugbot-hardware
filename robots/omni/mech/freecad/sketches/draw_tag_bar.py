# 2D: rear ID tag on a bar between the two rear deck posts (user's idea), replacing the rear tag plate.
# The tag sits ~28 mm inside the back of the body, so even an open-fronted robot touching the back keeps its camera ~31 mm
# away and sees the whole tag. A 5 mm ArUco 4x4 tag (z 51.5-56.5) clears the battery in the camera's line of sight and fits
# under the LED-board nut bosses. The bar snaps onto the posts with C-clips (open to the front). Side view (y 0), top view,
# rear view, to scale.
#   python draw_tag_bar.py <rear.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon as MP
from shapely.geometry import Point, box
from shapely.ops import unary_union

R = json.load(open(sys.argv[1])); OUT = sys.argv[2]
BODY_R, CAM_Z, LENS_X = 40.6, 47.1, 26.5          # the camera lens (every style, same base)
POST = (-11.5, 15.5); POST_D = 5.6                # rear deck posts (printed standoffs), z 30.6..60.6
LED_BOSS = (-14.3, -7.3, -3.0, 3.45, 57.0, 60.6)  # LED-board nut bosses under the deck (x0, x1, y0, y1, z0, z1)
CELL_C, CELL_R, CELL_X = (-23.8, 40.5), 8.2, (-32.0, -15.6)   # 16340 cell (axis along y), x extent
HOLDER = (-32.9, -14.7, 45.8)
TAG, TAG_Z0 = 5.0, 51.5                           # 5 mm tag, z 51.5..56.5 (0.5 under the LED bosses)
BAR_X0, BAR_X1 = -12.3, -10.8                     # bar: 1.5 thick in the posts' plane, tag face at x -12.3
BAR_Z0, BAR_Z1 = 50.5, 56.6
CLIP_BORE, CLIP_WALL, CLIP_OPEN = POST_D + 0.6, 1.6, 4.4   # C-clip: 0.3 a side on the post; mouth 4.4 (snaps over the 5.6 post)
HALF_V, HALF_H = 20.5, 26.5                       # camera half angles (41 x 53 deg)
C_P = "#A31621"; C_PE = "#5e0b12"; C_B = "#8a8f98"
# closest viewer: an open-fronted robot touching the back (its wall tips at x 35.04, y 20.5 on our wall r 40.6)
CENTRE_D = 35.04 + math.sqrt(BODY_R ** 2 - 20.5 ** 2)
LENS_T = LENS_X - CENTRE_D                         # its lens, in our frame
DIST = BAR_X0 - LENS_T
v_margin = DIST * math.tan(math.radians(HALF_V)) - (TAG_Z0 + TAG - CAM_Z)
h_margin = DIST * math.tan(math.radians(HALF_H)) - TAG / 2
def ray_z(x, ztag): return CAM_Z + (ztag - CAM_Z) * (x - LENS_T) / DIST
cell_clear = min(ray_z(x, TAG_Z0) - (CELL_C[1] + math.sqrt(max(0.0, CELL_R ** 2 - (x - CELL_C[0]) ** 2))) for x in [CELL_X[0] + 0.1 * k for k in range(int((CELL_X[1] - CELL_X[0]) * 10))])
read_reliable = TAG * 353 / 24                    # mm, 4 px per cell at 352 x 288 (f = 353 px)

fig = plt.figure(figsize=(18, 16))
fig.suptitle("Rear ID tag on a bar between the rear deck posts (2D, to scale) – replaces the rear tag plate", fontsize=17,
             fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.915, f"5 mm ArUco 4x4 tag, centre z 54, set {BODY_R + BAR_X0:.0f} mm inside the back of the body. A robot touching the back keeps its camera "
         f"{DIST:.0f} mm away: the whole tag is in view ({v_margin:.1f} mm spare at the top, ±{h_margin:.0f} mm sideways)\nand the line of sight "
         f"clears the battery by {cell_clear:.1f} mm. Reliable read up to ~{read_reliable / 10:.1f} cm lens-to-tag: only right behind. "
         "The bar snaps onto the 2 posts (C-clips open to the front): no screws, no other base change.", fontsize=12, color="#333")

# ---------------- side view (y 0) with the closest viewer's lens and its view ----------------
ax = fig.add_axes([0.04, 0.47, 0.58, 0.40])
for n, ws in R["side"].items():
    for w in ws:
        ax.plot([p[0] for p in w], [p[1] for p in w], color=C_B, lw=0.6)
ax.axhline(0, color="k", lw=1.2)
ax.add_patch(Rectangle((LED_BOSS[0], LED_BOSS[4]), LED_BOSS[1] - LED_BOSS[0], LED_BOSS[5] - LED_BOSS[4], fc="#e0e0e0", ec="#555", ls="--"))
ax.text(LED_BOSS[0] + 0.3, LED_BOSS[5] + 0.6, "LED nut boss", fontsize=8)
ax.add_patch(Circle(CELL_C, CELL_R, fc="#cfe0ff", ec="#2f5bb7", alpha=0.6)); ax.text(CELL_C[0], CELL_C[1], "16340", ha="center", fontsize=8)
ax.add_patch(Rectangle((BAR_X0, BAR_Z0), BAR_X1 - BAR_X0, BAR_Z1 - BAR_Z0, fc=C_P, ec=C_PE))
ax.add_patch(Rectangle((BAR_X0 - 0.2, TAG_Z0), 0.2, TAG, fc="k"))
# viewer: its front (wall tip) and lens, its view to the tag edges and its field of view
ax.add_patch(Circle((LENS_T, CAM_Z), 1.2, fc="#223")); ax.text(LENS_T - 1, CAM_Z + 2.2, "lens of a robot\ntouching the back", fontsize=9, ha="right")
for zt in (TAG_Z0, TAG_Z0 + TAG):
    ax.plot([LENS_T, BAR_X0], [CAM_Z, zt], color="#2e7d32", lw=0.9)
for s in (1, -1):
    ax.plot([LENS_T, BAR_X0 + 3], [CAM_Z, CAM_Z + s * (BAR_X0 + 3 - LENS_T) * math.tan(math.radians(HALF_V))], color="#7b61ff", ls="--", lw=0.8)
ax.axvline(-BODY_R, color="#999", ls=":", lw=0.8)
ax.annotate(f"tag bar (crimson = Scorpion; each style its colour):\n1.5 thick, z {BAR_Z0}–{BAR_Z1}, in the posts' plane", xy=(BAR_X1, 53),
            xytext=(-5, 70), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate(f"5 mm tag, z {TAG_Z0}–{TAG_Z0 + TAG}", xy=(BAR_X0 - 0.2, TAG_Z0 + 2), xytext=(-38, 66), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate(f"line of sight clears the cell by {cell_clear:.1f}", xy=(CELL_C[0], 49.9), xytext=(-50, 30), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.text(LENS_T + 2, CAM_Z - 9, "camera view (41° high)", color="#7b61ff", fontsize=9)
ax.set_title("SIDE VIEW – y 0, with the closest viewer (an open-fronted robot touching the back)", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-50, 8); ax.set_ylim(25, 82); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- top view at the bar's height ----------------
ax2 = fig.add_axes([0.66, 0.47, 0.32, 0.40])
for w in R["top"]["52.0"].get("Electronics:1/LEDCable", []):
    ax2.plot([p[0] for p in w], [p[1] for p in w], color="#222", lw=0.8)
th = [math.radians(a) for a in range(0, 361, 2)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
ax2.add_patch(Rectangle((CELL_X[0], -17.2), CELL_X[1] - CELL_X[0], 35.3, fc="#cfe0ff", ec="#2f5bb7", alpha=0.4))
ax2.text(-24, -14, "cell (below)", fontsize=8, ha="center")
ax2.add_patch(Rectangle((LED_BOSS[0], LED_BOSS[2]), LED_BOSS[1] - LED_BOSS[0], LED_BOSS[3] - LED_BOSS[2], fc="none", ec="#555", ls="--"))
parts = [box(BAR_X0, -POST[1], BAR_X1, POST[1])]
for s in (1, -1):
    c = Point(POST[0], s * POST[1])
    ring = c.buffer(CLIP_BORE / 2 + CLIP_WALL, quad_segs=32).difference(c.buffer(CLIP_BORE / 2, quad_segs=32))
    mouth = box(POST[0], s * POST[1] - CLIP_OPEN / 2, POST[0] + 10, s * POST[1] + CLIP_OPEN / 2)
    parts.append(ring.difference(mouth))
bar = unary_union(parts).difference(Point(POST[0], POST[1]).buffer(CLIP_BORE / 2)).difference(Point(POST[0], -POST[1]).buffer(CLIP_BORE / 2))
for g in getattr(bar, "geoms", [bar]):
    ax2.add_patch(MP(list(g.exterior.coords), closed=True, fc=C_P, ec=C_PE))
for s in (1, -1):
    ax2.add_patch(Circle((POST[0], s * POST[1]), POST_D / 2, fc="#f2c200", ec="#7a6100"))
ax2.add_patch(Rectangle((BAR_X0 - 0.4, -TAG / 2), 0.4, TAG, fc="k"))
ax2.annotate("C-clips open to the front: push the bar\nonto the posts from behind, it snaps on", xy=(POST[0] + 3, -POST[1]), xytext=(-46, -36),
             fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("LED nut boss (above the bar)", xy=(LED_BOSS[1], 0), xytext=(-8, 26), fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – at the bar (z ~54)", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-48, 8); ax2.set_ylim(-42, 42); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")

# ---------------- rear view ----------------
ax3 = fig.add_axes([0.04, 0.05, 0.45, 0.36])
ax3.add_patch(Rectangle((-BODY_R, 6.5), 2 * BODY_R, 22.5, fc="#f5f5f5", ec=C_B))
ax3.add_patch(Rectangle((-BODY_R, 29.0), 2 * BODY_R, 1.5, fc="#cfe3d4", ec="#2e6b3f"))
ax3.add_patch(Rectangle((-21.5, 30.6), 43, 15.2, fc="#e8e8e8", ec=C_B)); ax3.add_patch(Circle((0, 40.5), 8.2, fc="#cfe0ff", ec="#2f5bb7"))
ax3.text(0, 34, "battery (in front of the view, lower)", ha="center", fontsize=8)
ax3.add_patch(Rectangle((-20, 60.6), 40, 2.0, fc="none", ec=C_B)); ax3.add_patch(Wedge((0, 62.6), 15, 0, 180, fc="#eef", ec="#88a"))
for s in (1, -1):
    ax3.add_patch(Rectangle((s * POST[1] - POST_D / 2, 30.6), POST_D, 30.0, fc="#f2c200", ec="#7a6100"))
    ax3.add_patch(Rectangle((s * POST[1] - CLIP_BORE / 2 - CLIP_WALL, BAR_Z0), CLIP_BORE + 2 * CLIP_WALL, BAR_Z1 - BAR_Z0, fc=C_P, ec=C_PE, alpha=0.9))
ax3.add_patch(Rectangle((-POST[1], BAR_Z0), 2 * POST[1], BAR_Z1 - BAR_Z0, fc=C_P, ec=C_PE))
cell = TAG / 6
pat = ["111111", "101101", "110011", "100101", "101011", "111111"]
for i, row in enumerate(pat):
    for j, v in enumerate(row):
        ax3.add_patch(Rectangle((-TAG / 2 + j * cell, TAG_Z0 + TAG - (i + 1) * cell), cell, cell, fc="k" if v == "1" else "white", ec="none"))
ax3.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9); ax3.text(BODY_R - 1, CAM_Z - 2.5, "camera height", color="#7b61ff", fontsize=9, ha="right")
ax3.set_title("REAR VIEW (looking forward)", fontsize=13, fontweight="bold", loc="left")
ax3.set_xlim(-44, 44); ax3.set_ylim(0, 82); ax3.set_aspect("equal")
ax3.grid(True, lw=0.25, color="#ddd"); ax3.set_xlabel("y (mm)"); ax3.set_ylabel("z (mm)")

notes = ("• Removed again: the rear tag plate, its 2 wall pads / pockets / pilots,\n   the deck's slotted boss and the 2 plate screws.\n"
         "• Tag bar: one small print (PETG), C-clips Ø6.2 bore (0.3 a side on the\n   5.6 posts), 1.6 walls, 4.4 mouth; print flat (tag face down).\n"
         "• Closest lens-to-tag by style (touching the back): open front ~31 mm,\n   Wasp ~42, Beetle / Spider / gripper down ~68 (within the ~7.4 cm).\n"
         "• Referee still checks the tag pose (distance + angle behind).\n"
         "• To confirm in 3D: cell + LED boss clearances; test focus at ~3 cm.")
fig.text(0.52, 0.10, notes, fontsize=11, color="#222")
plt.savefig(OUT, dpi=100)
print("saved", OUT, {"closest_dist": round(DIST, 1), "v_margin": round(v_margin, 2), "h_margin": round(h_margin, 1), "cell_clear": round(cell_clear, 2), "read_reliable": round(read_reliable, 1)})
