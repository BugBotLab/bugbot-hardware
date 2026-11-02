# 2D (to scale): NFC reader board with right-angle (side-entry) JST-SH connectors instead of the vertical ones
# (user, 2026-10-26: the vertical plugs + cables crowd the main board's underside).
#   J1 SM08B at the near end, mouth facing +u (along the board, toward the main board's J20, which faces back at it):
#      its 7 mm plug lane must be free of parts -> the reader's other parts move toward the far end (re-place + re-route).
#   J2 SM02B at the far end, mouth facing +u over the existing edge notch: the coil cable comes up through the notch
#      and turns straight into the plug. Nothing can stick out of either end: the kick solenoid is 1.7 mm past the near
#      end and the chassis wall 2.4 mm past the tray at the far end (slices nfc_bugbot_slices.json, z 20-24.6).
#   C:/Python312/python.exe draw_nfc_connectors.py nfc_bugbot_slices.json nfcgeo.json out.png
import sys, json, math, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Pg, Rectangle, Circle
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

d = json.load(open(sys.argv[1])); geo = json.load(open(sys.argv[2])); OUT = sys.argv[3]
TH, CX, CY = 117.0, -8.5, 19.5
c, s = math.cos(math.radians(TH)), math.sin(math.radians(TH))
uv = lambda x, y: ((x - CX) * c + (y - CY) * s, -(x - CX) * s + (y - CY) * c)
grp = collections.defaultdict(list)
for l, z, pts in d:
    if len(pts) >= 3 and 19.9 <= z <= 24.6 and "MainBoard" not in l and "NFC" not in l:
        grp[l.split("/")[0]].append(Polygon([uv(*p) for p in pts]).buffer(0))
obst = {k: unary_union(v) for k, v in grp.items()}

fig = plt.figure(figsize=(21, 12.5))
ax = fig.add_axes([0.03, 0.40, 0.60, 0.50]); sx = fig.add_axes([0.03, 0.05, 0.60, 0.28]); lg = fig.add_axes([0.66, 0.05, 0.33, 0.85]); lg.axis("off")
view = box(-24, -14, 22, 14)
for k, g in obst.items():
    g = g.intersection(view)
    col = {"Kicker:1": "#7e57c2", "Frame:1": "#efe7c8"}.get(k, "#8fb3d9")
    for gg in getattr(g, "geoms", [g]):
        if gg.geom_type == "Polygon" and not gg.is_empty:
            ax.add_patch(Pg(list(gg.exterior.coords), fc=col, ec="#555", lw=0.5, alpha=0.75))
# main board underside, projected: U6 module and J20 (+ its plug lane), robot frame -> uv
def quad(x0, y0, x1, y1): return [uv(x0, y0), uv(x1, y0), uv(x1, y1), uv(x0, y1)]
m = geo["main"]
ax.add_patch(Pg(quad(*m["U6"][:4]), fc="#c8e6c9", ec="#2e7d32", lw=1.2, ls=":", alpha=0.35))
ax.text(*uv(5, 22), "U6 module on the main board's underside\n(projected, above the reader)", fontsize=9, color="#2e7d32", ha="center")
ax.add_patch(Pg(quad(*m["J20"][:4]), fc="#a5d6a7", ec="#1b5e20", lw=1.6))
jx, jy = -15.0, 27.89                                   # J20 centre (robot); mouth faces robot -y
ax.add_patch(Pg(quad(jx - 5.1, jy - 10.27, jx + 5.1, jy - 3.27), fc="none", ec="#1b5e20", lw=1.2, ls="--"))
ax.text(*uv(jx, jy + 0.5), "J20", fontsize=10, color="#1b5e20", weight="bold", ha="center")
# reader board + tray + notch + H1 post
board = [(-14, -9), (14, -9), (14, -3.4), (12.4, -3.4), (12.4, -1.6), (14, -1.6), (14, 9), (-14, 9)]
ax.add_patch(Rectangle((-14.3, -9.9), 29.2, 19.8, fc="#ffc400", ec="#8a6d10", alpha=0.25, ls="--"))
ax.add_patch(Pg(board, fc="#90caf9", ec="#1565c0", lw=1.4, alpha=0.6))
for ref, (u0, y0, u1, y1, fp) in geo["reader"].items():               # today's parts (KiCad y down -> v = -y)
    if ref in ("J1", "J2"):
        ax.add_patch(Rectangle((u0, -y1), u1 - u0, y1 - y0, fc="none", ec="#b71c1c", lw=1.0, ls=":"))
        continue
    ax.add_patch(Rectangle((u0, -y1), u1 - u0, y1 - y0, fc="#9e9e9e" if ref != "H1" else "none", ec="#424242", lw=0.6, alpha=0.8))
    if ref in ("U1", "Y1", "H1"): ax.text((u0 + u1) / 2, -(y0 + y1) / 2, ref, ha="center", va="center", fontsize=8)
# proposed J1: SM08B, centre u -10.4, mouth +u; body = courtyard u -13.68..-7.13, v -5.9..5.9; lane u -7.13..-0.13
ax.add_patch(Rectangle((-13.68, -5.9), 6.55, 11.8, fc="#455a64", ec="k", lw=1.2))
ax.text(-10.4, 0, "J1\nSM08B", color="w", ha="center", va="center", fontsize=9, weight="bold")
ax.add_patch(Rectangle((-7.13, -5.1), 7.0, 10.2, fc="#ef9a9a", ec="#b71c1c", lw=1.2, hatch="//", alpha=0.55))
ax.text(-3.6, 6.3, "J1 plug lane: no parts", color="#b71c1c", ha="center", fontsize=9)
# proposed J2: SM02B, mouth +u at u 12.4 (the notch's inner edge), pins centred on the notch (v -2.5)
ax.add_patch(Rectangle((12.4 - 6.55, -2.5 - 2.9), 6.55, 5.8, fc="#6a1b9a", ec="k", lw=1.2))
ax.text(12.4 - 3.3, -2.5, "J2\nSM02B", color="w", ha="center", va="center", fontsize=8, weight="bold")
ax.add_patch(Rectangle((12.4, -4.6), 3.0, 4.2, fc="#ce93d8", ec="#6a1b9a", lw=1.0, alpha=0.7))
ax.text(15.6, -6.2, "plug over the notch;\ncable drops through it", fontsize=8, color="#6a1b9a")
# 8-wire cable: J1 plug back -> J20 plug back (top view)
p0 = (-3.6, 0.0); p1 = uv(jx, jy - 9.0)
ax.plot([p0[0], (p0[0] + p1[0]) / 2, p1[0]], [p0[1], p0[1] + 2.5, p1[1]], color="#e65100", lw=3)
# free area for the rest of the reader's parts
ax.add_patch(Rectangle((-0.13, -9), 12.53, 18, fc="none", ec="#2e7d32", lw=2.0, ls="-."))
ax.text(6.1, 8.0, "U1, crystal, decoupling, both TX matching chains re-placed here (+ the lane's side strips)", fontsize=8.5, color="#2e7d32", ha="center")
ax.set_xlim(-24, 22); ax.set_ylim(-14, 14); ax.set_aspect("equal"); ax.grid(alpha=0.25)
ax.set_xlabel("u along the board (mm), J2 end +"); ax.set_ylabel("v (mm)")
ax.set_title("TOP VIEW in the reader board's frame (board at 117 deg, centre -8.5, 19.5)", loc="left", fontsize=12, weight="bold")
for k, (u, v, t) in {"sol": (-19.5, 0, "kick\nsolenoid"), "ch": (19.5, -10, "chassis\nwall")}.items():
    ax.text(u, v, t, fontsize=9, ha="center", color="#333")

# section along u
def bx(u0, z0, u1, z1, fc, ec, al=0.9, ls="-", lw=0.8, h=None):
    sx.add_patch(Rectangle((u0, z0), u1 - u0, z1 - z0, fc=fc, ec=ec, alpha=al, ls=ls, lw=lw, hatch=h))
bx(-24, 29.0, 22, 30.6, "#2e6b3f", "#1c4428")
bx(-8.5, 26.0, 18.5, 29.0, "#c8e6c9", "#2e7d32", 0.5, ":")                     # module band (approximate height)
bx(5.0, 26.1, 11.5, 29.0, "#a5d6a7", "#1b5e20", 1.0, "-")                      # J20 body (projected along u)
bx(-14.3, 16.2, 14.9, 18.8, "#ffc400", "#8a6d10", 0.6)
bx(-14.0, 18.8, 14.0, 20.4, "#90caf9", "#1565c0")
bx(-13.4, 20.4, -8.6, 24.65, "none", "#b71c1c", 1, ":", 1.2)                    # today's vertical J1
bx(7.2, 20.4, 11.2, 24.65, "none", "#b71c1c", 1, ":", 1.2)                      # today's vertical J2
bx(-13.68, 20.4, -7.13, 23.3, "#455a64", "k")                                   # SM08B 2.9 tall
bx(-7.13, 20.4, -0.13, 23.3, "#ef9a9a", "#b71c1c", 0.5, "-", 0.8, "//")
bx(5.85, 20.4, 12.4, 23.3, "#6a1b9a", "k")
bx(12.4, 20.6, 15.4, 23.1, "#ce93d8", "#6a1b9a", 0.8)
sx.plot([-3.6, 0, 4, 6.5], [21.9, 22.4, 26.5, 27.5], color="#e65100", lw=3)
sx.plot([13.6, 13.6, 13.6], [14.9, 18.8, 21.8], color="#6a1b9a", lw=2.4)
sx.axvline(-15.7, color="#7e57c2", lw=2); sx.axvline(17.3, color="#b0a060", lw=2)
sx.text(-23.5, 30.9, "main board (underside z 29)", fontsize=9); sx.text(-23.5, 19.2, "reader z 18.8-20.4", fontsize=9)
sx.text(-15.5, 13.5, "solenoid 1.7 past the end", fontsize=9, color="#7e57c2"); sx.text(14.5, 13.5, "chassis 2.4 past the tray", fontsize=9, color="#6d5f20")
sx.text(-13.6, 24.9, "today: vertical, to z 24.65 + plug + cable bend", fontsize=8.5, color="#b71c1c")
sx.set_xlim(-24, 22); sx.set_ylim(12, 32); sx.set_aspect("equal"); sx.grid(alpha=0.25)
sx.set_title("SECTION along the board (J2 end right)", loc="left", fontsize=12, weight="bold")

leg = [("#455a64", "J1 = JST SM08B-SRSS-TB side-entry (C160407, already on the main board as J20), 2.9 tall instead of 4.25 + the plug"),
       ("#ef9a9a", "J1 plug lane, 7 x 10.2: kept free of parts (same rule as the main board's connectors)"),
       ("#e65100", "8-wire cable J1 -> J20: the two mouths face each other, about 25 mm (today's cable loops up and over)"),
       ("#6a1b9a", "J2 = JST SM02B-SRSS-TB side-entry (C160402, already on the main board as J14-J16), mouth at the notch"),
       ("#ce93d8", "J2's plug sits over the notch: the coil cable comes up through tray + notch and turns straight in"),
       ("#9e9e9e", "today's reader parts: the ones in the lane (U1, Y1, decoupling, R6 / R7) move into the green area"),
       ("#a5d6a7", "J20 on the main board's underside (projected), mouth facing the reader's J1; U6 module dotted"),
       ("#7e57c2", "kick solenoid, past the near end: nothing can stick out there"),
       ("#efe7c8", "chassis wall, past the far end")]
for i, (f, t) in enumerate(leg):
    lg.text(0.0, 0.96 - i * 0.075, "■", color=f, fontsize=18, va="center", transform=lg.transAxes)
    lg.text(0.06, 0.96 - i * 0.075, t, fontsize=10, va="center", wrap=True, transform=lg.transAxes)
lg.text(0.0, 0.22, "Needs (after approval):\n 1. schematic: J1 -> SM08B, J2 -> SM02B (both in stock, Extended)\n 2. reader board re-placed round the J1 lane, re-routed,\n    DRC + pad-centre tidy\n 3. FreeCAD: new connector models, check the J1-J20 cable\n    and J2 over the notch; the floor's NFC-wire path unchanged\n 4. BOM / CPL for the reader",
        fontsize=10.5, va="top", transform=lg.transAxes, family="monospace")
fig.text(0.03, 0.955, "NFC reader: right-angle connectors (2D, to scale, mm)", fontsize=18, weight="bold")
fig.text(0.03, 0.925, "Off-board plug spots are all blocked (solenoid, wheels, chassis), so both plugs sit over the board. J1 faces J20 along the board; J2 faces the notch the coil cable already comes up through.", fontsize=11.5, color="#333")
plt.savefig(OUT, dpi=90)
print(OUT)
