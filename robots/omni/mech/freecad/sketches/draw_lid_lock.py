# 2D: Spider weighted lid with a bayonet (J-slot) lock, to scale. The lid is the follower weight (printed cup + M10
# washer, ~3.5 g); two lugs run in slots through the tube wall. At the top each slot turns 30 deg sideways to an entry
# notch: the lid only comes out if it is lifted to the top and twisted. Top view + side elevation (from +Y) + section.
import sys, math
OUT = sys.argv[1]
SC = 11.0
MC, R_IN, R_OUT, WALL = 42.5, 12.9, 14.5, 1.6
FLOOR, FT, SLOT, TAG_T, N = 15.7, 1.6, 1.35, 0.9, 10
TOP = 31.2                                         # magazine top, raised 3.5 mm (board still 4.4 mm away)
LID_D, LID_H = 24.6, 3.0
LUG_A, TWIST = 75.0, 30.0                          # lug angle from the front (each side), twist to the entry notch
LUG_W, LUG_H, SLOT_W = 1.6, 1.6, 2.2
lug_z_empty = FLOOR + LID_H / 2                    # lug centre with no tags
lug_z_full = FLOOR + N * TAG_T + LID_H / 2
J_Z0, J_Z1 = TOP - 2.6, TOP - 0.4                 # sideways part of the J at the top
SL_Z0 = lug_z_empty - LUG_H / 2 - 0.5
EXIT_A = math.degrees(math.asin((R_IN - 0.5) / R_OUT))
LIP_A = EXIT_A + 8.0
el = []
def a(s): el.append(s)
def T(x, y, s, size=13, anchor="start", col="#111", w="normal"):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{col}" font-weight="{w}" font-family="Segoe UI, Arial">{s}</text>')
T(30, 36, "Spider weighted lid with a twist lock (2D, to scale)", 22, w="bold")
T(30, 60, "The lid is the weight: it slides down as tags go out; its two lugs run in slots in the tube wall. At the top each slot", 14, col="#333")
T(30, 78, f"turns {TWIST:g} deg sideways: lift to the top + twist to take it out. Magazine 3.5 mm taller (top z {TOP}); board still 4.4 mm away.", 14, col="#333")

# ---------- TOP VIEW ----------
OX, OY = 30, 110
TX = lambda x: OX + (x - 22) * SC; TY = lambda y: OY + (24 - y) * SC
def circ(x, y, r, fill, stroke="#333", sw=1, dash=None, op=1):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<circle cx="{TX(x):.1f}" cy="{TY(y):.1f}" r="{r*SC:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def arc_band(r0, r1, a0, a1, fill, stroke="#333", op=1):
    pts = [(MC + r1 * math.cos(math.radians(t)), r1 * math.sin(math.radians(t))) for t in [a0 + (a1 - a0) * k / 20 for k in range(21)]]
    pts += [(MC + r0 * math.cos(math.radians(t)), r0 * math.sin(math.radians(t))) for t in [a1 - (a1 - a0) * k / 20 for k in range(21)]]
    a('<polygon points="' + " ".join(f"{TX(x):.1f},{TY(y):.1f}" for x, y in pts) + f'" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="1"/>')
T(OX, OY - 8, "TOP VIEW (front = right)", 15, w="bold")
for s in (1, -1):                                   # tabs to the arm plates
    y0, y1 = (11.0, 21.0) if s > 0 else (-21.0, -11.0)
    a(f'<rect x="{TX(36.5):.1f}" y="{TY(y1):.1f}" width="{6*SC:.1f}" height="{10*SC:.1f}" fill="#e8eaee" stroke="#444"/>')
    a(f'<rect x="{TX(36.5):.1f}" y="{TY(max(s*21.2, s*24.8)):.1f}" width="{(48.5+4-36.5)*SC:.1f}" height="{3.6*SC:.1f}" fill="#ffc400" fill-opacity="0.5" stroke="#8a6d10"/>')
circ(MC, 0, R_OUT, "#d5dbe2", "#444"); circ(MC, 0, R_IN, "#fff", "#666")
arc_band(R_OUT, R_OUT + 1.2, -LIP_A, LIP_A, "#c9d0d8")                       # lip over the tag exit
arc_band(R_IN - 0.05, R_OUT + 0.05, -EXIT_A, EXIT_A, "#ffcdd2", "#c62828", 0.6)   # tag exit (below the lip)
for s in (1, -1):
    arc_band(R_IN - 0.05, R_OUT + 0.05, s * LUG_A - 4.3, s * LUG_A + 4.3, "#fff", "#1565c0")          # vertical slot
    ea = s * (LUG_A + TWIST)
    arc_band(R_IN - 0.05, R_OUT + 0.05, ea - 4.3, ea + 4.3, "#e3f2fd", "#1565c0")                      # entry notch
circ(MC, 0, LID_D / 2, "#ffc400", "#8a6d10", 1, None, 0.85)
circ(MC, 0, 10.0, "#b9c0c8", "#555", 1, None, 0.9); circ(MC, 0, 5.25, "#ffc400", "#8a6d10")
for s in (1, -1):                                   # lugs (locked position)
    t = math.radians(s * LUG_A)
    x0, y0 = MC + (LID_D / 2 - 0.3) * math.cos(t), (LID_D / 2 - 0.3) * math.sin(t)
    x1, y1 = MC + (R_OUT + 0.3) * math.cos(t), (R_OUT + 0.3) * math.sin(t)
    a(f'<line x1="{TX(x0):.1f}" y1="{TY(y0):.1f}" x2="{TX(x1):.1f}" y2="{TY(y1):.1f}" stroke="#8a6d10" stroke-width="{LUG_W*SC:.1f}"/>')
T(TX(MC), TY(-17.5), f"lugs at +-{LUG_A:g} deg (blue slots); entry notches at +-{LUG_A+TWIST:g} deg (light blue)", 12, "middle", "#1565c0")
T(TX(MC), TY(-19.3), f"clear of: tag exit +-{EXIT_A:.0f} deg (red), lip +-{LIP_A:.0f} deg, tabs (grey, z &lt; 26: entry notches sit above them)", 12, "middle", "#333")
T(TX(MC), TY(-21.1), "arm plates yellow", 12, "middle", "#8a6d10")

# ---------- SIDE ELEVATION (from +Y): the J-slot ----------
OX2, OY2 = TX(74), 110
EX = lambda x: OX2 + (x - 26) * SC; EZ = lambda z: OY2 + (34 - z) * SC
T(OX2, OY2 - 8, "SIDE VIEW from the left (+Y): the J-slot in the wall", 15, w="bold")
a(f'<rect x="{EX(MC-R_OUT):.1f}" y="{EZ(TOP):.1f}" width="{2*R_OUT*SC:.1f}" height="{(TOP-(FLOOR-FT))*SC:.1f}" fill="#d5dbe2" stroke="#444"/>')
a(f'<rect x="{EX(36.5):.1f}" y="{EZ(26.0):.1f}" width="{6*SC:.1f}" height="{(26.0-(FLOOR-FT))*SC:.1f}" fill="#e8eaee" stroke="#444" stroke-dasharray="3 2"/>')
T(EX(39.5), EZ(20), "tab", 11, "middle", "#555")
xs = lambda ang: MC + R_OUT * math.cos(math.radians(ang))
x_slot, x_entry = xs(LUG_A), xs(LUG_A + TWIST)
hw = SLOT_W / 2
path = [(x_slot - hw, SL_Z0), (x_slot + hw, SL_Z0), (x_slot + hw, J_Z1), (x_entry - hw, J_Z1), (x_entry - hw, TOP), (x_entry + hw, TOP),
        (x_entry + hw, J_Z0), (x_slot - hw, J_Z0)]
a('<polygon points="' + " ".join(f"{EX(x):.1f},{EZ(z):.1f}" for x, z in path) + '" fill="#fff" stroke="#1565c0" stroke-width="1.5"/>')
for zc, lab, dash in ((lug_z_full, "lug, full stack", None), (lug_z_empty, "lug, last tag gone", "3 2"), ((J_Z0 + J_Z1) / 2, "", "2 2")):
    a(f'<rect x="{EX(x_slot - LUG_W/2):.1f}" y="{EZ(zc + LUG_H/2):.1f}" width="{LUG_W*SC:.1f}" height="{LUG_H*SC:.1f}" fill="#ffc400" stroke="#8a6d10"'
      + (f' stroke-dasharray="{dash}" fill-opacity="0.5"' if dash else "") + "/>")
a(f'<path d="M{EX(x_slot)-10:.1f},{EZ(J_Z1)-12:.1f} q 0 -10 {(x_entry-x_slot)*SC/2:.1f} -10 t {(x_entry-x_slot)*SC/2:.1f} 10" fill="none" stroke="#1565c0" stroke-width="1.2" marker-end="url(#ar)"/>')
a('<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#1565c0"/></marker></defs>')
def lead(x, y, tx, ty, s, s2=None):
    a(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" stroke="#666" stroke-width="0.8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#666"/>')
    T(tx + 5, ty + 4, s, 12)
    if s2: T(tx + 5, ty + 19, s2, 11, col="#555")
lead(EX(x_slot), EZ(lug_z_full), EX(62), EZ(24.5), f"lug {LUG_W:g} x {LUG_H:g} mm in a {SLOT_W:g} mm slot", "0.3 mm clear each side (any printer)")
lead(EX(x_slot), EZ(lug_z_empty), EX(62), EZ(18), "slot runs down to the empty position", "lug position = tags left (visible)")
lead(EX(x_entry), EZ(TOP - 0.2), EX(62), EZ(31.5), f"entry notch: lift to the top, twist {TWIST:g} deg, lift out", "falls back down only after the twist")
a(f'<line x1="{EX(MC-R_OUT-1):.1f}" y1="{EZ(FLOOR):.1f}" x2="{EX(MC+R_OUT+1):.1f}" y2="{EZ(FLOOR):.1f}" stroke="#999" stroke-dasharray="2 2"/>')
T(EX(MC - R_OUT - 1), EZ(FLOOR) + 14, "magazine floor", 11, col="#777")

# ---------- SECTION: the lid ----------
OY3 = TY(-24) + 40
SX = lambda x: OX + (x - 22) * SC * 1.25; SZ = lambda z: OY3 + (34 - z) * SC * 1.25
T(OX, OY3 - 8, "THE LID (section, full stack)", 15, w="bold")
def r3(x0, z0, x1, z1, fill, stroke="#333"):
    a(f'<rect x="{SX(min(x0,x1)):.1f}" y="{SZ(max(z0,z1)):.1f}" width="{abs(x1-x0)*SC*1.25:.1f}" height="{abs(z1-z0)*SC*1.25:.1f}" fill="{fill}" stroke="{stroke}"/>')
r3(MC - R_OUT, FLOOR - FT, MC - R_IN, TOP, "#d5dbe2", "#444"); r3(MC + R_IN, FLOOR + SLOT, MC + R_OUT, TOP, "#d5dbe2", "#444")
for i in range(N):
    r3(MC - 12.5, FLOOR + i * TAG_T, MC + 12.5, FLOOR + (i + 1) * TAG_T - 0.06, "#8e4dd0" if i % 2 else "#7a3bc0", "#4a1f80")
zb = FLOOR + N * TAG_T + 0.02
r3(MC - LID_D / 2, zb, MC + LID_D / 2, zb + 0.6, "#ffc400", "#8a6d10")
r3(MC - LID_D / 2, zb, MC - 10.2, zb + LID_H, "#ffc400", "#8a6d10"); r3(MC + 10.2, zb, MC + LID_D / 2, zb + LID_H, "#ffc400", "#8a6d10")
r3(MC - 10, zb + 0.6, MC - 5.25, zb + 2.6, "#b9c0c8", "#555"); r3(MC + 5.25, zb + 0.6, MC + 10, zb + 2.6, "#b9c0c8", "#555")
r3(MC - 4.65, zb + 0.6, MC + 4.65, zb + 2.0, "#ffc400", "#8a6d10")
r3(MC - LID_D / 2 - 0.2, zb + LID_H / 2 - LUG_H / 2, MC - R_OUT - 0.3, zb + LID_H / 2 + LUG_H / 2, "#ffc400", "#8a6d10")   # lug (shown through the slot)
T(SX(MC + R_OUT + 1.5), SZ(zb + 2.0), "printed cup 24.6 mm, 3 mm tall, 2 lugs + an M10 washer (DIN 125, 3 g) inside: ~3.5 g", 12)
T(SX(MC + R_OUT + 1.5), SZ(zb + 2.0) + 17, f"full stack: lid top z {zb + LID_H:.1f};  top of travel {TOP - 0.4:.1f} (the J); magazine top {TOP}", 12, col="#555")
T(SX(MC + R_OUT + 1.5), SZ(zb + 2.0) + 34, "sim (standalone): 3 g on the stack -> one tag per drop, 10/10", 12, col="#1a7f37", w="bold")
W, H = int(EX(100)), int(SZ(FLOOR - 4))
open(OUT, "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>")
print(W, H)
