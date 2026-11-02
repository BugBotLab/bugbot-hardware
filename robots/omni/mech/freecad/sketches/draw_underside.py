# 2D: the base robot's underside (sections of the BugBot_Base parts), to scale, for placing an NFC reader that reads the
# tags the robot drives over. Floor plate at z 7.3 (it spans 6.5-8.1), what sits just above it (z 9.5), and motor-cap
# level (z 13). A mini RC522 module (35 x 25 mm, sellers vary) and a 25 mm tag are drawn at the centre.
import sys, json
D = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SC = 9.0
el = []
def a(s): el.append(s)
X = lambda x: 60 + (x + 45) * SC; Y = lambda y: 130 + (45 - y) * SC
def path(wires, fill, stroke, op, sw=1.0, dash=None):
    d_ = " ".join("M" + " L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in w) + " Z" for w in wires)
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<path d="{d_}" fill="{fill}" fill-opacity="{op}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{sw}"{ds}/>')
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
T(60, 40, "Base robot underside: where can an NFC reader go? (to scale, looking down, front = right)", 21, w="bold")
T(60, 64, "Grey: chassis floor plate (z 6.5-8.1).  Red: parts just above it (z 9.5: gearmotors).  Orange: motor caps (z 13).  Blue: wheels.", 13, col="#333")
T(60, 82, "Dashed green: a mini RC522 (35 x 25 mm) at the centre.  Purple: a 25 mm tag under it.", 13, col="#333")
for nm, ws in D.get("floor", []):
    if nm == "Chassis":
        path(ws, "#d8d8d0", "#777", 1.0)
for nm, ws in D.get("floor", []):
    if nm != "Chassis":
        path(ws, "#8fb3d9", "#4a6f99", 0.8, 0.8)
for nm, ws in D.get("mid", []):
    if "Cap" in nm or "cap" in nm:
        path(ws, "#ffb74d", "#c77800", 0.55, 0.8)
for nm, ws in D.get("above", []):
    if nm in ("Gearmotor",) or "screw" in nm.lower():
        path(ws, "#e57373", "#b71c1c", 0.6, 1.0)
    elif "Roller" in nm or "Wheel" in nm or "Pin" in nm or "Liner" in nm or "Enc" in nm:
        path(ws, "#8fb3d9", "#4a6f99", 0.5, 0.6)
# candidate module + tag
a(f'<rect x="{X(-17.5):.1f}" y="{Y(12.5):.1f}" width="{35*SC:.1f}" height="{25*SC:.1f}" fill="none" stroke="#1a7f37" stroke-width="2" stroke-dasharray="6 4"/>')
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{12.5*SC:.1f}" fill="#8e4dd0" fill-opacity="0.18" stroke="#6a1b9a" stroke-dasharray="3 3"/>')
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="3" fill="#111"/>'); T(X(1), Y(-1.5), "centre", 11)
# grid ticks
for v in range(-40, 41, 10):
    a(f'<line x1="{X(v):.1f}" y1="{Y(-44):.1f}" x2="{X(v):.1f}" y2="{Y(-42):.1f}" stroke="#999"/>'); T(X(v), Y(-46.5), str(v), 10, "middle", "#777")
    a(f'<line x1="{X(-44):.1f}" y1="{Y(v):.1f}" x2="{X(-42):.1f}" y2="{Y(v):.1f}" stroke="#999"/>'); T(X(-46), Y(v) + 4, str(v), 10, "end", "#777")
T(X(0), Y(-50), "x (mm, forward)", 11, "middle", "#777")
W, H = int(X(48)), int(Y(-54))
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
