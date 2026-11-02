# 2D: Spider arm plate, now vs neater (sections of the FreeCAD shapes at y 23, to scale) + real screws.
import sys, json, math
D = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SC = 9.0; el = []
def a(s): el.append(s)
def text(x, y, s, size=13, anchor="start", col="#111", weight="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{weight}" font-family="Segoe UI, Arial">{s}</text>')
def panel(ox, oy, key, title, notes):
    X = lambda x: ox + (x + 2) * SC; Z = lambda z: oy + (50 - z) * SC
    text(X(-2), oy - 12, title, 17, weight="bold")
    a(f'<line x1="{X(-2):.1f}" y1="{Z(0):.1f}" x2="{X(60):.1f}" y2="{Z(0):.1f}" stroke="#333" stroke-width="1.5"/>')
    a(f'<rect x="{X(-2):.1f}" y="{Z(30.6):.1f}" width="{(36.4+2)*SC:.1f}" height="{1.6*SC:.1f}" fill="#2e6b3f"/>')
    a(f'<rect x="{X(-2):.1f}" y="{Z(29.0):.1f}" width="{(34.5+2)*SC:.1f}" height="{22.5*SC:.1f}" fill="#e9d9a6" stroke="#8a7a40" fill-opacity="0.7"/>')
    text(X(2), Z(18), "chassis (side wall at y 23)", 12, col="#6d5f2c"); text(X(2), Z(30.6) - 5, "main board", 12, col="#1c4428")
    a(f'<circle cx="{X(48.5):.1f}" cy="{Z(8):.1f}" r="{8*SC:.1f}" fill="#222" fill-opacity="0.25" stroke="#000" stroke-dasharray="4 3"/>')
    for w in D[key]:
        pts = " ".join(f"{X(x):.1f},{Z(z):.1f}" for x, z in w)
        a(f'<polygon points="{pts}" fill="#c77dd6" fill-opacity="0.85" stroke="#5e1270" stroke-width="1.3"/>')
    for sx, sz in ((39.5, 18.0), (39.5, 24.7)):        # M2 pan heads (cross recess)
        a(f'<circle cx="{X(sx):.1f}" cy="{Z(sz):.1f}" r="{1.9*SC:.1f}" fill="#d0d3d8" stroke="#555"/>')
        a(f'<path d="M{X(sx)-7:.1f},{Z(sz):.1f} H{X(sx)+7:.1f} M{X(sx):.1f},{Z(sz)-7:.1f} V{Z(sz)+7:.1f}" stroke="#555" stroke-width="2"/>')
    if key == "new":                                   # M3 socket head on the axle
        a(f'<circle cx="{X(48.5):.1f}" cy="{Z(8):.1f}" r="{2.75*SC:.1f}" fill="#2b2b2e" stroke="#000"/>')
        r = 0.866 * SC
        a('<polygon points="' + " ".join(f"{X(48.5) + r * math.cos(math.radians(60*k)):.1f},{Z(8) + r * math.sin(math.radians(60*k)):.1f}" for k in range(6)) + '" fill="#777"/>')
    else:
        a(f'<circle cx="{X(48.5):.1f}" cy="{Z(8):.1f}" r="{1.5*SC:.1f}" fill="#ccc" stroke="#333"/>')
    for i, n in enumerate(notes): text(X(-2), Z(-3) + 20 + i * 18, n, 13, col="#333")
panel(30, 110, "cur", "NOW (v3)", ["old hoop arm + boxes added: steps, a notch,", "a corner that juts out; plain-cylinder screws and axle"])
panel(30 + 64 * SC + 40, 110, "new", "NEATER", ["one L of constant width, rounded bends (r 6 outside, r 1.5 / 3 inside),", "round axle end; pivot end unchanged (servo-horn fit);",
      "screws: 2 x M2x8 pan (cross) per side; axle = M3x50 socket screw", "threaded into the far plate, roller spins on the shank"])
text(30, 50, "Spider arm plate: neater profile (2D, to scale, section through the plate)", 22, weight="bold")
text(30, 76, "Gaps unchanged: plate to chassis 1.6 mm, lowest point 4 mm above the floor. Roller shown dashed.", 14, col="#333")
W = int(30 + 2 * 64 * SC + 80); H = int(110 + 56 * SC + 110)
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
