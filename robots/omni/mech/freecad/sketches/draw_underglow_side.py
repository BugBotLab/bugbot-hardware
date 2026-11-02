# 2D (to scale): underglow with SIDE-emitting LEDs (WS2812B-4020-V6, JLC C52941387) facing outwards, + white solder mask on
# the floor PCB. Plan view of the ring, and a section showing how the light reaches the rim through the 4.9 mm gap.
# Footprint from JLC/EasyEDA (easyeda2kicad): 4 pads in a row along the long side: 1 DIN -1.68, 2 VDD -0.43, 3 DOUT +0.60,
# 4 GND +1.68 (mm); body 4.0 x 1.7 x 1.7 tall; light from one long face, parallel to the board.
# usage: python draw_underglow_side.py floor_outline.json floor_geom.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle, FancyArrowPatch
from shapely.geometry import Polygon, Point
F = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2])); OUT = sys.argv[3]
N, R, A0 = 7, 9.0, 10.2
GAP_NFC = 135.4
xy = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
angs = [A0 + 360 / N * k for k in range(N)]
fig = plt.figure(figsize=(16, 9.6))
ax = fig.add_axes([0.02, 0.07, 0.5, 0.83])
O = Polygon(F["outer"])
x, y = O.exterior.xy; ax.fill(x, y, color="#f2f2ee", ec="#999", zorder=0)                     # white solder mask
for h in F["holes"]:
    P = Polygon(h)
    if P.area > 300 and not P.contains(Point(0, 0)): x, y = P.exterior.xy; ax.fill(x, y, color="#cfd8dc", zorder=1)
for c in G["clamps"]:
    ax.add_patch(Circle(c, 1.2, fc="white", ec="#111", lw=0.6, zorder=6)); ax.add_patch(Circle(c, 1.9, fc="none", ec="#999", ls=":", zorder=6))
x, y = zip(*G["spiral"]); ax.plot(x, y, color="#c9a227", lw=0.5, zorder=2)
for a in angs:
    cx, cy = xy(R, a); t = a + 90
    P_ = lambda u, v: (cx + u * math.cos(math.radians(t)) - v * math.sin(math.radians(t)), cy + u * math.sin(math.radians(t)) + v * math.cos(math.radians(t)))
    # body: v from -1.36 (inward) to +0.3 (lens face, outward)
    ax.add_patch(MPoly([P_(u, v) for u, v in ((-2.0, -1.36), (2.0, -1.36), (2.0, 0.3), (-2.0, 0.3))], closed=True, fc="#fafafa", ec="#222", lw=0.9, zorder=5))
    ax.plot(*zip(P_(-2.0, 0.3), P_(2.0, 0.3)), color="#1e88e5", lw=2.5, zorder=6)                # the lens face
    for pu, pw in ((-1.68, 0.9), (-0.43, 0.7), (0.60, 0.45), (1.68, 0.9)):
        ax.add_patch(MPoly([P_(pu + du, dv) for du, dv in ((-pw / 2, -0.65), (pw / 2, -0.65), (pw / 2, 0.65), (-pw / 2, 0.65))], closed=True, fc="#d4a017", alpha=0.7, zorder=6))
    for k_ in range(9):                                                                             # light, fanning outwards
        da = (k_ - 4) * 15
        p0 = P_(0, 0.3); d_ = (math.cos(math.radians(a + da)), math.sin(math.radians(a + da)))
        L_ = 30 - 0.8 * abs(k_ - 4) ** 1.6
        ax.plot([p0[0], p0[0] + d_[0] * L_], [p0[1], p0[1] + d_[1] * L_], color="#42a5f5", alpha=0.12, lw=3, zorder=3)
ax.add_patch(Rectangle((-3.44, -3.85), 6.88, 5.3, fc="#eeeeee", ec="#333", lw=0.8, zorder=5))
ax.set_aspect("equal"); ax.set_xlim(-44, 44); ax.set_ylim(-44, 44); ax.grid(alpha=0.2)
ax.set_title("Plan, looking down through the floor (front = right). White = white solder mask; blue edge = lens", fontsize=9.5)
ax.annotate(f"{N} x WS2812B-4020 side-view, r {R:g}, {360 / N:.1f} deg apart,\nlens facing OUT (blue): light runs to the rim", xy(R, A0), (14, 40), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate("NFC wires cross the ring in a gap\n(bottom copper), as before", xy(9, GAP_NFC), (-43, 40), fontsize=9, arrowprops=dict(arrowstyle="->"))
# section through one LED, radial
sx = fig.add_axes([0.55, 0.52, 0.43, 0.38]); Z = 4
sx.set_title("Section through one LED (heights x4): the light travels in the 4.9 mm gap to the rim", fontsize=9.5)
def bx(x0, x1, z0, z1, fc, ec="#333", **k): sx.add_patch(Rectangle((x0, z0 * Z), x1 - x0, (z1 - z0) * Z, fc=fc, ec=ec, lw=0.8, **k))
bx(0, 40.6, 6.5, 8.1, "#d6d6cc"); sx.text(20, 7.3 * Z, "printed floor plate", ha="center", fontsize=8)
bx(0, 40.6, 4.9, 6.5, "#2e7d32"); sx.text(20, 5.7 * Z, "floor PCB 1.6", ha="center", fontsize=8, color="white")
bx(0, 40.6, 4.86, 4.9, "#ffffff", ec="#999"); sx.text(30, 4.55 * Z, "white solder mask (underside)", fontsize=7.5, ha="center")
bx(R - 1.36, R + 0.3, 3.2, 4.86, "#fafafa"); sx.plot([R + 0.3, R + 0.3], [3.2 * Z, 4.86 * Z], color="#1e88e5", lw=3)
sx.text(R - 0.5, 2.5 * Z, "LED 1.7 tall\n(3.2 mm to the table)", fontsize=7.5, ha="center")
bx(40.6 - 1.8, 40.6, 6.5, 12, "#d6d6cc"); sx.text(40.0, 11 * Z, "wall", fontsize=7.5, ha="center")
sx.axhline(0, color="#795548", lw=2); sx.text(1, 0.4, "table", fontsize=8)
for zz, col in ((4.0, "#1e88e5"),):
    for k_ in range(6):
        pts = [(R + 0.3, zz)]; up = True; xx, z_ = R + 0.3, zz
        slope = 0.12 + 0.07 * k_
        while xx < 40.6:
            z1 = 4.86 if up else 0.0
            dx = abs(z1 - z_) / slope; xx = min(40.6 + 3, xx + dx); z_ = z1 if xx < 40.6 + 3 else z_ + (z1 - z_) * 0.5
            pts.append((xx, z_)); up = not up
        X_, Y_ = zip(*pts); sx.plot(X_, [y_ * Z for y_ in Y_], color=col, alpha=0.35, lw=1)
sx.annotate("light leaves under the rim\n(a translucent rim would glow)", (41.5, 2.4 * Z), (30, 9.5 * Z), fontsize=8, arrowprops=dict(arrowstyle="->"))
sx.set_xlim(0, 46); sx.set_ylim(-1, 13 * Z); sx.set_yticks([0, 3.2 * Z, 4.9 * Z, 6.5 * Z]); sx.set_yticklabels(["0", "3.2", "4.9", "6.5"]); sx.grid(alpha=0.2)
tx = fig.add_axes([0.55, 0.05, 0.43, 0.42]); tx.axis("off")
tx.text(0, 1, "\n".join([
 "What changes from the approved 7-LED ring:",
 "  - LED: WS2812B-2020-V6 (down) -> WS2812B-4020-V6 side-view",
 "    (JLC C52941387, Extended, ~9.4k in stock, ~$0.11), lens OUT",
 "  - ring r 8.5 -> 9.0 (the 4 mm LEDs need more ring; 7 still fit,",
 "    gaps ~2 mm for the NFC wires and the feed - to confirm in KiCad,",
 "    else 6 LEDs)",
 "  - floor PCB solder mask: green -> WHITE (both sides; same price at",
 "    JLC): board + table act as a light box carrying light outwards",
 "  - pads in a row: DIN, VDD, DOUT, GND -> data enters one end, leaves",
 "    the other; 5 V / GND lanes on top, 100 nF + vias per LED as before",
 "",
 "Light: it shines sideways along the gap instead of into the table",
 "under the middle, so most of it reaches the rim (estimate; a bench",
 "test with one LED under a white card will confirm).",
 "Lens face from the EasyEDA footprint (silk open side): check it",
 "against the datasheet drawing before ordering.",
 "",
 "Optional, later: print the bottom band of the body in translucent",
 "white PETG so the rim glows from any angle."]), va="top", fontsize=8.8, family="monospace")
fig.suptitle("Underglow v2: side-emitting LEDs facing out + white solder mask (2D for approval, to scale)", fontsize=14, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT)
