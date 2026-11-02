# 2D (to scale): the NFC antenna as a standard 1.6 mm PCB screwed under the printed floor ("PCB floor plate").
#   outline = the floor outline (flush), the three wheel windows and the ball notch cut out; the 3-turn loop round the
#   edge on the top copper (against the floor); two plated holes at the centre for the cable's wires (hand-soldered);
#   held by the 3 existing nylon clamp screws (M2 x 4 -> M2 x 5). No chassis change: the old pocket and opening stay.
# usage: python draw_nfc_floor_pcb.py floor_slice.json flex_geom.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, Circle
from shapely.geometry import Polygon, Point
D = json.load(open(sys.argv[1])); GEO = json.load(open(sys.argv[2])); OUT = sys.argv[3]
ws = D["chassis"]["6.7"]
outer = max(ws, key=lambda w: Polygon(w).area)
O = Polygon(outer)
wins = [Polygon(w) for w in ws if w is not outer and Polygon(w).area > 300 and not Polygon(w).contains(Point(0, 0))]
pcb = O
for w in wins: pcb = pcb.difference(w)
CLAMPS = [(12.2 * math.cos(math.radians(36 + 120 * k)), 12.2 * math.sin(math.radians(36 + 120 * k))) for k in range(3)]
fig = plt.figure(figsize=(16, 10))
def patch(a, wires, fc, ec, al, lw=0.6, z=1):
    v, c = [], []
    for w in wires: v += list(w) + [w[0]]; c += [Path.MOVETO] + [Path.LINETO] * (len(w) - 1) + [Path.CLOSEPOLY]
    a.add_patch(PathPatch(Path(v, c), fc=fc, ec=ec, alpha=al, lw=lw, zorder=z))
def plan(a):
    for nm, zz in D["low"].items():
        if nm.startswith("DriveUnit:"):
            for z, w in zz.items(): patch(a, w, "#e57373", "none", 0.25, z=0)
    for g in getattr(pcb, "geoms", [pcb]):
        patch(a, [list(g.exterior.coords)] + [list(i.coords) for i in g.interiors], "#2e7d32", "#1b5e20", 0.85, 0.8, 2)
    x, y = zip(*GEO["spiral"]); a.plot(x, y, color="#e0b040", lw=0.7, zorder=3)
    for k in ("lead_a", "lead_b"):
        pts = GEO[k] + [(-1.27 if k == "lead_a" else 1.27, 0.0)]
        x, y = zip(*pts); a.plot(x, y, color="#e0b040", lw=1.0, zorder=3)
    for c in CLAMPS:
        a.add_patch(Circle(c, 1.2, fc="white", ec="#111", lw=0.8, zorder=4))
    for px in (-1.27, 1.27):
        a.add_patch(Circle((px, 0), 0.8, fc="#e0b040", ec="#7a5c00", zorder=4)); a.add_patch(Circle((px, 0), 0.45, fc="white", zorder=5))
    a.add_patch(Rectangle((-3.25, -2.95), 6.5, 5.9, fc="none", ec="#1565c0", lw=1.2, ls="--", zorder=5))
    a.add_patch(Circle((0, 0), 11.2, fc="none", ec="#1565c0", lw=1.0, ls=":", zorder=5))
ax = fig.add_axes([0.02, 0.06, 0.56, 0.84]); plan(ax)
ax.set_xlim(-45, 45); ax.set_ylim(-45, 45); ax.set_aspect("equal"); ax.grid(alpha=0.25)
ax.set_title("Looking down through the floor (front = right). Green = the PCB, 1 grid = 10 mm", fontsize=10)
ax.annotate("3-turn loop on the top copper\n(against the floor), round the edge", (-30, -26.5), (-44, -43), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate("3 x nylon M2 x 5 into the existing bosses\n(were M2 x 4 on the old coil)", CLAMPS[2], (6, -43), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate("2 plated holes: the cable's wires,\nhand-soldered, up through the existing\npocket (dotted) and opening (dashed)", (1.27, 0), (14, 30), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate("wheel windows + ball notch\ncut out (same as the floor)", (37, 0), (22, -12), fontsize=9, color="#fff", arrowprops=dict(arrowstyle="->", color="#fff"))
# detail of the tightest rim
cw = min(wins, key=lambda p: p.exterior.distance(O.exterior))
pc = min((Point(p) for p in cw.exterior.coords), key=lambda p: p.distance(O.exterior))
ax2 = fig.add_axes([0.60, 0.50, 0.38, 0.40]); plan(ax2)
ax2.set_xlim(pc.x - 4, pc.x + 4); ax2.set_ylim(pc.y - 3, pc.y + 3); ax2.set_aspect("equal"); ax2.grid(alpha=0.3)
ax2.set_title("Detail: the narrowest rim (wheel-window corner)", fontsize=10)
ax2.text(pc.x - 3.8, pc.y - 2.7, f"PCB rim {cw.exterior.distance(O.exterior):.2f} mm: 3 traces 0.18 / 0.15\n= 0.84 copper + 0.3 to each edge", fontsize=8, bbox=dict(fc="white", ec="#999"))
tx = fig.add_axes([0.60, 0.05, 0.38, 0.40]); tx.axis("off")
spec = [
 "PCB floor plate (replaces the flex ring; JLC standard, no assembly):",
 "  - 2-layer FR4 1.6 mm, ~81 x 77 mm, HASL, green; bare board",
 "  - outline flush with the floor; wheel windows and ball notch",
 "    the same as the floor's; 3 holes 2.4 for the clamp screws",
 "  - loop: 3 turns 0.18 / 0.15 on the top copper, the same path as",
 "    the flex (L ~2.4 uH); bottom copper only the 1 crossover",
 "  - centre: 2 plated holes 0.9 (pads 1.6), 2.54 apart: the cable's",
 "    2 wires soldered in (cable: JST-SH 2 at the reader end only)",
 "  - bottom: solder mask, nothing else (smooth, hard surface)",
 "",
 "Fixing: the 3 existing nylon clamps, M2 x 4 -> M2 x 5 (head 1.6 lower;",
 "tip at 9.9, in the existing 10.7 pilots). Chassis: no change.",
 "",
 "Underneath: 1.6 mm below the floor -> 4.9 mm clearance (tabletop: fine).",
 "Weight: ~10 g (estimate). Read zone ~72 mm wide, as the flex.",
 "Still: test a hand-wound 3-turn loop on the reader first (centre field).",
]
tx.text(0, 1, "\n".join(spec), va="top", fontsize=8.8, family="monospace")
fig.suptitle("NFC antenna as a 1.6 mm PCB under the floor (2D for approval, to scale)", fontsize=15, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT, "pcb area", round(pcb.area), "mm2, bbox", [round(v, 1) for v in pcb.bounds])
