# 2D (to scale): the NFC flex-ring antenna. A JLC 2-layer flex PCB glued flat to the floor underside: a 3-turn loop
# 0.3 mm in from the body edge (round the ball notch too), a tail at 128 deg between two wheel windows, and a round
# FR4-stiffened end that drops into the old 22 mm coil pocket with the same JST-SH 2 and clamps.
# usage: python draw_nfc_flex_ring.py floor_slice.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, Circle, Polygon as MPoly
from shapely.geometry import Polygon, LineString, Point
D = json.load(open(sys.argv[1])); OUT = sys.argv[2]
ws = D["chassis"]["7.9"]; outer = max(ws, key=lambda w: Polygon(w).area); O = Polygon(outer)
holes = [w for w in ws if w is not outer]
EDGE, BAND = 0.3, 1.2                      # flex outer edge in from the body edge; band width (3 x 0.2 traces, 0.15 gaps, 0.15 edges)
TR = [EDGE + 0.15 + 0.1 + k * 0.35 for k in range(3)]   # trace centre-lines (in from the edge)
TAIL_A, TAIL_W, DISC_D = 128.0, 2.2, 21.6
CLAMP_R, CLAMP_A1 = 12.2, 36.0
fig = plt.figure(figsize=(16, 10.5))
ax = fig.add_axes([0.02, 0.06, 0.58, 0.84])
def patch(a, wires, fc, ec, al, lw=0.6, z=1):
    v, c = [], []
    for w in wires: v += list(w) + [w[0]]; c += [Path.MOVETO] + [Path.LINETO] * (len(w) - 1) + [Path.CLOSEPOLY]
    a.add_patch(PathPatch(Path(v, c), fc=fc, ec=ec, alpha=al, lw=lw, zorder=z))
def draw_plan(a):
    patch(a, ws, "#d6d6cc", "#555", 1)
    for nm, zz in D["low"].items():
        if any(k in nm for k in ("DriveUnit", "Roller")):
            for z, w in zz.items(): patch(a, w, "#e57373", "none", 0.18)
    # flex band (polyimide, yellow coverlay)
    band = O.buffer(-EDGE).difference(O.buffer(-EDGE - BAND))
    tail = LineString([(0, 0), (39 * math.cos(math.radians(TAIL_A)), 39 * math.sin(math.radians(TAIL_A)))]).buffer(TAIL_W / 2, cap_style=2)
    tail = tail.difference(Point(0, 0).buffer(DISC_D / 2 - 0.5)).intersection(O.buffer(-EDGE - 0.5))
    flex = band.union(tail).union(Point(0, 0).buffer(DISC_D / 2))
    for g in getattr(flex, "geoms", [flex]):
        patch(a, [list(g.exterior.coords)] + [list(i.coords) for i in g.interiors], "#f2c14e", "#b8860b", 0.85, 0.8, 3)
    for d in TR:
        x, y = O.buffer(-d).exterior.xy; a.plot(x, y, color="#b45309", lw=0.9, zorder=4)
    a.add_patch(Circle((0, 0), DISC_D / 2, fc="#8d6e63", ec="#4e342e", alpha=0.55, zorder=4))
    a.add_patch(Rectangle((-3.25, -2.95), 6.5, 5.9, fc="#fafafa", ec="#222", lw=1, zorder=5))
    a.text(0, 0, "JST-SH 2\n(up)", ha="center", va="center", fontsize=6.5, zorder=6)
    for k in range(3):
        ang = math.radians(CLAMP_A1 + 120 * k)
        a.add_patch(Circle((CLAMP_R * math.cos(ang), CLAMP_R * math.sin(ang)), 1.9, fc="#bdbdbd", ec="#424242", zorder=6))
    # reader board above (dashed)
    c, s = math.cos(math.radians(117)), math.sin(math.radians(117))
    pts = [(-8.5 + u * c - v * s, 19.5 + u * s + v * c) for u, v in ((-14, -9), (14, -9), (14, 9), (-14, 9))]
    a.add_patch(MPoly(pts, closed=True, fc="none", ec="#1565c0", lw=1.4, ls="--", zorder=7))
draw_plan(ax)
ax.text(-8.5, 30.5, "reader board (above, unchanged)", color="#1565c0", fontsize=8, ha="center", zorder=8)
tx, ty = 25 * math.cos(math.radians(TAIL_A)), 25 * math.sin(math.radians(TAIL_A))
ax.annotate("tail: 2 traces (go + return)\n2.2 wide, 4.3 mm clear of the\nscrew holes and windows", (tx, ty), (-44, 38), fontsize=8, arrowprops=dict(arrowstyle="->"), zorder=9)
ax.annotate("3-turn loop, 1.2 wide,\n0.3 in from the edge", (O.buffer(-0.9).exterior.coords[0][0], O.buffer(-0.9).exterior.coords[0][1]), (26, 40), fontsize=8, arrowprops=dict(arrowstyle="->"), zorder=9)
ax.annotate("follows the ball notch", (29, 9), (16, 2), fontsize=8, arrowprops=dict(arrowstyle="->"), zorder=9)
ax.annotate("round end, FR4 stiffener 0.8,\nØ21.6 in the old 22.4 coil pocket;\nsame JST-SH 2 + 3 nylon clamps", (-5, -8), (-44, -44), fontsize=8, arrowprops=dict(arrowstyle="->"), zorder=9)
ax.set_aspect("equal"); ax.set_xlim(-46, 46); ax.set_ylim(-47, 46); ax.grid(alpha=0.25)
ax.set_title("Plan, looking down through the floor (front = right). 1 grid = 10 mm", fontsize=10)
# detail: the tightest corner (window corner at the left, 1.76 mm rim)
win = [Polygon(w) for w in holes if Polygon(w).area > 300]
cw = min(win, key=lambda p: p.exterior.distance(O.exterior))
pc = min((Point(p) for p in cw.exterior.coords), key=lambda p: p.distance(O.exterior))
ax2 = fig.add_axes([0.61, 0.50, 0.37, 0.40]); draw_plan(ax2)
ax2.set_xlim(pc.x - 4, pc.x + 4); ax2.set_ylim(pc.y - 3, pc.y + 3); ax2.set_aspect("equal"); ax2.grid(alpha=0.3)
ax2.set_title("Detail: tightest spot, a wheel-window corner (8 x 6 mm)", fontsize=10)
gap_in = cw.exterior.distance(O.buffer(-EDGE - BAND).exterior) if not cw.intersects(O.buffer(-EDGE - BAND).exterior) else 0
ax2.text(pc.x - 3.8, pc.y - 2.7, f"rim here {cw.exterior.distance(O.exterior):.2f} mm = the wall\nflex band {BAND} + {EDGE} to the outside\n-> {cw.exterior.distance(O.exterior) - EDGE - BAND:.2f} mm left to the window edge", fontsize=8, bbox=dict(fc="white", ec="#999"))
# section + spec
ax3 = fig.add_axes([0.61, 0.06, 0.37, 0.38]); ax3.axis("off")
spec = [
 "Stack at the rim: wall 1.8 wide, floor plate 1.6, flex 0.12",
 "glued under it, then 6.5 mm down to the floor / tags",
 "",
 "Flex PCB (JLC, 2-layer, 25 µm PI, 1 oz copper, yellow coverlay):",
 "  - loop: 3 turns, 0.20 mm traces, 0.15 mm gaps, on the top layer",
 "    (inner end crosses back to the tail on the bottom layer via 2 vias)",
 "  - outline: the floor outline 0.3 in, 1.2 wide, plus tail + Ø21.6 end",
 "    -> one piece, about 81 x 80 mm (fits JLC's 100 x 100 promo size)",
 "  - end: FR4 stiffener 0.8 (= the old coil board), JST-SH 2 SM02B-SRSS-TB",
 "    JLC-assembled; plugs into the existing 100 mm cable to the reader",
 "  - fixing: thin double-sided tape along the ring; the 3 nylon clamps",
 "    hold the end. No chassis change: the old pocket, JST opening and",
 "    clamps are reused as they are; the 22 mm coil board is dropped.",
 "",
 "Electrical (estimates - measure the first one):",
 "  - loop ~78 mm across; L ~2.7-3 µH (today's coil 2.08 µH): retune C6/C8/C9",
 "  - read zone: ~72 mm wide (now ~23 mm) once the centre has enough field",
 "  - centre field per amp is lower than today's small coil: model says",
 "    ~0.8x of the read limit at today's drive -> run the WS1850S TX a bit",
 "    harder or higher Q; test a hand-wound 3-turn wire loop on the reader",
 "    BEFORE ordering the flex to confirm",
]
ax3.text(0, 1, "\n".join(spec), va="top", fontsize=8.6, family="monospace")
fig.suptitle("NFC flex-ring antenna (JLC flex PCB) - 2D for approval, to scale", fontsize=15, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100)
print("saved", OUT)
