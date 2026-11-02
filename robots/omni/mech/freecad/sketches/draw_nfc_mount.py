# 2D: NFC reader mount in the base (to scale). A 20 mm round coil PCB sits flush in a pocket in the floor plate at the
# centre; a printed post (6 mm) rises between the gearmotors to a tray at z 16 that carries the reader board (up to
# 25 x 16.4: Elechouse PN5321 MINI, or the chip end of a cut-down mini RC522). One nylon M2 screw from below, through the
# coil's centre, clamps the coil into its pocket and holds the post. Top view (left) + section (right).
import sys, json, math
lab = json.load(open(sys.argv[1])); up = json.load(open(sys.argv[2])); OUT = sys.argv[3]
SC = 13.0
el = []
def a(s): el.append(s)
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
X = lambda x: 60 + (x + 28) * SC; Y = lambda y: 150 + (28 - y) * SC
def path(ws, fill, stroke, op, sw=1.0, dash=None):
    d_ = " ".join("M" + " L".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in w) + " Z" for w in ws)
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<path d="{d_}" fill="{fill}" fill-opacity="{op}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{sw}"{ds}/>')
a(f'<clipPath id="win"><rect x="{X(-28):.1f}" y="{Y(28):.1f}" width="{56*SC:.1f}" height="{56*SC:.1f}"/></clipPath>')
a('<g clip-path="url(#win)">')
path([w for l, z, w in lab if z == 7.3 and l == "Frame:1/Chassis"], "#d8d8d0", "#777", 1.0)
path([w for l, z, w in up if z == 18.5], "#8fb3d9", "#4a6f99", 0.35, 0.6)                       # wheels / encoder boards up at the tray
path([w for l, z, w in lab if z == 13.0 and "MotorCap" in l], "#ffb74d", "#c77800", 0.55, 0.8)
path([w for l, z, w in lab if z == 10.5 and "Gearmotor" in l], "#e57373", "#b71c1c", 0.55, 1.0)
for l, z, w in lab:
    if z == 8.5 and "screw" in l.lower():
        cx = sum(p[0] for p in w) / len(w); cy = sum(p[1] for p in w) / len(w)
        a(f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{1.9*SC:.1f}" fill="#9e9e9e" stroke="#424242"/>')
# floor pocket + coil
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{10.3*SC:.1f}" fill="#c8e6c9" stroke="#1b5e20" stroke-width="1.5" stroke-dasharray="4 2"/>')
for k in range(5):
    a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{(9.6 - k * 0.9)*SC:.1f}" fill="none" stroke="#2e7d32" stroke-width="1.2"/>')
a(f'<rect x="{X(9.6):.1f}" y="{Y(1.2):.1f}" width="{1.6*SC:.1f}" height="{2.4*SC:.1f}" fill="#fff" stroke="#6a1b9a"/>')   # lead notch
# post
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{3.0*SC:.1f}" fill="#ffc400" stroke="#8a6d10" stroke-width="1.5"/>')
a(f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="{1.9*SC:.1f}" fill="#eeeeee" stroke="#555"/>')
# tray (rounded rect 28 x 19.4, r 3) at 42 deg + the board 25 x 16.4
def rr(L, W, r, th, n=10):
    pts = []
    c, s = math.cos(th), math.sin(th)
    for cx, cy, a0 in ((L/2 - r, W/2 - r, 0), (-L/2 + r, W/2 - r, 90), (-L/2 + r, -W/2 + r, 180), (L/2 - r, -W/2 + r, 270)):
        for k in range(n + 1):
            an = math.radians(a0 + 90 * k / n); x = cx + r * math.cos(an); y = cy + r * math.sin(an)
            pts.append((x * c - y * s, x * s + y * c))
    return pts
th = math.radians(42)
path([rr(28, 19.4, 3, th)], "none", "#1565c0", 1.0, 2.0, "8 4")
path([rr(25, 16.4, 0.5, th)], "#90caf9", "#1565c0", 0.45, 1.2)
a('</g>')
T(60, 40, "NFC reader mount in the base (2D, to scale)", 21, w="bold")
T(60, 64, "20 mm coil flush in the floor at the centre; a 6 mm printed post between the gearmotors carries the reader board's tray at z 16.6 (1 mm over the motor caps);", 13, col="#333")
T(60, 82, "one nylon M2 x 10 from below through the coil's centre clamps the coil and holds the post. Fits a 25 x 16.4 board (PN5321 MINI, or a cut-down RC522).", 13, col="#333")
T(X(-28), Y(28) - 10, "TOP VIEW (centre of the base, front = right)", 14, w="bold")
leg = [("#c8e6c9", "#1b5e20", "floor pocket 20.6, coil 20 (green rings)"), ("#ffc400", "#8a6d10", "post 6 mm (screw at its centre)"),
       ("#90caf9", "#1565c0", "reader board 25 x 16.4 on its tray (dashed) at 42 deg"), ("#e57373", "#b71c1c", "gearmotors (z 8.9-15.1)"),
       ("#ffb74d", "#c77800", "motor caps (to z 15.6)"), ("#8fb3d9", "#4a6f99", "wheels / encoder boards at tray height"),
       ("#9e9e9e", "#424242", "motor-cap screws (unchanged)")]
for i, (f, s, t) in enumerate(leg):
    a(f'<rect x="{X(-28):.1f}" y="{Y(-28) + 14 + i*18:.1f}" width="14" height="12" fill="{f}" stroke="{s}"/>'); T(X(-28) + 20, Y(-28) + 25 + i * 18, t, 12)
T(X(-28), Y(-28) + 14 + 7 * 18 + 12, "Clearances: post to gearmotors 2.2 mm (worst, at z 13); tray 1.0 mm over the motor caps; tray corners 3.6 mm to the wheels / encoder boards.", 12, col="#1a7f37", w="bold")
# ---- section ----
SS = 13.0
SX0 = X(28) + 60
sx = lambda x: SX0 + (x + 16) * SS; sz = lambda z: Y(28) + (32 - z) * SS
T(sx(-16), sz(32) - 10, "SECTION through the centre (along the board)", 14, w="bold")
def box(x0, z0, x1, z1, fill, stroke, op=1, dash=None):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<rect x="{sx(min(x0,x1)):.1f}" y="{sz(max(z0,z1)):.1f}" width="{abs(x1-x0)*SS:.1f}" height="{abs(z1-z0)*SS:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}"{ds}/>')
a(f'<line x1="{sx(-16):.1f}" y1="{sz(0):.1f}" x2="{sx(16):.1f}" y2="{sz(0):.1f}" stroke="#333" stroke-width="1.5"/>'); T(sx(-16), sz(0) + 16, "mat", 11, col="#555")
box(-16, 6.5, -10.3, 8.1, "#d8d8d0", "#777"); box(10.3, 6.5, 16, 8.1, "#d8d8d0", "#777")
box(-10.3, 7.3, 10.3, 8.1, "#d8d8d0", "#777")                                   # 0.8 mm lip over the coil
box(-10.0, 6.5, -1.1, 7.3, "#66bb6a", "#1b5e20"); box(1.1, 6.5, 10.0, 7.3, "#66bb6a", "#1b5e20")   # coil PCB 0.8
box(-1.9, 5.1, 1.9, 6.5, "#bdbdbd", "#424242")                                  # nylon pan head under the floor
box(-0.8, 6.5, 0.8, 15.5, "#e0e0e0", "#555", 0.9)                               # the screw's shank, up into the post
box(-3.0, 8.1, 3.0, 16.6, "#ffc400", "#8a6d10", 0.85)                           # post
box(-14.0, 16.6, 14.0, 17.8, "#ffc400", "#8a6d10", 0.85)                        # tray
box(-14.0, 17.8, -13.0, 19.6, "#ffc400", "#8a6d10", 0.85); box(13.0, 17.8, 14.0, 19.6, "#ffc400", "#8a6d10", 0.85)   # clips
box(-12.5, 17.8, 12.5, 22.2, "#90caf9", "#1565c0", 0.8)                         # reader board (4.4 incl. parts)
box(-16, 8.9, -5.2, 15.1, "#e57373", "#b71c1c", 0.3, "4 3"); box(5.2, 8.9, 16, 15.1, "#e57373", "#b71c1c", 0.3, "4 3")
box(-16, 29.0, 16, 30.6, "#2e6b3f", "#1c4428")
a(f'<path d="M{sx(9.8):.1f},{sz(7.3):.1f} C{sx(10.5):.1f},{sz(10):.1f} {sx(4.5):.1f},{sz(12):.1f} {sx(4):.1f},{sz(16):.1f} L{sx(9):.1f},{sz(17.8):.1f}" fill="none" stroke="#6a1b9a" stroke-width="2"/>')
a(f'<path d="M{sx(-11):.1f},{sz(22.2):.1f} C{sx(-12):.1f},{sz(25):.1f} {sx(-10):.1f},{sz(27):.1f} {sx(-9):.1f},{sz(29):.1f}" fill="none" stroke="#555" stroke-width="2" stroke-dasharray="4 2"/>')
box(-12.5, 0, 12.5, 0.9, "#8e4dd0", "#4a1f80")
for x0, z0, x1, z1, s, col in ((10.5, 7.0, 16.5, 4.0, "coil PCB 20 x 0.8, pocket from below, flush", "#1b5e20"),
                               (2.0, 5.8, 16.5, 2.2, "nylon M2 x 10 pan head: 5.1 mm above the mat", "#424242"),
                               (3.0, 12.0, 16.5, 13.2, "post 6 mm: 2.2 mm from the gearmotors", "#8a6d10"),
                               (12.0, 19.5, 16.5, 23.0, "reader board on the tray, held by 2 clips", "#1565c0"),
                               (6.0, 15.0, 16.5, 17.8, "2-wire antenna lead (twisted, ~25 mm)", "#6a1b9a"),
                               (-10.0, 26.0, 16.5, 27.0, "8-wire cable to the main board's JST-SH", "#555")):
    a(f'<line x1="{sx(x0):.1f}" y1="{sz(z0):.1f}" x2="{sx(x1):.1f}" y2="{sz(z1):.1f}" stroke="#888" stroke-width="0.8"/>')
    T(sx(x1) + 4, sz(z1) + 4, s, 12, col=col)
T(sx(-16), sz(-3) + 6, "tag on the mat: 6.5 mm below the coil's copper", 12, col="#6a1b9a")
W, H = int(sx(48)), int(max(Y(-28) + 14 + 9 * 18 + 20, sz(-3) + 30))
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
