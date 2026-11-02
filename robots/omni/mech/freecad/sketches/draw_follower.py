# 2D: Spider follower weight (section through the magazine, to scale). A printed cup holding an M10 washer (DIN 125,
# 20 x 10.5 x 2 mm, ~3 g) rides on the tag stack. Sim (dispense_test.py, 24 mm drops, no ledge): 3 g -> 10/10 singles.
import sys
OUT = sys.argv[1]
SC = 14.0
MC, R_IN, R_OUT = 42.5, 12.9, 14.5
FLOOR, FT, SLOT, TAG_T, N = 15.7, 1.6, 1.35, 0.9, 10
TOP = FLOOR + N * TAG_T + 3.0
RX, RZ, RR = 48.5, 8.0, 8.0
F_D, F_BASE, W_OD, W_ID, W_T = 24.6, 0.6, 20.0, 10.5, 2.0
el = []
def a(s): el.append(s)
X = lambda x: 40 + (x - 24) * SC; Z = lambda z: 120 + (34 - z) * SC
def R(x0, z0, x1, z1, fill, stroke="#333", sw=1, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<rect x="{X(min(x0,x1)):.1f}" y="{Z(max(z0,z1)):.1f}" width="{abs(x1-x0)*SC:.1f}" height="{abs(z1-z0)*SC:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
def lead(x, y, tx, ty, s, s2=None):
    a(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="#666" stroke-width="0.8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#666"/>')
    T(tx + 5, ty + 4, s, 13)
    if s2: T(tx + 5, ty + 20, s2, 12, col="#555")
T(40, 40, "Spider follower weight (2D section, to scale)", 22, w="bold")
T(40, 66, "Printed cup + M10 washer, ~3.4 g, rides on the stack. Fits in the 3 mm above the 10 tags: magazine height unchanged.", 14, col="#333")
a(f'<line x1="{X(24):.1f}" y1="{Z(0):.1f}" x2="{X(64):.1f}" y2="{Z(0):.1f}" stroke="#333" stroke-width="1.5"/>')
# magazine walls + floor (window open to the front)
R(MC - R_OUT, FLOOR - FT, MC - R_IN, TOP, "#d5dbe2", "#444")
R(MC + R_IN, FLOOR + SLOT, MC + R_OUT, TOP, "#d5dbe2", "#444")
R(MC - R_IN, FLOOR - FT, RX - 5.8, FLOOR, "#d5dbe2", "#444")
a(f'<circle cx="{X(RX):.1f}" cy="{Z(RZ):.1f}" r="{RR*SC:.1f}" fill="#222"/><circle cx="{X(RX):.1f}" cy="{Z(RZ):.1f}" r="{5.5*SC:.1f}" fill="#555"/>')
for i in range(N):
    R(MC - 12.5, FLOOR + i * TAG_T, MC + 12.5, FLOOR + (i + 1) * TAG_T - 0.06, "#8e4dd0" if i % 2 else "#7a3bc0", "#4a1f80", 0.5)
zf = FLOOR + N * TAG_T + 0.02
# follower cup: base 0.6 + rim, washer in the pocket
R(MC - F_D / 2, zf, MC + F_D / 2, zf + F_BASE, "#ffc400", "#8a6d10")
R(MC - F_D / 2, zf, MC - W_OD / 2 - 0.2, zf + F_BASE + W_T, "#ffc400", "#8a6d10")
R(MC + W_OD / 2 + 0.2, zf, MC + F_D / 2, zf + F_BASE + W_T, "#ffc400", "#8a6d10")
for s in (-1, 1):
    x0, x1 = (MC - W_OD / 2, MC - W_ID / 2) if s < 0 else (MC + W_ID / 2, MC + W_OD / 2)
    R(x0, zf + F_BASE, x1, zf + F_BASE + W_T, "#b9c0c8", "#555")
R(MC - W_ID / 2 + 0.6, zf + F_BASE, MC + W_ID / 2 - 0.6, zf + F_BASE + 1.4, "#ffc400", "#8a6d10")   # centre boss (locates the washer)
lead(X(MC + 7.5), Z(zf + F_BASE + 1.0), X(66), Z(30.5), "M10 washer (DIN 125): 20 x 10.5 x 2 mm, steel, ~3.0 g", "the weight; any ~3 g washer or coin works")
lead(X(MC - 11.5), Z(zf + 0.3), X(66), Z(26.5), f"printed cup, {F_D} mm: 0.6 mm clear of the 25.8 bore each side", "a close fit so it can't tilt or flip; ~0.4 g")
lead(X(MC), Z(FLOOR + 4), X(66), Z(21.5), "10 tags, 25 x 0.9 mm", None)
lead(X(MC + R_IN + 0.5), Z(FLOOR + 0.7), X(66), Z(16.5), "one-tag slot 1.35 mm, window open to the front", None)
lead(X(RX + 5), Z(RZ - 5), X(66), Z(9.5), "16 mm TPU roller", None)
T(40, Z(-3) + 10, f"Top of the cup z {zf + F_BASE + W_T:.1f} with a full stack; magazine top {TOP:.1f} (unchanged). Reload: lift the cup out, drop tags in, cup back.", 13, col="#333")
T(40, Z(-3) + 30, "Sim (standalone, 24 mm drops): 0 g -> 10/11 and 10/12 singles;  3 g -> 10/10 in both friction cases;  6 and 10 g -> one miss with sticky tags.", 13, col="#1a7f37", w="bold")
T(40, Z(-3) + 50, "Open top, no lid: if the robot flips over the cup can fall out (a lid would raise the magazine and close the 2 mm gap to the board).", 13, col="#c62828")
W, H = int(X(110)), int(Z(-3) + 70)
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
