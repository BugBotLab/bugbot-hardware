# 2D (to scale): the underglow as a COMPLETE ring: 7 WS2812B-2020 on r 8.5, 51.4 deg apart, no empty slot.
#   - the NFC antenna's 2 wires drop to the bottom copper through 2 vias just outside the ring (r 12.6) and cross the
#     ring in the gap at 139 deg on the bottom, then run to their plated holes (they are no longer in the LEDs' way)
#   - the LED chain breaks in the gap at 293 deg, where the feed from J2 comes up (bottom) onto the top lanes
#   - per LED as before: 5 V / GND lanes + data on the top copper, LED + 100 nF + vias on the bottom
# usage: python draw_underglow_full_ring.py floor_outline.json floor_geom.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle
from shapely.geometry import Polygon, Point
F = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2])); OUT = sys.argv[3]
N, R, A0 = 7, 8.5, 10.2
GAP_NFC, GAP_FEED = 139.0, 293.0
xy = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
angs = [A0 + 360 / N * k for k in range(N)]
fig = plt.figure(figsize=(16, 9.5))
def board(a):
    O = Polygon(F["outer"])
    x, y = O.exterior.xy; a.fill(x, y, color="#2e7d32", alpha=0.85, zorder=0)
    for h in F["holes"]:
        P = Polygon(h)
        if P.area > 300 and not P.contains(Point(0, 0)): x, y = P.exterior.xy; a.fill(x, y, color="white", zorder=1)
    for c in G["clamps"]:
        a.add_patch(Circle(c, 1.2, fc="white", ec="#111", lw=0.6, zorder=6)); a.add_patch(Circle(c, 1.9, fc="none", ec="#999", lw=0.8, ls=":", zorder=6))
def ring(a, big):
    # top lanes + data: arcs from just after the feed gap round to just before it (counter-clockwise), never closed
    a_s, a_e = GAP_FEED + 3, GAP_FEED + 360 - 3
    for r_, c_, w_ in ((R + 0.9, "#555", 2.4), (R, "#64b5f6", 1.2), (R - 0.9, "#e53935", 2.4)):
        pts = [xy(r_, a_s + (a_e - a_s) * t / 300) for t in range(301)]; x, y = zip(*pts); a.plot(x, y, color=c_, lw=w_ if big else w_ / 2, alpha=0.8, zorder=3)
    for k, ang in enumerate(sorted(angs, key=lambda g: (g - GAP_FEED) % 360)):
        cx, cy = xy(R, ang); rot = ang + 90
        P = lambda u, v: (cx + u * math.cos(math.radians(rot)) - v * math.sin(math.radians(rot)), cy + u * math.sin(math.radians(rot)) + v * math.cos(math.radians(rot)))
        a.add_patch(MPoly([P(u, v) for u, v in ((-1.1, -1.0), (1.1, -1.0), (1.1, 1.0), (-1.1, 1.0))], closed=True, fc="#fafafa", ec="#222", lw=0.8, zorder=5))
        a.add_patch(MPoly([P(u, v) for u, v in ((-2.5, -0.5), (-2.0, -0.5), (-2.0, 0.5), (-2.5, 0.5))], closed=True, fc="#a1887f", ec="#333", lw=0.5, zorder=5))
        if big: a.text(cx, cy, str(k + 1), ha="center", va="center", fontsize=8, zorder=6)
    # feed (bottom): from J2's vias to the gap at 293 deg, up to the lane starts
    vias = [(-1.0, -3.75), (0.0, -3.75), (1.0, -3.75)]
    for (vx, vy), r_, c_ in zip(vias, (R + 0.9, R, R - 0.9), ("#555", "#64b5f6", "#e53935")):
        tgt = xy(r_, GAP_FEED + 3); mid = xy(r_ - 1.6, GAP_FEED)
        a.plot([vx, vx, mid[0], tgt[0]], [vy, vy - 1.0 - 0.6 * (vx + 1), mid[1], tgt[1]], color=c_, lw=1.4 if big else 0.8, ls=(0, (2, 1)), zorder=4)
        a.add_patch(Circle(tgt, 0.275, color=c_, zorder=7)); a.add_patch(Circle((vx, vy), 0.275, color=c_, zorder=7))
    # NFC wires: top down the tail to r 12.6, vias, then bottom across the ring in the 139 deg gap to the holes
    for side, hole in ((-1, G["wire_holes"][0]), (1, G["wire_holes"][1])):
        top_end = xy(12.6, 128 + side * 2.5)
        la = G["lead_a"] if side < 0 else G["lead_b"]
        tp = [p for p in la if math.hypot(*p) >= 12.6] + [top_end]
        x, y = zip(*tp); a.plot(x, y, color="#e0b040", lw=1.6 if big else 0.8, zorder=4)
        b1 = xy(10.6, GAP_NFC + side * 2.2); b2 = xy(6.4, GAP_NFC + side * 3.5)
        a.plot([top_end[0], b1[0], b2[0], hole[0]], [top_end[1], b1[1], b2[1], hole[1]], color="#e0b040", lw=1.6 if big else 0.8, ls=(0, (2, 1)), zorder=4)
        a.add_patch(Circle(top_end, 0.275, color="#b8860b", zorder=7))
        a.add_patch(Circle(hole, 0.8, fc="#e0b040", ec="#7a5c00", zorder=7)); a.add_patch(Circle(hole, 0.45, fc="white", zorder=8))
    a.add_patch(Rectangle((-3.44, -3.85), 6.88, 5.3, fc="#eeeeee", ec="#333", lw=0.8, zorder=5))
    a.add_patch(Rectangle((-3.8, -4.2), 7.6, 8.4, fc="none", ec="#c62828", lw=1.0, ls="--", zorder=6))
ax = fig.add_axes([0.02, 0.06, 0.55, 0.84]); board(ax); ring(ax, True)
ax.set_xlim(-16, 16); ax.set_ylim(-15, 17); ax.set_aspect("equal"); ax.grid(alpha=0.25)
ax.set_title("Centre of the floor PCB, looking down (front = right). Solid = top copper, dashed = bottom copper. 1 grid = 5 mm", fontsize=9.5)
ax.annotate("NFC wires: vias to the bottom at r 12.6,\ncross the ring in the 139 deg gap", xy(11.5, 136), (-15.5, 15.5), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.annotate("chain break + feed (bottom, from J2's\nvias) in the 293 deg gap", xy(8.5, 293), (4, -14.5), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.annotate("7 LEDs, r 8.5, 51.4 deg (7.6 mm) apart\n- a complete ring, no empty slot", xy(8.5, 10.2), (6.5, 14.5), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax2 = fig.add_axes([0.6, 0.48, 0.38, 0.42]); board(ax2); ring(ax2, False)
x, y = zip(*G["spiral"]); ax2.plot(x, y, color="#e0b040", lw=0.4)
ax2.set_xlim(-43, 43); ax2.set_ylim(-43, 43); ax2.set_aspect("equal"); ax2.set_xticks([]); ax2.set_yticks([]); ax2.set_title("whole floor PCB", fontsize=10)
tx = fig.add_axes([0.6, 0.04, 0.38, 0.4]); tx.axis("off")
tx.text(0, 1, "\n".join([
 "Why 7 and r 8.5 (not 8-9 at r 9.5):",
 "  - each LED's copper (LED, 100 nF, vias) takes ~5.6 mm of ring;",
 "    the NFC wires and the feed each need a ~1.6 mm gap between",
 "    two LEDs -> spacing >= ~7.2 mm",
 "  - at r 9.5 the LED copper reaches r 10.8 and the nylon screw",
 "    heads start at r 10.3: no even spacing misses all 3",
 "  - at r 8.5 everything stays inside r 9.8 (0.36 mm to the heads);",
 "    7 LEDs give 7.6 mm spacing, 2.0 mm gaps",
 "",
 "Changes from the board as built (8 of 9 slots at r 9.5):",
 "  - 7 LEDs instead of 8, evenly round the whole ring",
 "  - the NFC wires: top -> 2 vias at r 12.6 -> bottom to the holes",
 "  - the feed runs to the 293 deg gap instead of the 144 deg one",
 "  - J2, C13, the floor opening and the 3D parts as before",
 "",
 "Glow: ~17 mm ring of LEDs under the centre (as before)."]), va="top", fontsize=8.8, family="monospace")
fig.suptitle("Underglow: complete ring of 7 LEDs (2D for approval, to scale)", fontsize=15, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT)
