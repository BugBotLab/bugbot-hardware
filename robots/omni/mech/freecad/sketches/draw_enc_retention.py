# 2D concept (to scale) for holding the wheel-encoder boards: now vs proposed card guides. One drive unit, its own frame:
# x radial (out), y along the wheel's face, z up. Numbers from build_encoder.py and the Params sheet.
#   C:/Python312/python.exe mech/freecad/sketches/draw_enc_retention.py   -> sketches/enc_retention_v1.png
import math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enc_retention_v1.png")
X_BACK, T = 37.97, 0.8; X_FRONT = X_BACK - T
BY0, BY1, BZ0, BZ1 = 3.0, 11.0, 7.5, 24.2
PLATE_Z, PLATE_T, PCB_Z, PCB_T = 6.5, 1.6, 29.0, 1.6
R_IN, R_OUT = 38.8, 40.6
WF, RING_H = 32.55, 1.2
SLOT = (X_FRONT - 0.2, X_BACK + 0.2, 7.3)               # x0, x1, floor z
G_W, G_D, RIB = 1.2, 0.8, 1.4                           # guide groove width (0.2 a side), depth, rib wall beside it
C = dict(board="#1b6638", cu="#c8a24a", wall="#d9d9d4", plate="#cfcfca", new="#e8742a", main="#2d5a2d", wheel="#333333", mag="#b8261e")

fig = plt.figure(figsize=(16, 9.6))
axs = [fig.add_axes([0.03, 0.08, 0.30, 0.80]), fig.add_axes([0.36, 0.08, 0.30, 0.80]), fig.add_axes([0.69, 0.42, 0.29, 0.46])]
note = fig.add_axes([0.675, 0.04, 0.32, 0.33]); note.axis("off")


def wall_x(y):                                           # the wall's inner face at y (a circle round the robot centre)
    return math.sqrt(R_IN ** 2 - y ** 2)


# ---- 1. NOW: side section through the board (x vs z) ----
a = axs[0]; a.set_title("NOW - side section through an encoder board\n(held only by the socket above and a loose slot below)", fontsize=11)
xw = wall_x(7)
a.add_patch(Rectangle((xw, PLATE_Z), R_OUT - xw, PCB_Z - PLATE_Z, fc=C["wall"], ec="k", lw=0.8))
a.add_patch(Rectangle((28, PLATE_Z), xw - 28, PLATE_T, fc=C["plate"], ec="k", lw=0.8))
a.add_patch(Rectangle((SLOT[0], SLOT[2]), SLOT[1] - SLOT[0], PLATE_Z + PLATE_T - SLOT[2] + 0.02, fc="white", ec="k", lw=0.6))
a.add_patch(Rectangle((28, PCB_Z), R_OUT - 28, PCB_T, fc=C["main"], ec="k", lw=0.8))
a.add_patch(Rectangle((35.12, 24.4), 2.0, PCB_Z - 24.4, fc="#222", ec="k", lw=0.6)); a.text(34.9, 26.5, "1x4 socket", ha="right", fontsize=8)
a.add_patch(Rectangle((X_FRONT, BZ0), T, BZ1 - BZ0, fc=C["board"], ec="k", lw=0.8))
a.add_patch(Rectangle((X_FRONT - 1.2, 22.0), 1.2, 2.2, fc=C["cu"], ec="k", lw=0.5))
a.plot([36.1, 36.1], [22.8, 26.0], color=C["cu"], lw=2)
a.add_patch(Rectangle((X_FRONT - 0.9, 11.0), 0.9, 2.0, fc="#111", ec="k", lw=0.5)); a.text(X_FRONT - 1.2, 10.3, "MT6701", ha="right", fontsize=7)
a.add_patch(Rectangle((WF - 15.21, 0.0), 15.21, 24.0, fc="none", ec=C["wheel"], lw=0.8, ls="--")); a.text(26, 1, "wheel (axle along x)", fontsize=7)
a.add_patch(Rectangle((WF, 8.0), RING_H, 8.0, fc="#999", ec="k", lw=0.5)); a.add_patch(Rectangle((WF + RING_H - 0.1, 9.0), 0.1, 6.0, fc=C["mag"]))
a.annotate("0.2 play each side\nin the plate slot", (X_FRONT - 0.1, 7.6), (30.5, 3.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.annotate("wall 0.2 behind,\nnot touching", (xw, 16), (39.2, 19.5), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.annotate("only friction\non 4 pins", (36.1, 25.0), (30.5, 27.4), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.set_xlim(28, 41.5); a.set_ylim(0, 32); a.set_aspect("equal"); a.set_xlabel("x radial (mm)"); a.set_ylabel("z (mm)")

# ---- 2. PROPOSED: looking out at the board from the wheel (y vs z) ----
a = axs[1]; a.set_title("PROPOSED - card guides (seen from the wheel side)\nboard slides down in from above, held on 3 edges", fontsize=11)
a.add_patch(Rectangle((-1.5, PLATE_Z), 17, PCB_Z - PLATE_Z, fc=C["wall"], ec="none"))
a.add_patch(Rectangle((-1.5, PLATE_Z), 17, PLATE_T, fc=C["plate"], ec="k", lw=0.6))
a.add_patch(Rectangle((-1.5, PCB_Z), 17, PCB_T, fc=C["main"], ec="k", lw=0.6))
a.add_patch(Rectangle((BY0, BZ0), BY1 - BY0, BZ1 - BZ0, fc=C["board"], ec="k", lw=0.8))
a.add_patch(Rectangle((6.5, 10.5), 3.0, 3.0, fc="#111")); a.text(8, 14.0, "MT6701 (on the axle)", ha="center", fontsize=7, color="w")
for y0, y1 in ((BY0 - 0.3 - RIB, BY0 + 0.5), (BY1 - 0.5, BY1 + 0.3 + RIB)):   # the ribs: their lips cover 0.5 of each board edge (U1 pads are 1.15 in)
    a.add_patch(Rectangle((y0, 7.3), y1 - y0, 24.0 - 7.3, fc=C["new"], ec="k", lw=0.8, alpha=0.85))
a.add_patch(Rectangle((5.5, 25.0), 5.0, 4.0, fc="#222")); a.text(8, 27.0, "socket", ha="center", color="w", fontsize=7)
a.annotate("new rib with a 1.2 groove\n(0.2 a side, 0.8 deep; lip over 0.5 of the edge,\nclear of the MT6701 pads 1.15 in)", (1.0, 18), (-1.3, 31.2), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.annotate("board edge in the groove:\n0.3 play sideways", (BY1 + 0.5, 14), (11.2, 4.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.set_xlim(-2, 16.5); a.set_ylim(0, 33); a.set_aspect("equal"); a.set_xlabel("y along the wheel face (mm)"); a.set_ylabel("z (mm)")

# ---- 3. PROPOSED: top section at z 16 (x vs y) ----
a = axs[2]; a.set_title("PROPOSED - top section at mid height (z 16)", fontsize=11)
ys = [i / 10 for i in range(-20, 161)]
a.add_patch(Polygon([(wall_x(y), y) for y in ys] + [(R_OUT, ys[-1]), (R_OUT, ys[0])], fc=C["wall"], ec="k", lw=0.8))
for y0, y1, gy0, gy1 in ((BY0 - 0.3 - RIB, BY0 + 0.5, BY0 - 0.3, BY0 + 0.5), (BY1 - 0.5, BY1 + 0.3 + RIB, BY1 - 0.5, BY1 + 0.3)):
    x_in = 36.2
    xr = wall_x(max(abs(y0), abs(y1)))
    a.add_patch(Rectangle((x_in, y0), xr - x_in + 0.4, y1 - y0, fc=C["new"], ec="k", lw=0.8))
    a.add_patch(Rectangle((X_FRONT - 0.2, gy0), G_W, gy1 - gy0, fc="white", ec="k", lw=0.5))   # the groove
a.add_patch(Rectangle((X_FRONT, BY0), T, BY1 - BY0, fc=C["board"], ec="k", lw=0.8))
a.add_patch(Rectangle((WF, 4.0), RING_H, 8.0, fc="#999", ec="k", lw=0.5)); a.text(WF - 0.2, 12.6, "magnet ring", fontsize=7, ha="right")
a.annotate("1.4 to the magnet", (X_FRONT, 8), (31.0, 14.5), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.annotate("board front / back:\n0.2 play in the grooves", (X_BACK, 2.6), (38.2, -1.3), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.set_xlim(30.5, 41.5); a.set_ylim(-2, 15.5); a.set_aspect("equal"); a.set_xlabel("x radial (mm)"); a.set_ylabel("y (mm)")

note.text(0, 1, "\n".join([
    "Proposal: two printed ribs on the chassis wall, one each side of every encoder",
    "board, with a groove the board's side edges slide down in (a card guide).",
    "",
    "- the board is held on 3 edges (both sides + the plate slot below) and the",
    "  socket above only makes the electrical contact: the pins stop carrying it",
    "- the magnet gap is set by the grooves (1.4 mm, +-0.2), not by the pins",
    "- no PCB change, no extra parts; clearances 0.2-0.3 a side (any printer)",
    "- assembly: drop the 3 boards into their guides, then lower the main board",
    "  onto the 3 headers",
    "",
    "Orange = new. Not shown: an option with an M2 screw through the board (needs a",
    "hole in the 8 mm wide encoder PCB: tight beside the chip; only if guides are not",
    "enough).",
]), va="top", fontsize=8.6, family="monospace", wrap=True)
fig.suptitle("Wheel encoder boards: holding them properly (concept v1, to scale, mm)", fontsize=14, weight="bold")
fig.savefig(OUT, dpi=110); print(OUT)
