# 2D (to scale): why v1 (SS-12D11G5R at the old slot, 237 deg) does not fit once placed, and two ways out.
# Robot frame from above (X, Y mm). Clearances measured in FreeCAD with SW1 placed on the KiCad board (2026-10-24).
#   C:/Python312/python.exe mech/freecad/sketches/draw_power_switch_v2.py   -> sketches/power_switch_v2.png
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "power_switch_v2.png")
R_IN, R_OUT, SLOT_W = 38.8, 40.6, 7.8
BT1 = (-32.95, -14.65, -21.47, 21.47)                   # battery holder body (top side)
H7, H7_R = (-11.5, -15.5), 2.8                           # deck standoff (top side), 5.6 across
POSTS = [(36 * math.cos(math.radians(a)), 36 * math.sin(math.radians(a))) for a in (222, 260)]   # PCB posts (under), ~2.5 r


def frame(ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    return lambda t, r: (r * u[0] + t * v[0], r * u[1] + t * v[1])


def poly(ax, P, pts, **kw):
    ax.add_patch(Polygon([P(t, r) for t, r in pts], closed=True, **kw))


def ss12(ax, ang, col, alpha=0.85):                      # SS-12D11G5R: body centre r 29.75; tabs r 31.32; pins r 22.12
    P = frame(ang)
    poly(ax, P, [(-6.75, 26.6), (6.75, 26.6), (6.75, 32.9), (-6.75, 32.9)], fc=col, ec="k", lw=0.8, alpha=alpha)
    poly(ax, P, [(-1.2, 32.9), (1.2, 32.9), (1.2, 37.9), (-1.2, 37.9)], fc=col, ec="k", lw=0.8)
    for t in (-4.8, 0, 4.8):
        ax.add_patch(Circle(P(t, 22.12), 1.3, fc="#c8a040", ec="k", lw=0.6))
    for t in (-6.645, 6.645):
        ax.add_patch(Circle(P(t, 31.32), 1.2, fc="#c8a040", ec="k", lw=0.6))


def msk(ax, ang):                                         # MSK12C02G25: handle tip r 39.5 (in the slot), pads behind
    P = frame(ang)
    poly(ax, P, [(-3.35, 34.1), (3.35, 34.1), (3.35, 37.0), (-3.35, 37.0)], fc="#3a9a4a", ec="k", lw=0.8)
    poly(ax, P, [(-0.7, 37.0), (0.7, 37.0), (0.7, 39.5), (-0.7, 39.5)], fc="#2a7a3a", ec="k", lw=0.8)
    for t in (-2.25, -0.75, 2.25):
        poly(ax, P, [(t - 0.3, 33.7), (t + 0.3, 33.7), (t + 0.3, 34.7), (t - 0.3, 34.7)], fc="#c8a040", ec="k", lw=0.4)


def scene(ax, slot_ang, title):
    ax.set_title(title, fontsize=10.5)
    for a0 in (slot_ang,):
        th = math.degrees(SLOT_W / 2 / R_IN)
        ax.add_patch(Wedge((0, 0), R_OUT, 205, a0 - th, width=R_OUT - R_IN, fc="#d9d9d4", ec="k", lw=0.6))
        ax.add_patch(Wedge((0, 0), R_OUT, a0 + th, 285, width=R_OUT - R_IN, fc="#d9d9d4", ec="k", lw=0.6))
        P = frame(a0); ax.text(*P(0, 43.0), f"slot {a0} deg", ha="center", fontsize=8)
    ax.add_patch(Rectangle((BT1[0], BT1[2]), BT1[1] - BT1[0], BT1[3] - BT1[2], fc="#9ab4d8", ec="k", lw=0.8, alpha=0.6))
    ax.text(-24, -12, "battery holder\nBT1 (on top)", ha="center", fontsize=8)
    ax.add_patch(Circle(H7, H7_R, fc="#b9a6d8", ec="k", lw=0.8, alpha=0.8)); ax.text(H7[0] + 3.0, H7[1] + 0.6, "deck standoff\n(on top)", fontsize=7.5)
    for p in POSTS:
        ax.add_patch(Circle(p, 2.5, fc="#999", ec="k", lw=0.6)); ax.add_patch(Circle(p, 1.15, fc="white", ec="k", lw=0.4))
    ax.text(POSTS[1][0] + 2.8, POSTS[1][1] - 1.0, "PCB post", fontsize=7.5)
    ax.set_xlim(-34, 2); ax.set_ylim(-46, 0); ax.set_aspect("equal"); ax.grid(alpha=0.25)


fig, axs = plt.subplots(1, 3, figsize=(18, 8.2))
scene(axs[0], 237, "v1 as placed: SS-12D11G5R at 237 deg")
ss12(axs[0], 237, "#e04040", 0.6)
axs[0].annotate("pin 1 under the battery holder\n(0.45 mm^3 overlap)", frame(237)(-4.8, 22.12), (-33.5, -1.0), fontsize=8.5, va="top",
                color="#b00000", arrowprops=dict(arrowstyle="->", color="#b00000"))
axs[0].annotate("pin 2 touches the\ndeck standoff", frame(237)(0, 22.12), (-12.0, -1.0), fontsize=8.5, va="top", color="#b00000",
                arrowprops=dict(arrowstyle="->", color="#b00000"))
scene(axs[1], 244, "A: the same switch, slot turned to 244 deg")
ss12(axs[1], 244, "#e8742a")
P = frame(244)
axs[1].annotate("pin 1: 0.17 to the holder and\n0.22 to the standoff: its pad sits\nhalf under the standoff -> the\nstandoff needs a notch", P(-4.8, 22.12),
                (-33.5, -1.0), fontsize=8, va="top", arrowprops=dict(arrowstyle="->"))
axs[1].annotate("+ the chassis slot moves 7 deg", P(0, 39.7), (-31, -44.5), fontsize=8, arrowprops=dict(arrowstyle="->"))
scene(axs[2], 237, "B: small switch + a P-FET (slot unchanged)")
msk(axs[2], 237)
P = frame(237)
axs[2].annotate("MSK12C02G25 (6.7 x 2.9, SMD, 2.5 handle)\nits handle stands in the wall slot:\nnothing goes through the board,\nclear of the holder, standoff and posts",
                P(0, 36), (-33.5, -1.0), fontsize=8, va="top", arrowprops=dict(arrowstyle="->"))
fig.text(0.68, 0.012, "\n".join([
    "B, the circuit: SI2333 (28 mOhm, 6.5 A) high-side after the polarity FET; 100 k gate-source keeps it off;",
    "the switch pulls the gate to GND = on (42 uA while on, 0 off). The switch never carries the motor current.",
    "Cost: MSK12C02G25 C22435663 $0.04 + SI2333 $0.06 + 100k  vs  A: SS-12D11G5R $0.50 (+ chassis and standoff edits)",
]), fontsize=8.6, family="monospace", ha="center")
fig.suptitle("Power switch v2: v1 collides once placed. A = turn the slot 7 deg and notch a standoff; B = small switch + FET",
             fontsize=13, weight="bold")
fig.tight_layout(rect=(0, 0.11, 1, 0.95)); fig.savefig(OUT, dpi=110); print(OUT)
