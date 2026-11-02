# BugBot LED ring board: schematic + 2-layer PCB, generated (so it stays parametric like the rest of the robot).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_led_board.py
# 8 x WS2812B-2020 on a 25.6 mm disc that sits in the top deck's pocket under the dome; 74AHCT1G125 level shifter
# (ESP32 3.3 V data -> 5 V LEDs), 33R series, 10 uF bulk, 100 nF per LED; the 3-wire JST-SH lead from J4 on the main
# board is soldered into 3 holes in the middle (5V / DIN / GND); 2 x 2.2 holes at r 10.8 for the M2 nylon screws.
# Robot frame: X, Y as in FreeCAD (board centre = robot axis); KiCad: x = 100 + X, y = 100 - Y.
import math, os, re, uuid
import pcbnew

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/design/schematics/retired/LED"
KS = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"
KF = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
LIBDIR = BB + "/design/lib/BugBot"
OD, N, R_LED, R_5V, R_CAP, R_SCREW, KEEP = 25.6, 8, 9.3, 7.0, 6.5, 10.8, 2.6
os.makedirs(OUT, exist_ok=True)
U = lambda: str(uuid.uuid4())
ROOT = U()

# ------------------------------------------------------------------ parts and nets
LED_A = [-22.5 - 45 * k for k in range(N)]                 # robot angles (deg), D1..D8 clockwise (the footprint's DOUT leads that way); the chain breaks at the 0 deg screw
PARTS = []   # ref, lib_id, value, footprint, {pin: net}, (sch x, sch y)
PARTS.append(("J1", "Connector_Generic:Conn_01x03", "LED lead (5V DIN GND)", "BugBot:SolderWire_1x03_P2.60mm_D0.7mm",
              {"1": "+5V", "2": "DIN_IN", "3": "GND"}, (30, 40)))
PARTS.append(("U1", "74xGxx:74LVC1G125", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-23-5",
              {"1": "GND", "2": "DIN_IN", "3": "GND", "4": "DIN_BUF", "5": "+5V"}, (70, 40)))
PARTS.append(("R1", "Device:R", "33R", "Resistor_SMD:R_0402_1005Metric", {"1": "DIN_BUF", "2": "D1_DIN"}, (100, 40)))
PARTS.append(("C9", "Device:C", "10uF", "Capacitor_SMD:C_0603_1608Metric", {"1": "+5V", "2": "GND"}, (30, 70)))
for k in range(N):
    din = f"D{k + 1}_DIN"; dout = f"D{k + 2}_DIN" if k < N - 1 else "D8_DOUT"
    PARTS.append((f"D{k + 1}", "LED:WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
                  {"1": dout, "2": "GND", "3": din, "4": "+5V"}, (125 + 40 * (k % 4), 40 + 35 * (k // 4))))
    PARTS.append((f"C{k + 1}", "Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric", {"1": "+5V", "2": "GND"}, (125 + 40 * (k % 4), 120 + 25 * (k // 4))))
for i, h in enumerate(("H1", "H2")):
    PARTS.append((h, "Mechanical:MountingHole", "M2", "MountingHole:MountingHole_2.2mm_M2", {}, (30 + 15 * i, 110)))
NC = {("D8", "1")}                                          # last DOUT: no connect
# JLCPCB assembly parts (checked against the JLC library 2026-10-20, see schematics/retired/LED/JLC_BOM.md): ref prefix -> MPN, LCSC, datasheet / part page.
# The LED is the WS2812B-2020-V6 (the plain WS2812B-2020 C965555 is end-of-life at JLC); same pinout and land pattern as KiCad's footprint.
JLC = {"D": ("WS2812B-2020-V6", "C52917434", "https://jlcpcb.com/partdetail/Worldsemi-WS2812B_2020V6/C52917434"),
       "U": ("SN74AHCT1G125DBVR", "C7484", "https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf"),
       "R": ("0402WGF330JTCE", "C25105", "https://jlcpcb.com/partdetail/25848-0402WGF330JTCE/C25105"),
       "C9": ("CL10A106KP8NNNC", "C19702", "https://jlcpcb.com/partdetail/20411-CL10A106KP8NNNC/C19702"),
       "C": ("CL05B104KO5NNNC", "C1525", "https://jlcpcb.com/partdetail/1877-CL05B104KO5NNNC/C1525")}
def jlc(ref):
    return JLC.get(ref) or JLC.get(ref[0])

# ------------------------------------------------------------------ schematic
def sexp_block(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: return t[i:j + 1]
def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    t = open(KS + lib + ".kicad_sym", encoding="utf-8").read()
    blk = sexp_block(t, t.index(f'(symbol "{name}"'))
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1), blk
def pin_table(blk):
    return {m.group(9): (float(m.group(3)), float(m.group(4)), float(m.group(5))) for m in re.finditer(
        r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]*)"', blk, re.S)}
def prop(name, val, x, y, hide=False):
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {x:.2f} {y:.2f} 0)\n' + ("\t\t\t(hide yes)\n" if hide else "") +
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')

libs, pins, body, sym_uuid = {}, {}, [], {}
need = sorted({p[1] for p in PARTS} | {"power:PWR_FLAG"})
for lid in need:
    libs[lid], raw = lib_symbol(lid); pins[lid] = pin_table(raw)
pwr_n = [0]
def place(lib_id, ref, value, fp, x, y, hide_ref=False):
    su = U(); sym_uuid[ref] = su
    s = (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom {"no" if ref[0] in "#HJ" else "yes"})\n'
         f'\t\t(on_board {"no" if ref.startswith("#") else "yes"})\n\t\t(dnp no)\n\t\t(uuid "{su}")\n')
    part = jlc(ref) if not ref.startswith("#") else None
    s += prop("Reference", ref, x + 2, y - 6, hide_ref) + prop("Value", value, x + 2, y + 6) + prop("Footprint", fp, x, y, True) + prop("Datasheet", part[2] if part else "", x, y, True)
    if part:
        s += prop("MPN", part[0], x, y, True) + prop("LCSC", part[1], x, y, True)
    for num in pins[lib_id]:
        s += f'\t\t(pin "{num}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    s += f'\t\t(instances\n\t\t\t(project "BugBot_LED"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
    body.append(s)
def label(net, x, y, ang=0, just="left bottom"):
    body.append(f'\t(label "{net}"\n\t\t(at {x:.2f} {y:.2f} {ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
def wire(x0, y0, x1, y1):
    body.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {x0:.2f} {y0:.2f}) (xy {x1:.2f} {y1:.2f})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
# a pin's tip points away from its body opposite to its rotation: a short wire out, the label at its end
OUTW = {0: (-1, 0, 0, "right bottom"), 180: (1, 0, 0, "left bottom"), 90: (0, 1, 90, "right bottom"), 270: (0, -1, 90, "left bottom")}
def pin_label(net, X, Y, rot):
    dx, dy, ang, just = OUTW[int(rot) % 360]
    X1, Y1 = X + 2.54 * dx, Y + 2.54 * dy
    wire(X, Y, X1, Y1); label(net, X1, Y1, ang, just)
G = lambda v: round(v / 2.54) * 2.54
for ref, lid, val, fp, netmap, (sx, sy) in PARTS:
    sx, sy = G(sx), G(sy)
    place(lid, ref, val, fp, sx, sy)
    for num, (px, py, prot) in pins[lid].items():
        X, Y = sx + px, sy - py
        if (ref, num) in NC:
            body.append(f'\t(no_connect\n\t\t(at {X:.2f} {Y:.2f})\n\t\t(uuid "{U()}")\n\t)\n')
        elif num in netmap:
            pin_label(netmap[num], X, Y, prot)
for i, net in enumerate(("+5V", "GND")):                     # power flags: the nets come in on the lead
    x, y = G(30 + 20 * i), G(140)
    place("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", "", x, y, True)
    label(net, x, y)
sch = (f'(kicad_sch\n\t(version 20250610)\n\t(generator "bugbot")\n\t(generator_version "10.0")\n\t(uuid "{ROOT}")\n\t(paper "A4")\n'
       f'\t(title_block\n\t\t(title "BugBot LED ring")\n\t\t(rev "1")\n\t\t(comment 1 "8 x WS2812B-2020, 74AHCT1G125 level shifter, 3-wire lead to J4 on the main board")\n\t)\n'
       '\t(lib_symbols\n' + "".join("\t\t" + libs[l].replace("\n", "\n\t\t") + "\n" for l in need) + '\t)\n' + "".join(body) +
       f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
open(f"{OUT}/BugBot_LED.kicad_sch", "w", encoding="utf-8").write(sch)
if not os.path.exists(f"{OUT}/BugBot_LED.kicad_pro"):
    open(f"{OUT}/BugBot_LED.kicad_pro", "w").write('{\n  "meta": {\n    "filename": "BugBot_LED.kicad_pro",\n    "version": 3\n  }\n}\n')

# ------------------------------------------------------------------ board
mm = pcbnew.FromMM
def P(X, Y): return pcbnew.VECTOR2I(mm(100 + X), mm(100 - Y))
def polar(r, a): return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(1.0))
ds.SetGridOrigin(P(0, 0)); ds.SetAuxOrigin(P(0, 0))                 # grid origin = the robot axis (the ECAD link exports from it)
ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15); ds.m_ViasMinSize = mm(0.5); ds.m_MinThroughDrill = mm(0.25)
nets = {}
def net(n):
    n = n if n.startswith("/") else "/" + n
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
    return nets[n]
edge = pcbnew.PCB_SHAPE(board); edge.SetShape(pcbnew.SHAPE_T_CIRCLE); edge.SetLayer(pcbnew.Edge_Cuts)
edge.SetCenter(P(0, 0)); edge.SetEnd(P(OD / 2, 0)); edge.SetWidth(mm(0.05)); board.Add(edge)
fps = {}
def add_fp(ref, fp, X, Y, rot, value):
    lib, name = fp.split(":")
    f = pcbnew.FootprintLoad((LIBDIR if lib == "BugBot" else KF + lib) + ".pretty", name)
    f.SetReference(ref); f.SetValue(value); f.SetFPIDAsString(fp)
    f.SetPosition(P(X, Y)); f.SetOrientationDegrees(rot)
    f.SetPath(pcbnew.KIID_PATH(f"/{sym_uuid[ref]}"))
    if jlc(ref):
        for k, v in zip(("MPN", "LCSC", "Datasheet"), jlc(ref)):
            f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
    if name.startswith("LED_WS2812B-2020"):        # the library footprint points at a model KiCad 10 doesn't ship: ours instead
        f.Models().clear()
        m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KIPRJMOD}/../lib/3dmodels/LED_WS2812B-2020_PLCC4_2.0x2.0mm.step"; f.Models().push_back(m)
    board.Add(f); fps[ref] = f
    return f
def pad(ref, num): return fps[ref].FindPadByNumber(num)
def xy(p):
    v = p.GetPosition(); return (pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y))
def track(pts, n, w=0.2, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board); t.SetStart(P(*a)); t.SetEnd(P(*b)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net(n)); board.Add(t)
def via(X, Y, n):
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(X, Y)); v.SetDrill(mm(0.3)); v.SetWidth(mm(0.6)); v.SetNet(net(n)); board.Add(v)

partmap = {p[0]: p for p in PARTS}
# LEDs tangential: of the 4 rotations take the one with DOUT + VDD inner, DOUT leading (clockwise), DIN outer and trailing
for k, a in enumerate(LED_A):
    ref = f"D{k + 1}"; X, Y = polar(R_LED, a)
    best = None
    lib, name = partmap[ref][3].split(":")
    probe = pcbnew.FootprintLoad(KF + lib + ".pretty", name)          # not on the board: just to read its pads
    ang = lambda q: (math.degrees(math.atan2(q[1], q[0])) - a + 540) % 360 - 180
    for rot in (a, a + 90, a + 180, a + 270):
        probe.SetPosition(P(X, Y)); probe.SetOrientationDegrees(rot % 360)
        dout, din = xy(probe.FindPadByNumber("1")), xy(probe.FindPadByNumber("3"))
        vdd, vss = xy(probe.FindPadByNumber("4")), xy(probe.FindPadByNumber("2"))
        R_ = lambda q: math.hypot(*q)
        if R_(dout) < R_(din) and R_(vdd) < R_(vss) and ang(dout) < ang(vdd):
            best = rot % 360
    add_fp(ref, partmap[ref][3], X, Y, best, "WS2812B-2020")
    cX, cY = polar(R_CAP, a + 8)
    add_fp(f"C{k + 1}", partmap[f"C{k + 1}"][3], cX, cY, (a + 8) % 360, "100nF")        # pad 1 out, pad 2 in (checked below)
    c1, c2 = xy(pad(f"C{k + 1}", "1")), xy(pad(f"C{k + 1}", "2"))
    if math.hypot(*c1) < math.hypot(*c2):
        fps[f"C{k + 1}"].SetOrientationDegrees((a + 8 + 180) % 360)
add_fp("J1", partmap["J1"][3], -2.6, -1.2, 0, "LED lead (5V DIN GND)")
add_fp("U1", partmap["U1"][3], 2.0, 3.0, 0, "74AHCT1G125")
add_fp("R1", partmap["R1"][3], 3.7, 0.6, 0, "33R")
add_fp("C9", partmap["C9"][3], 0.4, -3.4, 0, "10uF")
add_fp("H1", partmap["H1"][3], R_SCREW, 0, 0, "M2")
add_fp("H2", partmap["H2"][3], -R_SCREW, 0, 0, "M2")
for ref, lid, val, fp, netmap, _ in PARTS:
    for num, n in netmap.items():
        if (ref, num) not in NC:
            pad(ref, num).SetNet(net(n))
pad("D8", "1").SetNet(nets.setdefault("unconnected-(D8-DOUT-Pad1)", pcbnew.NETINFO_ITEM(board, "unconnected-(D8-DOUT-Pad1)")))
board.Add(nets["unconnected-(D8-DOUT-Pad1)"])

# --- routing
ring = [polar(R_5V, t) for t in range(0, 361, 5)]
track(ring, "+5V", 0.4)                                                    # 5V ring inside the LEDs
for k, a in enumerate(LED_A):
    d = f"D{k + 1}"; c = f"C{k + 1}"
    vdd = xy(pad(d, "4")); track([vdd, polar(R_5V, math.degrees(math.atan2(vdd[1], vdd[0])))], "+5V", 0.3)
    vss = xy(pad(d, "2")); av = math.degrees(math.atan2(vss[1], vss[0]))
    gv = polar(10.75, av); track([vss, gv], "GND", 0.3); via(*gv, "GND")
    c2 = xy(pad(c, "2")); ac = math.degrees(math.atan2(c2[1], c2[0])); cv = polar(5.35, ac)
    track([c2, cv], "GND", 0.3); via(*cv, "GND")
    c1 = xy(pad(c, "1")); track([c1, polar(R_5V, math.degrees(math.atan2(c1[1], c1[0])))], "+5V", 0.3)
    if k < N - 1:
        o = xy(pad(d, "1")); i = xy(pad(f"D{k + 2}", "3"))
        mid_a = (a + LED_A[k + 1]) / 2
        if abs((mid_a % 360) - 180) < 1:          # round the screw hole at 180: under the next LED's 5V pad on the bottom
            va, vb = polar(8.0, 192), polar(10.6, 160)
            track([o, va], f"D{k + 2}_DIN"); via(*va, f"D{k + 2}_DIN")
            track([va, polar(7.7, 180), polar(7.7, 170), vb], f"D{k + 2}_DIN", 0.2, pcbnew.B_Cu); via(*vb, f"D{k + 2}_DIN")
            track([vb, i], f"D{k + 2}_DIN")
        else:
            track([o, polar(9.1, mid_a), i], f"D{k + 2}_DIN")
# centre
j1, j2, j3 = xy(pad("J1", "1")), xy(pad("J1", "2")), xy(pad("J1", "3"))
track([j1, polar(R_5V, 188)], "+5V", 0.4)
c9a, c9b = xy(pad("C9", "1")), xy(pad("C9", "2"))
track([j1, (c9a[0], j1[1] - 1.2), c9a], "+5V", 0.4)
track([c9b, (j3[0], c9b[1]), j3], "GND", 0.4); via(j3[0] + 1.0, j3[1] - 1.4, "GND"); track([j3, (j3[0] + 1.0, j3[1] - 1.4)], "GND", 0.4)
u = {n: xy(pad("U1", n)) for n in "12345"}
track([j2, (-0.6, 0.0), (-0.6, u["2"][1]), u["2"]], "DIN_IN")
via(0.0, 4.3, "GND"); track([u["1"], (0.0, 4.3)], "GND", 0.3)
via(1.7, 1.2, "GND"); track([u["3"], (1.7, 1.2)], "GND", 0.3)
track([u["5"], polar(R_5V, 55)], "+5V", 0.3)
r1a, r1b = xy(pad("R1", "1")), xy(pad("R1", "2"))
track([u["4"], r1a], "DIN_BUF")
# R1 -> D1 DIN: under the 5V ring on the bottom, back up beside D1
d1 = xy(pad("D1", "3")); a1 = math.degrees(math.atan2(d1[1], d1[0]))
vin = (r1b[0] + 0.9, r1b[1]); vout = polar(10.6, a1)
track([r1b, vin], "D1_DIN"); via(*vin, "D1_DIN")
track([vin, polar(8.2, a1 + 3), vout], "D1_DIN", 0.2, pcbnew.B_Cu); via(*vout, "D1_DIN"); track([vout, d1], "D1_DIN")
# GND pour on the bottom; no copper round the screw holes
z = pcbnew.ZONE(board); z.SetLayer(pcbnew.B_Cu); z.SetNet(net("GND"))
ol = z.Outline(); ol.NewOutline()
for t in range(0, 360, 5):
    ol.Append(P(*polar(OD / 2 - 0.25, t)))
z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2)); board.Add(z)
for s in (-1, 1):
    k = pcbnew.ZONE(board); k.SetIsRuleArea(True); k.SetLayerSet(pcbnew.LSET.AllCuMask())
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    ol = k.Outline(); ol.NewOutline()
    for t in range(0, 360, 15):
        ol.Append(P(s * R_SCREW + KEEP * math.cos(math.radians(t)), KEEP * math.sin(math.radians(t))))
    board.Add(k)
for f in fps.values():
    f.Reference().SetVisible(False); f.Value().SetVisible(False)          # a 25 mm board: no room for designators
for txt, X, Y, sz in (("BugBot LED", 0, 2.4, 0.8), ("5V", -2.6, -2.85, 0.8), ("DIN", 0.0, -2.85, 0.8), ("GND", 2.6, -2.85, 0.8)):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(X, Y)); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(sz), mm(sz))); t.SetTextThickness(mm(0.12)); board.Add(t)
board.BuildConnectivity()                                  # zones are filled by kicad-cli (DRC --refill-zones)
pcbnew.SaveBoard(f"{OUT}/BugBot_LED.kicad_pcb", board)

# ------------------------------------------------------------------ JLCPCB assembly files (BOM + CPL), origin = board centre (aux origin), Y up
# JLC's library footprints are rotated against KiCad's for some packages: SOT-23-5 has pin 1 bottom-right at 0 deg in JLC/EasyEDA
# (KiCad: top-left), so +180; the WS2812B-2020 and the 0402/0603 chips match KiCad (0).
ROT_OFS = {"SOT-23-5": 180}
os.makedirs(f"{OUT}/jlc", exist_ok=True)
groups = {}
for ref, lid, val, fp, netmap, _ in PARTS:
    if jlc(ref):
        groups.setdefault((val, fp.split(":")[1], jlc(ref)[1]), []).append(ref)
key = lambda r: (r[0], int(r[1:]))
with open(f"{OUT}/jlc/BugBot_LED_BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Comment,Designator,Footprint,LCSC\n")
    for (val, fpn, lc), refs in sorted(groups.items(), key=lambda g: key(min(g[1], key=key))):
        des = ",".join(sorted(refs, key=key))
        fh.write(f'"{val}","{des}","{fpn}","{lc}"\n')
with open(f"{OUT}/jlc/BugBot_LED_CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
    for ref in sorted((r for r in fps if jlc(r)), key=key):
        f = fps[ref]; X, Y = xy(f); fpn = partmap[ref][3].split(":")[1]
        rot = (f.GetOrientationDegrees() + ROT_OFS.get(fpn, 0)) % 360
        fh.write(f"{ref},{X:.4f}mm,{Y:.4f}mm,Top,{rot:g}\n")
print("ok", len(fps), "footprints", len(nets), "nets")
