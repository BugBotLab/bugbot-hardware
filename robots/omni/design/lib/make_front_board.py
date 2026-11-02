# BugBot front sensor board: schematic + 2-layer PCB, generated (parametric like the rest of the robot).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_front_board.py
# Stands vertically behind the mast. KiCad top (F) faces the front of the robot: VL53L5CX in the ToF window and the 24-pin
# DVP camera module (taped on, flex up through the board slot); the back (B) carries the FPC socket (opening up), the two
# camera LDOs (2V8 AVDD, 1V2 DVDD), passives and the 2 x 10 1.27 mm right-angle header whose pins go down into J6 on the
# main board. Board frame: KiCad x = 100 + robot Y, y = 100 - robot Z (as FreeCAD's ECAD link); the outline, the slot
# and the M2 hole come from FreeCAD (design/schematics/Front/mcad.json, written by mech/freecad/build_frontpcb.py).
# Routed by Freerouting (Java 25); GND pours on both layers are filled by kicad-cli (DRC --refill-zones).
import json, math, os, re, subprocess, uuid
import pcbnew

PRJ = "BugBot_Front"
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/design/schematics/Front"
KS = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"
KF = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
LIBDIR = BB + "/design/lib/BugBot"
JAVA = os.path.expanduser("~/.gradle/jdks/eclipse_adoptium-25-amd64-windows.2/bin/java.exe")
FREEROUTING = "C:/Users/Jerome/Documents/GitHub/freerouting/build/dist/freerouting-executable.jar"
MCAD = json.load(open(f"{OUT}/mcad.json"))
# robot-frame numbers from the Params sheet (mech/freecad/bugbot_params.py)
CAM_Z, TOF_Z, HDR_Z, SOCK_Y = 47.6, 56.1, 37.95, -4.5     # HDR_Z = hdr_zm (fsb_z0 + 3.3; 39.2 until 2026-10-27: J1 sat 1.28 above J6)
U = lambda: str(uuid.uuid4())
ROOT = U()

# ------------------------------------------------------------------ custom symbols (embedded in the schematic)
def pin_sx(num, name, x, y, rot, typ="passive"):
    return (f'\t\t\t(pin {typ} line\n\t\t\t\t(at {x:.2f} {y:.2f} {rot})\n\t\t\t\t(length 2.54)\n'
            f'\t\t\t\t(name "{name}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n'
            f'\t\t\t\t(number "{num}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')
def custom_symbol(lib_id, ref, left, right, w=10.16, fp=""):
    """left / right: [(num, name, type)], top to bottom."""
    name = lib_id.split(":")[1]
    n = max(len(left), len(right)); h = (n + 1) * 2.54 / 2
    eff = '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n'
    s = (f'(symbol "{lib_id}"\n\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
         f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 {h + 1.27:.2f} 0)\n{eff}\t\t)\n'
         f'\t\t(property "Value" "{name}"\n\t\t\t(at 0 {-h - 1.27:.2f} 0)\n{eff}\t\t)\n'
         f'\t\t(property "Footprint" "{fp}"\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(property "Datasheet" ""\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(property "Description" ""\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(symbol "{name}_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start {-w / 2:.2f} {h:.2f})\n\t\t\t\t(end {w / 2:.2f} {-h:.2f})\n'
         '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
         f'\t\t(symbol "{name}_1_1"\n')
    for i, (num, nm, typ) in enumerate(left):
        s += pin_sx(num, nm, -w / 2 - 2.54, h - 2.54 * (i + 1), 0, typ)
    for i, (num, nm, typ) in enumerate(right):
        s += pin_sx(num, nm, w / 2 + 2.54, h - 2.54 * (i + 1), 180, typ)
    return s + '\t\t)\n\t\t(embedded_fonts no)\n\t)'
CUSTOM = {
    "BugBot:VL53L5CX": custom_symbol("BugBot:VL53L5CX", "U", [("B1", "AVDD", "power_in"), ("B7", "AVDD", "power_in"), ("A4", "IOVDD", "power_in"),
        ("C3", "SDA", "bidirectional"), ("C4", "SCL", "input"), ("A3", "INT", "open_collector"), ("A5", "LPn", "input"), ("A1", "I2C_RST", "input"),
        ("C2", "RSVD6", "bidirectional")],
        [("C1", "GND", "power_in"), ("C7", "GND", "power_in"), ("B4", "THERMAL", "power_in"), ("A2", "RSVD4", "passive"), ("A6", "RSVD1", "passive"),
         ("A7", "RSVD2", "passive"), ("C6", "RSVD3", "passive"), ("C5", "RSVD5", "no_connect")], 15.24),
    "BugBot:LDO_XC6206": custom_symbol("BugBot:LDO_XC6206", "U", [("3", "VIN", "power_in")], [("2", "VOUT", "power_out"), ("1", "GND", "power_in")]),
}

# ------------------------------------------------------------------ parts and nets
NC = set()
PARTS = []   # ref, lib_id, value, footprint, {pin: net}, (sch x, sch y), side, dnp
def part(ref, lib, val, fp, nets, at, side="B", dnp=False):
    PARTS.append((ref, lib, val, fp, nets, at, side, dnp))
# odd pins = the row away from the edge (reached from above), even = the row by the edge (reached only through the 2 mm
# channel under it): the two 3V3 at its -Y end (beside the LDOs), three GND in the middle tied to pin 7 (GND, outer row)
# by short locked links, the 5 data lines that use the channel at its +Y end. Signals in the FPC's order along Y.
# TOF_INT is not on the header (the ToF is polled; R5 keeps it pulled up).
HDR = {1: "SDA", 3: "SCL", 5: "VSYNC", 7: "GND", 9: "HREF", 11: "D9", 13: "XCLK", 15: "D8", 17: "D7", 19: "PCLK",
       2: "3V3", 4: "3V3", 6: "GND", 8: "GND", 10: "GND", 12: "D6", 14: "D2", 16: "D5", 18: "D3", 20: "D4"}
part("J1", "Connector_Generic:Conn_02x10_Odd_Even", "To J6 (2x10 1.27 RA)", "Connector_PinHeader_1.27mm:PinHeader_2x10_P1.27mm_Horizontal",
     {str(k): v for k, v in HDR.items()}, (40, 50))
# standard 24-pin DVP camera FPC (OV2640 / OV3660 / OV5640 modules, as the ESP32-CAM): Y0 / Y1 unused in 8-bit mode
CAM = {1: None, 2: "GND", 3: "SDA", 4: "2V8", 5: "SCL", 6: "CAM_RST", 7: "VSYNC", 8: "CAM_PWDN", 9: "HREF", 10: "1V2", 11: "DOVDD",
       12: "D9", 13: "XCLK", 14: "D8", 15: "GND", 16: "D7", 17: "PCLK", 18: "D6", 19: "D2", 20: "D5", 21: "D3", 22: "D4", 23: None, 24: None}
part("J2", "Connector_Generic_MountingPin:Conn_01x24_MountingPin", "Camera 24P 0.5 FPC", "BugBot:FPC_SHOUHAN_0.5-24P_HYH2.0_Horizontal",
     dict({str(k): v for k, v in CAM.items() if v}, MP="GND"), (110, 60))
NC |= {("J2", str(k)) for k, v in CAM.items() if not v}
# LPn (A5) tied high: I2C always on
TOF = {"B1": "3V3", "B7": "3V3", "A4": "3V3", "C3": "SDA", "C4": "SCL", "A3": "TOF_INT", "A5": "3V3", "A1": "TOF_RST", "C2": "TOF_GPIO",
       "C1": "GND", "C7": "GND", "B4": "GND", "A2": "GND", "A6": "GND", "A7": "GND", "C6": "GND"}
part("U2", "BugBot:VL53L5CX", "VL53L5CX", "BugBot:ST_VL53L5CX_LGA16_6.4x3.0mm", TOF, (180, 50), "F")
NC |= {("U2", "C5")}
part("U3", "BugBot:LDO_XC6206", "XC6206P282MR (2V8 AVDD)", "Package_TO_SOT_SMD:SOT-23-3", {"3": "3V3", "2": "2V8", "1": "GND"}, (40, 110))
part("U4", "BugBot:LDO_XC6206", "XC6206P122MR (1V2 DVDD)", "Package_TO_SOT_SMD:SOT-23-3", {"3": "3V3", "2": "1V2", "1": "GND"}, (40, 140))
C0402, C0603, R0402 = "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric", "Resistor_SMD:R_0402_1005Metric"
caps = [("C1", "10uF", C0603, "3V3"), ("C2", "1uF", C0402, "3V3"), ("C3", "1uF", C0402, "2V8"), ("C4", "1uF", C0402, "3V3"), ("C5", "1uF", C0402, "1V2"),
        ("C6", "100nF", C0402, "2V8"), ("C7", "100nF", C0402, "1V2"), ("C8", "100nF", C0402, "DOVDD"), ("C9", "100nF", C0402, "CAM_RST"),
        ("C10", "4.7uF", C0402, "3V3"), ("C11", "100nF", C0402, "3V3")]
for i, (ref, val, fp, n) in enumerate(caps):
    part(ref, "Device:C", val, fp, {"1": n, "2": "GND"}, (80 + 15 * (i % 6), 110 + 30 * (i // 6)))
res = [("R4", "47k", "TOF_RST", "GND"),          # the I2C pull-ups (2.2k) are on the main board, with the Qwiic port and the IMU
       ("R5", "47k", "TOF_INT", "3V3"), ("R6", "47k", "TOF_GPIO", "3V3"), ("R7", "10k", "CAM_RST", "DOVDD"), ("R8", "10k", "CAM_PWDN", "GND"),
       ("R9", "0R", "3V3", "DOVDD"), ("R10", "0R", "2V8", "DOVDD")]
for i, (ref, val, a, b) in enumerate(res):
    part(ref, "Device:R", val, R0402, {"1": a, "2": b}, (180 + 15 * (i % 5), 110 + 30 * (i // 5)), dnp=(ref == "R10"))
# JLCPCB assembly parts (LCSC numbers checked 2026-10-20): ref -> MPN, LCSC, datasheet / part page
JLC = {"U2": ("VL53L5CXV0GC/1", "C3178303", "https://www.st.com/resource/en/datasheet/vl53l5cx.pdf"),
       "J2": ("FPC 0.5-24P HYH2.0", "C6364666", "https://www.lcsc.com/datasheet/C6364666.pdf"),
       "J1": ("HX PZ1.27-2x10P WZ", "C22438116", "https://www.lcsc.com/product-detail/C22438116.html"),
       "U3": ("XC6206P282MR", "C347374", "https://www.lcsc.com/product-detail/C347374.html"),
       "U4": ("XC6206P122MR-G", "C424699", "https://www.lcsc.com/product-detail/C424699.html"),
       "10uF": ("CL10A106KP8NNNC", "C19702", ""), "4.7uF": ("CL05A475MP5NRNC", "C23733", ""), "1uF": ("CL05A105KA5NQNC", "C52923", ""),
       "100nF": ("CL05B104KO5NNNC", "C1525", ""), "47k": ("0402WGF4702TCE", "C25792", ""),
       "10k": ("0402WGF1002TCE", "C25744", ""), "0R": ("0402WGF0000TCE", "C17168", "")}
partmap = {p[0]: p for p in PARTS}
def jlc(ref):
    return JLC.get(ref) or JLC.get(partmap[ref][2]) if ref in partmap else None

# ------------------------------------------------------------------ schematic
def sexp_block(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: return t[i:j + 1]
def lib_symbol(lib_id):
    if lib_id in CUSTOM:
        return CUSTOM[lib_id], CUSTOM[lib_id]
    lib, name = lib_id.split(":")
    t = open(KS + lib + ".kicad_sym", encoding="utf-8").read()
    blk = sexp_block(t, t.index(f'(symbol "{name}"'))
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1), blk
def pin_table(blk):
    return {m.group(9): (float(m.group(3)), float(m.group(4)), float(m.group(5)), m.group(8)) for m in re.finditer(
        r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]*)"', blk, re.S)}
def prop(name, val, x, y, hide=False):
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {x:.2f} {y:.2f} 0)\n' + ("\t\t\t(hide yes)\n" if hide else "") +
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
libs, pins, body, sym_uuid = {}, {}, [], {}
need = sorted({p[1] for p in PARTS} | {"power:PWR_FLAG"})
for lid in need:
    libs[lid], raw = lib_symbol(lid); pins[lid] = pin_table(raw)
def place(lib_id, ref, value, fp, x, y, hide_ref=False, dnp=False):
    su = U(); sym_uuid[ref] = su
    s = (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom {"no" if ref[0] in "#H" else "yes"})\n'
         f'\t\t(on_board {"no" if ref.startswith("#") else "yes"})\n\t\t(dnp {"yes" if dnp else "no"})\n\t\t(uuid "{su}")\n')
    pj = jlc(ref) if not ref.startswith("#") else None
    s += prop("Reference", ref, x + 2, y - 6, hide_ref) + prop("Value", value, x + 2, y + 6) + prop("Footprint", fp, x, y, True) + prop("Datasheet", pj[2] if pj else "", x, y, True)
    if pj:
        s += prop("MPN", pj[0], x, y, True) + prop("LCSC", pj[1], x, y, True)
    for num in pins[lib_id]:
        s += f'\t\t(pin "{num}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
    s += f'\t\t(instances\n\t\t\t(project "{PRJ}"\n\t\t\t\t(path "/{ROOT}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
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
for ref, lid, val, fp, netmap, (sx, sy), side, dnp in PARTS:
    sx, sy = G(sx), G(sy)
    place(lid, ref, val, fp, sx, sy, dnp=dnp)
    for num, (px, py, prot, pname) in pins[lid].items():
        X, Y = sx + px, sy - py
        if (ref, num) in NC:
            body.append(f'\t(no_connect\n\t\t(at {X:.2f} {Y:.2f})\n\t\t(uuid "{U()}")\n\t)\n')
        elif num in netmap:
            pin_label(netmap[num], X, Y, prot)
for i, net in enumerate(("3V3", "GND")):                       # the supply comes in on the header
    x, y = G(40 + 20 * i), G(190)
    place("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", "", x, y, True)
    label(net, x, y)
sch = (f'(kicad_sch\n\t(version 20250610)\n\t(generator "bugbot")\n\t(generator_version "10.0")\n\t(uuid "{ROOT}")\n\t(paper "A4")\n'
       f'\t(title_block\n\t\t(title "BugBot front sensor board")\n\t\t(rev "2")\n'
       f'\t\t(comment 1 "VL53L5CX 8x8 ToF + 24-pin DVP camera (OV2640 / OV5640) on a 0.5 mm FPC socket; 2x10 1.27 RA header to J6")\n'
       f'\t\t(comment 2 "DOVDD: R9 0R from 3V3 (OV2640); for an OV5640 fit R10 instead (2V8) and U4 = XC6206P152MR (1V5)")\n\t)\n'
       '\t(lib_symbols\n' + "".join("\t\t" + libs[l].replace("\n", "\n\t\t") + "\n" for l in need) + '\t)\n' + "".join(body) +
       f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
open(f"{OUT}/{PRJ}.kicad_sch", "w", encoding="utf-8").write(sch)

# ------------------------------------------------------------------ board
mm = pcbnew.FromMM
def P(X, Y): return pcbnew.VECTOR2I(mm(100 + X), mm(100 - Y))
def xy(o):
    v = o.GetPosition(); return (pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y))
board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(1.6))
ds.SetGridOrigin(P(0, 0)); ds.SetAuxOrigin(P(0, 0))
ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15); ds.m_ViasMinSize = mm(0.5); ds.m_MinThroughDrill = mm(0.25)
ds.m_CopperEdgeClearance = mm(0.3)
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetTrackWidth(mm(0.2)); nc.SetClearance(mm(0.15)); nc.SetViaDiameter(mm(0.5)); nc.SetViaDrill(mm(0.3))
nets = {}
def net(n):
    n = n if n.startswith("/") or n.startswith("unconnected") else "/" + n
    if n not in nets:
        ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni
    return nets[n]
for e in MCAD["outline"]:
    (a, b) = e["line"]
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetWidth(mm(0.05)); board.Add(s)
fps = {}
def load(fp):
    lib, name = fp.split(":")
    return pcbnew.FootprintLoad((LIBDIR if lib == "BugBot" else KF + lib) + ".pretty", name)
def orient(f, X, Y, rot, side):
    f.SetPosition(P(X, Y)); f.SetOrientationDegrees(0)
    if side == "B" and not f.IsFlipped():
        f.Flip(P(X, Y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(rot)
def pick_rot(fp, X, Y, side, test):
    """first of 0 / 90 / 180 / 270 for which test(pad-position dict) holds (a probe footprint, never added to the board)."""
    pr = load(fp); scratch = pcbnew.BOARD(); scratch.Add(pr)          # Flip() needs the footprint on a board
    for rot in (0, 90, 180, 270):
        orient(pr, X, Y, rot, side)
        if test({p.GetNumber(): xy(p) for p in pr.Pads()}, pr):
            return rot
    raise RuntimeError(f"no orientation for {fp}")
def add_fp(ref, X, Y, rot):
    _, lid, val, fp, netmap, _, side, dnp = partmap[ref]
    f = load(fp)
    f.SetReference(ref); f.SetValue(val); f.SetFPIDAsString(fp)
    board.Add(f)
    orient(f, X, Y, rot, side)
    f.SetPath(pcbnew.KIID_PATH(f"/{sym_uuid[ref]}"))
    if dnp:
        try: f.SetDNP(True)
        except AttributeError: f.SetAttributes(f.GetAttributes() | pcbnew.FP_DNP)
    if jlc(ref):
        for k, v in zip(("MPN", "LCSC", "Datasheet"), jlc(ref)):
            f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.B_Fab if side == "B" else pcbnew.F_Fab)
    fps[ref] = f
    return f

# J1: pads in two rows along Y, its pins pointing down (-Z) past the board's bottom edge; pad 2's row nearer the edge
J1FP = partmap["J1"][3]
def j1_ok(pp, pr):
    p1, p2, p3 = pp["1"], pp["2"], pp["3"]
    return abs(p1[0] - p2[0]) < 0.01 and p2[1] < p1[1] and abs(p3[1] - p1[1]) < 0.01 and p3[0] > p1[0]
y1 = SOCK_Y - 9 * 1.27 / 2
add_fp("J1", y1, HDR_Z, pick_rot(J1FP, y1, HDR_Z, "B", j1_ok))
# J2: FPC socket on the back, opening up (+Z) toward the flex slot, pad row at Z 44.1
J2FP = partmap["J2"][3]
def j2_ok(pp, pr):
    mp = [v for k, v in pp.items() if k == "MP"]
    return mp[0][1] > pp["1"][1] and pp["1"][0] < pp["24"][0]
add_fp("J2", 0.0, 44.1, pick_rot(J2FP, 0.0, 44.1, "B", j2_ok))
# front: ToF and the camera module (mechanical footprint, not in the schematic)
add_fp("U2", 0.0, TOF_Z, 0)
cam = load("BugBot:Camera_DVP24_Module_8.5mm"); cam.SetReference("MK1"); cam.SetValue("OV2640 / OV5640 24P module")
cam.SetFPIDAsString("BugBot:Camera_DVP24_Module_8.5mm"); board.Add(cam); orient(cam, 0.0, CAM_Z, 0, "F")
# back, right strip (Y -12.2 .. -8.6): 3V3 bulk, the two LDOs with their 1 uF caps
add_fp("C1", -10.6, 41.7, 0)
add_fp("U3", -10.6, 44.8, 90); add_fp("C2", -11.4, 47.9, 90); add_fp("C3", -9.5, 47.9, 90)
add_fp("U4", -10.6, 51.0, 90); add_fp("C4", -11.4, 54.0, 90); add_fp("C5", -9.5, 54.0, 90)
# back, a column on the ear above the socket (the board between the header and the socket stays clear for the bus):
# DOVDD select, its cap, reset RC, power-down, AVDD / DVDD caps
# above the slot (the flex slot's keep-out boxes in anything beside it lower down): 4 in the ear, 4 left of the ToF
for k, ref in enumerate(("C8", "R9", "R10", "R7")):
    add_fp(ref, 8.2, 54.3 + 1.05 * k, 180 if ref == "C8" else 0)      # C8 turned: its DOVDD pad in line with R9 / R10 / R7
for k, ref in enumerate(("C9", "R8", "C6", "C7")):
    add_fp(ref, -5.6, 54.3 + 1.05 * k, 180)                            # GND pads in a line on the -Y side
# back, above the slot: the ToF's caps right behind it, pull-ups along the top
add_fp("C10", -1.3, 55.9, 90); add_fp("C11", 1.3, 55.9, 90)
for ref, Y in (("R6", 1.5), ("R4", 3.5), ("R5", 5.4)):     # GPIO / RST / INT pull-ups over their vias
    add_fp(ref, Y, 59.3, 180 if ref in ("R4", "R6") else 0)            # R4 / R6 turned: signal pads toward their tracks
for k, h in enumerate(MCAD["holes"], 1):                     # FreeCAD's holes, as its ECAD push writes them (board-only)
    hf = load("MountingHole:MountingHole_2.2mm_M2"); hf.SetReference(f"H{k}"); hf.SetValue(f"MCAD hole d={h['d']:.2f}")
    hf.SetFPIDAsString("MountingHole:MountingHole_2.2mm_M2"); hf.SetBoardOnly(True)
    hf.Reference().SetVisible(False); hf.Value().SetVisible(False); board.Add(hf); hf.SetPosition(P(*h["at"]))
for ref, lid, val, fp, netmap, _, side, dnp in PARTS:
    for p in fps[ref].Pads():
        num = p.GetNumber()
        if (ref, num) in NC:
            nm = pins[lid][num][3]
            p.SetNet(net(f"unconnected-({ref}-{nm}-Pad{num})"))
        elif num in netmap:
            p.SetNet(net(netmap[num]))
OUTLINE = [tuple(e["line"][0]) for e in MCAD["outline"][:8]]   # the board's outer corners (FreeCAD's sketch)
# GND pours on both layers (filled by kicad-cli), stitching vias
def pour(layer):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net("GND"))
    ol = z.Outline(); ol.NewOutline()
    for X, Y in OUTLINE:
        ol.Append(P(X, Y))
    z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetAssignedPriority(0); board.Add(z)
# ToF fan-out (locked, the router builds on it): the GND pads tied to the thermal pad, which has 3 vias to the back;
# each signal / supply pad a short stub out of the package to its own via
def ptrack(pts, n, w=0.2, layer=pcbnew.F_Cu):
    for a_, b_ in zip(pts, pts[1:]):
        tk = pcbnew.PCB_TRACK(board); tk.SetStart(P(*a_)); tk.SetEnd(P(*b_)); tk.SetWidth(mm(w)); tk.SetLayer(layer)
        tk.SetNet(net(n)); tk.SetLocked(True); board.Add(tk)
def pvia(Y, Z, n, size=0.5, drill=0.3):
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(Y, Z)); v.SetDrill(mm(drill)); v.SetWidth(mm(size)); v.SetNet(net(n)); v.SetLocked(True); board.Add(v)
dv = [xy(fps["C8"].FindPadByNumber("1"))] + [xy(fps[r].FindPadByNumber("2")) for r in ("R9", "R10", "R7")]
ptrack(dv, "DOVDD", 0.25, pcbnew.B_Cu)                       # DOVDD spine through the 4 pads in a line
c8g = xy(fps["C8"].FindPadByNumber("2")); ptrack([c8g, (c8g[0], c8g[1] - 0.65)], "GND", 0.25, pcbnew.B_Cu); pvia(c8g[0], c8g[1] - 0.65, "GND")
gp = [xy(fps[r].FindPadByNumber("2")) for r in ("C9", "R8", "C6", "C7")]          # GND spine through the left block, via on top
ptrack(gp + [(gp[-1][0], gp[-1][1] + 0.65)], "GND", 0.25, pcbnew.B_Cu); pvia(gp[-1][0], gp[-1][1] + 0.65, "GND")
j1p = {p.GetNumber(): xy(p) for p in fps["J1"].Pads()}       # header GND links: 6 - 8 - 10 along the edge row, 8 up to 7
ptrack([j1p["6"], j1p["8"], j1p["10"]], "GND", 0.3, pcbnew.B_Cu); ptrack([j1p["8"], j1p["7"]], "GND", 0.3, pcbnew.B_Cu)
ptrack([j1p["6"], j1p["8"], j1p["10"]], "GND", 0.3, pcbnew.F_Cu); ptrack([j1p["8"], j1p["7"]], "GND", 0.3, pcbnew.F_Cu)
tofp = {p.GetNumber(): xy(p) for p in fps["U2"].Pads()}
b4 = tofp["B4"]
for dy in (-0.75, 0.0, 0.75):                               # thermal pad -> back GND
    pvia(b4[0] + dy, b4[1], "GND")
ptrack([tofp["A5"], tofp["A4"]], "3V3", 0.25)                 # LPn to IOVDD, pad to pad
ty, tz = tofp["B4"]
for pn in ("A1", "A2", "A3", "A4", "A6", "A7", "C1", "C2", "C3", "C4", "C6", "C7"):
    py_, pz = tofp[pn]; n = TOF[pn]
    if pn in ("A1", "A3"):                                   # RST / INT: out sideways on the (empty) front to vias beside the chip
        zl = pz - (0.45 if pn == "A1" else 1.1)
        ye = ty + (4.3 if pn == "A1" else 5.3)
        ptrack([(py_, pz), (py_, zl), (ye, zl)], n); pvia(ye, zl, n)
        continue
    s = -1 if pn[0] == "A" else 1                            # a via straight out of each pad (A row below, C row above)
    ptrack([(py_, pz), (py_, pz + 0.6 * s)], n, 0.25 if n == "GND" else 0.2); pvia(py_, pz + 0.6 * s, n)
LANE = tofp["C2"][1] + 1.35                                 # the lane between the C-row vias and the pull-up row (back)
def up_to(ref, vy, vz, n):
    q = xy(fps[ref].FindPadByNumber("1")); ptrack([(vy, vz), (vy, LANE), (q[0], LANE), q], n, 0.2, pcbnew.B_Cu)
up_to("R6", tofp["C2"][0], tofp["C2"][1] + 0.6, "TOF_GPIO")
up_to("R4", ty + 4.3, tofp["A1"][1] - 0.45, "TOF_RST")
up_to("R5", ty + 5.3, tofp["A3"][1] - 1.1, "TOF_INT")
g4 = xy(fps["R4"].FindPadByNumber("2")); c1v = (tofp["C1"][0], tofp["C1"][1] + 0.6)
ptrack([g4, (g4[0], g4[1] - 0.75), c1v], "GND", 0.2, pcbnew.B_Cu)           # R4's GND to the ToF's C1 GND via
for pn, s in (("B1", 1), ("B7", -1)):                       # AVDD at both ends
    py_, pz = tofp[pn]; ptrack([(py_, pz), (py_ + 0.85 * s, pz)], "3V3", 0.3); pvia(py_ + 0.85 * s, pz, "3V3")
def keepout(outer, hole=None):
    """no tracks / vias / pours (the router sees it; the slot is an inner board edge it does not know)."""
    k = pcbnew.ZONE(board); k.SetIsRuleArea(True); k.SetLayerSet(pcbnew.LSET.AllCuMask())
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    ol = k.Outline(); ol.NewOutline()
    for q in outer: ol.Append(P(*q))
    if hole:
        ol.NewHole()
        for q in hole: ol.Append(P(*q))
    board.Add(k)
d = 0.35                                                    # edge band: copper keeps 0.3 from every edge
for e in MCAD["outline"][:8]:                              # a thin strip on every outer edge (a keep-out with a hole reads as solid)
    (ya, za), (yb, zb) = e["line"]
    keepout([(min(ya, yb) - d, min(za, zb) - d), (max(ya, yb) + d, min(za, zb) - d), (max(ya, yb) + d, max(za, zb) + d), (min(ya, yb) - d, max(za, zb) + d)])
sl = [e["line"] for e in MCAD["outline"]][8:]               # the 4 slot edges (after the 8 outline edges)
sy = [p[0] for l in sl for p in l]; sz = [p[1] for l in sl for p in l]
keepout([(min(sy) - d, min(sz) - d), (max(sy) + d, min(sz) - d), (max(sy) + d, max(sz) + d), (min(sy) - d, max(sz) + d)])
for f in list(fps.values()) + [cam]:
    f.Value().SetVisible(False)
    f.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6))); f.Reference().SetTextThickness(mm(0.1))
    f.Reference().SetVisible(f.GetReference() in ("J1", "J2", "U2", "U3", "U4"))
for txt, X, Y, layer, mir in (("BugBot front v2", 4.3, 38.6, pcbnew.F_SilkS, False),):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(P(X, Y)); t.SetLayer(layer); t.SetMirrored(mir)
    t.SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5))); t.SetTextThickness(mm(0.08)); board.Add(t)
board.BuildConnectivity()
pcb = f"{OUT}/{PRJ}.kicad_pcb"
pcbnew.SaveBoard(pcb, board)

# ------------------------------------------------------------------ autoroute (Freerouting), then back into KiCad
dsn, ses = f"{OUT}/_route/{PRJ}.dsn", f"{OUT}/_route/{PRJ}.ses"
os.makedirs(f"{OUT}/_route", exist_ok=True)
assert pcbnew.ExportSpecctraDSN(board, dsn), "DSN export failed"
if os.path.exists(ses): os.remove(ses)
r = subprocess.run([JAVA, "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", "100", "--gui.enabled=false"],
                   capture_output=True, text=True, timeout=900)
open(f"{OUT}/_route/freerouting.log", "w").write(r.stdout[-20000:] + r.stderr[-5000:])
assert os.path.exists(ses), "Freerouting wrote no session: see _route/freerouting.log"
assert pcbnew.ImportSpecctraSES(board, ses), "SES import failed"
pcbnew.SaveBoard(pcb, board)

pour(pcbnew.F_Cu); pour(pcbnew.B_Cu)                        # GND pours on top of the routing (kicad-cli fills them)
board.BuildConnectivity()
pcbnew.SaveBoard(pcb, board)
# project rules (SaveBoard rewrites the .kicad_pro with defaults): JLCPCB 2-layer capabilities
pro = f"{OUT}/{PRJ}.kicad_pro"; dj = json.load(open(pro))
ru = dj["board"]["design_settings"]["rules"]
ru.update(min_copper_edge_clearance=0.3, min_track_width=0.127, min_clearance=0.127, min_text_height=0.5, min_resolved_spokes=1)
json.dump(dj, open(pro, "w"), indent=2)

# ------------------------------------------------------------------ JLCPCB assembly files (origin = robot axis, KiCad aux origin)
ROT_OFS = {"SOT-23-3": 180}
os.makedirs(f"{OUT}/jlc", exist_ok=True)
key = lambda r: (re.match(r"\D+", r).group(), int(re.search(r"\d+", r).group()))
groups = {}
for ref, lid, val, fp, netmap, _, side, dnp in PARTS:
    if jlc(ref) and not dnp:
        groups.setdefault((val, fp.split(":")[1], jlc(ref)[1]), []).append(ref)
with open(f"{OUT}/jlc/{PRJ}_BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Comment,Designator,Footprint,LCSC\n")
    for (val, fpn, lc), refs in sorted(groups.items(), key=lambda g: key(min(g[1], key=key))):
        fh.write(f'"{val}","{",".join(sorted(refs, key=key))}","{fpn}","{lc}"\n')
with open(f"{OUT}/jlc/{PRJ}_CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
    for ref in sorted((r for r in fps if jlc(r) and not partmap[r][7]), key=key):
        f = fps[ref]; X, Y = xy(f); fpn = partmap[ref][3].split(":")[1]
        rot = (f.GetOrientationDegrees() + ROT_OFS.get(fpn, 0)) % 360
        fh.write(f"{ref},{X:.4f}mm,{Y:.4f}mm,{'Bottom' if partmap[ref][6] == 'B' else 'Top'},{rot:g}\n")
from hand_solder import split                    # through-hole connectors we solder: out of the JLC files
split(PRJ, f"{OUT}/jlc")
# pin tips of J1 in the robot frame (for J6 on the main board): pin -> (Y, X behind the board)
tips = {}
for p in fps["J1"].Pads():
    Yp, Zp = xy(p)
    tips[p.GetNumber()] = (round(Yp, 3), "near" if Zp < HDR_Z - 0.5 else "far")
json.dump(tips, open(f"{OUT}/_route/j1_pins.json", "w"), indent=1)
tr = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]; vi = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
print("ok", len(fps), "footprints", len(nets), "nets", len(tr), "tracks", len(vi), "vias")
