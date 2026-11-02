# 2D (to scale): the NFC flex antenna's end, v2 - a small tab instead of the 22 mm round end.
#   the tab carries the JST-SH 2 (same place and turn as before: up through the existing 6.5 x 5.9 opening) and one
#   nylon M2 x 4 into the existing clamp boss at 156 deg; FR4 0.2 stiffener UNDER the tab (no pocket needed).
#   chassis: the 22.4 coil pocket, the other two clamp bosses and their pilots are removed.
# usage: python draw_nfc_flex_tab.py floor_slice.json flex_geom.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, Circle, Polygon as MPoly
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
D = json.load(open(sys.argv[1])); GEO = json.load(open(sys.argv[2])); OUT = sys.argv[3]
ws = D["chassis"]["6.7"]
CLAMP_R, A1 = 12.2, 36.0
SCREW = (CLAMP_R * math.cos(math.radians(A1 + 120)), CLAMP_R * math.sin(math.radians(A1 + 120)))
TA = math.radians(128)
ux, uy = math.cos(TA), math.sin(TA); nx, ny = -uy, ux
CY = (2.945, 2.645)                                          # JST courtyard half sizes (rot 180, centred)
TAB_M, SCREW_R, NECK = 1.0, 2.6, 5.2
rect = Polygon([(-CY[0] - TAB_M, -CY[1] - TAB_M), (CY[0] + TAB_M, -CY[1] - TAB_M), (CY[0] + TAB_M, CY[1] + TAB_M), (-CY[0] - TAB_M, CY[1] + TAB_M)])
neck = LineString([(0, 0), SCREW]).buffer(NECK / 2, cap_style=2)
tail = Polygon([(r * ux + o * nx, r * uy + o * ny) for r, o in ((3.0, -1.3), (20, -1.3), (20, 1.3), (3.0, 1.3))])
tab = unary_union([rect, neck, Point(SCREW).buffer(SCREW_R, 64), tail]).buffer(0.5, 32).buffer(-1.0, 32).buffer(0.5, 32)
fig = plt.figure(figsize=(16, 10))
def patch(a, wires, fc, ec, al, lw=0.6, z=1, ls="-"):
    v, c = [], []
    for w in wires: v += list(w) + [w[0]]; c += [Path.MOVETO] + [Path.LINETO] * (len(w) - 1) + [Path.CLOSEPOLY]
    a.add_patch(PathPatch(Path(v, c), fc=fc, ec=ec, alpha=al, lw=lw, zorder=z, ls=ls))
def plan(a, detail):
    outer = max(ws, key=lambda w: Polygon(w).area)
    keep = [outer] + [w for w in ws if w is not outer and not Polygon(w).contains(Point(5, 5))]   # the coil pocket is filled now
    patch(a, keep, "#d6d6cc", "#555", 1)
    for nm, zz in D["low"].items():
        if nm.startswith("DriveUnit:"):                                                          # placed drive units only
            for z, w in zz.items(): patch(a, w, "#e57373", "none", 0.18)
    a.add_patch(Circle((0, 0), 11.2, fc="none", ec="#c62828", lw=1.5, ls="--", zorder=6))          # removed pocket
    for k in range(3):
        ang = math.radians(A1 + 120 * k); p = (CLAMP_R * math.cos(ang), CLAMP_R * math.sin(ang))
        if k == 1: continue
        a.add_patch(Circle(p, 1.8, fc="none", ec="#c62828", lw=1.5, ls="--", zorder=6))
        if detail: a.plot([p[0] - 1.3, p[0] + 1.3], [p[1] - 1.3, p[1] + 1.3], color="#c62828", lw=1.5, zorder=6); a.plot([p[0] - 1.3, p[0] + 1.3], [p[1] + 1.3, p[1] - 1.3], color="#c62828", lw=1.5, zorder=6)
    for ring in GEO["outline"][:1]:                                                                     # the flex ring (unchanged)
        pass
    flex_ring = Polygon(GEO["outline"][0], GEO["outline"][1:])
    ring_only = flex_ring.difference(Point(0, 0).buffer(11.3))
    new_flex = unary_union([ring_only, tab])
    for g in getattr(new_flex, "geoms", [new_flex]):
        patch(a, [list(g.exterior.coords)] + [list(i.coords) for i in g.interiors], "#f2c14e", "#b8860b", 0.85, 0.8, 3)
    x, y = zip(*GEO["lead_a"]); a.plot(x, y, color="#b45309", lw=1, zorder=4)
    x, y = zip(*GEO["lead_b"]); a.plot(x, y, color="#b45309", lw=1, zorder=4)
    qa = min(((-0.5, 1.325), (0.5, 1.325)), key=lambda t: math.dist(t, GEO["lead_a"][-1])); qb = (-qa[0], qa[1])
    for lead, q in ((GEO["lead_a"], qa), (GEO["lead_b"], qb)):
        a.plot([lead[-1][0], q[0]], [lead[-1][1], q[1]], color="#b45309", lw=1, zorder=7)
    a.add_patch(Rectangle((-3.25, -2.95), 6.5, 5.9, fc="#ffffff", ec="#222", lw=1.2, zorder=5))
    a.add_patch(Rectangle((-CY[0], -CY[1]), 2 * CY[0], 2 * CY[1], fc="#eeeeee", ec="#666", lw=0.8, zorder=5))
    for px in (-0.5, 0.5): a.add_patch(Rectangle((px - 0.3, 1.325 - 0.775), 0.6, 1.55, fc="#d4a017", ec="none", zorder=6))
    a.add_patch(Circle(SCREW, 1.9, fc="#bdbdbd", ec="#424242", zorder=7))
    a.add_patch(Circle(SCREW, 0.8, fc="#424242", zorder=8))
plan_ax = fig.add_axes([0.02, 0.07, 0.55, 0.82]); plan(plan_ax, True)
plan_ax.set_xlim(-19, 9); plan_ax.set_ylim(-9, 15); plan_ax.set_aspect("equal"); plan_ax.grid(alpha=0.3)
plan_ax.set_title("Centre of the floor, looking down (front = right), 1 grid = 5 mm", fontsize=10)
plan_ax.annotate("tab: connector + 1 screw\n(FR4 0.2 stiffener under it)", (-6, 3), (-18.5, 13), fontsize=9, arrowprops=dict(arrowstyle="->"), zorder=9)
plan_ax.annotate("JST-SH 2: same place, same turn,\nup through the existing 6.5 x 5.9 opening", (2.5, 2.5), (1.0, 11.5), fontsize=9, arrowprops=dict(arrowstyle="->"), zorder=9)
plan_ax.annotate("nylon M2 x 4 into the kept boss (156 deg)", SCREW, (-18.5, -1.5), fontsize=9, arrowprops=dict(arrowstyle="->"), zorder=9)
plan_ax.annotate("removed: 22.4 pocket,\n2 bosses + pilots, 2 screws", (7.9, -3), (2.5, -8.3), fontsize=9, color="#c62828", arrowprops=dict(arrowstyle="->", color="#c62828"), zorder=9)
plan_ax.annotate("tail from the ring (unchanged)", (-10, 12.8), (-18.5, 9.5), fontsize=9, arrowprops=dict(arrowstyle="->"), zorder=9)
ov = fig.add_axes([0.60, 0.50, 0.38, 0.40]); plan(ov, False)
ov.set_xlim(-44, 44); ov.set_ylim(-44, 44); ov.set_aspect("equal"); ov.set_xticks([]); ov.set_yticks([])
ov.add_patch(Rectangle((-19, -9), 28, 24, fc="none", ec="#1565c0", lw=1.2, zorder=9)); ov.set_title("whole flex (the ring is unchanged)", fontsize=10)
# section through the connector and the screw (along the line centre -> screw), not to scale in z (x 3)
sx = fig.add_axes([0.60, 0.07, 0.38, 0.36]); sx.set_title("Section centre -> screw (heights x3)", fontsize=10)
L = CLAMP_R + 4; Z = 3
def bx(x0, x1, z0, z1, fc, ec="#333", lab=None, **k):
    sx.add_patch(Rectangle((x0, z0 * Z), x1 - x0, (z1 - z0) * Z, fc=fc, ec=ec, lw=0.8, **k))
    if lab: sx.text((x0 + x1) / 2, (z1 * Z + z0 * Z) / 2, lab, ha="center", va="center", fontsize=7)
bx(-6, -3.25, 6.5, 8.1, "#d6d6cc"); bx(3.25, L, 6.5, 8.1, "#d6d6cc", lab="floor plate 1.6")
bx(CLAMP_R - 1.8, CLAMP_R + 1.8, 8.1, 11.3, "#d6d6cc", lab="boss")
bx(-4.0, CLAMP_R + 2.6, 6.38, 6.5, "#f2c14e", lab=None); sx.text(CLAMP_R + 3.0, 6.44 * Z, "flex 0.12", fontsize=7, va="center")
bx(-4.0, CLAMP_R + 2.6, 6.18, 6.38, "#a1887f"); sx.text(CLAMP_R + 3.0, 6.25 * Z, "FR4 0.2", fontsize=7, va="center")
bx(-2.0, 2.0, 6.5, 10.75, "#eeeeee", lab="JST")
bx(CLAMP_R - 1.9, CLAMP_R + 1.9, 4.78, 6.18, "#bdbdbd"); bx(CLAMP_R - 0.8, CLAMP_R + 0.8, 6.18, 10.18, "#9e9e9e", lab="M2")
sx.axhline(0, color="#795548", lw=2); sx.text(-5.8, 0.4, "floor / tags", fontsize=7)
sx.set_xlim(-6, L + 1); sx.set_ylim(-1, 12.5 * Z); sx.set_yticks([0, 6.5 * Z, 8.1 * Z, 11.3 * Z]); sx.set_yticklabels(["0", "6.5", "8.1", "11.3"]); sx.grid(alpha=0.2)
fig.text(0.60, 0.455, "Underside: flex 0.12 + FR4 0.2 = 0.32 below the floor (6.18 clearance left); screw head 1.4 below that.\nThe tab replaces the Ø22 round end; the ring, tail, copper and inductance are unchanged.", fontsize=8.5)
fig.suptitle("NFC flex antenna v2: small tab instead of the round end (2D for approval, to scale)", fontsize=15, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100)
print("saved", OUT, "tab area mm2", round(tab.area, 1), "tab bbox", [round(v, 1) for v in tab.bounds])
