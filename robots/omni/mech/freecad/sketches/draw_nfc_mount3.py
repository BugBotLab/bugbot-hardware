# 2D: NFC reader mount v3 (to scale) - one position for EVERY variant (it also clears the BugBot's kick solenoid).
#   v2 put the reader board over the motor caps at the centre: the BugBot's solenoid fills that space. v3 moves it to the
#   open floor between drive units 1 and 2, under the main board.
#   C:/Python312/python.exe draw_nfc_mount3.py bugbot_slices.json cable_path.json out.png
#   coil:  unchanged from v2 (22 mm, pocket from below, 3 nylon M2x4 clamps into bosses at r 12.2, JST-SH 2 up the column)
#   tray:  printed, z 16.2-18.8, on 3 printed posts (5 mm, part of the chassis, from the floor), one M2x6 pan screw each,
#          heads in counterbores under the board; 2 snap clips on the long edges, end stops on the short edges
#   board: 28 x 18 at 117 deg, centre (-8.5, 19.5), z 18.8-20.4; J2 (coil) at the far end beside an edge notch; J1 (to the
#          main board) at the near end. Motor-cap screws unchanged (M2x6).
#   cable: coil JST-SH 2 -> up the column to z 14.5 -> out between the gearmotors (40 mm, 1.6 mm wide channel) -> up under
#          the notch (3.4 mm clear from the floor up) -> through the tray and the notch -> loops into J2 (a 50 mm cable).
import sys, json, math, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Pg, Circle, Rectangle
from shapely.geometry import Polygon

d = json.load(open(sys.argv[1])); cable = json.load(open(sys.argv[2])); OUT = sys.argv[3]
grp = collections.defaultdict(list)
for l, z, pts in d:
    if len(pts) >= 3:
        grp[(l, z)].append(Polygon(pts).buffer(0))
occ = collections.defaultdict(list)
for (l, z), ps in grp.items():
    g = ps[0]
    for p in ps[1:]:
        g = g.symmetric_difference(p)
    occ[z].append((l, g))
TH, CX, CY = 117.0, -8.5, 19.5
c, s = math.cos(math.radians(TH)), math.sin(math.radians(TH))
W = lambda u, v: (CX + u * c - v * s, CY + u * s + v * c)
POSTS = [(12.5, 6.5), (12.5, -6.5), (-6.5, 6.0)]
CLAMP = [(12.2 * math.cos(math.radians(a)), 12.2 * math.sin(math.radians(a))) for a in (36, 156, 276)]

fig = plt.figure(figsize=(21, 11))
ax = fig.add_axes([0.02, 0.07, 0.46, 0.80]); sx = fig.add_axes([0.51, 0.36, 0.48, 0.50])
def draw(z, pick, fc, ec, al):
    for l, g in occ.get(z, []):
        if not pick(l):
            continue
        for gg in getattr(g, "geoms", [g]):
            if gg.is_empty or gg.geom_type != "Polygon":
                continue
            ax.add_patch(Pg(list(gg.exterior.coords), closed=True, fc=fc, ec=ec, alpha=al, lw=0.6))
            for h in gg.interiors:
                ax.add_patch(Pg(list(h.coords), closed=True, fc="w", ec=ec, lw=0.4))
draw(8.5, lambda l: "Chassis" in l, "#efe7c8", "#b0a060", 1.0)
draw(20.0, lambda l: "Wheel" in l or "EncBoard" in l, "#8fb3d9", "#4a6f99", 0.45)
draw(11.5, lambda l: "Gearmotor" in l, "#e57373", "#b71c1c", 0.5)
draw(13.5, lambda l: "MotorCap" in l, "#ffb74d", "#c77800", 0.55)
draw(20.0, lambda l: "Kicker" in l, "#7e57c2", "#4527a0", 0.35)
draw(27.5, lambda l: "MainBoard" in l, "#a5d6a7", "#2e7d32", 0.6)
ax.add_patch(Circle((0, 0), 11.2, fc="#c8e6c9", ec="#1b5e20", lw=1.4, ls="--"))
for k in range(4):
    ax.add_patch(Circle((0, 0), 9.85 - 0.5 * k, fc="none", ec="#2e7d32", lw=0.9))
ax.add_patch(Rectangle((-3.25, -2.95), 6.5, 5.9, fc="#fff", ec="#6a1b9a", lw=1.2)); ax.add_patch(Rectangle((-2.0, -1.5), 4.0, 3.0, fc="#ce93d8", ec="#6a1b9a"))
for x, y in CLAMP:
    ax.add_patch(Circle((x, y), 1.8, fc="#fff59d", ec="#8a6d10"))
tray = [W(u, v) for u, v in [(-14.3, -9.9), (14.9, -9.9), (14.9, 9.9), (-14.3, 9.9)]]
board = [W(u, v) for u, v in [(-14, -9), (14, -9), (14, -3.4), (12.4, -3.4), (12.4, -1.6), (14, -1.6), (14, 9), (-14, 9)]]
ax.add_patch(Pg(tray, closed=True, fc="#ffc400", ec="#8a6d10", alpha=0.35, lw=1.4, ls="--"))
ax.add_patch(Pg(board, closed=True, fc="#90caf9", ec="#1565c0", alpha=0.55, lw=1.3))
for (u0, v0, u1, v1, col, lab) in ((-13.65, -5.95, -8.35, 5.95, "#333", "J1"), (6.55, -5.45, 11.85, 0.45, "#6a1b9a", "J2"), (-6.7, -3.2, -0.3, 3.2, "#222", "U1")):
    q = [W(u0, v0), W(u1, v0), W(u1, v1), W(u0, v1)]
    ax.add_patch(Pg(q, closed=True, fc="none", ec=col, lw=1.4)); ax.text(*W((u0 + u1) / 2, (v0 + v1) / 2), lab, ha="center", va="center", fontsize=10, color=col, weight="bold")
for u, v in POSTS:
    ax.add_patch(Circle(W(u, v), 2.5, fc="#ffe082", ec="#8a6d10", lw=1.2)); ax.add_patch(Circle(W(u, v), 0.8, fc="#616161", ec="k"))
ax.plot([p[0] for p in cable], [p[1] for p in cable], color="#6a1b9a", lw=2.6, ls=(0, (3, 1.5)))
ax.set_xlim(-38, 22); ax.set_ylim(-14, 40); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title("TOP VIEW (BugBot shown, with its kicker; front = +x)", loc="left", fontsize=12, weight="bold")
leg = [("#90caf9", "reader board 28 x 18 at 117 deg (centre -8.5, 19.5), z 18.8-20.4; J2 + notch at the far end"),
       ("#ffc400", "printed tray z 16.2-18.8 (dashed), 2 snap clips on the long edges"),
       ("#ffe082", "3 printed posts (5 mm, chassis) from the floor, M2x6 pan screw each (heads counterbored under the board)"),
       ("#ce93d8", "coil cable (dashed purple): column -> z 14.5 between the gearmotors -> up under the notch -> J2 (50 mm JST-SH 2)"),
       ("#c8e6c9", "coil 22 in its floor pocket + 3 nylon clamps (yellow), as v2"),
       ("#7e57c2", "BugBot kick solenoid (the Base and Spider have none)"),
       ("#a5d6a7", "main-board underside parts (z 25.8+)"), ("#e57373", "gearmotors"), ("#ffb74d", "motor caps (screws unchanged: M2x6)")]
for i, (f, t) in enumerate(leg):
    fig.text(0.51, 0.30 - i * 0.026, "■", color=f, fontsize=14, va="center"); fig.text(0.525, 0.30 - i * 0.026, t, fontsize=10.5, va="center")

def bx(u0, z0, u1, z1, fc, ec, al=0.9, ls="-"):
    sx.add_patch(Rectangle((min(u0, u1), min(z0, z1)), abs(u1 - u0), abs(z1 - z0), fc=fc, ec=ec, alpha=al, ls=ls, lw=0.8))
sx.plot([-22, 22], [0, 0], color="#333", lw=1.5)
bx(-22, 6.5, 22, 8.1, "#efe7c8", "#b0a060")
for u, v in POSTS[:2] + [(POSTS[2][0], 0)]:
    bx(u - 2.5, 8.1, u + 2.5, 16.2, "#ffe082", "#8a6d10"); bx(u - 0.8, 11.5, u + 0.8, 17.8, "#616161", "#222")
    bx(u - 2.0, 17.8, u + 2.0, 18.8, "#9e9e9e", "#222")
bx(-14.3, 16.2, 14.9, 18.8, "#ffc400", "#8a6d10", 0.8)
bx(-14.0, 18.8, 12.4, 20.4, "#90caf9", "#1565c0")
bx(-13.4, 20.4, -8.6, 24.65, "#bdbdbd", "#333"); bx(7.2, 20.4, 11.2, 24.65, "#ce93d8", "#6a1b9a")
bx(-22, 8.9, -15, 15.1, "#e57373", "#b71c1c", 0.25, "--"); bx(-22, 12.5, -15.5, 15.6, "#ffb74d", "#c77800", 0.3, "--")
bx(5.5, 25.8, 11.5, 29.0, "#a5d6a7", "#2e7d32", 0.8, ":")
bx(-22, 29.0, 22, 30.6, "#2e6b3f", "#1c4428")
sx.plot([13.2, 13.2, 13.2, 12.0, 9.2, 9.2], [14.5, 16.2, 21.0, 25.3, 25.3, 24.65], color="#6a1b9a", lw=2.2)
sx.annotate("coil cable arrives at z 14.5 from the column", (13.2, 14.5), (1.0, 10.5), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777"))
sx.annotate("3 posts from the floor (part of the chassis)", (0.0 - 6.5, 12.0), (-21.0, 4.0), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777"))
sx.annotate("tray z 16.2-18.8 (0.6 over the caps)", (2.0, 17.5), (-6.0, 13.6), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777"))
sx.annotate("reader board z 18.8-20.4, connectors to 24.65", (-2.0, 20.0), (-21.0, 26.5), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777"))
sx.annotate("main-board part (6 x 6, to z 25.8): 2.8 from J2's plug", (8.0, 26.5), (-4.0, 31.6), fontsize=9.5, arrowprops=dict(arrowstyle="-", color="#777"))
sx.set_xlim(-22, 22); sx.set_ylim(-1, 33); sx.set_aspect("equal"); sx.grid(alpha=0.2)
sx.set_title("SECTION along the board (117 deg), J2 end right; posts rotated in", loc="left", fontsize=12, weight="bold")
fig.text(0.02, 0.955, "NFC reader mount v3 (2D, to scale, mm): one position for every variant", fontsize=18, weight="bold")
fig.text(0.02, 0.925, "v2's spot over the motor caps is where the BugBot's kick solenoid sits. v3: the reader board goes on the open floor between drive units 1 and 2, "
                      "under the main board; the floor coil stays at the centre.", fontsize=11.5, color="#333")
fig.text(0.02, 0.02, "Worst-case clearances (BugBot, the fullest variant): posts 1.8 to the motor caps; tray 0.93 to the chassis wall, 0.6 over the caps; board 1.7 to the solenoid; "
                     "J1 plug 2.05 to the solenoid; J2 plug 2.8 to the main board's parts.", fontsize=11, color="#1a7f37", weight="bold")
plt.savefig(OUT, dpi=90)
print(OUT)
