# 2D concept (to scale): a recess in the TagBar's back face that shows where the 9.5 mm ArUco sticker goes.
# Numbers from tag_mounts.py (TAG): bar 1.5 thick (x -15.6..-14.1), z 48.7..58.9, between the posts at y +-15.5.
#   C:/Python312/python.exe mech/freecad/sketches/draw_tag_recess.py   -> sketches/tag_recess_v1.png
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tag_recess_v1.png")
X0, X1, Z0, Z1, PY = -15.6, -14.1, 48.7, 58.9, 15.5
TAG, TZ = 9.5, (49.2, 58.7)
RW, RD = TAG + 0.6, 0.25                # recess: 0.3 a side round the sticker, 0.25 deep, the bar's full height
RO = 2.5 + 1.6                          # clip outer radius

fig = plt.figure(figsize=(14, 6.5))
a = fig.add_axes([0.03, 0.15, 0.55, 0.7]); b = fig.add_axes([0.63, 0.15, 0.17, 0.7]); n = fig.add_axes([0.81, 0.1, 0.19, 0.8]); n.axis("off")

a.set_title("TagBar from behind the robot (y vs z, mm)", fontsize=11)
a.add_patch(Rectangle((-PY, Z0), 2 * PY, Z1 - Z0, fc="#f2f2ee", ec="k", lw=1.0))
for s in (-1, 1):
    a.add_patch(Rectangle((s * PY - RO, Z0), 2 * RO, Z1 - Z0, fc="#e6e6e2", ec="k", lw=0.8))
    a.text(s * PY, Z0 - 0.8, "clip on post", ha="center", fontsize=8)
a.add_patch(Rectangle((-RW / 2, Z0), RW, Z1 - Z0, fc="#e8742a", ec="k", lw=1.0, alpha=0.85))
a.add_patch(Rectangle((-TAG / 2, TZ[0]), TAG, TAG, fc="none", ec="k", lw=1.0, ls="--"))
for i in range(4):                                                 # a sketch of the 4x4 marker in the recess
    for j in range(4):
        if (i * 3 + j) % 3 == 0:
            a.add_patch(Rectangle((-TAG / 2 + 1.19 + i * 1.78, TZ[0] + 1.19 + j * 1.78), 1.78, 1.78, fc="#333", ec="none", alpha=0.35))
a.annotate(f"NEW recess {RW:.1f} wide x {RD} deep,\nthe bar's full height (open top and bottom)", (RW / 2, 56.5), (7.5, 61.6),
           fontsize=9, arrowprops=dict(arrowstyle="->"))
a.annotate("9.5 mm sticker: 0.3 mm play each side\n(the bar's edges set its height: 0.5 over/under)", (-TAG / 2, 50.5), (-16.5, 45.2),
           fontsize=9, arrowprops=dict(arrowstyle="->"))
a.set_xlim(-21, 21); a.set_ylim(44, 63.5); a.set_aspect("equal"); a.set_xlabel("y (mm)"); a.set_ylabel("z (mm)")

b.set_title("Section at y 0 (x vs z)", fontsize=11)
b.add_patch(Rectangle((X0 + RD, Z0), (X1 - X0) - RD, Z1 - Z0, fc="#f2f2ee", ec="k", lw=1.0))
b.add_patch(Rectangle((X0, Z0), RD, Z1 - Z0, fc="white", ec="#e8742a", lw=1.0, ls="--"))
b.add_patch(Rectangle((X0 + RD - 0.15, TZ[0]), 0.15, TAG, fc="#333"))
b.annotate("sticker ~flush with the face\n(the 0.25 step is easy to see\nand feel; edges protected)", (X0 + RD - 0.1, 54), (X0 - 3.3, 60.6), fontsize=8,
           arrowprops=dict(arrowstyle="->"))
b.add_patch(Rectangle((-14.7, 56.6), X1 + 14.7, Z1 - 56.6, fc="white", ec="k", lw=0.6, ls=":"))
b.annotate("existing LED-boss notch\n(front, top middle):\n0.65 left there", (-14.6, 57.7), (-13.9, 44.5), fontsize=7.5, arrowprops=dict(arrowstyle="->"))
b.annotate("1.25 left", (X1 - 0.5, 52), (X1 + 0.6, 50), fontsize=8, arrowprops=dict(arrowstyle="->"))
b.text(X0 - 0.4, 47.5, "rear", ha="center", fontsize=8); b.text(X1 + 0.4, 47.5, "front", ha="center", fontsize=8)
b.set_xlim(-19.5, -12); b.set_ylim(44, 63.5); b.set_aspect("equal")

n.text(0, 1, "\n".join([
    "Change (TagBar,",
    "tag_mounts.py):",
    "",
    "- a 0.25 mm deep recess",
    "  in the back face,",
    "  10.1 wide (the",
    "  9.5 sticker + 0.3",
    "  a side), the full",
    "  bar height",
    "- shows where the tag",
    "  goes and squares it",
    "  up; the bar's top",
    "  and bottom edges",
    "  set the height",
    "- the sticker's edges",
    "  sit below the face",
    "  (harder to peel)",
    "- bar 1.25 thick there;",
    "  0.65 at the LED-boss",
    "  notch (0.4 deep would",
    "  leave only 0.5)",
    "- no other change",
]), va="top", fontsize=9, family="monospace")
fig.suptitle("TagBar: a recess for the ArUco sticker (concept v1, to scale)", fontsize=13, weight="bold")
fig.savefig(OUT, dpi=110); print(OUT)
