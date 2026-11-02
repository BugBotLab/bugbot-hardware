# 2D: Wasp striker ram. Replaces the kick disc on the JF-0520B plunger so the kicker can tap another robot.
# Side view (section on the plunger axis, y -2.8) + top view (section at the plunger axis, z 22.3) + part detail, to scale.
# Robot outlines are sections of the BugBot model (sections json from FreeCAD, gripper and ball left out).
#   python draw_wasp_ram.py <sections.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

SEC, OUT = sys.argv[1], sys.argv[2]
S = json.load(open(SEC))
Y0, Z0 = -2.8, 22.3            # plunger axis (sol_dy, sol_z)
STROKE = 6.4                   # sol_washer_x - spring solid
BODY_R = 40.6
# ram, robot frame x (retracted)
HEAD = (18.5, 21.5, 12.0)      # same as the kick disc: return stop, M3 thin nut pocket
ROD = (21.5, 34.6, 10.0)
NECK = (34.6, 35.6, 7.0)
KNOB = (35.6, 37.6, 10.0)
CAP = (34.6, 40.6, 16.0)       # TPU 95A cap, face flush with the body outline when retracted
CAM = (26.5, 47.1); TOF = (26.5, 55.6)

C_ROB = "#8a8f98"; C_RAM = "#e67e22"; C_TPU = "#2c3e50"; C_TGT = "#4a90d9"

def outlines(ax, secs, col=C_ROB, lw=0.7):
    for n, ws in secs.items():
        for w in ws:
            ax.plot([p[0] for p in w], [p[1] for p in w], color=col, lw=lw)

def ram_side(ax, dx, solid=True, axis_y=Z0):
    ls = "-" if solid else "--"
    for (x0, x1, d), fc in ((HEAD, C_RAM), (ROD, C_RAM), (NECK, C_RAM), (KNOB, C_RAM), (CAP, C_TPU)):
        if fc == C_TPU and solid:
            # cap drawn as a section: outer minus the socket
            ax.add_patch(Rectangle((x0 + dx, axis_y - d / 2), x1 - x0, d, fc=C_TPU, ec="k", lw=0.8, alpha=0.9, zorder=3))
            ax.add_patch(Rectangle((KNOB[0] + dx, axis_y - KNOB[2] / 2), KNOB[1] - KNOB[0], KNOB[2], fc=C_RAM, ec="k", lw=0.6, zorder=4))
            ax.add_patch(Rectangle((NECK[0] + dx, axis_y - NECK[2] / 2), NECK[1] - NECK[0], NECK[2], fc=C_RAM, ec="k", lw=0.6, zorder=4))
            continue
        ax.add_patch(Rectangle((x0 + dx, axis_y - d / 2), x1 - x0, d, fc=fc if solid else "none",
                               ec="k" if solid else C_RAM, lw=0.8 if solid else 1.2, ls=ls, alpha=0.9 if solid else 1, zorder=3))

fig = plt.figure(figsize=(17, 15.5))
fig.suptitle("Wasp striker ram (2D, to scale) – replaces the kick disc, no other part changes", fontsize=17, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.945, "Same JF-0520B solenoid, bracket and 6.4 mm stroke. Gripper arm off (the SG90 stays, unused). "
         "Retracted: the TPU face sits on the body outline. Fired: it reaches 6.4 mm past it.", fontsize=12, color="#333")

# ---------------- side view ----------------
ax = fig.add_axes([0.04, 0.53, 0.92, 0.39])
outlines(ax, S["side"]["-2.8"])
ax.axhline(0, color="k", lw=1.5)
ram_side(ax, 0, True); ram_side(ax, STROKE, False)
# body outline line at the axis
ax.axvline(BODY_R, color="#999", lw=0.8, ls=":")
ax.text(BODY_R + 0.3, 1.2, "body outline\nx 40.6", fontsize=9, color="#666")
# target robot: another 80 mm robot, its wall 4.4 mm away (in range)
gap = 4.4; tx = BODY_R + gap
ax.add_patch(Rectangle((tx, 6.5), 12, 22.5, fc=C_TGT, alpha=0.25, ec=C_TGT))
ax.add_patch(Rectangle((tx, 29.0), 12, 1.6, fc="#2e6b3f", alpha=0.5, ec="#1c4428"))
ax.text(tx + 6, 17, "target\nrobot\nwall", ha="center", fontsize=10, color="#1f5d99")
ax.annotate("", xy=(BODY_R + STROKE, 33.5), xytext=(BODY_R, 33.5), arrowprops=dict(arrowstyle="<->", color=C_RAM, lw=1.5))
ax.text(BODY_R + STROKE / 2, 34.3, "reach 6.4", ha="center", color=C_RAM, fontsize=11, fontweight="bold")
# camera + ToF sight lines over the fired ram
ax.add_patch(Circle(CAM, 2.5, fc="#223")); ax.text(CAM[0] + 3.5, CAM[1] - 0.5, "camera", fontsize=9)
cam_dn = math.atan2(CAM[1], 120 - CAM[0])            # lower edge of view meets the floor ~12 cm ahead
xs = [CAM[0], 62]; ax.plot(xs, [CAM[1] - (x - CAM[0]) * math.tan(cam_dn) for x in xs], color="#7b61ff", ls="--", lw=0.9)
tof_dn = math.radians(37)
xs = [TOF[0], 62]; ax.plot(xs, [TOF[1] - (x - TOF[0]) * math.tan(tof_dn) for x in xs], color="#16a085", ls="--", lw=0.9)
ax.text(52, 41.5, "camera: lowest ray", color="#7b61ff", fontsize=9)
ax.text(48, 31.5, "ToF 74° cone edge", color="#16a085", fontsize=9, rotation=-33)
# labels
ax.annotate("JF-0520B solenoid\n(unchanged)", xy=(8, 26), xytext=(-2, 40), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("main board underside z 29\n1.7 mm above the rod at full stroke", xy=(24, 29), xytext=(1, 33.6), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("PETG ram, Ø10 rod\nhead = old kick disc (Ø12 × 3, M3 thin nut)", xy=(27, Z0 - 4), xytext=(14, 3), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("TPU 95A cap Ø16 × 6", xy=(39, Z0 - 7), xytext=(46, 9.5), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.set_title("SIDE VIEW – section on the plunger axis (y −2.8). Solid = retracted, dashed = fired.", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-6, 64); ax.set_ylim(-1, 50); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- top view ----------------
ax2 = fig.add_axes([0.04, 0.05, 0.56, 0.44])
outlines(ax2, S["top"]["22.3"])
th = [i * 2 * math.pi / 180 for i in range(181)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
for dx, solid in ((0, True), (STROKE, False)):
    for (x0, x1, d), fc in ((HEAD, C_RAM), (ROD, C_RAM), (CAP, C_TPU)):
        ax2.add_patch(Rectangle((x0 + dx, Y0 - d / 2), x1 - x0, d, fc=fc if solid else "none", ec="k" if solid else C_RAM,
                                ls="-" if solid else "--", lw=0.8 if solid else 1.2, alpha=0.9 if solid else 1, zorder=3))
# target robot, round, 4.4 mm ahead
cx = BODY_R + gap + 40.6
ax2.plot([cx + 40.6 * math.cos(t) for t in th], [40.6 * math.sin(t) for t in th], color=C_TGT, lw=1.2)
ax2.text(cx - 30, -2, "target robot", color="#1f5d99", fontsize=10)
ax2.annotate("wall tips y ±20.5:\n12 mm clear each side", xy=(35, 20.4), xytext=(44, 30), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("kick bracket\n2.3 mm", xy=(12, -14), xytext=(-8, -30), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("ram on the solenoid axis,\n2.8 mm right of centre (as the kicker)", xy=(30, Y0), xytext=(5, 10), fontsize=10,
             arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – section at the plunger axis (z 22.3)", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-42, 90); ax2.set_ylim(-43, 47); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")

# ---------------- part detail ----------------
ax3 = fig.add_axes([0.63, 0.20, 0.35, 0.28])
yy = 0
def r(x0, x1, d, fc, ec="k", hatch=None):
    ax3.add_patch(Rectangle((x0, yy - d / 2), x1 - x0, d, fc=fc, ec=ec, lw=0.9, hatch=hatch))
r(*HEAD, C_RAM); r(*ROD, C_RAM)
r(CAP[0], CAP[1], CAP[2], C_TPU)
r(*NECK, C_RAM); r(*KNOB, C_RAM)
ax3.add_patch(Rectangle((18.5, -5.65 / 2), 1.9, 5.65, fc="#bbb", ec="k", lw=0.6))   # M3 thin nut pocket
ax3.add_patch(Rectangle((18.5, -1.6), 4.5, 3.2, fc="white", ec="k", lw=0.6))         # M3 thread clearance
ax3.text(18.6, 7.2, "M3 thin nut\n(as kick disc)", fontsize=9)
ax3.text(26, 6.3, "PETG Ø10", fontsize=9, color="#a04000")
ax3.text(35, 9.2, "TPU cap: lip Ø7.4\nstretches over the\nØ10 knob + CA glue", fontsize=9, color=C_TPU)
for xv, lab in ((18.5, "18.5"), (21.5, "21.5"), (34.6, "34.6"), (40.6, "40.6")):
    ax3.plot([xv, xv], [-8.8, -10.3], color="#666", lw=0.6); ax3.text(xv, -12, lab, ha="center", fontsize=8)
ax3.text(17, -15, "x in the robot frame, retracted. Total length 22.1 mm.", fontsize=9)
ax3.set_title("Ram + cap (section)", fontsize=12, fontweight="bold", loc="left")
ax3.set_xlim(16, 46); ax3.set_ylim(-16.5, 13); ax3.set_aspect("equal"); ax3.axis("off")

notes = ("• Print: ram standing on its head (round, no supports),\n   100 % infill PETG; cap in TPU 95A.\n"
         "• Round all the way: it can turn on the plunger thread\n   without tilting the face.\n"
         "• Clearances (model check): main board 1.7 fired, 0.7 retracted\n   (same as the kick disc); kick bracket 2.3; motor caps 2.7+.\n"
         "• Out of the camera's and ToF's view when fired. Hits other\n   robots at z 14–30 (their wall), or a ball 2 mm above centre.\n"
         "• Ram + cap ≈ 3 g vs 0.4 g kick disc: slower stroke, more\n   momentum. Measure the plunger mass to check the kick.")
fig.text(0.63, 0.06, notes, fontsize=10, va="bottom", color="#222")
plt.savefig(OUT, dpi=110)
print("saved", OUT)
