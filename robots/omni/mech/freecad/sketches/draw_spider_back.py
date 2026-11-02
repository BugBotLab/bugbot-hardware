# 2D: Spider using the existing gripper arm + servo. The arm carries the magazine and a TPU ground roller between its
# tips. Arm down -> roller on the floor; driving forward turns it; its top drags the bottom tag out of the front slot.
# Side view (lowered solid, raised dashed) + top view, to scale. Pivot, arm, mast, board, chassis from the BugBot model.
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
def poly(pts, fill, stroke="#333", sw=1, dash=None, op=1):
    a('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="{fill}"{st(stroke, sw, dash, op)}/>')

PX, PZ = 8.0, 36.7                 # existing arm pivot (servo + pivot tube unchanged)
PCB_TOP = 30.6; CAM_Z = PCB_TOP + 17; TOF_Z = PCB_TOP + 25.5
D = 16.0; RR = D / 2               # TPU ground roller
RX, RZ = 48.5, RR                  # roller axle (option A: magazine back in the pocket)
RX_OLD = 60.0; MC_OLD = RX_OLD - 6.0; MC_B = 47.5
MC = RX - 6.0                      # magazine centre: roller contact 6 mm ahead of the centre
R_IN, R_OUT = 12.9, 14.5
FLOOR = D - 0.3                    # roller pokes 0.3 mm through the floor window
TOP = FLOOR + 20 * 0.9 + 4.0 + 3.0 # stack + follower + head
LIFT = 4.0                         # degrees the servo raises the arm to park
def rot(x, z, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    dx, dz = x - PX, z - PZ
    return PX + dx * c - dz * s, PZ + dx * s + dz * c

# ================= SIDE VIEW =================
OX, OY = 50, 120
X = lambda x: OX + (x + 20) * SC; Z = lambda z: OY + (84 - z) * SC
def P(pts, deg=0): return [(X(p[0]), Z(p[1])) for p in (rot(x, z, deg) for x, z in pts)]
def box_pts(x0, z0, x1, z1): return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
text(X(-20), OY - 70, "Spider v3: magazine moved back into the pocket (2D, to scale)", 22, weight="bold")
text(X(-20), OY - 44, "Option A: magazine 11.5 mm further back, sitting in the board / chassis ball notch; shorter arm. Kicker has to go.", 14, col="#333")
text(X(-20), OY - 16, "SIDE VIEW (section at the centreline; arm lowered = solid, parked = dashed)", 15, weight="bold")
line(X(-20), Z(0), X(105), Z(0), "#333", 1.5); text(X(-19), Z(0) + 16, "floor", 11, col="#555")
# robot (from the model)
poly(P(box_pts(-20, 6.5, 37.5, 29.0)), "#e9d9a6", "#8a7a40", 1, None, 0.8); text(X(-15), Z(14), "chassis", 12, col="#6d5f2c")
poly(P(box_pts(24.4, 10.0, 37.6, 29.1)), "#ffffff", "#8a7a40", 0.8, "3 2"); text(X(24.8), Z(11.5), "ball pocket (open", 9, col="#6d5f2c"); text(X(24.8), Z(11.5) + 11, "above the floor)", 9, col="#6d5f2c")
poly(P(box_pts(-20, PCB_TOP - 1.6, 36.4, PCB_TOP)), "#2e6b3f", "#1c4428"); text(X(-15), Z(PCB_TOP) - 4, "main board", 11, col="#1c4428")
poly(P(box_pts(14.2, 30.6, 24.0, 61.4)), "#e2b93b", "#8a6d10"); text(X(19.1), Z(40), "mast", 11, "middle", "#5b4708")
poly(P(box_pts(-18.5, 57.0, 24.0, 61.4)), "#e2b93b", "#8a6d10")
a(f'<path d="M{X(-15):.1f},{Z(62):.1f} A{15*SC:.1f},{18.8*SC:.1f} 0 0 1 {X(15):.1f},{Z(62):.1f} Z" fill="#dfe3e8" stroke="#666"/>')
a(f'<circle cx="{X(26.5):.1f}" cy="{Z(CAM_Z):.1f}" r="{3*SC:.1f}" fill="#223"/>'); text(X(27), Z(CAM_Z) - 22, "camera", 11, col="#222")
poly(P(box_pts(25.5, TOF_Z - 1, 27.5, TOF_Z + 1)), "#333", "#000"); text(X(28.5), Z(TOF_Z) + 4, "ToF", 11, col="#222")
# camera lower sight line over the parked magazine
line(X(26.5), Z(CAM_Z), X(105), Z(CAM_Z - (105 - 26.5) * math.tan(math.radians(3))), "#7b61ff", 0.8, "6 4")
# old gripper (ghost)
a(f'<polyline points="{X(PX):.1f},{Z(PZ):.1f} {X(66.7):.1f},{Z(17.8):.1f}" fill="none" stroke="#c62828" stroke-width="5" stroke-opacity="0.18"/>')
a(f'<circle cx="{X(66.7):.1f}" cy="{Z(17.8):.1f}" r="{2.5*SC:.1f}" fill="#ff6b6b" fill-opacity="0.18" stroke="#c62828" stroke-dasharray="4 3"/>')
text(X(72), Z(21), "old front bar", 11, col="#c62828")
# kicker (can stay: the pocket behind the magazine is free)
poly(P(box_pts(-1.5, 15.8, 21.5, 28.8)), "#b0b7bf", "#555", 0.8, "3 2", 0.6); text(X(1), Z(21), "kicker (removed in A)", 10, col="#333")
poly(P(box_pts(21.5, 16.3, 31.5, 28.3)), "#ff6b6b", "#c62828", 1, "4 2", 0.35); text(X(21.7), Z(30) , "kick stroke 10 mm", 10, col="#c62828")
poly(P(box_pts(MC_OLD - R_OUT, FLOOR - 1.6, MC_OLD + R_OUT, TOP)), "none", "#1a7f37", 1.2, "6 4"); text(X(MC_OLD + R_OUT) + 4, Z(TOP) + 14, "v2 magazine", 11, col="#1a7f37")
def dispenser(deg, dash=None, op=1.0):
    # arm side plate (outline): pivot boss -> roller axle, with a lug up the magazine back
    arm = [(4, 39.7), (42, 39.7), (42, 11), (RX + 3, 11), (RX + 3, 5), (36.5, 5), (36.5, 33.7), (4, 33.7)]   # same L as the old hoop arm (top run z 33.7-39.7 over the board), lower run to the axle
    poly(P(arm, deg), "#9c27b0" if not dash else "none", "#5e1270", 1.2, dash, 0.35 * op)
    mag = box_pts(MC - R_OUT, FLOOR - 1.6, MC + R_OUT, TOP)
    poly(P(mag, deg), "#d5dbe2" if not dash else "none", "#444", 1.2, dash, op)
    if not dash:
        poly(P(box_pts(MC - R_IN, FLOOR, MC + R_IN, TOP), deg), "#f6f8fa", "#666", 0.8)
        for i in range(20):
            poly(P(box_pts(MC - 12.5, FLOOR + i * 0.9, MC + 12.5, FLOOR + (i + 1) * 0.9 - 0.12), deg), "#ffe9a8", "#b08800", 0.4)
        poly(P(box_pts(MC - 11.5, FLOOR + 18, MC + 11.5, FLOOR + 22), deg), "#888", "#444", 0.8)
        poly(P(box_pts(MC + R_IN, FLOOR, MC + R_OUT + 0.1, FLOOR + 1.35), deg), "#fff", "#c62828", 1.2)
    cx, cz = rot(RX, RZ, deg)
    a(f'<circle cx="{X(cx):.1f}" cy="{Z(cz):.1f}" r="{RR*SC:.1f}" fill="{"#222" if not dash else "none"}"{st("#000", 1.2, dash, 0.9)}/>')
    if not dash:
        a(f'<circle cx="{X(cx):.1f}" cy="{Z(cz):.1f}" r="{(RR-2.5)*SC:.1f}" fill="#555" stroke="#000"/>')
        a(f'<circle cx="{X(cx):.1f}" cy="{Z(cz):.1f}" r="{1.5*SC:.1f}" fill="#ccc" stroke="#333"/>')
    a(f'<circle cx="{X(PX):.1f}" cy="{Z(PZ):.1f}" r="{2.5*SC:.1f}" fill="#fff" stroke="#5e1270" stroke-width="1.5"/>')
dispenser(LIFT, "5 3")
dispenser(0)
# motion arrows: robot forward, roller spin, tag out
ax = X(78); line(X(70), Z(-5), X(90), Z(-5), "#1a7f37", 2.5)
a(f'<path d="M{X(90)-8:.1f},{Z(-5)-6:.1f} L{X(90):.1f},{Z(-5):.1f} L{X(90)-8:.1f},{Z(-5)+6:.1f}" fill="none" stroke="#1a7f37" stroke-width="2.5"/>')
text(X(70), Z(-5) + 22, "robot drives forward ~20 mm", 12, col="#1a7f37", weight="bold")
a(f'<path d="M{X(RX-5):.1f},{Z(RZ+RR+3):.1f} A{(RR+3)*SC:.1f},{(RR+3)*SC:.1f} 0 0 1 {X(RX+RR+3):.1f},{Z(RZ):.1f}" fill="none" stroke="#e67e22" stroke-width="2.5"/>')
a(f'<path d="M{X(RX+RR+3)-6:.1f},{Z(RZ)-9:.1f} L{X(RX+RR+3):.1f},{Z(RZ):.1f} L{X(RX+RR+3)+6:.1f},{Z(RZ)-9:.1f}" fill="none" stroke="#e67e22" stroke-width="2.5"/>')
poly([(X(MC + 18), Z(FLOOR + 0.9)), (X(MC + 30), Z(FLOOR + 0.9)), (X(MC + 30), Z(FLOOR)), (X(MC + 18), Z(FLOOR))], "#ffe9a8", "#b08800", 1)
a(f'<path d="M{X(MC+31):.1f},{Z(FLOOR+0.5):.1f} Q{X(MC+38):.1f},{Z(FLOOR):.1f} {X(MC+40):.1f},{Z(1.5):.1f}" fill="none" stroke="#b08800" stroke-width="2" stroke-dasharray="4 3"/>')
poly(P(box_pts(MC + 28, 0, MC + 53, 0.9)), "#ffe9a8", "#b08800", 0.8)
# leads
lead(X(RX + 2), Z(RZ - 2), X(92), Z(4), "16 mm TPU roller (tyre on a hub)", "ground turns it; its top drags the bottom tag")
lead(X(MC + R_OUT), Z(FLOOR + 0.7), X(92), Z(FLOOR + 6), "one-tag front slot + gate", "tag drops in front, roller rolls over it")
lead(X(MC), Z(TOP - 2), X(92), Z(TOP + 4), "magazine 20 tags, rides on the arm", f"top z {TOP:.1f} lowered / {rot(MC + R_OUT, TOP, LIFT)[1]:.1f} parked")
lead(X(PX), Z(PZ), X(-15), Z(48), "existing pivot + SG90 (unchanged)", None)
lead(X(38.5), Z(20), X(-15), Z(-6), "new arm plates (both sides, y 17-25)", "same L shape as the old hoop arms; lower run ends at the axle")
text(X(-20), Z(-16), f"Parked = servo lifts the arm {LIFT:.0f} deg: roller {math.hypot(RX-PX, RZ-PZ)*math.radians(LIFT)*(RX-PX)/math.hypot(RX-PX, RZ-PZ):.1f} mm off the floor. Camera at z {CAM_Z:.1f} still looks over the magazine.", 12, col="#333")
SIDE_BOTTOM = Z(-20)

# ================= TOP VIEW =================
OX2, OY2 = 50, SIDE_BOTTOM + 60
TX = lambda x: OX2 + (x + 20) * SC; TY = lambda y: OY2 + (45 - y) * SC
def RT(x0, y0, x1, y1, fill, stroke="#333", sw=1, dash=None, op=1):
    a(f'<rect x="{TX(min(x0,x1)):.1f}" y="{TY(max(y0,y1)):.1f}" width="{abs(x1-x0)*SC:.1f}" height="{abs(y1-y0)*SC:.1f}" fill="{fill}"{st(stroke, sw, dash, op)}/>')
text(TX(-20), OY2 - 16, "TOP VIEW (lowered)", 15, weight="bold")
a(f'<clipPath id="cf"><rect x="{TX(-20):.1f}" y="{TY(45):.1f}" width="{57.5*SC:.1f}" height="{90*SC:.1f}"/></clipPath>')
a(f'<circle cx="{TX(0):.1f}" cy="{TY(0):.1f}" r="{40.6*SC:.1f}" fill="#e9d9a6" stroke="#8a7a40" stroke-width="1.2" clip-path="url(#cf)"/>')
a(f'<path d="M{TX(37.5):.1f},{TY(25):.1f} L{TX(71.2):.1f},{TY(25):.1f} L{TX(71.2):.1f},{TY(-25):.1f} L{TX(37.5):.1f},{TY(-25):.1f}" fill="none"{st("#1a7f37", 1.6, "7 4")}/>')
text(TX(71.2) + 6, TY(-25) + 4, "original outline (x 71.2, y +/-25)", 12, col="#1a7f37")
RT(0.9, 8.6, 27.0, 35.7, "#cfd6de", "#555"); text(TX(3), TY(30), "wheel 1", 11, col="#333")
RT(-0.2, -32.6, 24.6, -13.7, "#cfd6de", "#555"); text(TX(2), TY(-28), "wheel 3", 11, col="#333")
RT(14.2, -20, 24.0, 20, "#e2b93b", "#8a6d10", 1, None, 0.85)
RT(-13.7, -11.3, 18.5, 17.9, "#3b5ea8", "#1d3466", 1, "4 2", 0.25); text(TX(-12), TY(-8), "SG90 (existing)", 10, col="#1d3466")
for y0, y1 in ((17.3, 24.8), (-24.8, -17.2)):
    RT(3.0, y0, RX + 3, y1, "#9c27b0", "#5e1270", 1.2, None, 0.35)
text(TX(32), TY(21) + 4, "arm plate", 11, "middle", "#5e1270"); text(TX(32), TY(-21) + 4, "arm plate", 11, "middle", "#5e1270")
RT(RX - RR, -12, RX + RR, 12, "#222", "#000", 1, None, 0.85)
RT(RX - 1.5, -24.8, RX + 1.5, 24.8, "#bbb", "#555", 0.6)
a(f'<path d="M{TX(36.4):.1f},{TY(17.9):.1f} A{19.6*SC:.1f},{19.6*SC:.1f} 0 0 0 {TX(36.4):.1f},{TY(-17.9):.1f}" fill="none" stroke="#2e6b3f" stroke-width="2.5"/>')
text(TX(20.5), TY(-20) + 4, "main board notch", 11, col="#1c4428")
RT(14.2, -20, 24.0, 20, "#e2b93b", "#8a6d10", 1, None, 0.85); RT(24.0, -12.2, 26.1, 9.6, "#2e6b3f", "#1c4428", 1)
RT(21.5, -8.8, 31.5, 3.2, "#ff6b6b", "#c62828", 1, "4 2", 0.35)
a(f'<circle cx="{TX(MC_OLD):.1f}" cy="{TY(0):.1f}" r="{R_OUT*SC:.1f}" fill="none" stroke="#1a7f37" stroke-width="1.2" stroke-dasharray="6 4"/>')
a(f'<circle cx="{TX(MC_B):.1f}" cy="{TY(0):.1f}" r="{R_OUT*SC:.1f}" fill="none" stroke="#e67e22" stroke-width="1.4" stroke-dasharray="3 3"/>')
text(TX(MC_OLD + R_OUT) + 4, TY(8), "v2", 12, col="#1a7f37", weight="bold")
text(TX(MC_B + R_OUT) + 4, TY(-2), "B", 12, col="#e67e22", weight="bold")
text(TX(MC - R_OUT) + 60, TY(-17) + 4, "A", 13, col="#111", weight="bold")
a(f'<circle cx="{TX(MC):.1f}" cy="{TY(0):.1f}" r="{R_OUT*SC:.1f}" fill="#d5dbe2" fill-opacity="0.85" stroke="#444" stroke-width="1.2"/>')
a(f'<circle cx="{TX(MC):.1f}" cy="{TY(0):.1f}" r="{R_IN*SC:.1f}" fill="#f6f8fa" fill-opacity="0.7" stroke="#666"/>')
RT(MC - R_OUT, -2.5, MC - R_OUT + 2, 2.5, "#888", "#444")
text(TX(MC - 3), TY(5), "magazine", 12, "middle", "#333")
RT(MC + R_IN, -12.0, MC + R_OUT + 0.2, 12.0, "#fff", "#c62828", 1.2)
lead(TX(RX + 3), TY(-8), TX(80), TY(-12), "roller 20 wide on a 3 mm axle", "through both arm plates")
lead(TX(MC - R_OUT), TY(0), TX(40), TY(-40), f"A: magazine back x {MC-R_OUT:.1f}: {MC-R_OUT-26.1:.1f} mm to the front board", "kick stroke reaches x 31.5: kicker removed")
text(TX(-20), TY(-48), f"A: centre x {MC:.1f}, front x {MC+R_OUT:.1f} (v2 {MC_OLD+R_OUT:.1f}): robot 11.5 mm shorter. Notch clearance ~4 mm. Kicker removed.", 12, col="#333", weight="bold")
text(TX(-20), TY(-48) + 18, f"B: centre x {MC_B:.1f}, back x {MC_B-R_OUT:.1f} clears the extended kicker by 1.5 mm: kicker stays, robot 6.5 mm shorter.", 12, col="#e67e22", weight="bold")
text(TX(-20), TY(-48) + 36, f"Camera: lowered top z {TOP:.1f} now {MC-R_OUT-26.5:.1f} mm in front of the lens; blocks the view below ~{math.degrees(math.atan((CAM_Z-TOP)/(MC+R_OUT-26.5))):.0f} deg down (v2 ~{math.degrees(math.atan((CAM_Z-TOP)/(MC_OLD+R_OUT-26.5))):.0f} deg).", 12, col="#333")
H = int(TY(-48) + 60); Wd = int(X(150))
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}"><rect width="{Wd}" height="{H}" fill="#fff"/>' + "".join(el) + "</svg>"
open(OUT, "w", encoding="utf-8").write(svg)
print(Wd, H)
