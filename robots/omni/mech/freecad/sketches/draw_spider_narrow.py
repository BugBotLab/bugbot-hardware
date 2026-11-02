# 2D: narrower Spider layout. SG90 stands on end beside the magazine, shaft +X; roller axis turned to X; tag leaves
# through a side slot on the right (-Y). Top view + front view, to scale. Geometry from the BugBot/Spider models.
import sys, math
OUT = sys.argv[1]
SC = 6.5
el = []
def a(s): el.append(s)
def st(stroke, sw, dash, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f' stroke="{stroke}" stroke-width="{sw}"{d} fill-opacity="{op}"'
def text(x, y, s, size=12, anchor="start", col="#111", weight="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{weight}" font-family="Segoe UI, Arial">{s}</text>')
def line(x0, y0, x1, y1, col="#666", sw=1, dash=None):
    a(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"{st(col, sw, dash)}/>')
def lead(x, y, tx, ty, s, s2=None, anchor="start"):
    line(x, y, tx, ty, "#666", 0.8); a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#666"/>')
    dx = 5 if anchor == "start" else -5
    text(tx + dx, ty + 4, s, 12, anchor)
    if s2: text(tx + dx, ty + 19, s2, 11, anchor, "#555")

# geometry (robot frame, mm)
MC, MY = 47.0, -4.0                     # magazine centre (x, y): moved 4 mm right
R_IN, R_OUT = 12.9, 14.5
FLOOR, TOP = 11.2, 42.2
ROLL_Y, ROLL_Z, ROLL_R = MY - 4.0, 7.25, 4.25   # roller now on an X axis, 4 mm toward the exit side
SV_X0, SV_BODY, SV_BOSS, SV_TIP = 38.5, 61.2, 64.5, 67.7   # SG90 height along +X: case, top boss, spline tip
SV_Y0, SV_Y1 = 12.2, 24.5                # SG90 width 12.3 along Y
SV_SY = (SV_Y0 + SV_Y1) / 2
EAR_Z0, BODY_Z0, BODY_Z1, EAR_Z1 = 3.0, 7.85, 30.35, 35.2  # SG90 length along Z (ears 32.2, case 22.5)
SH_Z = BODY_Z0 + 5.65                    # output shaft near the lower end -> 13.5
P_S, P_R = 6.0, 3.0                      # pulley radii (12 / 6 mm, 2:1)
BELT_X = 66.2

# ================= TOP VIEW (X right, Y up) =================
OX, OY = 40, 120
X = lambda x: OX + (x + 45) * SC; Y = lambda y: OY + (52 - y) * SC
def R(x0, y0, x1, y1, fill, stroke="#333", sw=1, dash=None, op=1):
    a(f'<rect x="{X(min(x0,x1)):.1f}" y="{Y(max(y0,y1)):.1f}" width="{abs(x1-x0)*SC:.1f}" height="{abs(y1-y0)*SC:.1f}" fill="{fill}"{st(stroke, sw, dash, op)}/>')
def C(x, y, r, fill, stroke="#333", sw=1, dash=None, op=1):
    a(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{r*SC:.1f}" fill="{fill}"{st(stroke, sw, dash, op)}/>')
text(X(-45), OY - 70, "Narrower Spider layout (2D, to scale)", 22, weight="bold")
text(X(-45), OY - 44, "SG90 stands on end beside the magazine, shaft forward; roller turned 90 deg; tag goes out the RIGHT side", 14, col="#333")
text(X(-45), OY - 16, "TOP VIEW", 15, weight="bold")
# chassis: circle R 40.6 cut flat at x 37.5 (pocket notch at floor level shown dashed)
a(f'<clipPath id="cf"><rect x="{X(-45):.1f}" y="{Y(45):.1f}" width="{(37.5+45)*SC:.1f}" height="{90*SC:.1f}"/></clipPath>')
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{40.6*SC:.1f}" fill="#e9d9a6" stroke="#8a7a40" stroke-width="1.2" clip-path="url(#cf)"/>')
C(44.4, 0, 20, "#fff", "#8a7a40", 1, "4 3")
text(X(-30), Y(-2), "chassis", 13, col="#6d5f2c")
# original BugBot outline: chassis + gripper footprint (x to 71.2, y +/-25)
a(f'<path d="M{X(37.5):.1f},{Y(25):.1f} L{X(71.2):.1f},{Y(25):.1f} L{X(71.2):.1f},{Y(-25):.1f} L{X(37.5):.1f},{Y(-25):.1f}" fill="none"{st("#1a7f37", 1.6, "7 4")}/>')
text(X(71.2) + 6, Y(-25) + 4, "original BugBot outline", 12, col="#1a7f37")
text(X(71.2) + 6, Y(-25) + 19, "(gripper reached x 71.2, y +/-25)", 11, col="#1a7f37")
# wheels 1 and 3 (front), mast, front board
R(0.9, 8.6, 27.0, 35.7, "#cfd6de", "#555"); text(X(4), Y(22), "wheel 1", 11, col="#333")
R(-0.2, -32.6, 24.6, -13.7, "#cfd6de", "#555"); text(X(3), Y(-24), "wheel 3", 11, col="#333")
R(14.2, -20, 24.0, 20, "#e2b93b", "#8a6d10"); text(X(19.1), Y(0), "mast", 11, "middle", "#5b4708")
# current (outboard) servo, ghost
R(40.5, 17.0, 72.7, 47.8, "#ff6b6b", "#c62828", 1.2, "5 3", 0.18)
text(X(56.6), Y(44.0), "current servo + holder", 11, "middle", "#c62828")
text(X(56.6), Y(40.0) + 6, "(y to +47.8: 7.2 mm outside)", 11, "middle", "#c62828")
# magazine bracket (unchanged idea: plate on mast face, 2 x M2 at y +/-17)
R(24.0, -20, 27.0, 20, "#b9c2cc", "#555")
R(27.0, MY - 5.5, MC - R_OUT + 1, MY + 5.5, "#b9c2cc", "#555")
# magazine
C(MC, MY, R_OUT, "#d5dbe2", "#444", 1.2); C(MC, MY, R_IN, "#f6f8fa", "#666", 0.8)
text(X(MC), Y(MY + 7), "magazine", 12, "middle", "#333")
text(X(MC), Y(MY + 7) + 15, "20 tags", 11, "middle", "#555")
# roller (axis along X, under the floor), shaft out to the belt plane
R(42.0, ROLL_Y - ROLL_R, 52.0, ROLL_Y + ROLL_R, "#222", "#000", 1, None, 0.85)
R(40.0, ROLL_Y - 1, 67.6, ROLL_Y + 1, "#9aa0a6", "#555", 0.6)
# side exit slot + tag path
R(MC - 13.5, MY - R_OUT - 0.3, MC + 13.5, MY - R_IN, "#fff", "#c62828", 1.2)
C(MC, -36.0, 12.5, "#ffe9a8", "#b08800", 1, "4 3", 0.8)
text(X(MC), Y(-36.0) + 4, "tag drops here", 11, "middle", "#7a5d00")
line(X(MC + 16), Y(MY - 6), X(MC + 16), Y(-30), "#b08800", 2)
a(f'<path d="M{X(MC+16)-5:.1f},{Y(-30)-8:.1f} L{X(MC+16):.1f},{Y(-30):.1f} L{X(MC+16)+5:.1f},{Y(-30)-8:.1f}" fill="none" stroke="#b08800" stroke-width="2"/>')
# servo (new): case, top boss, spline; pulleys + belt in the plane x 66.2
R(SV_X0, SV_Y0, SV_BODY, SV_Y1, "#3b5ea8", "#1d3466", 1.2)
R(SV_BODY, SV_SY - 5.9, SV_BOSS, SV_SY + 5.9, "#3b5ea8", "#1d3466", 1)
R(SV_BOSS, SV_SY - 2.4, SV_TIP, SV_SY + 2.4, "#ddd", "#555", 0.8)
text(X((SV_X0 + SV_BODY) / 2), Y(SV_SY) + 5, "SG90 (on end)", 12, "middle", "#fff", "bold")
R(65.0, SV_SY - P_S, 67.4, SV_SY + P_S, "#e67e22", "#9a4f0c")
R(65.0, ROLL_Y - P_R, 67.4, ROLL_Y + P_R, "#e67e22", "#9a4f0c")
line(X(BELT_X), Y(SV_SY + P_S), X(BELT_X), Y(ROLL_Y - P_R), "#111", 2.2)
lead(X(66.2), Y(3), X(80), Y(8), "O-ring belt 2:1", "plane x 66, in front of the tube")
lead(X(47), Y(ROLL_Y - ROLL_R + 0.5), X(80), Y(-10), "roller 8.5 mm, axis now along X", "pushes the bottom tag to -Y")
lead(X(MC), Y(MY - R_OUT), X(80), Y(-18), "side slot 1.35 mm + gate (right side)")
# dimensions
def dimy(x, y0, y1, s):
    line(X(x), Y(y0), X(x), Y(y1), "#1a7f37", 0.9)
    for yy in (y0, y1): line(X(x) - 4, Y(yy), X(x) + 4, Y(yy), "#1a7f37", 0.9)
    text(X(x) + 5, (Y(y0) + Y(y1)) / 2 + 4, s, 11, col="#1a7f37")
text(X(SV_X0), Y(25) - 6, "widest point y +24.5: 0.5 mm inside the old outline", 11, col="#1a7f37")
text(X(-45), Y(-50), "servo to wheel 1: 11.5 mm (x)  |  servo to chassis front: 3.5 mm  |  servo to main board edge: 2.1 mm  |  servo to tube: 1.7 mm", 11, col="#333")
TOP_BOTTOM = Y(-50)

# ================= FRONT VIEW (from +X: robot's left on the right) =================
OX2, OZ2 = 40, TOP_BOTTOM + 70 + 82 * SC
U = lambda y: OX2 + (y + 45) * SC; W = lambda z: OZ2 - z * SC
def RF(y0, z0, y1, z1, fill, stroke="#333", sw=1, dash=None, op=1):
    a(f'<rect x="{U(min(y0,y1)):.1f}" y="{W(max(z0,z1)):.1f}" width="{abs(y1-y0)*SC:.1f}" height="{abs(z1-z0)*SC:.1f}" fill="{fill}"{st(stroke, sw, dash, op)}/>')
def CF(y, z, r, fill, stroke="#333", sw=1, dash=None, op=1):
    a(f'<circle cx="{U(y):.1f}" cy="{W(z):.1f}" r="{r*SC:.1f}" fill="{fill}"{st(stroke, sw, dash, op)}/>')
text(U(-45), W(82) - 14, "FRONT VIEW (looking at the robot's nose; its left is on your right)", 15, weight="bold")
line(U(-45), W(0), U(52), W(0), "#333", 1.5); text(U(-44), W(0) + 16, "floor", 11, col="#555")
RF(-40.6, 6.5, 40.6, 29.0, "#e9d9a6", "#8a7a40", 1, None, 0.55)
RF(-40.6, 25.5, 40.6, 27.1, "#2e6b3f", "#1c4428")
RF(-20, 30.6, 20, 61.4, "#e2b93b", "#8a6d10", 1, None, 0.9)
a(f'<path d="M{U(-15):.1f},{W(62):.1f} A{15*SC:.1f},{18.8*SC:.1f} 0 0 1 {U(15):.1f},{W(62):.1f} Z" fill="#dfe3e8" stroke="#666"/>')
CF(0, 44.1, 3.2, "#223", "#000"); text(U(4.5), W(44.1) + 4, "camera", 11, col="#222")
RF(-4, 51.6, 4, 53.6, "#333", "#000"); text(U(4.5), W(52.6) + 4, "ToF", 11, col="#222")
for yy in (-40.6, 40.6): line(U(yy), W(0), U(yy), W(70), "#1a7f37", 1.2, "7 4")
for yy in (-25, 25): line(U(yy), W(0), U(yy), W(55), "#1a7f37", 1, "3 3")
text(U(40.6) - 4, W(70) - 6, "chassis +/-40.6", 11, "end", "#1a7f37")
text(U(25) + 4, W(55) - 6, "gripper +/-25", 11, col="#1a7f37")
# old servo ghost
RF(17.0, 13.1, 47.8, 25.4, "#ff6b6b", "#c62828", 1.2, "5 3", 0.18)
# magazine (section through its centre), floor, side slot, tags
RF(MY - R_OUT, FLOOR - 1.6, MY + R_OUT, TOP, "#d5dbe2", "#444", 1.2)
RF(MY - R_IN, FLOOR, MY + R_IN, TOP, "#f6f8fa", "#666", 0.8)
for i in range(20):
    RF(MY - 12.5, FLOOR + i * 0.9, MY + 12.5, FLOOR + (i + 1) * 0.9 - 0.12, "#ffe9a8", "#b08800", 0.4)
RF(MY - 12.5, FLOOR + 18, MY + 12.5, FLOOR + 22, "#888", "#444", 0.8)
RF(MY - R_OUT - 0.1, FLOOR, MY - R_IN, FLOOR + 1.35, "#fff", "#c62828", 1.2)
RF(-43.5, 0.0, -18.5, 0.9, "#ffe9a8", "#b08800", 0.8)
a(f'<path d="M{U(MY-R_OUT-1):.1f},{W(FLOOR+0.6):.1f} Q{U(-36):.1f},{W(FLOOR+0.6):.1f} {U(-33):.1f},{W(2.5):.1f}" fill="none" stroke="#b08800" stroke-width="2" stroke-dasharray="4 3"/>')
text(U(-44), W(FLOOR + 6), "tag out", 12, col="#7a5d00")
# roller + pulleys + belt (all seen end-on now)
CF(ROLL_Y, ROLL_Z, ROLL_R, "#222", "#000")
CF(SV_SY, SH_Z, P_S, "#e67e22", "#9a4f0c", 1, None, 0.9)
CF(ROLL_Y, ROLL_Z, P_R, "none", "#e67e22", 1.5)
# open-belt tangents
c1, c2, r1, r2 = (SV_SY, SH_Z), (ROLL_Y, ROLL_Z), P_S, P_R
dx, dz = c2[0] - c1[0], c2[1] - c1[1]; Ld = math.hypot(dx, dz); an = math.atan2(dz, dx); b = math.acos((r1 - r2) / Ld)
for s in (1, -1):
    p1 = (c1[0] + r1 * math.cos(an + s * b), c1[1] + r1 * math.sin(an + s * b))
    p2 = (c2[0] + r2 * math.cos(an + s * b), c2[1] + r2 * math.sin(an + s * b))
    line(U(p1[0]), W(p1[1]), U(p2[0]), W(p2[1]), "#111", 2.2)
# servo seen from the front: its spline end; ears top and bottom
RF(SV_Y0, EAR_Z0, SV_Y1, EAR_Z1, "#3b5ea8", "#1d3466", 0.8, None, 0.55)
RF(SV_Y0, BODY_Z0, SV_Y1, BODY_Z1, "#3b5ea8", "#1d3466", 1.2)
CF(SV_SY, SH_Z, 2.4, "#ddd", "#555")
CF(SV_SY, SH_Z, P_S, "none", "#e67e22", 2)
lead(U(SV_SY), W(BODY_Z1 - 3), U(46), W(40), "SG90 on end, shaft forward", "screwed by its two ears to the magazine")
lead(U(SV_SY + 3), W(EAR_Z0 + 1), U(46), W(-6), "lower ear 3 mm above floor", "(same as the roller)")
lead(U(ROLL_Y), W(ROLL_Z), U(-44), W(-8), "roller end-on", None)
text(U(-44), W(24), "main board + chassis are behind", 11, col="#555")
text(U(-44), W(24) + 14, "(x &lt; 37.5; servo starts at x 38.5)", 11, col="#555")
text(U(-45), W(-16), "Servo top z 35.2 stays below the magazine top (42.2) and the camera (44.1).", 12, col="#333")
text(U(-45), W(-16) + 18, "Widest point y +24.5 (was +47.8). Front x 67.7 (was 72.7; gripper was 71.2).", 12, col="#333", weight="bold")
H = int(W(-16) + 40); Wd = int(X(110))
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}"><rect width="{Wd}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>"
open(OUT, "w", encoding="utf-8").write(svg)
print(Wd, H)
