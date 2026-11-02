# Footprints the main board was missing (placeholders with no pads), from the makers' drawings:
#   Waveshare_ESP32-P4-Module     88 pads from Waveshare's land pattern DXF (datasheets/waveshare_p4_land): 25 x 25 module,
#                                 22 pads a side at 1.0 mm, 1.5 x 0.7 mm centred on the module edge; pin 1 = the dot at the
#                                 top of the left side, numbered anticlockwise (left side down, bottom, right side up, top)
#   SW_CK_L101011ML04Q_RA         C&K L series, ML mounting, 04 terminations (catalog p. I-22/23): 3 pins at 4.75, 1.65 holes.
#                                 L101 = SPST between pins 1 and 2: both outer pads are numbered 1 (the third is a dummy on an
#                                 L101), so the switch works whichever end the model's pin 1 is. Pads (and 2 holes for the
#                                 model's pegs) sit where our 3D model has them, so the FreeCAD placement stays right.
#   SW_ZX-QC4545-4.3TP            ZX-QC4545 drawing: lands 7.2 / 4.5 x 4.1 / 1.9; 1-2 and 3-4 joined inside, so the top
#                                 pair is pad 1 and the bottom pair pad 2 (as Switch:SW_Push)
#   Texas_DLA0010A_VSON-HR-10     TPS63802 datasheet land pattern (p. 36), replacing the EasyEDA copy (0.07 mm off)
#   C:/Python312/python.exe design/lib/make_main_footprints.py        (needs ezdxf for the module's DXF)
import math, os
import ezdxf

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
LIB = BB + "/design/lib/BugBot.pretty"
DXF = BB + "/design/lib/datasheets/waveshare_p4_land/x/ESP32-P4_Module-PCB-Land-Pattern.dxf"
MODEL = "${KIPRJMOD}/../lib/3dmodels/"
FONT = '(effects (font (size 0.8 0.8) (thickness 0.12)))'


def smd(num, x, y, w, h):
    return f'  (pad "{num}" smd roundrect (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))\n'
def tht(num, x, y, d, drill):
    return f'  (pad "{num}" thru_hole circle (at {x:.3f} {y:.3f}) (size {d:.3f} {d:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask"))\n'
def npth(x, y, drill):
    return f'  (pad "" np_thru_hole circle (at {x:.3f} {y:.3f}) (size {drill:.3f} {drill:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask"))\n'
def rect(layer, x0, y0, x1, y1, w):
    return f'  (fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))\n'
def circle(layer, x, y, r, w=0.12):
    return f'  (fp_circle (center {x:.3f} {y:.3f}) (end {x + r:.3f} {y:.3f}) (stroke (width {w}) (type solid)) (fill solid) (layer "{layer}"))\n'
# Waveshare's own STEP (wiki ESP32-P4-Module-3D.zip, 2025-07-30): its corner at the origin, its PCB at z -0.8..0, drawn
# from above like the land pattern DXF -> shifted by half the module and lifted onto our board
MODEL_OFFSET = {"Waveshare_ESP32-P4-Module.step": (-12.5, -12.5, 0.8)}


def footprint(name, descr, body, ref_y, attr="smd", model=None):
    s = (f'(footprint "{name}"\n  (version 20240108)\n  (generator "bugbot")\n  (layer "F.Cu")\n  (descr "{descr}")\n  (attr {attr})\n'
         f'  (property "Reference" "REF**" (at 0 {-ref_y:.2f} 0) (layer "F.SilkS") {FONT})\n'
         f'  (property "Value" "{name}" (at 0 {ref_y:.2f} 0) (layer "F.Fab") {FONT})\n'
         f'  (fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") {FONT})\n' + body)
    if model:
        ox, oy, oz = MODEL_OFFSET.get(model, (0, 0, 0))
        s += f'  (model "{MODEL}{model}" (offset (xyz {ox} {oy} {oz})) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
    open(f"{LIB}/{name}.kicad_mod", "w", encoding="utf-8").write(s + ")\n")
    print("wrote", name)


# ---- ESP32-P4 module
pads = []
for e in ezdxf.readfile(DXF).modelspace().query('SOLID[layer=="TopLayer"]'):
    xs = [e.dxf.get(f"vtx{i}")[0] for i in range(4)]; ys = [e.dxf.get(f"vtx{i}")[1] for i in range(4)]
    pads.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)))
assert len(pads) == 88
cx = (min(p[0] for p in pads) + max(p[0] for p in pads)) / 2; cy = (min(p[1] for p in pads) + max(p[1] for p in pads)) / 2
P = [(round(x - cx, 3), round(cy - y, 3), w, h) for x, y, w, h in pads]           # KiCad: y down
left = sorted([p for p in P if p[0] < -12], key=lambda p: p[1])                    # top -> bottom
bottom = sorted([p for p in P if p[1] > 12], key=lambda p: p[0])                   # left -> right
right = sorted([p for p in P if p[0] > 12], key=lambda p: -p[1])                   # bottom -> top
top = sorted([p for p in P if p[1] < -12], key=lambda p: -p[0])                    # right -> left
order = left + bottom + right + top
assert [len(s) for s in (left, bottom, right, top)] == [22, 22, 22, 22] and len(set(order)) == 88
assert left[0][:2] == (-12.5, -10.5)                                               # the pin-1 dot (DXF 86.64, 92.86) is beside it
body = "".join(smd(i + 1, x, y, w, h) for i, (x, y, w, h) in enumerate(order))
body += rect("F.Fab", -12.5, -12.5, 12.5, 12.5, 0.1) + rect("F.CrtYd", -13.5, -13.5, 13.5, 13.5, 0.05)
body += circle("F.SilkS", -14.0, -10.5, 0.2) + circle("F.Fab", -11.5, -11.5, 0.3, 0.1)
footprint("Waveshare_ESP32-P4-Module", "Waveshare ESP32-P4-Module V1.1 (25 x 25, 88 castellated pads at 1.0 mm), from Waveshare's PCB land pattern DXF",
          body, 14.3, model="Waveshare_ESP32-P4-Module.step")

# ---- C&K L101011ML04Q: pins where the 3D model has them (it carries the robot's 33 deg turn); KiCad y = -model y
PINS = [(-3.10, -4.26), (0.84, -1.70), (4.79, 0.86)]                                # model x, y (STEP section at z -1.5)
PEGS = [(8.22, 2.38), (-5.87, -6.77)]
pitch = math.dist(PINS[0], PINS[2]) / 2
assert abs(pitch - 4.75) < 0.1, pitch
body = "".join(tht(n, x, -y, 2.6, 1.65) for n, (x, y) in zip(("1", "2", "1"), PINS))
body += "".join(npth(x, -y, 1.9) for x, y in PEGS)
body += rect("F.Fab", -10.081, -8.713, 10.081, 8.712, 0.1) + rect("F.CrtYd", -10.331, -8.963, 10.331, 8.962, 0.05)
footprint("SW_CK_L101011ML04Q_RA", "C&K L101011ML04Q slide switch (SPST, right angle, PC pins at 4.75 mm, 1.65 holes); both outer pins = pad 1",
          body, 9.71, attr="through_hole", model="SW_CK_L101011ML04Q_RA.step")

# ---- ZX-QC4545-4.3TP
PX, PY, PW, PH = (7.2 + 4.5) / 4, (4.1 + 1.9) / 4, (7.2 - 4.5) / 2, (4.1 - 1.9) / 2
body = "".join(smd(n, sx * PX, sy * PY, PW, PH) for n, sx, sy in (("1", -1, -1), ("1", 1, -1), ("2", -1, 1), ("2", 1, 1)))
body += rect("F.Fab", -2.25, -2.25, 2.25, 2.25, 0.1) + rect("F.CrtYd", -3.85, -2.5, 3.85, 2.5, 0.05)
body += f'  (fp_circle (center 0 0) (end 1.225 0) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))\n'
footprint("SW_ZX-QC4545-4.3TP", "ZX-QC4545-4.3TP 4.5 x 4.5 tact switch, lands from its drawing; pads 1 (top pair) / 2 (bottom pair)",
          body, 3.25, model="SW_ZX-QC4545-4.3TP.step")

# ---- TPS63802 DLA (VSON-HR 10, 2 x 3): pins 1-5 left 0.6 x 0.25 at x -0.9; 6, 7, 9, 10 right 0.9 x 0.25 at x 0.75;
# 8 (GND) 1.3 long, x -0.1 .. 1.2; pitch 0.5, pin 1 top left, 10 top right
body = "".join(smd(n, -0.9, -1.0 + 0.5 * (n - 1), 0.6, 0.25) for n in range(1, 6))
body += "".join(smd(n, 0.75, 1.0 - 0.5 * (n - 6), 0.9, 0.25) for n in (6, 7, 9, 10)) + smd(8, 0.55, 0.0, 1.3, 0.25)
body += rect("F.Fab", -1.0, -1.5, 1.0, 1.5, 0.1) + rect("F.CrtYd", -1.45, -1.75, 1.45, 1.75, 0.05) + circle("F.SilkS", -1.45, -1.3, 0.1)
footprint("Texas_DLA0010A_VSON-HR-10_2x3mm_P0.5mm", "TI DLA0010A VSON-HR 10 (TPS63802), land pattern from the TPS63802 datasheet", body, 2.3)

# ---- XKB SS-12D11G5R power switch (replaces the C&K: $0.50 vs $7.12, 3 A; approved 2D mech/freecad/sketches/power_switch_v1.png)
# From its drawing (datasheets/SS-12D11G5R_C388633.pdf): body 13.5 x 6.3, 6.6 off the board; knob 2.45 x 4.0, 5.0 proud of the
# front face, 2.4 travel, centre 3.3 off the board; 2 case tabs (d 1.5 holes, 13.29 apart) 1.58 inside the front face; 3 bent
# pins (d 1.6 holes, 4.8 pitch) 9.2 behind the tabs. SPDT: pin 2 common, the contact bridge moves with the knob (knob at the
# pin-1 end = 1-2 made = ON). Origin = body centre, knob toward -y. LCSC's STEP for it is 2.9 mm off its own pads, so the 3D
# model is built here from the same numbers.
SSW = dict(L=13.5, D=6.3, H=6.6, kw=2.45, kh=4.0, kl=5.0, kz=3.3, tab_x=13.29 / 2, tab_y=-6.3 / 2 + 1.58)
SSW["pin_y"] = SSW["tab_y"] + 9.2
body = "".join(tht(n, x, SSW["pin_y"], 2.6, 1.6) for n, x in (("1", -4.8), ("2", 0.0), ("3", 4.8)))
body += "".join(f'  (pad "" thru_hole circle (at {s * SSW["tab_x"]:.3f} {SSW["tab_y"]:.3f}) (size 2.4 2.4) (drill 1.5) (layers "*.Cu" "*.Mask"))\n'
                for s in (-1, 1))
body += rect("F.Fab", -6.75, -3.15, 6.75, 3.15, 0.1) + rect("F.Fab", -1.225, -8.15, 1.225, -3.15, 0.1)
body += rect("F.CrtYd", -8.0, -8.4, 8.0, SSW["pin_y"] + 1.55, 0.05)
body += (f'  (fp_text user "ON" (at -4.8 -4.6 0) (layer "F.SilkS") {FONT})\n'
         f'  (fp_line (start -1.6 -4.6) (end -3.4 -4.6) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))\n')
footprint("SW_XKB_SS-12D11G5R_RA", "XKB SS-12D11G5R right-angle slide switch, SPDT 3 A; knob toward -y; pin 2 common, knob at pin 1 = 1-2 on",
          body, 9.6, attr="through_hole", model="SW_XKB_SS-12D11G5R_RA.step")

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.gp import gp_Pnt
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
def box(x0, y0, z0, x1, y1, z1):                                  # KiCad 3D frame: y up (= -footprint y), z up off the board
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()
parts = [box(-6.75, -3.15, 0, 6.75, 3.15, SSW["H"]),
         box(-SSW["kw"] / 2, 3.15, SSW["kz"] - SSW["kh"] / 2, SSW["kw"] / 2, 3.15 + SSW["kl"], SSW["kz"] + SSW["kh"] / 2)]
py = -SSW["pin_y"]
for x in (-4.8, 0.0, 4.8):                                         # legs: out of the back face 1 mm up, then down through the board
    parts += [box(x - 0.4, py - 0.25, 0.75, x + 0.4, -3.15, 1.25), box(x - 0.4, py - 0.25, -2.8, x + 0.4, py + 0.25, 1.25)]
for s in (-1, 1):
    parts.append(box(s * SSW["tab_x"] - 0.4, -SSW["tab_y"] - 0.1, -2.8, s * SSW["tab_x"] + 0.4, -SSW["tab_y"] + 0.1, 0.5))
shape = parts[0]
for p in parts[1:]:
    shape = BRepAlgoAPI_Fuse(shape, p).Shape()
w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs)
w.Write(BB + "/design/lib/3dmodels/SW_XKB_SS-12D11G5R_RA.step"); print("wrote SW_XKB_SS-12D11G5R_RA.step")

# ---- power switch v2 (approved: mech/freecad/sketches/switch_usb_move_v1.png): MSK12C02G25 SMD slide switch on the
# underside at 237 deg, its handle in the wall slot; it only pulls the SI2333 high-side FET's gate (the SS-12D11 above fits
# nowhere round the wall). From its drawing (datasheets/MSK12C02G25_C22435663.pdf): body 6.7 x 2.8 x 1.45, handle 1.3 wide,
# 2.5 proud, 1.0 high, 1.6 travel; pins 1 / 2 / 3 at x 2.25 / -0.75 / -2.25 (2 = common), 1 mm behind the body; 4 shell
# tabs (8.3 / 2.3 apart) and 2 locating holes d0.8. Handle toward -y; the origin is LCSC's.
body = "".join(smd(n, x, 1.58, 0.7, 1.0) for n, x in (("1", 2.25), ("2", -0.75), ("3", -2.25)))
body += "".join(f'  (pad "" smd roundrect (at {sx * 3.65:.3f} {y:.3f}) (size 1.0 0.7) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))\n'
                for sx in (-1, 1) for y in (-1.58, 0.72))
body += npth(-1.5, -0.42, 0.8) + npth(1.5, -0.42, 0.8)
body += rect("F.Fab", -3.35, -1.88, 3.35, 0.92, 0.1) + rect("F.Fab", -0.65, -4.38, 0.65, -1.88, 0.1)
CY = [(-4.4, 2.35), (4.4, 2.35), (4.4, -2.15), (1.75, -2.15), (1.75, -4.6), (-1.75, -4.6), (-1.75, -2.15), (-4.4, -2.15)]
body += ('  (fp_poly (pts ' + " ".join(f"(xy {x} {y})" for x, y in CY) +
         ') (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))\n')   # narrow in front: only the handle enters the slot
body += (f'  (fp_text user "ON" (at 3.9 -3.2 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.12))))\n'
         f'  (fp_line (start 1.0 -3.2) (end 2.8 -3.2) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n')
footprint("SW_MSK12C02G25_SMD", "MSK12C02G25 SMD slide switch (SPDT, handle 2.5 toward -y); pin 2 common; knob at the pin-1 end = ON (check with a meter)",
          body, 5.2, model="SW_MSK12C02G25_SMD.step")
parts = [box(-3.35, -0.92, 0, 3.35, 1.88, 1.45), box(-0.65, 1.88, 0.35, 0.65, 4.38, 1.35)]
for x in (2.25, -0.75, -2.25):
    parts.append(box(x - 0.3, -2.08, 0, x + 0.3, -0.92, 0.15))
for sx in (-1, 1):
    for y in (1.58, -0.72):
        parts.append(box(sx * 3.35, y - 0.3, 0, sx * 3.9, y + 0.3, 0.15))
shape = parts[0]
for p in parts[1:]:
    shape = BRepAlgoAPI_Fuse(shape, p).Shape()
w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs)
w.Write(BB + "/design/lib/3dmodels/SW_MSK12C02G25_SMD.step"); print("wrote SW_MSK12C02G25_SMD.step")
