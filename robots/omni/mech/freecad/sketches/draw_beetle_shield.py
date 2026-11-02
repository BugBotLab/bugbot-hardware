# 2D: Beetle passive shield. Two rigid side plates on the gripper's pivot mounts (same pivot ends as the hoop arms) carry
# a low blade 16 mm ahead of the body, BELOW the Wasp's stinger. A Wasp that drives in is stopped by its wall tips on the
# blade, so its fired ram ends short of the Beetle. No moving parts: feet + tail on the main board fix the angle.
# Side view (section y +23, through the left plate) + top view (z 10) with a Wasp head-on, to scale.
#   python draw_beetle_shield.py <arm_zone.json> <base_low.json> <ram_sections.json> <out.png>
import sys, json, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch

ARM, LOW, RAM, OUT = sys.argv[1:5]
A = json.load(open(ARM)); LO = json.load(open(LOW)); R = json.load(open(RAM))
BODY_R = 40.6
PIV = (8.0, 36.7)
# shield (robot frame, mm)
BAR_Z0, BAR_Z1 = 34.0, 40.0          # top run, same as the hoop arm
LEG_X0, LEG_X1 = 34.5, 41.0          # leg down past the wall tips / board edge (1.0 to the board at y 23)
TOE_Z0, TOE_Z1 = 7.5, 13.0           # low run + blade: below the stinger cap (z 14.3)
BLADE_X1 = 56.6                      # blade face: 16 ahead of the body
BLADE_T = 4.0
FOOT = (28.0, 33.3)                  # front foot on the board top (z 30.6), above the chassis wall
TAIL = (1.0, 6.0)                    # tail under the pivot, on the board top
PCB_TOP = 30.6
PL_Y = (21.25, 24.75)                # plate faces |y| (the hoop arms' arm_in .. outside)
# Wasp
W_TIP_X, W_TIP_Y = 35.04, 20.5       # its wall tips: most forward point above its base plate (z 8.1+), from the model
W_FIRED = 47.0                       # its fired cap face
W_CAP_Z = (14.3, 30.3)
WASP_CX = BLADE_X1 + W_TIP_X         # Wasp centre when its tips rest on the blade (Beetle frame)
CAP_IN = WASP_CX - W_FIRED           # fired cap face, Beetle x

C_SH = "#f2c200"; C_SH_E = "#7a6100"; C_W = "#4a90d9"; C_BASE = "#8a8f98"

def plate_patches(ax, alpha=1.0, ec=C_SH_E):
    pp = [Circle(PIV, 6.0),
          Rectangle((PIV[0], BAR_Z0), LEG_X1 - PIV[0], BAR_Z1 - BAR_Z0),
          Rectangle((LEG_X0, TOE_Z0), LEG_X1 - LEG_X0, BAR_Z1 - TOE_Z0),
          Rectangle((LEG_X0, TOE_Z0), BLADE_X1 - LEG_X0, TOE_Z1 - TOE_Z0),
          Rectangle((FOOT[0], PCB_TOP), FOOT[1] - FOOT[0], BAR_Z0 - PCB_TOP),
          Rectangle((TAIL[0], PCB_TOP), TAIL[1] - TAIL[0], PIV[1] - PCB_TOP)]
    for p in pp:
        p.set_facecolor(C_SH); p.set_edgecolor(C_SH); p.set_alpha(alpha); ax.add_patch(p)

def outlines(ax, secs, skip=("Gripper", "Ball"), col=C_BASE, lw=0.6, xf=None):
    for n, ws in secs.items():
        if n.startswith(skip):
            continue
        for w in ws:
            xs = [p[0] for p in w]; ys = [p[1] for p in w]
            if xf: xs = [xf(x) for x in xs]
            ax.plot(xs, ys, color=col, lw=lw)

fig = plt.figure(figsize=(17, 17))
fig.suptitle("Beetle passive shield (2D, to scale) – stops a Wasp before its stinger can reach", fontsize=17, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.935, "Two rigid side plates on the gripper's pivot mounts (no gripper arms), a low blade 16 mm ahead of the body. "
         "The blade sits BELOW the stinger (z 7.5–13 vs 14.3–30.3),\nso a Wasp is stopped by its own wall tips on the blade and its fired ram ends "
         f"{CAP_IN - BODY_R:.1f} mm short of the Beetle's body outline. No moving parts.", fontsize=12, color="#333")

# ---------------- side view ----------------
ax = fig.add_axes([0.04, 0.49, 0.92, 0.39])
outlines(ax, A["side"]["23.0"])
ax.axhline(0, color="k", lw=1.5)
plate_patches(ax)
# blade (at y 0, dashed)
ax.add_patch(Rectangle((BLADE_X1 - BLADE_T, TOE_Z0), BLADE_T, TOE_Z1 - TOE_Z0, fc="none", ec=C_SH_E, ls="--", lw=1))
ax.add_patch(Circle((BLADE_X1 - BLADE_T / 2, (TOE_Z0 + TOE_Z1) / 2), 1.6, fc="white", ec="k", lw=0.6))
# Wasp, head-on: its section on the ram axis, mirrored to face -x, fired
xf = lambda x: WASP_CX - x
outlines(ax, R["side"]["-2.8"], col=C_W, lw=0.6, xf=xf)
ax.add_patch(Rectangle((CAP_IN, W_CAP_Z[0]), 6.0, W_CAP_Z[1] - W_CAP_Z[0], fc=C_W, alpha=0.35, ec=C_W))
ax.add_patch(Rectangle((CAP_IN + 6.0, 17.3), 13.1, 10, fc=C_W, alpha=0.2, ec=C_W))
ax.text(CAP_IN + 10, 33, "Wasp, fired\n(its ram axis)", color="#1f5d99", fontsize=11)
ax.axvline(BODY_R, color="#999", lw=0.8, ls=":"); ax.text(BODY_R - 0.3, 47.5, "Beetle body\noutline 40.6", fontsize=9, color="#666", ha="right")
ax.annotate("", xy=(BODY_R, 24), xytext=(CAP_IN, 24), arrowprops=dict(arrowstyle="<->", color="#c62828", lw=1.5))
ax.text((BODY_R + CAP_IN) / 2, 25, f"{CAP_IN - BODY_R:.1f} gap", color="#c62828", ha="center", fontsize=11, fontweight="bold")
ax.annotate("", xy=(BLADE_X1, 4.0), xytext=(BODY_R, 4.0), arrowprops=dict(arrowstyle="<->", color=C_SH_E, lw=1.2))
ax.text((BLADE_X1 + BODY_R) / 2, 2.0, "16 standoff", color=C_SH_E, ha="center", fontsize=10)
ax.axhspan(W_CAP_Z[0], W_CAP_Z[1], xmin=0.0, xmax=1.0, color=C_W, alpha=0.05)
ax.text(-18, 15, "stinger height band z 14.3–30.3", color=C_W, fontsize=9)
# labels
ax.annotate("pivot end as the hoop arm\n(R: on the pivot screw + bushing;\nL: on the servo horn, 2 screws)", xy=PIV, xytext=(-18, 52), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("front foot on the board top,\nright above the chassis wall:\ntakes the push from the blade", xy=(30.5, PCB_TOP), xytext=(12, 47), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("tail on the board top:\nstops the blade lifting", xy=(3.5, PCB_TOP + 1), xytext=(-18, 22), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("leg 1.0 ahead of the board edge\nand the wall", xy=(LEG_X0, 20), xytext=(15, 3.2), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax.annotate("blade 4 × 5.5 between the toes,\nM3 through-bolt (as the gripper's front bar)", xy=(BLADE_X1 - 2, 10.25), xytext=(56, 40), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="#666"))
ax.set_title("SIDE VIEW – section through the left plate (y +23); Wasp head-on (its section on the ram axis), fired", fontsize=13, fontweight="bold", loc="left")
ax.set_xlim(-20, 105); ax.set_ylim(-1, 58); ax.set_aspect("equal")
ax.grid(True, lw=0.25, color="#ddd"); ax.set_xlabel("x (mm, forward)"); ax.set_ylabel("z (mm)")

# ---------------- top view ----------------
ax2 = fig.add_axes([0.04, 0.05, 0.92, 0.40])
outlines(ax2, LO["top"]["11.0"])
th = [math.radians(a) for a in range(0, 361, 2)]
ax2.plot([BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color="#999", ls=":", lw=0.8)
for s in (1, -1):
    y0, y1 = sorted((s * PL_Y[0], s * PL_Y[1]))
    ax2.add_patch(Rectangle((LEG_X0, y0), BLADE_X1 - LEG_X0, y1 - y0, fc=C_SH, ec=C_SH_E))
ax2.add_patch(Rectangle((BLADE_X1 - BLADE_T, -PL_Y[0]), BLADE_T, 2 * PL_Y[0], fc=C_SH, ec=C_SH_E))
ax2.plot([BLADE_X1 - BLADE_T / 2] * 2, [-PL_Y[1] - 1.5, PL_Y[1] + 1.5], color="k", lw=1.2)
# Wasp outline at z 11 (its base), mirrored, + its ram (z 22) dashed
outlines(ax2, {n: [[(WASP_CX - p[0], -p[1]) for p in w] for w in ws] for n, ws in R["top"]["17.5"].items() if "Chassis" in n}, col=C_W, lw=0.9)
ax2.plot([WASP_CX + BODY_R * math.cos(t) for t in th], [BODY_R * math.sin(t) for t in th], color=C_W, ls=":", lw=0.6)
ax2.add_patch(Rectangle((CAP_IN, 2.8 - 8), WASP_CX - 18.5 - CAP_IN, 16, fc="none", ec=C_W, ls="--", lw=1.2))
ax2.text(WASP_CX - 5, 0, "Wasp", color="#1f5d99", fontsize=12, ha="center")
ax2.annotate("its wall tips rest on the blade", xy=(BLADE_X1, 20.5), xytext=(70, 45), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate(f"fired ram (z 14–30, passes over the blade):\nface at x {CAP_IN:.1f}, {CAP_IN - BODY_R:.1f} outside the Beetle", xy=(CAP_IN, 6), xytext=(55, -48),
             fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.annotate("blade 49.5 wide: a Wasp up to ±4.5 off-centre rests on\nboth tips, up to ±45 on one tip (the plates take the rest)",
             xy=(BLADE_X1 - 2, -15), xytext=(-40, -50), fontsize=10, arrowprops=dict(arrowstyle="-", color="#666"))
ax2.set_title("TOP VIEW – section at z 11 (Beetle base) with the shield; Wasp head-on (its chassis at z 17.5, ram dashed)", fontsize=13, fontweight="bold", loc="left")
ax2.set_xlim(-45, 140); ax2.set_ylim(-55, 55); ax2.set_aspect("equal")
ax2.grid(True, lw=0.25, color="#ddd"); ax2.set_xlabel("x (mm)"); ax2.set_ylabel("y (mm)")
fig.text(0.04, 0.012, "Print: plates flat (like the hoop arms), blade on its long face; PETG. Servo stays fitted but unpowered: "
         "the feet and tail set the angle. Only the front is shielded – the sides and back are open to stings and backstabs.",
         fontsize=10.5, color="#222")
plt.savefig(OUT, dpi=105)
print("saved", OUT, "Wasp cap face", round(CAP_IN, 2))
