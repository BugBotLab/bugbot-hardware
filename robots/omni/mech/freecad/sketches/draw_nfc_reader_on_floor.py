# 2D (to scale): the NFC reader moved onto the antenna floor PCB (2026-10-31, to save the reader board's JLC order).
# Plan of the floor PCB's underside (looking down through the floor, front = right) with the reader's parts packed into
# the biggest free patch inside the loop, the loop fed right beside it, and 12 solder holes at the centre for the two
# cables (reader 8 + underglow 3 wires; hand-soldered through-hole). Every part on the underside: one-sided assembly.
# Geometry from the KiCad boards (dumped by KiCad python): floor outline, wheel windows, loop, LEDs, clamp holes.
# usage: python draw_nfc_reader_on_floor.py boards.json out.png
import sys, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon as MPoly
from shapely.geometry import Polygon, Point, box
from shapely import affinity
B = json.load(open(sys.argv[1])); OUT = sys.argv[2]
F, R = B["BugBot_NFCfloor"], B["BugBot_NFC"]
LOOP_IN, LOOP_GAP = 39.2, 2.2          # loop's inner turn radius; keep the reader this far inside it
WIN_GAP, CENTRE_KEEP = 1.0, 14.5       # parts to the wheel-window edges; LED ring + clamp heads (r 12.2 + 2.3)
NOTCH = ((37.43, 0.0), 17.2)           # ball notch arc + the loop round it
BLOCK_H = 13.0                         # reader block depth after re-packing (now 17.2 with the two connectors)
HOLE_PITCH, HOLE_ROWS, HOLE_COLS = 1.27, 2, 6
OPENING = (7.6, 8.4)                   # floor plate's centre opening the wires go up through
REMOVED = {"J1", "J2", "H1"}           # reader connectors + mounting hole: gone on the floor PCB


def arc_pts(p0, pm, p1, n=40):
    (x1, y1), (x2, y2), (x3, y3) = p0, pm, p1
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a0, am, a1 = (math.atan2(y - uy, x - ux) for x, y in (p0, pm, p1))
    def norm(a): return (a - a0) % (2 * math.pi)
    ccw = norm(am) < norm(a1)
    span = norm(a1) if ccw else -((a0 - a1) % (2 * math.pi))
    return [(ux + r * math.cos(a0 + span * k / n), uy + r * math.sin(a0 + span * k / n)) for k in range(n + 1)]


edges = [e for e in F["edge"] if not isinstance(e, dict)]
holes = [e for e in F["edge"] if isinstance(e, dict)]
lines = [arc_pts(*e) if len(e) == 3 else e for e in edges]
# wheel windows: closed chains of segments away from the outer rim
chains = []
for ln in lines:
    for c in chains:
        if math.dist(c[-1], ln[0]) < 0.01: c.extend(ln[1:]); break
        if math.dist(c[0], ln[-1]) < 0.01: c[:0] = ln[:-1]; break
    else: chains.append(list(ln))
for _ in range(3):                                                      # merge chains that now touch
    merged = []
    for c in chains:
        for m in merged:
            if math.dist(m[-1], c[0]) < 0.01: m.extend(c[1:]); break
            if math.dist(m[0], c[-1]) < 0.01: m[:0] = c[:-1]; break
        else: merged.append(c)
    chains = merged
polys = sorted((Polygon(c) for c in chains if len(c) > 3), key=lambda p: -p.area)
outer, windows = polys[0], polys[1:]

free = Point(0, 0).buffer(LOOP_IN - LOOP_GAP)
for w in windows: free = free.difference(w.buffer(WIN_GAP))
free = free.difference(Point(0, 0).buffer(CENTRE_KEEP)).difference(Point(*NOTCH[0]).buffer(NOTCH[1]))
best = None                                                             # longest BLOCK_H-deep block in the free patch
for rot in range(0, 180, 5):
    g = affinity.rotate(free, -rot, origin=(0, 0))
    minx, miny, maxx, maxy = g.bounds
    for k in range(int((maxy - miny - BLOCK_H) / 0.5) + 1):
        y0 = miny + 0.5 * k; run = 0
        for j in range(int((maxx - minx) / 0.5) + 1):
            x = minx + 0.5 * j
            if g.contains(box(x, y0, x + 0.5, y0 + BLOCK_H)):
                run += 0.5
                if best is None or run > best[0]: best = (run, rot, x + 0.5 - run, y0)
            else: run = 0
L, rot, bx0, by0 = best
block = affinity.rotate(box(bx0, by0, bx0 + L, by0 + BLOCK_H), rot, origin=(0, 0))
bc = block.centroid

fig = plt.figure(figsize=(17, 10.4))
ax = fig.add_axes([0.02, 0.06, 0.52, 0.86])
x, y = outer.exterior.xy; ax.fill(x, y, color="#f2f2ee", ec="#888", lw=1, zorder=0)
for w in windows: x, y = w.exterior.xy; ax.fill(x, y, color="#cfd8dc", ec="#888", zorder=1)
x, y = free.exterior.xy if free.geom_type == "Polygon" else max(free.geoms, key=lambda g: g.area).exterior.xy
ax.fill(x, y, color="#c8e6c9", alpha=0.35, zorder=1)
loop_nets = {n for a, b, w, layer, n in F["tracks"] if a and math.hypot(*a) > LOOP_IN}
def is_lead(a, b):                                                      # loop-net track inside the loop, not round the notch
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return math.hypot(*m) < LOOP_IN - 1 and math.dist(m, NOTCH[0]) > NOTCH[1] - 4
old = []
for a, b, w, layer, n in F["tracks"]:
    if b and n in loop_nets:
        if is_lead(a, b): old.append((a, b))
        else: ax.plot([a[0], b[0]], [a[1], b[1]], color="#c9a227", lw=0.5, zorder=2)
for h in holes:
    ax.add_patch(Circle(h["circle"], h["r"], fc="white", ec="#111", lw=0.7, zorder=6))
for f in F["fps"]:
    if f["ref"].startswith(("D", "C")):
        (x0, y0), (x1, y1) = f["bb"]
        ax.add_patch(Rectangle((x0, y1), x1 - x0, y0 - y1, fc="#fafafa" if f["ref"][0] == "D" else "#ffe0b2", ec="#333", lw=0.5, zorder=5))
# old feed (leads to the centre) crossed out; new feed beside the reader
for a, b in old: ax.plot([a[0], b[0]], [a[1], b[1]], color="#c62828", lw=0.6, ls=":", zorder=2)
# reader parts: the reader board's layout (less J1/J2/H1), squeezed into the block's depth, turned + moved into place
parts = [f for f in R["fps"] if f["ref"] not in REMOVED]
xs = [p for f in parts for p in (f["bb"][0][0], f["bb"][1][0])]; ys = [p for f in parts for p in (f["bb"][0][1], f["bb"][1][1])]
sx, sy = L / (max(xs) - min(xs)), BLOCK_H / (max(ys) - min(ys)); cx0, cy0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
def place(u, v):
    u, v = (u - cx0) * sx, (v - cy0) * sy
    return (bc.x + u * ca - v * sa, bc.y + u * sa + v * ca)
x, y = block.exterior.xy; ax.fill(x, y, color="#e3f2fd", ec="#1565c0", lw=1.4, zorder=4)
for f in parts:
    (x0, y0), (x1, y1) = f["bb"]; mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = abs(x1 - x0) / 2, abs(y1 - y0) / 2
    pts = [place(mx + du * hw, my + dv * hh) for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    col = "#90caf9" if f["ref"] == "U1" else ("#fff59d" if f["ref"] == "Y1" else "#ffffff")
    ax.add_patch(MPoly(pts, closed=True, fc=col, ec="#0d47a1", lw=0.5, zorder=5))
    if f["ref"] in ("U1", "Y1"): ax.text(*place(mx, my), f["ref"], fontsize=6.5, ha="center", va="center", zorder=6)
feed_a = math.atan2(bc.y, bc.x); fp = (LOOP_IN * math.cos(feed_a), LOOP_IN * math.sin(feed_a))
near = min(block.exterior.coords, key=lambda p: math.dist(p, fp))
ax.plot([near[0], fp[0]], [near[1], fp[1]], color="#2e7d32", lw=2.2, zorder=6)
# 12 solder holes at the centre (replace J2 and the coil's two holes), inside the floor plate's opening
ax.add_patch(Rectangle((-OPENING[0] / 2, -OPENING[1] / 2), *OPENING, fc="none", ec="#6a1b9a", ls="--", lw=1, zorder=6))
for i in range(HOLE_COLS):
    for j in range(HOLE_ROWS):
        hx, hy = (i - (HOLE_COLS - 1) / 2) * HOLE_PITCH, (j - (HOLE_ROWS - 1) / 2) * 2 * HOLE_PITCH
        ax.add_patch(Circle((hx, hy), 0.5, fc="#e0b040", ec="#7a5c00", lw=0.5, zorder=7))
ax.annotate(f"reader parts (WS1850S U1, crystal Y1, matching network,\n~30 x 0402) packed into {L:.0f} x {BLOCK_H:g} mm, underside",
            (bc.x, bc.y), (-43, -40), fontsize=9, arrowprops=dict(arrowstyle="->", color="#1565c0"))
ax.annotate("loop fed here: matching network\n~3 mm from the loop (was a 25 mm\nlead + the coil cable)", fp, (-43, 37), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="#2e7d32"))
ax.annotate("12 solder holes (1.27 mm) in the\nfloor plate's 7.6 x 8.4 opening:\nreader cable 8 + underglow 3 (+1 GND)", (0, 0), (14, -40), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="#6a1b9a"))
ax.annotate("old feed to the centre: removed", max((p for ab in old for p in ab), key=lambda p: math.hypot(*p)) if old else (0, 0), (-43, 22), fontsize=8.5, color="#c62828",
            arrowprops=dict(arrowstyle="->", color="#c62828"))
ax.set_aspect("equal"); ax.set_xlim(-45, 45); ax.set_ylim(-45, 45); ax.grid(alpha=0.2)
ax.set_title("Floor PCB underside, looking down through the floor (front = right). Green = room left for parts", fontsize=9.5)
# section
s = fig.add_axes([0.57, 0.62, 0.41, 0.28]); Z = 4
def bxs(x0, x1, z0, z1, fc, ec="#333"): s.add_patch(Rectangle((x0, z0 * Z), x1 - x0, (z1 - z0) * Z, fc=fc, ec=ec, lw=0.8))
bxs(0, 40.6, 6.5, 8.1, "#d6d6cc"); s.text(28, 7.2 * Z, "printed floor plate (unchanged)", ha="center", fontsize=8)
bxs(0, 40.6, 4.9, 6.5, "#f2f2ee", "#888"); s.text(28, 5.5 * Z, "floor PCB 1.6, white mask", ha="center", fontsize=8)
bxs(8, 9.7, 3.2, 4.9, "#fafafa"); s.text(8.8, 2.6 * Z, "LED 1.7", ha="center", fontsize=7.5)
bxs(20, 27, 4.0, 4.9, "#90caf9"); s.text(23.5, 3.2 * Z, "reader parts ≤ 0.9\n(4.0 mm to the table)", ha="center", fontsize=7.5)
bxs(-0.5, 1.5, 6.5, 12, "#e0b040"); s.text(2, 10.5 * Z, "wires up through\nthe opening", fontsize=7.5)
s.axhline(0, color="#795548", lw=2); s.text(30, 0.4, "table", fontsize=8)
s.set_xlim(-1, 42); s.set_ylim(-1, 13 * Z); s.set_yticks([0, 3.2 * Z, 4.9 * Z, 6.5 * Z]); s.set_yticklabels(["0", "3.2", "4.9", "6.5"])
s.set_title("Section (heights x4): everything hangs under the board, nothing above it changes", fontsize=9.5)
t = fig.add_axes([0.57, 0.03, 0.41, 0.55]); t.axis("off")
t.text(0, 1, "\n".join([
 "What changes:",
 "  - reader board (28 x 18), its printed tray and the 2-wire coil cable: GONE",
 "  - its parts move onto the floor PCB's underside, next to the loop's feed",
 "  - floor J2 (SMD JST, top) -> 12 plated solder holes: every SMD part is",
 "    now on ONE side -> JLC Economic assembly instead of Standard",
 "  - main J20 (NFC, JST-SH 8) + J17 (underglow): unchanged; the two cables",
 "    are bought pre-crimped one end, the other end soldered into the holes",
 "  - floor plate, chassis, main board: unchanged (3 tray posts left unused)",
 "",
 "JLC, 5 sets (VAT incl.): reader order gone + floor Standard -> Economic",
 "  ~ -£100 per order (and the floor board's placement file gets its",
 "  Bottom side right: today it says Top for the LEDs, a bug)",
 "",
 "Risk: the reader's ground copper sits inside the loop (~4 % of its area)",
 "  and the feed moves, so the tuning shifts. The matching values were",
 "  never measured anyway: the wire-loop bench test planned before ordering",
 "  should be done with the reader parts in this spot, and the first",
 "  boards may need C6/C8/C9 changed (same as before).",
 "Reader parts re-placed + routed by script; DRC + JLC check before order."]),
 va="top", fontsize=8.8, family="monospace")
fig.suptitle("NFC reader on the antenna floor PCB: one board instead of two (2D for approval, to scale)", fontsize=14, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT, "block", round(L, 1), "x", BLOCK_H, "rot", rot, "centre", round(bc.x, 1), round(bc.y, 1))
