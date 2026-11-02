# 2D: Spider spring presser (section through the magazine, to scale). A lever pivots on a post on the front wall top;
# its long arm reaches back over the stack with a small free roller; a soft compression spring under the short front
# tail pushes the tail up, so the roller presses the stack down. Full stack solid, empty dashed.
import sys, math
OUT = sys.argv[1]
SC = 13.0
MC, R_IN, R_OUT = 42.5, 12.9, 14.5
FLOOR, FT, SLOT, TAG_T, N = 15.7, 1.6, 1.35, 0.9, 10
TOP = FLOOR + N * TAG_T + 3.0                      # 27.7 (magazine top, unchanged)
RX, RZ, RR = 48.5, 8.0, 8.0
PIV = (57.5, 29.5)                                 # lever pivot (pin on a post at the front wall top)
A, B = 13.0, 4.5                                   # long arm (to the roller centre), short tail (to the spring seat)
PR = 2.0                                           # presser roller radius (4 mm, free on a 1 mm pin)
el = []
def a(s): el.append(s)
X = lambda x: 40 + (x - 24) * SC; Z = lambda z: 130 + (40 - z) * SC
def R(x0, z0, x1, z1, fill, stroke="#333", sw=1, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<rect x="{X(min(x0,x1)):.1f}" y="{Z(max(z0,z1)):.1f}" width="{abs(x1-x0)*SC:.1f}" height="{abs(z1-z0)*SC:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def C(x, z, r, fill, stroke="#333", sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<circle cx="{X(x):.1f}" cy="{Z(z):.1f}" r="{r*SC:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def L(x0, z0, x1, z1, col="#333", sw=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<line x1="{X(x0):.1f}" y1="{Z(z0):.1f}" x2="{X(x1):.1f}" y2="{Z(z1):.1f}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"{d}/>')
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
def lead(x, y, tx, ty, s, s2=None):
    a(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="#666" stroke-width="0.8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#666"/>')
    T(tx + 5, ty + 4, s, 13)
    if s2: T(tx + 5, ty + 20, s2, 12, col="#555")

def lever_angle(stack_top):
    """angle (rad, below horizontal) that puts the roller on the stack top"""
    zc = stack_top + PR
    return math.asin((PIV[1] - zc) / A)
def lever(stack_top, dash=None, op=1.0):
    th = lever_angle(stack_top)
    rx, rz = PIV[0] - A * math.cos(th), PIV[1] - A * math.sin(th)
    tx, tz = PIV[0] + B * math.cos(th), PIV[1] + B * math.sin(th)
    L(tx, tz, rx, rz, "#b8860b" if not dash else "#b8860b", 9 if not dash else 2, dash)
    if not dash:
        L(tx, tz, rx, rz, "#ffc400", 7)
    C(rx, rz, PR, "#222" if not dash else "none", "#000", 1, dash)
    return th, (rx, rz), (tx, tz)

T(40, 40, "Spider spring presser (2D section, to scale)", 22, w="bold")
T(40, 66, "A lever on the front wall: a soft spring lifts its short tail, its long arm presses a 4 mm roller onto the stack.", 14, col="#333")
T(40, 86, "Solid: full stack (10 tags).  Dashed: last tag.  Magazine height unchanged; the lever stays below z 32 (camera at 47.6).", 14, col="#333")
a(f'<line x1="{X(24):.1f}" y1="{Z(0):.1f}" x2="{X(70):.1f}" y2="{Z(0):.1f}" stroke="#333" stroke-width="1.5"/>')
# magazine section: back wall, front wall above the slot (with a slot for the lever), floor
R(MC - R_OUT, FLOOR - FT, MC - R_IN, TOP, "#d5dbe2", "#444")
R(MC + R_IN, FLOOR + SLOT, MC + R_OUT, TOP, "#d5dbe2", "#444")
R(MC + R_IN - 0.05, 17.0, MC + R_OUT + 0.05, TOP + 0.05, "#ffffff", "#c62828", 1, "3 2")      # lever slot in the front wall
R(MC - R_IN, FLOOR - FT, RX - 5.8, FLOOR, "#d5dbe2", "#444")
# post + spring seat on the front of the tube
R(MC + R_OUT, 22.0, PIV[0] + 1.6, 31.0, "#e8eaee", "#444")                                     # pivot post (printed with the magazine)
R(PIV[0] + 1.6, 22.0, PIV[0] + B + 2.0, 24.0, "#e8eaee", "#444")                                # spring seat ledge
C(PIV[0], PIV[1], 0.75, "#888", "#333")
C(RX, RZ, RR, "#222", "#000"); C(RX, RZ, 5.5, "#555", "#000")
for i in range(N):
    R(MC - 12.5, FLOOR + i * TAG_T, MC + 12.5, FLOOR + (i + 1) * TAG_T - 0.06, "#8e4dd0" if i % 2 else "#7a3bc0", "#4a1f80", 0.5)
th1, r1, t1 = lever(FLOOR + N * TAG_T)
th0, r0, t0 = lever(FLOOR + TAG_T, "4 3")
R(MC - 12.5, FLOOR, MC + 12.5, FLOOR + TAG_T, "none", "#7a3bc0", 1, "4 3")
# spring (zigzag) between the seat and the tail, full-stack position
sx = PIV[0] + B
zt, zb = t1[1] - 0.5, 24.0
pts = [(sx, zb)]
for k in range(1, 10):
    pts.append((sx + (0.9 if k % 2 else -0.9), zb + (zt - zb) * k / 10))
pts.append((sx, zt))
a('<polyline points="' + " ".join(f"{X(x):.1f},{Z(z):.1f}" for x, z in pts) + '" fill="none" stroke="#1565c0" stroke-width="1.8"/>')
# numbers
travel = (FLOOR + N * TAG_T) - (FLOOR + TAG_T)
sweep = math.degrees(th0 - th1)
tail_full, tail_empty = t1[1], t0[1]
spring_stroke = tail_empty - tail_full
lead(X(r1[0]), Z(r1[1]), X(66), Z(36), "presser roller 4 mm, 6 wide, free on a 1 mm pin", "the last tag rolls out under it, no rubbing")
lead(X((r1[0] + PIV[0]) / 2), Z((r1[1] + PIV[1]) / 2), X(66), Z(32), f"lever 3 mm wide: arm {A:g} mm, tail {B:g} mm (ratio {A/B:.1f} : 1)", "lifts up and back for reloading")
lead(X(PIV[0]), Z(PIV[1]), X(66), Z(28), "pivot: 1.5 mm pin in a post on the front wall", "(above the slot: the tag exit stays clear)")
lead(X(sx + 0.9), Z((zt + zb) / 2), X(66), Z(24), f"soft spring under the tail: stroke {spring_stroke:.1f} mm over the whole stack", "e.g. 0.2 mm wire, 3 mm OD, ~20 coils, k ~0.04 N/mm")
lead(X(MC + R_IN + 0.8), Z(20), X(66), Z(20), "slot in the front wall for the lever (3.6 wide)", None)
T(40, Z(-3) + 10, f"Stack top travels {travel:.1f} mm; the lever sweeps {sweep:.0f} deg; the tail moves {spring_stroke:.1f} mm.", 13, col="#333")
fs0, k = 0.15, 0.04                                      # spring preload at full stack (N) and rate (N/mm): ESTIMATES
f_full = fs0 * B / A
f_empty = (fs0 + k * spring_stroke) * B / A
T(40, Z(-3) + 30, f"Force on the stack: spring {fs0:.2f} N at full stack, {fs0 + k*spring_stroke:.2f} N at the last tag x {B:g}/{A:g} "
                  f"= {f_full:.3f} .. {f_empty:.3f} N  (= {f_full/0.00981:.0f} .. {f_empty/0.00981:.0f} g of weight; sim: 3 g best)", 13, col="#1a7f37", w="bold")
T(40, Z(-3) + 50, "Spring strength is the open question: it wants a very soft one. I'd test the force range in the sim before choosing.", 13, col="#c62828")
W, H = int(X(118)), int(Z(-3) + 70)
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
