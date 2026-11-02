# 2D: NFC reader mount v2 (to scale), for the WS1850S reader board (28 x 18, kicad/BugBot_NFC) + the 22 mm floor coil
# (kicad/BugBot_NFCcoil). Inputs: slices of the base robot (FreeCAD, BugBot doc, variants.base_parts) as json.
#   C:/Python312/python.exe draw_nfc_mount2.py slices.json out.png
#   coil:  in a 22.4 pocket from BELOW, flush with the floor underside (copper 5.6 mm over a tag), held by 3 nylon M2x4
#          pan screws from below (heads overlap the copper-free rim) into 3.6 mm bosses at r 12.2; its JST-SH 2 points up
#          through a 6.6 x 5.4 opening at the centre into the free column between the gearmotors.
#   tray:  printed, z 15.6-18.2, sits on the three motor-cap tops; the three INNER motor-cap screws become M2x8 (from M2x6)
#          and go through it (counterbored, heads flush) - same screws, same holes, the caps are clamped as before.
#   board: on the tray at 98 deg, 2 snap clips on the short edges; J1 (8-pin, to the main board) at one end, J2 (coil)
#          at the other beside a 1.8 x 1.6 edge notch; the coil cable runs up the column, along a groove under the tray
#          and up through the notch.
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Pg, Circle, Rectangle, FancyBboxPatch
from shapely.geometry import Polygon, Point, box
from shapely.affinity import rotate
from shapely.ops import unary_union

d = json.load(open(sys.argv[1])); OUT = sys.argv[2]
by = {}
for l, z, pts in d:
    if len(pts) >= 3:
        by.setdefault(z, []).append((l, pts))
TH = 98.0
SCR = [(8.44, 10.21), (-13.07, 2.21), (4.63, -12.42)]                 # inner motor-cap screws (r 13.25)
CLAMP = [(12.2 * math.cos(math.radians(a)), 12.2 * math.sin(math.radians(a))) for a in (36, 156, 276)]
notch = Polygon([(-14, -9), (14, -9), (14, -0.9), (12.4, -0.9), (12.4, 0.9), (14, 0.9), (14, 9), (-14, 9)])
B = rotate(notch, TH, origin=(0, 0))
T = unary_union([rotate(box(-14, -9, 14, 9), TH, origin=(0, 0)).buffer(0.9, join_style=2)] + [Point(x, y).buffer(3.0) for x, y in SCR]).convex_hull
c, s = math.cos(math.radians(TH)), math.sin(math.radians(TH))
R = lambda x, y: (x * c - y * s, x * s + y * c)

fig = plt.figure(figsize=(20, 10.5))
ax = fig.add_axes([0.02, 0.06, 0.45, 0.82]); sx = fig.add_axes([0.50, 0.30, 0.49, 0.58])
def fill(a, pts, fc, ec, al=0.5, lw=0.8, ls="-", z=1):
    a.add_patch(Pg(pts, closed=True, fc=fc, ec=ec, alpha=al, lw=lw, ls=ls, zorder=z))
for l, pts in by.get(7.3, []):
    if "Chassis" in l: fill(ax, pts, "#d8d8d0", "#777", 1.0, z=0)
for l, pts in by.get(20.0, []): fill(ax, pts, "#8fb3d9", "#4a6f99", 0.35)
for l, pts in by.get(10.5, []):
    if "Gearmotor" in l: fill(ax, pts, "#e57373", "#b71c1c", 0.45)
for l, pts in by.get(13.0, []):
    if "MotorCap" in l: fill(ax, pts, "#ffb74d", "#c77800", 0.5)
for l, pts in by.get(8.5, []):
    if "screw" in l:
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        inner = any(math.hypot(cx - x, cy - y) < 0.5 for x, y in SCR)
        ax.add_patch(Circle((cx, cy), 1.9, fc="#1565c0" if inner else "#9e9e9e", ec="#222", alpha=0.9, zorder=6))
# coil + pocket + opening + clamps
ax.add_patch(Circle((0, 0), 11.2, fc="#c8e6c9", ec="#1b5e20", lw=1.5, ls="--", zorder=2))
for k in range(4):
    ax.add_patch(Circle((0, 0), 9.85 - 0.5 * k, fc="none", ec="#2e7d32", lw=1.0, zorder=3))
ax.add_patch(Rectangle((-3.3, -2.7), 6.6, 5.4, fc="#fff", ec="#6a1b9a", lw=1.2, zorder=3))
ax.add_patch(Rectangle((-2.0, -1.5), 4.0, 3.0, fc="#ce93d8", ec="#6a1b9a", zorder=4))
for x, y in CLAMP:
    ax.add_patch(Circle((x, y), 1.8, fc="#fff59d", ec="#8a6d10", zorder=5)); ax.add_patch(Circle((x, y), 1.9, fc="none", ec="#333", ls=":", zorder=5))
# tray, board, groove, connectors
fill(ax, list(T.exterior.coords), "#ffc400", "#8a6d10", 0.30, 1.4, "--", z=7)
fill(ax, list(B.exterior.coords), "#90caf9", "#1565c0", 0.45, 1.2, z=8)
for (x0, y0, x1, y1, col, lab) in ((-13.65, -5.95, -8.35, 5.95, "#555", "J1"), (6.3, -2.65, 12.15, 2.65, "#6a1b9a", "J2"), (-6.7, -3.2, -0.3, 3.2, "#222", "U1")):
    q = [R(x0, y0), R(x1, y0), R(x1, y1), R(x0, y1)]; fill(ax, q, "none", col, 1, 1.4, z=9)
    ax.text(*R((x0 + x1) / 2, (y0 + y1) / 2), lab, ha="center", va="center", fontsize=10, color=col, zorder=10, weight="bold")
g = [R(0, 0), R(13.2, 0)]
ax.plot([p[0] for p in g], [p[1] for p in g], color="#6a1b9a", lw=3, ls=(0, (3, 2)), zorder=9)
ax.set_xlim(-26, 26); ax.set_ylim(-26, 26); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title("TOP VIEW, centre of the base (front = +x, right)", loc="left", fontsize=12, weight="bold")
leg = [("#c8e6c9", "#1b5e20", "coil 22 in a 22.4 pocket from below (green rings = copper)"),
       ("#ce93d8", "#6a1b9a", "coil's JST-SH 2 (up) in a 6.6 x 5.4 opening; cable path (dashed purple) under the tray to the notch"),
       ("#fff59d", "#8a6d10", "3 nylon M2x4 pan screws from below + 3.6 bosses (r 12.2): 0.76 to the gearmotors"),
       ("#1565c0", "#222", "the 3 inner motor-cap screws: M2x6 -> M2x8 through the tray (counterbored)"),
       ("#ffc400", "#8a6d10", "printed tray (dashed), z 15.6-18.2, on the 3 motor caps; 2 snap clips hold the board"),
       ("#90caf9", "#1565c0", "reader board 28 x 18 at 98 deg, with the notch beside J2"),
       ("#e57373", "#b71c1c", "gearmotors"), ("#ffb74d", "#c77800", "motor caps (top z 15.6)"), ("#8fb3d9", "#4a6f99", "wheels / encoder boards at z 20")]
for i, (f, e, t) in enumerate(leg):
    fig.text(0.50, 0.25 - i * 0.024, "■", color=f, fontsize=14, va="center"); fig.text(0.515, 0.25 - i * 0.024, t, fontsize=10.5, va="center")

# ---- section along the board axis (98 deg), unrolled; u = distance along the axis (J2 end +)
def bx(u0, z0, u1, z1, fc, ec, al=0.9, ls="-", lw=0.8, zo=2):
    sx.add_patch(Rectangle((min(u0, u1), min(z0, z1)), abs(u1 - u0), abs(z1 - z0), fc=fc, ec=ec, alpha=al, ls=ls, lw=lw, zorder=zo))
sx.plot([-20, 20], [0, 0], color="#333", lw=1.5); sx.text(-19.5, -1.4, "mat", fontsize=9, color="#555")
bx(-10, 0, -6, 0.9, "#8e4dd0", "#4a1f80"); sx.text(-10, 1.2, "tag 0.9", fontsize=8, color="#4a1f80")
bx(-20, 6.5, -11.2, 8.1, "#d8d8d0", "#777"); bx(11.2, 6.5, 20, 8.1, "#d8d8d0", "#777")
bx(-11.2, 7.3, -3.3, 8.1, "#d8d8d0", "#777"); bx(3.3, 7.3, 11.2, 8.1, "#d8d8d0", "#777")         # 0.8 lip over the coil
bx(-11.0, 6.5, 11.0, 7.3, "#66bb6a", "#1b5e20")                                                    # coil PCB 0.8
bx(-2.0, 7.3, 2.0, 11.55, "#ce93d8", "#6a1b9a"); bx(-1.5, 11.55, 1.5, 13.0, "#ce93d8", "#6a1b9a", 0.6)
bx(12.2 - 1.0, 6.5, 12.2 + 1.0, 10.5, "#fff59d", "#8a6d10", 1); bx(12.2 - 1.9, 5.1, 12.2 + 1.9, 6.5, "#fff59d", "#8a6d10", 1)   # clamp (rotated in)
bx(10.4, 8.1, 14.0, 11.0, "#d8d8d0", "#777")                                                       # its boss
bx(-20, 8.9, -5.2, 15.1, "#e57373", "#b71c1c", 0.25, "--"); bx(5.2, 8.9, 20, 15.1, "#e57373", "#b71c1c", 0.25, "--")
bx(-20, 12.5, -6.0, 15.6, "#ffb74d", "#c77800", 0.35, "--"); bx(6.0, 12.5, 20, 15.6, "#ffb74d", "#c77800", 0.35, "--")
bx(-14.9, 15.6, 14.9, 18.2, "#ffc400", "#8a6d10", 0.8)                                            # tray
bx(-14.9, 18.2, -14.0, 20.4, "#ffc400", "#8a6d10", 0.8); bx(14.0, 18.2, 14.9, 20.4, "#ffc400", "#8a6d10", 0.8)   # clips
bx(-14.0, 18.2, 12.4, 19.8, "#90caf9", "#1565c0", 0.9)                                            # board (notch beyond 12.4)
bx(-13.4, 19.8, -8.6, 24.05, "#bdbdbd", "#333"); bx(7.2, 19.8, 11.2, 24.05, "#ce93d8", "#6a1b9a")   # J1, J2
bx(-7.2, 18.2, -4.8, 19.8, "#fff", "#1565c0", 1, ":"); bx(-7.7, 16.6, -4.3, 18.2, "#bbdefb", "#1565c0", 1, ":")   # a cap screw's counterbore (rotated in)
bx(-6.85, 8.6, -5.15, 16.6, "#90a4ae", "#37474f", 0.9, ":")
sx.plot([0, 0, 0.6, 13.2, 13.2, 13.2, 12.4, 9.2, 9.2], [13.0, 15.0, 16.2, 16.2, 19.8, 25.8, 26.6, 26.6, 24.05], color="#6a1b9a", lw=2.2)
bx(-20, 29.0, 20, 30.6, "#2e6b3f", "#1c4428")
sx.text(-19.5, 29.3, "main board (underside clear to ~28.5 here)", fontsize=9, color="#fff")
notes = [((0.0, 10.0), (-19.5, 4.6), "coil JST-SH 2 + plug, up into the free column (r 5.2)"),
         ((-8.0, 6.9), (-19.5, 2.6), "coil 22 x 0.8 in its pocket, flush: copper 5.6 mm over a tag"),
         ((12.2, 5.6), (8.0, 2.6), "nylon M2x4 clamp (x3)"),
         ((6.0, 16.9), (15.5, 13.5), "groove under the tray"),
         ((-6.0, 12.0), (-19.5, 22.0), "inner cap screw M2x8 (was M2x6), head flush in the tray"),
         ((0.0, 17.0), (-3.0, 27.5), "tray z 15.6-18.2 on the 3 cap tops"),
         ((-2.0, 19.0), (-12.0, 26.5), "reader board z 18.2-19.8, parts to 24.05"),
         ((13.2, 21.0), (15.5, 22.0), "cable up the notch, loops into J2")]
for (u, z), (tu, tz), t in notes:
    sx.annotate(t, (u, z), (tu, tz), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777", lw=0.7))
sx.set_xlim(-20, 20); sx.set_ylim(-2, 31); sx.set_aspect("equal"); sx.grid(alpha=0.2)
sx.set_title("SECTION along the board (98 deg), parts on other angles rotated in", loc="left", fontsize=12, weight="bold")
fig.text(0.02, 0.955, "NFC reader mount v2 (2D, to scale, mm)", fontsize=18, weight="bold")
fig.text(0.02, 0.925, "WS1850S reader board 28 x 18 (KiCad, DRC clean) on a printed tray over the motor caps; 22 mm coil board flush in the floor; "
                      "no part of the robot changes except the floor centre, 3 bosses and 3 longer cap screws.", fontsize=11.5, color="#333")
fig.text(0.02, 0.02, "Clearances (worst case): board / tray to wheels and encoder boards 1.7; clamp bosses to gearmotors 0.76; tray 0 on the caps (it rests on them); "
                     "parts top 24.05 to the main board ~4.5.", fontsize=11, color="#1a7f37", weight="bold")
plt.savefig(OUT, dpi=90)
print(OUT)
