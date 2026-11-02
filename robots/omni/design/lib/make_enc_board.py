# BugBot wheel encoder board (x 3, identical): schematic + 2-layer PCB, generated like the LED board.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_enc_board.py
# MT6701QT-ACD magnetic angle sensor (QFN-16, A/B quadrature 1024 pulses/turn out of the box) on the wheel's axle line,
# 100 nF + 1 uF on VDD, MODE (pin 14) to GND = ABZ mode (datasheet fig. 7), centre pad left unconnected (the datasheet
# gives it no function). A 1x4 1.27 mm right-angle header at the top edge points up into a 1x4 1.27 mm SMD socket on the
# main board's underside: 3V3, GND, A, B. Clip the header's 4 leads flush (<= 0.5 mm) on the back after assembly:
# the back of the board faces the chassis wall.
# Board frame (KiCad): origin = chip centre = the wheel axle; X across the board, Y down = toward the floor.
# In the drive-unit frame (X radial): the top side faces the wheel; KiCad X = -(y - 8), KiCad Y = -(z - 12).
import math, os, re, uuid
import pcbnew

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/design/schematics/Enc"
KS = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"
KF = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
X0, X1, Y0, Y1 = -3.0, 5.0, -12.2, 4.5          # outline: 8 x 16.7 (board top edge z 24.2, bottom z 7.5)
THK = 0.8
HDR_Y = -11.1                                   # header pad row (pin tips reach z 28.6, 3.9 mm into the 4.3 mm socket)
HDR_X = [-0.905 + 1.27 * k for k in range(4)]   # pads 1..4: 3V3, GND, A, B (pad 1 nearest the board's -X edge)
os.makedirs(OUT, exist_ok=True)
U = lambda: str(uuid.uuid4())
ROOT = U()

# ------------------------------------------------------------------ MT6701QT symbol (no KiCad library symbol exists)
def _pin(typ, x, y, rot, name, num, hide=False):
    return (f'\t\t\t(pin {typ} line\n\t\t\t\t(at {x} {y} {rot})\n\t\t\t\t(length 2.54)' + ('\n\t\t\t\t(hide yes)' if hide else '') +
            f'\n\t\t\t\t(name "{name}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)'
            f'\n\t\t\t\t(number "{num}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')
def _p(name, val, y, hide=False):
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at 0 {y} 0)\n' + ('\t\t\t(hide yes)\n' if hide else '') +
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
MT_PINS = ([("power_in", 0, 15.24, 270, "VDD", "13"), ("power_in", 0, -15.24, 90, "GND", "16"), ("passive", 5.08, -15.24, 90, "EP", "17"),
            ("input", -10.16, 5.08, 0, "MODE", "14")] +
           [("bidirectional", 10.16, 10.16, 180, "A/SDA", "6"), ("bidirectional", 10.16, 7.62, 180, "B/SCL", "7"), ("bidirectional", 10.16, 5.08, 180, "Z/CSN", "8"),
            ("output", 10.16, 2.54, 180, "U", "11"), ("output", 10.16, 0, 180, "V", "12"), ("output", 10.16, -2.54, 180, "W", "9"),
            ("output", 10.16, -5.08, 180, "OUT", "15"), ("output", 10.16, -7.62, 180, "PUSH", "5")] +
           [("no_connect", -10.16, -2.54 - 2.54 * i, 0, "NC", n) for i, n in enumerate(("1", "2", "3", "4", "10"))])
MT_SYM = ('(symbol "BugBot:MT6701QT"\n\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n' +
          _p("Reference", "U", 17.78) + _p("Value", "MT6701QT", -17.78) + _p("Footprint", "", 0, True) + _p("Datasheet", "", 0, True) +
          '\t\t(symbol "MT6701QT_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -7.62 12.7)\n\t\t\t\t(end 7.62 -12.7)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n'
          '\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
          '\t\t(symbol "MT6701QT_1_1"\n' + "".join(_pin(*p) for p in MT_PINS) + '\t\t)\n\t\t(embedded_fonts no)\n\t)')

# ------------------------------------------------------------------ parts and nets
PARTS = [  # ref, lib_id, value, footprint, {pin: net}, (sch x, sch y)
    ("U1", "BugBot:MT6701QT", "MT6701QT-ACD", "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.7x1.7mm",
     {"13": "+3V3", "16": "GND", "14": "GND", "6": "ENC_A", "7": "ENC_B"}, (90, 80)),
    ("C1", "Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3V3", "2": "GND"}, (50, 70)),
    ("C2", "Device:C", "1uF", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3V3", "2": "GND"}, (60, 70)),
    ("J1", "Connector_Generic:Conn_01x04", "To main board (3V3 GND A B)", "Connector_PinHeader_1.27mm:PinHeader_1x04_P1.27mm_Horizontal",
     {"1": "+3V3", "2": "GND", "3": "ENC_A", "4": "ENC_B"}, (150, 80)),
]
NC = {("U1", n) for n in ("1", "2", "3", "4", "5", "8", "9", "10", "11", "12", "15", "17")}
JLC = {"U1": ("MT6701QT-ACD", "C49257133", "https://jlcpcb.com/partdetail/C49257133"),
       "C1": ("CL05B104KO5NNNC", "C1525", "https://jlcpcb.com/partdetail/1877-CL05B104KO5NNNC/C1525"),
       "C2": ("CL05A105KA5NQNC", "C52923", "https://jlcpcb.com/partdetail/53938-CL05A105KA5NQNC/C52923"),
       "J1": ("HX PZ1.27-1x4P WZ", "C22438190", "https://jlcpcb.com/partdetail/C22438190")}
jlc = lambda ref: JLC.get(ref)

# ------------------------------------------------------------------ schematic
def sexp_block(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: return t[i:j + 1]
def lib_symbol(lib_id):
    if lib_id == "BugBot:MT6701QT": return MT_SYM, MT_SYM
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
def place(lib_id, ref, value, fp, x, y, hide_ref=False):
    su = U(); sym_uuid[ref] = su
    s = (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom {"no" if ref.startswith("#") else "yes"})\n'
         f'\t\t(on_board {"no" if ref.startswith("#") else "yes"})\n\t\t(dnp no)\n\t\t(uuid "{su}")\n')
    part = jlc(ref) if not ref.startswith("#") else None
    s += prop("Reference", ref, x + 2, y - 6, hide_ref) + prop("Value", value, x + 2, y + 6) + prop("Footprint", fp, x, y, True) + prop("Datasheet", part[2] if part else "", x, y, True)
    if part:
        s += prop("MPN", part[0], x, y, True) + prop("LCSC", part[1], x, y, True)
    for num in pins[lib_id]:
        s += f'\t\t(pin "{num}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    s += f'\t\t(instances\n\t\t\t(project "BugBot_Enc"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
    body.append(s)
def label(net, x, y, ang=0, just="left bottom"):
    body.append(f'\t(label "{net}"\n\t\t(at {x:.2f} {y:.2f} {ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
def wire(x0, y0, x1, y1):
    body.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {x0:.2f} {y0:.2f}) (xy {x1:.2f} {y1:.2f})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
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
for i, net in enumerate(("+3V3", "GND")):                    # power flags: the nets come in on the header
    x, y = G(40 + 20 * i), G(120)
    place("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", "", x, y, True)
    label(net, x, y)
sch = (f'(kicad_sch\n\t(version 20250610)\n\t(generator "bugbot")\n\t(generator_version "10.0")\n\t(uuid "{ROOT}")\n\t(paper "A4")\n'
       f'\t(title_block\n\t\t(title "BugBot wheel encoder")\n\t\t(rev "1")\n\t\t(comment 1 "MT6701QT-ACD, A/B 1024 pulses per turn; plugs into the main board underside (1x4 1.27 mm)")\n\t)\n'
       '\t(lib_symbols\n' + "".join("\t\t" + libs[l].replace("\n", "\n\t\t") + "\n" for l in need) + '\t)\n' + "".join(body) +
       f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
open(f"{OUT}/BugBot_Enc.kicad_sch", "w", encoding="utf-8").write(sch)
open(BB + "/design/lib/BugBot_Enc.kicad_sym", "w", encoding="utf-8").write(
    '(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "bugbot")\n\t(generator_version "10.0")\n\t' + MT_SYM.replace('"BugBot:MT6701QT"', '"MT6701QT"') + '\n)\n')
open(f"{OUT}/sym-lib-table", "w").write('(sym_lib_table\n  (version 7)\n  (lib (name "BugBot")(type "KiCad")(uri "${KIPRJMOD}/../lib/BugBot_Enc.kicad_sym")(options "")(descr "BugBot wheel-encoder symbol"))\n)\n')
if not os.path.exists(f"{OUT}/BugBot_Enc.kicad_pro"):
    open(f"{OUT}/BugBot_Enc.kicad_pro", "w").write('{\n  "meta": {\n    "filename": "BugBot_Enc.kicad_pro",\n    "version": 3\n  }\n}\n')

# ------------------------------------------------------------------ board
mm = pcbnew.FromMM
def P(X, Y): return pcbnew.VECTOR2I(mm(100 + X), mm(100 + Y))      # Y down (board frame above)
board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(THK))
ds.SetGridOrigin(P(0, 0)); ds.SetAuxOrigin(P(0, 0))                   # origin = chip centre = axle
ds.m_TrackMinWidth = mm(0.127); ds.m_MinClearance = mm(0.127); ds.m_ViasMinSize = mm(0.45); ds.m_MinThroughDrill = mm(0.2)
ds.m_CopperEdgeClearance = mm(0.25)
ds.m_NetSettings.GetDefaultNetclass().SetClearance(mm(0.127)); ds.m_NetSettings.GetDefaultNetclass().SetTrackWidth(mm(0.15))
nets = {}
def net(n):
    n = n if n.startswith("/") else "/" + n
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
    return nets[n]
for (a, b) in [((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))]:
    e = pcbnew.PCB_SHAPE(board); e.SetShape(pcbnew.SHAPE_T_SEGMENT); e.SetLayer(pcbnew.Edge_Cuts)
    e.SetStart(P(*a)); e.SetEnd(P(*b)); e.SetWidth(mm(0.05)); board.Add(e)
fps = {}
partmap = {p[0]: p for p in PARTS}
def add_fp(ref, X, Y, rot):
    fp = partmap[ref][3]; lib, name = fp.split(":")
    f = pcbnew.FootprintLoad(KF + lib + ".pretty", name)
    f.SetReference(ref); f.SetValue(partmap[ref][2]); f.SetFPIDAsString(fp)
    f.SetPosition(P(X, Y)); f.SetOrientationDegrees(rot)
    f.SetPath(pcbnew.KIID_PATH(f"/{sym_uuid[ref]}"))
    if jlc(ref):
        for k, v in zip(("MPN", "LCSC", "Datasheet"), jlc(ref)):
            f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
    board.Add(f); fps[ref] = f
    return f
def pad(ref, num): return fps[ref].FindPadByNumber(num)
def xy(p):
    v = p.GetPosition(); return (pcbnew.ToMM(v.x) - 100, pcbnew.ToMM(v.y) - 100)
def track(pts, n, w=0.2, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board); t.SetStart(P(*a)); t.SetEnd(P(*b)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net(n)); board.Add(t)
def via(X, Y, n):
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(X, Y)); v.SetDrill(mm(0.25)); v.SetWidth(mm(0.5)); v.SetNet(net(n)); board.Add(v)

add_fp("U1", 0.0, 0.0, 0)
add_fp("C1", 1.7, -3.1, 0)
add_fp("C2", 1.7, -4.3, 0)
# right-angle header: its pins run along the footprint's +X; turn it so they point up (-Y), then put pad 1 at HDR_X[0]
j = add_fp("J1", 0.0, 0.0, 90)
p1 = xy(pad("J1", "1")); p4 = xy(pad("J1", "4"))
if p4[0] < p1[0]:                                  # pad 4 must be at +X: turn the other way
    j.SetOrientationDegrees(270); p1 = xy(pad("J1", "1"))
j.SetPosition(P(HDR_X[0] - p1[0], HDR_Y - p1[1]))
for ref, lid, val, fp, netmap, _ in PARTS:
    for num, n in netmap.items():
        pad(ref, num).SetNet(net(n))
NAMES = {p_[5]: p_[4] for p_ in MT_PINS}
for (ref, num) in sorted(NC):                       # the schematic's no-connect nets, so the board matches it
    nn = f"unconnected-({ref}-{NAMES[num].replace('/', '{slash}')}-Pad{num})"
    ni = pcbnew.NETINFO_ITEM(board, nn); board.Add(ni); pad(ref, num).SetNet(ni)
for g in list(j.GraphicalItems()):                 # the header overhangs the top edge: no silkscreen off the board
    if g.GetLayer() == pcbnew.F_SilkS: j.Remove(g)
# sanity: the header's body / pins must reach up (toward -Y) past the top edge
bbJ = j.GetBoundingBox(False, False)
assert pcbnew.ToMM(bbJ.GetTop()) - 100 < Y0 - 3, "header pins do not point up"

# --- routing (top: power; bottom: A and B under a GND pour)
u = {n: xy(pad("U1", n)) for n in ("6", "7", "13", "14", "16")}
c1a, c1b, c2a, c2b = xy(pad("C1", "1")), xy(pad("C1", "2")), xy(pad("C2", "1")), xy(pad("C2", "2"))
h = {n: xy(pad("J1", n)) for n in "1234"}
# 3V3: pin 13 -> C1 -> C2 -> header pad 1
track([u["13"], (u["13"][0], -2.15), (c1a[0], -2.62), c1a, c2a, (c2a[0], -5.2), (h["1"][0], -7.4), h["1"]], "+3V3", 0.25)
# GND: pin 16 and MODE (pin 14) and the capacitors to vias into the bottom pour
via(-0.95, -2.45, "GND"); track([u["16"], (u["16"][0], -2.0), (-0.95, -2.45)], "GND", 0.2)
via(0.05, -2.55, "GND"); track([u["14"], (u["14"][0], -2.1), (0.05, -2.55)], "GND", 0.2)
for c in (c1b, c2b):
    vx = c[0] + 0.75; via(vx, c[1], "GND"); track([c, (vx, c[1])], "GND", 0.25)
# A and B: down out of the chip, through to the bottom, up the board edges to header pads 3 and 4
va, vb = (-0.65, 2.45), (0.65, 2.45)
track([u["6"], (u["6"][0], 2.0), va], "ENC_A"); via(*va, "ENC_A")
track([u["7"], (u["7"][0], 2.0), vb], "ENC_B"); via(*vb, "ENC_B")
track([va, (-2.3, 0.8), (-2.3, -8.4), (h["3"][0], -9.9), h["3"]], "ENC_A", 0.2, pcbnew.B_Cu)
track([vb, (4.1, -1.0), (4.1, -9.7), (h["4"][0], -10.3), h["4"]], "ENC_B", 0.2, pcbnew.B_Cu)
# GND pours, both sides
for layer in (pcbnew.B_Cu, pcbnew.F_Cu):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net("GND"))
    ol = z.Outline(); ol.NewOutline()
    for p_ in ((X0 + 0.3, Y0 + 0.3), (X1 - 0.3, Y0 + 0.3), (X1 - 0.3, Y1 - 0.3), (X0 + 0.3, Y1 - 0.3)):
        ol.Append(P(*p_))
    z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.15)); board.Add(z)
for f in fps.values():
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
for txt, X, Y, sz in (("ENC", 1.0, 3.7, 0.8), ("B A GND 3V3", 1.0, -8.0, 0.8)):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(X, Y)); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(sz), mm(sz))); t.SetTextThickness(mm(0.1)); board.Add(t)
board.BuildConnectivity()
pcbnew.SaveBoard(f"{OUT}/BugBot_Enc.kicad_pcb", board)

# ------------------------------------------------------------------ JLCPCB assembly files (BOM + CPL), origin = chip centre
ROT_OFS = {}          # QFN-16 / 0402: JLC and KiCad agree; the THT header is placed by JLC from its holes (check the preview)
os.makedirs(f"{OUT}/jlc", exist_ok=True)
with open(f"{OUT}/jlc/BugBot_Enc_BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Comment,Designator,Footprint,LCSC\n")
    for ref, lid, val, fp, netmap, _ in PARTS:
        fh.write(f'"{val}","{ref}","{fp.split(":")[1]}","{jlc(ref)[1]}"\n')
with open(f"{OUT}/jlc/BugBot_Enc_CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
    for ref in ("C1", "C2", "J1", "U1"):
        f = fps[ref]; X, Y = xy(f)
        fh.write(f"{ref},{X:.4f}mm,{-Y:.4f}mm,Top,{f.GetOrientationDegrees() % 360:g}\n")
from hand_solder import split                    # through-hole connectors we solder: out of the JLC files
split("BugBot_Enc", f"{OUT}/jlc")
print("ok", {r: [round(v, 3) for v in xy(f)] + [f.GetOrientationDegrees()] for r, f in fps.items()},
      "header pads", {n: [round(v, 3) for v in xy(pad("J1", n))] for n in "1234"})
