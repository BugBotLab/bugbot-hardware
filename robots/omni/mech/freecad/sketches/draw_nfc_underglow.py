# 2D (to scale): 12 underglow LEDs on the NFC floor PCB + a JST-SH 3 for them.
#   LEDs: WS2812B-2020-V6 on the BOTTOM face (pointing at the table), 100 nF each; SN74AHCT1G125 level shifter + 10 uF
#   near the centre, also on the bottom; JST-SH 3 (BM03B-SRSS-TB, upright) on the TOP face, up through the floor opening
#   beside the 2 NFC wire holes. The LED traces run as an open chain (no closed ring) so the NFC loop is not shorted.
#   Chassis: the floor opening grows from 6.5 x 5.9 to 7.6 x 8.4 for the bigger connector + the wire holes.
# v2: all 12 LEDs 3.0 mm in from the robot's edge (following the outline), equally spaced (design/lib/underglow_geom.py)
# usage: python draw_nfc_underglow.py floor_outline.json floor_geom.json floor_slice.json underglow.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, Circle, Polygon as MPoly
from shapely.geometry import Polygon, Point, LineString
F = json.load(open(sys.argv[1])); GEO = json.load(open(sys.argv[2])); S = json.load(open(sys.argv[3])); UG = json.load(open(sys.argv[4])); OUT = sys.argv[5]
O = Polygon(F["outer"])
win = [Polygon(h) for h in F["holes"] if Polygon(h).area > 300 and not Polygon(h).contains(Point(0, 0))]
board = O
for w in win: board = board.difference(w)
LEDS = [(33, a) for a in (214, 229, 244, 259)] + [(33, a) for a in (89, 100, 111, 121)] + [(19, a) for a in (-28, -16, -4, 8)]
# chain order: connector -> front (right to left) -> upper-left gap -> rear-left gap  (an open "C", never a ring)
ORDER = [(19, 8), (19, -4), (19, -16), (19, -28)][::-1] + [(33, 89), (33, 100), (33, 111), (33, 121)][::-1]
ORDER = [(19, -28), (19, -16), (19, -4), (19, 8), (33, 89), (33, 100), (33, 111), (33, 121), (33, 214), (33, 229), (33, 244), (33, 259)]
xy = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
OPEN = (-3.8, 3.8, -4.2, 4.2)                   # new opening x0 x1 y0 y1
J3 = (0.0, -1.2)                                 # JST-SH 3 centre (courtyard 6.9 x 5.3)
NFC_H = [(-1.27, 3.0), (1.27, 3.0)]              # NFC wire holes (moved up 3.0)
U1 = (0.0, -7.5); C13 = (4.5, -7.5)
fig = plt.figure(figsize=(16, 10.2))
def patch(a, wires, fc, ec, al, lw=0.6, z=1):
    v, c = [], []
    for w in wires: v += list(w) + [w[0]]; c += [Path.MOVETO] + [Path.LINETO] * (len(w) - 1) + [Path.CLOSEPOLY]
    a.add_patch(PathPatch(Path(v, c), fc=fc, ec=ec, alpha=al, lw=lw, zorder=z))
def plan(a, big):
    for nm, zz in S["low"].items():
        if nm.startswith("DriveUnit:"):
            for z, w in zz.items(): patch(a, w, "#e57373", "none", 0.22, z=0)
    patch(a, [list(board.exterior.coords)] + [list(i.coords) for i in board.interiors], "#2e7d32", "#1b5e20", 0.85, 0.8, 1)
    x, y = zip(*GEO["spiral"]); a.plot(x, y, color="#e0b040", lw=0.6, zorder=2)
    for k in ("lead_a", "lead_b"):
        pts = GEO[k][:-1] + [NFC_H[0] if k == "lead_a" else NFC_H[1]]; x, y = zip(*pts); a.plot(x, y, color="#e0b040", lw=0.9, zorder=2)
    path = [J3, tuple(UG["U1"])] + [tuple(p) for p in UG["feed"][1:]] + [tuple(p) for p in UG["bus"]]
    x, y = zip(*path); a.plot(x, y, color="#64b5f6", lw=2.2 if big else 1.2, alpha=0.9, zorder=3)
    for l in UG["leds"]:
        cx, cy, ang = l["x"], l["y"], l["ang"]
        rot = lambda dx, dy: (cx + dx * math.cos(math.radians(ang)) - dy * math.sin(math.radians(ang)), cy + dx * math.sin(math.radians(ang)) + dy * math.cos(math.radians(ang)))
        a.add_patch(MPoly([rot(dx, dy) for dx, dy in ((-1.1, -1.0), (1.1, -1.0), (1.1, 1.0), (-1.1, 1.0))], closed=True, fc="#fafafa", ec="#222", lw=0.8, zorder=5))
        a.add_patch(MPoly([rot(dx, dy) for dx, dy in ((1.5, -0.25), (2.5, -0.25), (2.5, 0.25), (1.5, 0.25))], closed=True, fc="#a1887f", ec="#333", lw=0.5, zorder=5))
        if big: a.text(cx, cy, str(l["n"]), ha="center", va="center", fontsize=7, zorder=6)
    a.add_patch(Rectangle((OPEN[0], OPEN[2]), OPEN[1] - OPEN[0], OPEN[3] - OPEN[2], fc="none", ec="#c62828", lw=1.2, ls="--", zorder=6))
    a.add_patch(Rectangle((-3.25, -2.95), 6.5, 5.9, fc="none", ec="#888", lw=0.8, ls=":", zorder=6))
    a.add_patch(Rectangle((J3[0] - 3.44, J3[1] - 2.65), 6.88, 5.3, fc="#eeeeee", ec="#333", lw=0.8, zorder=6))
    for px in (-1, 0, 1): a.add_patch(Rectangle((J3[0] + px - 0.3, J3[1] + 1.32 - 0.8), 0.6, 1.6, fc="#d4a017", zorder=7))
    for h in NFC_H:
        a.add_patch(Circle(h, 0.8, fc="#e0b040", ec="#7a5c00", zorder=7)); a.add_patch(Circle(h, 0.45, fc="white", zorder=8))
    a.add_patch(Rectangle((U1[0] - 1.5, U1[1] - 1.5), 3, 3, fc="#424242", ec="#000", zorder=6))
    a.add_patch(Rectangle((C13[0] - 0.8, C13[1] - 0.5), 1.6, 1.0, fc="#a1887f", ec="#000", zorder=6))
    for c in GEO["clamps"]: a.add_patch(Circle(c, 1.2, fc="white", ec="#111", lw=0.8, zorder=6))
ax = fig.add_axes([0.02, 0.06, 0.55, 0.84]); plan(ax, True)
ax.set_xlim(-44, 44); ax.set_ylim(-44, 44); ax.set_aspect("equal"); ax.grid(alpha=0.25)
ax.set_title("Looking down through the floor (front = right). White squares = LEDs (numbers = chain order), 1 grid = 10 mm", fontsize=9.5)
ax.annotate("all 12 LEDs 3.0 mm in from the edge, 20.3 mm apart\nalong the outline (round the ball notch too);\n100 nF beside each LED", (UG["leds"][4]["x"], UG["leds"][4]["y"]), (8, -43), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.annotate("chain break at the NFC tail:\nthe bus never passes the loop's joint", (-24, 31), (-43, 41), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.annotate("blue: 5 V + GND + data (bottom copper), an open chain;\nround the inner side of a window where the 3 mm line\nclips its corner; fed from U1 round r 8.5", xy(8.5, 200), (-43, -40), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax2 = fig.add_axes([0.58, 0.47, 0.40, 0.43]); plan(ax2, False)
ax2.set_xlim(-10, 10); ax2.set_ylim(-10.5, 6.5); ax2.set_aspect("equal"); ax2.grid(alpha=0.3)
ax2.set_title("Centre detail (1 grid = 2.5 mm)", fontsize=10)
ax2.text(-9.7, -1.4, "red dashed: new\nfloor opening\n7.6 x 8.4\n(was 6.5 x 5.9,\n dotted)", fontsize=7, color="#c62828")
ax2.annotate("JST-SH 3 (top face, up through the opening)", J3, (-9.6, -4.5), fontsize=8, arrowprops=dict(arrowstyle="->"))
ax2.annotate("NFC wire holes (moved up 3 mm)", NFC_H[1], (3.0, 5.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
ax2.annotate("U1 level shifter + C13 10 uF\n(bottom face)", U1, (-9.6, -9.6), fontsize=8, arrowprops=dict(arrowstyle="->"))
tx = fig.add_axes([0.58, 0.04, 0.40, 0.38]); tx.axis("off")
spec = [
 "Parts (all on JLC; same as the top LED ring):",
 "  D1-D12  WS2812B-2020-V6  C52917434  (Ext)  bottom face, lens down,",
 "          3.0 mm in from the edge, 20.3 mm apart along the outline",
 "  C1-C12  100 nF 0402      C1525      (Basic) beside each LED (along the edge)",
 "  U1      SN74AHCT1G125    C7484      (Ext)  3.3 V data -> 5 V",
 "  R1      33 R series      C25105     (Basic)",
 "  C13     10 uF 0603       C19702     (Basic)",
 "  J2      JST-SH 3 BM03B-SRSS-TB upright, TOP face (5 V, GND, DIN)",
 "  -> JLC assembles the bottom; J2 (top) hand-soldered or 2-sided assembly",
 "",
 "Board: still 2-layer FR4 1.6; NFC loop, outline, clamp holes unchanged.",
 "LEDs 0.9 proud below the board -> ~4.0 mm to the table.",
 "Power: 12 x up to ~36 mA = ~0.43 A at full white from the 5 V boost:",
 "  the firmware caps brightness. Data: 1 P4 GPIO (new main-board",
 "  JST-SH 3, to add) or chained from the top ring's DOUT.",
 "Chassis: the floor opening 6.5 x 5.9 -> 7.6 x 8.4 (to check in 3D).",
]
tx.text(0, 1, "\n".join(spec), va="top", fontsize=8.6, family="monospace")
fig.suptitle("NFC floor PCB + 12 underglow LEDs (2D for approval, to scale)", fontsize=15, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT)
