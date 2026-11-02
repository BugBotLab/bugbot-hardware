# 2D: NFC reader in the base (to scale, looking down, front = right). Why a mini RC522 can't sit flush in the floor at
# the centre (it overlaps the wheel pockets and rollers), and what fits: a 20 mm round antenna coil flush in the floor
# inside the motor-cap screws, with a small reader board (<= 30 x 20) above the motor caps, wired to it.
import sys, json, math
D = json.load(open(sys.argv[1])); SCR = json.load(open(sys.argv[2]))["screws"]; OUT = sys.argv[3]
SC = 9.0
el = []
def a(s): el.append(s)
X = lambda x: 60 + (x + 45) * SC; Y = lambda y: 150 + (45 - y) * SC
def path(wires, fill, stroke, op, sw=1.0, dash=None):
    d_ = " ".join("M" + " L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in w) + " Z" for w in wires)
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<path d="{d_}" fill="{fill}" fill-opacity="{op}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{sw}"{ds}/>')
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
T(60, 40, "NFC reader in the base: what fits (2D, to scale, looking down, front = right)", 21, w="bold")
T(60, 64, "Red: a mini RC522 (37 x 25) flush at the centre - it lands on the wheel pockets and rollers at every angle (11-13 %), so", 13, col="#c62828")
T(60, 82, "moving the motor-cap screws is not enough.  Green: a 20 mm round antenna coil fits flush in the floor inside the screws.", 13, col="#1a7f37")
T(60, 100, "Blue dashed: a reader board up to 30 x 20 fits above the motor caps (z 16-21) right over it; 2 wires down to the coil.", 13, col="#1565c0")
for nm, ws in D.get("floor", []):
    if nm == "Chassis": path(ws, "#d8d8d0", "#777", 1.0)
for nm, ws in D.get("floor", []):
    if nm != "Chassis": path(ws, "#8fb3d9", "#4a6f99", 0.8, 0.8)
for nm, ws in D.get("mid", []):
    if "Cap" in nm or "cap" in nm: path(ws, "#ffb74d", "#c77800", 0.5, 0.8)
for nm, ws in D.get("above", []):
    if nm == "Gearmotor": path(ws, "#e57373", "#b71c1c", 0.6, 1.0)
    elif "screw" not in nm.lower(): path(ws, "#8fb3d9", "#4a6f99", 0.45, 0.6)
# screws (pan heads 3.8)
for _, sx, sy in SCR:
    a(f'<circle cx="{X(sx):.1f}" cy="{Y(sy):.1f}" r="{1.9*SC:.1f}" fill="#9e9e9e" stroke="#424242"/>')
    a(f'<circle cx="{X(sx):.1f}" cy="{Y(sy):.1f}" r="{0.8*SC:.1f}" fill="#424242"/>')
rmin = min(math.hypot(x, y) for _, x, y in SCR) - 1.9
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{rmin*SC:.1f}" fill="none" stroke="#555" stroke-dasharray="2 3"/>')
T(X(-rmin * 0.7), Y(-rmin * 0.75) + 16, f"clear circle {2*rmin:.1f} mm (inside the screw heads)", 11, col="#444")
# red: RC522 window at the centre
a(f'<rect x="{X(-18.8):.1f}" y="{Y(12.8):.1f}" width="{37.6*SC:.1f}" height="{25.6*SC:.1f}" fill="#e53935" fill-opacity="0.12" stroke="#c62828" stroke-width="2" stroke-dasharray="6 4"/>')
T(X(-18.8), Y(12.8) - 6, "mini RC522 37 x 25: hits the wheel pockets", 12, col="#c62828")
# blue: reader board above
a(f'<rect x="{X(-15):.1f}" y="{Y(10):.1f}" width="{30*SC:.1f}" height="{20*SC:.1f}" fill="none" stroke="#1565c0" stroke-width="2" stroke-dasharray="8 4"/>')
T(X(-15), Y(-10) + 16, "reader board up to 30 x 20, above the motor caps (z 16-21)", 12, col="#1565c0")
# green: 20 mm coil + its 20.6 pocket
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{10.3*SC:.1f}" fill="#43a047" fill-opacity="0.35" stroke="#1b5e20" stroke-width="2"/>')
for k in range(4):
    a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{(9.2 - k*1.0)*SC:.1f}" fill="none" stroke="#1b5e20" stroke-width="1"/>')
T(X(0), Y(0) + 4, "20 mm coil", 12, "middle", "#0d3b12", "bold")
for v in range(-40, 41, 10):
    T(X(v), Y(-47), str(v), 10, "middle", "#777"); T(X(-47), Y(v) + 4, str(v), 10, "end", "#777")
# side section (right)
SX0, SY0 = X(48) + 40, 160
SS = 9.0
sx = lambda x: SX0 + (x + 20) * SS; sz = lambda z: SY0 + (32 - z) * SS
T(SX0, SY0 - 18, "SECTION through the centre", 15, w="bold")
a(f'<line x1="{sx(-20):.1f}" y1="{sz(0):.1f}" x2="{sx(20):.1f}" y2="{sz(0):.1f}" stroke="#333" stroke-width="1.5"/>'); T(sx(-20), sz(0) + 16, "mat", 11, col="#555")
a(f'<rect x="{sx(-20):.1f}" y="{sz(8.1):.1f}" width="{40*SS:.1f}" height="{1.6*SS:.1f}" fill="#d8d8d0" stroke="#777"/>'); T(sx(12), sz(8.1) - 4, "floor plate 6.5-8.1", 11, col="#555")
a(f'<rect x="{sx(-10.3):.1f}" y="{sz(7.3):.1f}" width="{20.6*SS:.1f}" height="{0.8*SS:.1f}" fill="#43a047" stroke="#1b5e20"/>')
T(sx(-10.3), sz(6.5) + 16, "coil PCB 0.8 mm in a pocket from below, flush; 0.8 mm lip above", 11, col="#1b5e20")
a(f'<rect x="{sx(-20):.1f}" y="{sz(15.1):.1f}" width="{40*SS:.1f}" height="{6.2*SS:.1f}" fill="#e57373" fill-opacity="0.35" stroke="#b71c1c" stroke-dasharray="4 3"/>'); T(sx(-19), sz(12), "gearmotors / caps (z 8.9-15.6)", 11, col="#b71c1c")
a(f'<rect x="{sx(-15):.1f}" y="{sz(18.6):.1f}" width="{30*SS:.1f}" height="{2.6*SS:.1f}" fill="#90caf9" stroke="#1565c0"/>'); T(sx(-15), sz(18.6) - 4, "reader board (z 16-19), held to the motor caps", 11, col="#1565c0")
a(f'<rect x="{sx(-20):.1f}" y="{sz(30.6):.1f}" width="{40*SS:.1f}" height="{1.6*SS:.1f}" fill="#2e6b3f"/>'); T(sx(-19), sz(30.6) - 4, "main board", 11, col="#1c4428")
a(f'<path d="M{sx(3):.1f},{sz(16):.1f} C{sx(3):.1f},{sz(12):.1f} {sx(11):.1f},{sz(11):.1f} {sx(9):.1f},{sz(8.1):.1f}" fill="none" stroke="#6a1b9a" stroke-width="2"/>')
T(sx(9.5), sz(10), "2-wire lead", 11, col="#6a1b9a")
a(f'<path d="M{sx(-8):.1f},{sz(19.2):.1f} L{sx(-8):.1f},{sz(29):.1f}" stroke="#555" stroke-dasharray="3 2"/>'); T(sx(-7.5), sz(25), "6-wire to the main board", 11, col="#555")
a(f'<rect x="{sx(-12.5):.1f}" y="{sz(0.9):.1f}" width="{25*SS:.1f}" height="{0.9*SS:.1f}" fill="#8e4dd0"/>'); T(sx(-12.5), sz(0) + 28, "tag on the mat: 6.1 mm below the coil", 11, col="#6a1b9a")
T(SX0, sz(-6), "Sim (robot_io.NfcReader): 20 mm coil reads a tag within 11 mm of the centre line", 12, col="#1a7f37", w="bold")
T(SX0, sz(-6) + 18, "(24 mm: 12.5; RC522's own 28 x 21 coil: 16). Same read lane as before, give or take 1-2 mm.", 12, col="#333")
T(SX0, sz(-6) + 36, "Reader board candidates (up to 30 x 20) that drive an external antenna: PN532 minis (~25 x 16): price to check.", 12, col="#333")
W, H = int(sx(44)), int(Y(-52))
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
