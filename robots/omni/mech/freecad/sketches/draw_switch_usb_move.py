# 2D (to scale): where the power switch and the USB-C can go without hitting anything in any style.
# Clear angles from a sweep of each part's envelope (+0.5 mm) against every part of all six styles (exported from FreeCAD,
# 2026-10-24) plus the planned kicker capacitor; each wall slot also checked against everything but the wall.
#   C:/Python312/python.exe mech/freecad/sketches/draw_switch_usb_move.py   -> sketches/switch_usb_move_v1.png
import os, math, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, Rectangle, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "switch_usb_move_v1.png")
FREE_SMALL = [(38, 40), (62, 78), (102, 116), (150, 160), (182, 210), (234, 248), (272, 280), (302, 322)]
FREE_USB = [(68, 78), (102, 114), (150, 156), (188, 210), (234, 248), (272, 276), (308, 316)]
R_IN, R_OUT = 38.8, 40.6
WHEELS, POSTS = (40, 160, 280), (90, 138, 222, 260)
SW_ANG, USB_ANG, USB_OLD = 237, 199, 300
BT1 = (-32.95, -14.65, -21.47, 21.47)


def frame(ang):
    a = math.radians(ang); u = (math.cos(a), math.sin(a)); v = (-math.sin(a), math.cos(a))
    return lambda t, r: (r * u[0] + t * v[0], r * u[1] + t * v[1])


def poly(ax, ang, pts, **kw):
    P = frame(ang); ax.add_patch(Polygon([P(t, r) for t, r in pts], closed=True, **kw))


fig = plt.figure(figsize=(17, 8.6))
a = fig.add_axes([0.02, 0.10, 0.40, 0.80]); b = fig.add_axes([0.44, 0.10, 0.36, 0.80]); n = fig.add_axes([0.80, 0.08, 0.20, 0.84]); n.axis("off")

# ---- ring map of clear angles
a.set_title("Clear angles round the wall (all six styles)", fontsize=11)
a.add_patch(Circle((0, 0), R_OUT, fc="#f4f4f0", ec="k", lw=0.8))
for lo, hi in FREE_SMALL:
    a.add_patch(Wedge((0, 0), 46, lo - 1, hi + 1, width=3.0, fc="#3a9a4a", ec="none"))
for lo, hi in FREE_USB:
    a.add_patch(Wedge((0, 0), 50, lo - 1, hi + 1, width=3.0, fc="#3a6ad0", ec="none"))
a.add_patch(Wedge((0, 0), 54, 0, 360, width=3.0, fc="#e04040", ec="none", alpha=0.35))
for w in WHEELS:
    P = frame(w); a.add_patch(Rectangle((P(-6, 33)[0] - 0, P(-6, 33)[1]), 0, 0)); a.add_patch(Circle(P(0, 37), 5.0, fc="#555", ec="k"))
    a.text(*P(0, 37), "wheel", color="w", ha="center", va="center", fontsize=7)
for p in POSTS:
    a.add_patch(Circle(frame(p)(0, 36), 2.5, fc="#999", ec="k", lw=0.6))
for ang, txt, col in ((SW_ANG, "switch\n237 (stays)", "#2a7a3a"), (USB_ANG, "USB-C\nnew 199", "#2a4aa0"), (USB_OLD, "USB-C\nold 300", "#b00000")):
    P = frame(ang); a.plot(*zip(P(0, 30), P(0, 58)), color=col, lw=1.6, ls="--" if ang == USB_OLD else "-")
    a.text(*P(0, 62.5), txt, color=col, ha="center", va="center", fontsize=8.5, weight="bold")
a.text(0, 0, "front = 0 deg (+X)\nkicker / ball end", ha="center", va="center", fontsize=8)
a.annotate("", (16, 0), (6, 0), arrowprops=dict(arrowstyle="->"))
a.text(-62, -60, "rings, outside in:  red = SS-12D11 switch: clear nowhere   blue = USB-C clear   green = small switch clear",
       fontsize=8)
a.set_xlim(-66, 66); a.set_ylim(-64, 66); a.set_aspect("equal"); a.axis("off")

# ---- the rear-left quarter, to scale
b.set_title("Rear-left quarter from above (mm): the proposed places", fontsize=11)
b.add_patch(Wedge((0, 0), R_OUT, 170, 270, width=R_OUT - R_IN, fc="#d9d9d4", ec="k", lw=0.6))
b.add_patch(Rectangle((BT1[0], BT1[2]), BT1[1] - BT1[0], BT1[3] - BT1[2], fc="#9ab4d8", ec="k", lw=0.6, alpha=0.5))
b.text(-24, 0, "battery holder BT1\n(on top)", ha="center", fontsize=8)
for p in (222, 260, 138):
    b.add_patch(Circle(frame(p)(0, 36), 2.5, fc="#999", ec="k", lw=0.6)); b.add_patch(Circle(frame(p)(0, 36), 1.15, fc="white", ec="k", lw=0.4))
b.add_patch(Circle((-11.5, -15.5), 2.8, fc="#b9a6d8", ec="k", lw=0.6)); b.text(-8.4, -15.0, "deck standoff", fontsize=7)
# USB-C at 199: receptacle 8.94 x 7.3 under the PCB, mouth at the wall's outside; new slot 13.2 wide
poly(b, USB_ANG, [(-6.6, R_IN - 1.0), (6.6, R_IN - 1.0), (6.6, R_OUT + 0.3), (-6.6, R_OUT + 0.3)], fc="white", ec="#2a4aa0", lw=1.0, ls="--")
poly(b, USB_ANG, [(-4.47, R_OUT - 7.3), (4.47, R_OUT - 7.3), (4.47, R_OUT), (-4.47, R_OUT)], fc="#3a6ad0", ec="k", lw=0.8, alpha=0.9)
P = frame(USB_ANG); b.text(*P(0, 30.0), "USB-C\n(underside)", ha="center", va="center", fontsize=8, color="#2a4aa0")
b.annotate("new slot 13.2 x 5.2\n(old one at 300 is filled)", P(6.6, 40.0), (-45, 12), fontsize=8, arrowprops=dict(arrowstyle="->"))
# switch at 237: MSK12C02G25 under the PCB, handle in the existing slot (7.8 wide)
poly(b, SW_ANG, [(-3.9, R_IN - 1.0), (3.9, R_IN - 1.0), (3.9, R_OUT + 0.3), (-3.9, R_OUT + 0.3)], fc="white", ec="#2a7a3a", lw=1.0, ls="--")
poly(b, SW_ANG, [(-3.35, 34.1), (3.35, 34.1), (3.35, 37.0), (-3.35, 37.0)], fc="#3a9a4a", ec="k", lw=0.8)
poly(b, SW_ANG, [(-0.7, 37.0), (0.7, 37.0), (0.7, 39.5), (-0.7, 39.5)], fc="#2a7a3a", ec="k", lw=0.8)
P = frame(SW_ANG)
b.annotate("power switch MSK12C02G25\n(handle in the existing slot)\n+ SI2333 FET nearby", P(0, 35.5), (-44, -46), fontsize=8,
           arrowprops=dict(arrowstyle="->"))
b.set_xlim(-46, 2); b.set_ylim(-47, 18); b.set_aspect("equal"); b.grid(alpha=0.25)

n.text(0, 1, "\n".join([
    "Proposal",
    "",
    "USB-C: 300 -> 199 deg",
    "  (rear left; the old place",
    "  hits wheel 3's encoder",
    "  board). Chassis: usb_ang",
    "  199, the 300 slot closes.",
    "",
    "Power switch: stays at",
    "  237 deg, existing slot,",
    "  but as a small SMD",
    "  MSK12C02G25 (C22435663)",
    "  driving an SI2333 high-",
    "  side FET: the SS-12D11",
    "  (and the C&K) collide",
    "  at every angle - the",
    "  battery holder, the deck",
    "  standoffs, the posts and",
    "  the style modules leave",
    "  no 14 x 16 mm gap.",
    "",
    "Both on the rear-left,",
    "away from the kicker and",
    "the gripper; 40 deg apart.",
    "",
    "Checked: envelope + 0.5 mm",
    "vs every part of all six",
    "styles + the planned 330 uF",
    "capacitor; each slot vs",
    "everything but the wall.",
]), va="top", fontsize=9, family="monospace")
fig.suptitle("Power switch and USB-C: places that do not collide (concept v1, to scale)", fontsize=14, weight="bold")
fig.savefig(OUT, dpi=110); print(OUT)
