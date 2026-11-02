# 2D: rear ID tag plate for every robot (heals and backstabs: another robot's front camera reads it up close from behind).
# A printed bracket shares the top deck's two rear screws (standoffs at x -11.5, y +-15.5): two arms on the deck run back over
# the battery and a panel hangs just behind the battery cradle, its face inside the body outline. The ArUco tag (20 mm,
# 4x4) sits at another robot's camera height (lens z 47.1). Side view (y +15.5, through an arm), top view, rear view, to scale.
#   python draw_rear_tag.py <rear.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from shapely.geometry import Point, box
from shapely.ops import unary_union

R = json.load(open(sys.argv[1])); OUT = sys.argv[2]
BODY_R = 40.6; CAM_Z = 47.1
SCREW = (-11.5, 15.5)                 # rear deck screws (M2, into the printed standoffs), +-y
LUG_TOP = 62.6                        # deck lug top under the screw heads
ARM_T, ARM_Y0, ARM_Y1 = 2.0, 13.5, 17.5   # arms: 2 thick, |y| 13.5..17.5 (0.7 clear of the LED board at |y| 12.8)
EYE_R = 3.2                           # eye round each screw (cut at |y| 13.5: the LED board is right inside it)
PANEL_X0, PANEL_X1 = -36.3, -34.3     # panel: face at x -36.3 (inside the body outline at its corners), 1.4 behind the cradle (x -32.9)
PANEL_HW = 18.0                       # panel half width
PANEL_Z0 = 35.0                       # panel bottom; top = arm top
TAG = 20.0                            # ArUco 4x4 tag, 20 mm, centred on y 0 and the camera height
TAG_Z = CAM_Z
LED_HW = 12.8; DOME_R = 15.0
C_P = "#f2c200"; C_PE = "#7a6100"

arm_top = LUG_TOP + ARM_T
def top_poly():
    arms = []
    for s in (1, -1):
        eye = Point(SCREW[0], s * SCREW[1]).buffer(EYE_R, quad_segs=32)
        arm = box(PANEL_X1 - 0.01, s * ARM_Y0 if s > 0 else -ARM_Y1, SCREW[0], s * ARM_Y1 if s > 0 else -ARM_Y0)
        keep = box(-60, ARM_Y0, 0, 60) if s > 0 else box(-60, -60, 0, -ARM_Y0)
        arms.append(unary_union([eye, arm]).intersection(keep).difference(Point(SCREW[0], s * SCREW[1]).buffer(1.25, quad_segs=16)))
    panel = box(PANEL_X0, -PANEL_HW, PANEL_X1, PANEL_HW)
    return unary_union(arms + [panel])

def draw_poly(ax, p, **kw):
    for g in getattr(p, "geoms", [p]):
        from matplotlib.patches import Polygon as MP
        ax.add_patch(MP(list(g.exterior.coords), closed=True, **kw))
        for h in g.interiors:
            ax.add_patch(MP(list(h.coords), closed=True, fc="white", ec=kw.get("ec", "k"), lw=kw.get("lw", 1)))

fig = plt.figure(figsize=(17, 15))
fig.suptitle("Rear ID tag plate (2D, to scale) – for every robot: heals and backstabs", fontsize=17, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.915, "A printed bracket shares the top deck's two rear screws. Two arms run back over the battery;\na panel hangs just behind the battery "
         "cradle with a 20 mm ArUco tag at another robot's camera height (z 47).\nNo new holes in the base. The deck screws get 2 mm longer (M2 x 6 -> M2 x 8). "
         "Same part on every style.", fontsize=12, color="#333")

# ---------------- side view (section through an arm, y +15.5; battery + deck from y 0 dashed) ----------------
ax = fig.add_axes([0.04, 0.47, 0.55, 0.42])
for n, ws in R["side"].items():
    for w in ws:
        ax.plot([p[0] for p in w], [p[1] for p in w], color="#8a8f98", lw=0.6)
ax.axhline(0, color="k", lw=1.2)
ax.add_patch(Rectangle((PANEL_X1, LUG_TOP), SCREW[0] + EYE_R - PANEL_X1, ARM_T, fc=C_P, ec=C_PE))           # arm
ax.add_patch(Rectangle((PANEL_X0, PANEL_Z0), PANEL_X1 - PANEL_X0, arm_top - PANEL_Z0, fc=C_P, ec=C_PE))      # panel
ax.add_patch(Rectangle((PANEL_X0 - 0.2, TAG_Z - TAG / 2), 0.2, TAG, fc="k"))                                  # tag sticker
ax.plot([SCREW[0]] * 2, [56.6, arm_top + 0.6], color="#555", lw=2.5)                                         # screw
ax.add_patch(Rectangle((SCREW[0] - 1.9, arm_top), 3.8, 1.3, fc="#bbb", ec="k", lw=0.6))                      # head
ax.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9)
ax.text(-47, CAM_Z + 0.8, "other robots' camera height z 47.1", color="#7b61ff", fontsize=9)
ax.annotate("arm 2 thick on the deck lug,\nunder the rear deck screw (M2 x 8 now)", xy=(SCREW[0], arm_top), xytext=(-30, 74), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("panel 2 thick, face at x -36.3\n(1.4 behind the battery cradle)", xy=(PANEL_X0, 40), xytext=(-47, 18), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("20 mm ArUco tag\n(sticker), centre z 47", xy=(PANEL_X0 - 0.2, TAG_Z + 6), xytext=(-47, 58), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("16340 cell + cradle (y 0)", xy=(-24, 44), xytext=(-24, 52), fontsize=9, ha="center", arrowprops=dict(arrowstyle="-", color="#666"))
ax.axvline(-BODY_R, color="#999", ls=":", lw=0.8)
ax.set_title("SIDE VIEW – section at y +15.5 (through an arm)", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-48, 12); ax.set_ylim(-1, 84); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- top view ----------------
ax2 = fig.add_axes([0.60, 0.47, 0.38, 0.42])
for n, ws in R["top"]["45.0"].items():
    for w in ws:
        ax2.plot([p[0] for p in w], [p[1] for p in w], color="#8a8f98", lw=0.6)
th = [math.radians(a) for a in range(0, 361, 2)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
ax2.add_patch(Circle((0, 0), DOME_R, fc="#eef", ec="#88a", ls="--")); ax2.text(0, 0, "dome", ha="center", fontsize=9, color="#557")
ax2.add_patch(Rectangle((-LED_HW, -LED_HW), 2 * LED_HW, 2 * LED_HW, fc="none", ec="#2e6b3f", ls="--"))
ax2.text(-LED_HW + 0.5, LED_HW - 3, "LED board", fontsize=8, color="#2e6b3f")
draw_poly(ax2, top_poly(), fc=C_P, ec=C_PE, lw=1.0)
for s in (1, -1):
    ax2.add_patch(Circle((SCREW[0], s * SCREW[1]), 1.9, fc="#bbb", ec="k", lw=0.6))
ax2.annotate("eyes cut at |y| 13.5:\n0.7 clear of the LED board", xy=(SCREW[0], -13.6), xytext=(-5, -35), fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("panel 36 wide,\ninside the outline", xy=(PANEL_X0, -16), xytext=(-47, -44), fontsize=9, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW (battery at z 45 grey)", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-48, 20); ax2.set_ylim(-48, 48); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")

# ---------------- rear view (looking forward, +x) ----------------
ax3 = fig.add_axes([0.04, 0.05, 0.55, 0.36])
ax3.plot([-BODY_R, BODY_R], [6.5, 6.5], color="#8a8f98"); ax3.plot([-BODY_R, BODY_R], [29.0, 29.0], color="#8a8f98")
ax3.add_patch(Rectangle((-BODY_R, 6.5), 2 * BODY_R, 22.5, fc="none", ec="#8a8f98"))
ax3.add_patch(Rectangle((-BODY_R, 29.0), 2 * BODY_R, 1.5, fc="#cfe3d4", ec="#2e6b3f"))
ax3.add_patch(Rectangle((-20, 57.0), 40, 5.6, fc="none", ec="#8a8f98"))
from matplotlib.patches import Wedge
ax3.add_patch(Wedge((0, 62.0), DOME_R, 0, 180, fc="#eef", ec="#88a"))
ax3.add_patch(Rectangle((-PANEL_HW, PANEL_Z0), 2 * PANEL_HW, arm_top - PANEL_Z0, fc=C_P, ec=C_PE))
# a 4x4 ArUco-like pattern (illustration): 6x6 cells incl. the black border
cell = TAG / 6
pat = ["111111", "101101", "110011", "100101", "101011", "111111"]
for i, row in enumerate(pat):
    for j, v in enumerate(row):
        ax3.add_patch(Rectangle((-TAG / 2 + j * cell, TAG_Z + TAG / 2 - (i + 1) * cell), cell, cell, fc="k" if v == "1" else "white", ec="none"))
ax3.axhline(CAM_Z, color="#7b61ff", ls="--", lw=0.9)
ax3.text(BODY_R - 1, CAM_Z + 0.8, "camera height", color="#7b61ff", fontsize=9, ha="right")
ax3.annotate(f"tag 20 x 20: 3.3 mm cells. At 10 cm another robot's camera\n(352 px, 53°) sees ~12 px per cell, at 20 cm ~6", xy=(TAG / 2, TAG_Z), xytext=(22, 40), fontsize=10,
             arrowprops=dict(arrowstyle="-", color="#666"))
ax3.set_title("REAR VIEW (looking forward)", fontsize=13, fontweight="bold", loc="left")
ax3.set_xlim(-45, 75); ax3.set_ylim(0, 82); ax3.set_aspect("equal")
ax3.grid(True, lw=0.25, color="#ddd"); ax3.set_xlabel("y (mm)"); ax3.set_ylabel("z (mm)")

notes = ("• Print: bracket on its back (panel face down), PETG; tag = printed sticker\n   (or a 2-colour print).\n"
         "• Fixing: the 2 rear deck screws, M2 x 6 -> M2 x 8. No new holes.\n"
         "• Clearances: LED board 0.7, dome 1.1, battery cradle 1.4,\n   battery top (z 48.7) to the arms 13.9.\n"
         "• The cell still lifts out of its cradle (13.9 above it).\n"
         "• Same part on every style: one tag per robot (team + number).\n"
         "• From straight behind, the panel hides the dome's lowest 2.6 mm.")
fig.text(0.62, 0.10, notes, fontsize=11, color="#222")
plt.savefig(OUT, dpi=100)
print("saved", OUT)
