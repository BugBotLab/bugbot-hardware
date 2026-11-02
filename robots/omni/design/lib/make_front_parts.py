# Footprints for the front sensor board (BugBot.pretty), written as text so they stay reproducible.
#   python design/lib/make_front_parts.py          (3D models: make_front_models.py in FreeCAD)
# ST_VL53L5CX_LGA16: from ST DS13754 rev 8, figure 22 (bottom view, mirrored here to the top view). 16 pads 0.5 x 0.5,
#   pitch 0.75; A row (A1 .. A7) at y +1.05, C row at y -1.05 (KiCad y down), A1 / C1 at x +2.25; B1 x +2.65, B7 x -2.65;
#   B4 thermal pad 2.316 x 1.2 in the middle. Cap 6.4 x 3.03 x 1.5.
# Camera_DVP24_Module: the 24-pin camera module (OV2640 / OV5640 style, 8.5 x 8.5, 21 mm flex), taped to the front face,
#   flex up through the board slot to J2 on the back. No pads: outline + 3D model only (not assembled by JLC).
import os, uuid
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib/BugBot.pretty"
U = lambda: str(uuid.uuid4())

def fp(name, descr, body, attr="smd"):
    return (f'(footprint "{name}"\n\t(version 20241229)\n\t(generator "bugbot")\n\t(layer "F.Cu")\n\t(descr "{descr}")\n'
            f'\t(property "Reference" "REF**" (at 0 -2.6 0) (layer "F.SilkS") (uuid "{U()}") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
            f'\t(property "Value" "{name}" (at 0 2.6 0) (layer "F.Fab") (uuid "{U()}") (effects (font (size 0.8 0.8) (thickness 0.12))))\n'
            f'\t(attr {attr})\n' + body + ')\n')
def line(x0, y0, x1, y1, layer, w=0.1):
    return f'\t(fp_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{U()}"))\n'
def rect(x0, y0, x1, y1, layer, w=0.05):
    return f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'
def circle(x, y, r, layer, w=0.1):
    return f'\t(fp_circle (center {x:.3f} {y:.3f}) (end {x + r:.3f} {y:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'
def smd(num, x, y, w, h, paste_ratio=None):
    extra = f' (solder_paste_margin_ratio {paste_ratio})' if paste_ratio is not None else ""
    return f'\t(pad "{num}" smd roundrect (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.1){extra} (uuid "{U()}"))\n'
def text(s, x, y, layer, size=0.5):
    return f'\t(fp_text user "{s}" (at {x:.3f} {y:.3f} 0) (layer "{layer}") (uuid "{U()}") (effects (font (size {size} {size}) (thickness 0.08))))\n'
def model(path, off=(0, 0, 0), rot=(0, 0, 0)):
    return (f'\t(model "{path}"\n\t\t(offset (xyz {off[0]} {off[1]} {off[2]}))\n\t\t(scale (xyz 1 1 1))\n'
            f'\t\t(rotate (xyz {rot[0]} {rot[1]} {rot[2]}))\n\t)\n')

# ---------------------------------------------------------------- VL53L5CX
b = ""
for k in range(7):
    x = 2.25 - 0.75 * k
    b += smd(f"A{k + 1}", x, 1.05, 0.5, 0.5) + smd(f"C{k + 1}", x, -1.05, 0.5, 0.5)
b += smd("B1", 2.65, 0, 0.5, 0.5) + smd("B7", -2.65, 0, 0.5, 0.5) + smd("B4", 0, 0, 2.316, 1.2, -0.3)
b += rect(-3.2, -1.515, 3.2, 1.515, "F.Fab", 0.1) + text("${REFERENCE}", 0, 0, "F.Fab", 0.5)
b += circle(-2.05, -0.1, 0.26, "F.Fab", 0.05) + rect(1.6, -0.45, 2.3, 0.25, "F.Fab", 0.05)   # Rx lens, Tx window (top view)
b += line(-3.3, -1.62, 3.3, -1.62, "F.SilkS", 0.12) + line(-3.3, 1.62, 2.3, 1.62, "F.SilkS", 0.12)   # gap by A1
b += circle(3.05, 1.85, 0.08, "F.SilkS", 0.16)
b += rect(-3.5, -1.8, 3.5, 1.8, "F.CrtYd", 0.05)
b += model("${KIPRJMOD}/../lib/3dmodels/ST_VL53L5CX_LGA16.step")
open(f"{D}/ST_VL53L5CX_LGA16_6.4x3.0mm.kicad_mod", "w").write(
    fp("ST_VL53L5CX_LGA16_6.4x3.0mm", "ST VL53L5CX 8x8 ToF, LGA-16 6.4 x 3.0 x 1.5 (DS13754 rev 8, fig. 22)", b))

# ---------------------------------------------------------------- camera module (mechanical only)
M = 8.5
b = rect(-M / 2, -M / 2, M / 2, M / 2, "F.Fab", 0.1) + circle(0, 0, 3.3, "F.Fab", 0.1)
b += rect(-6.1, -M / 2 - 1.2, 6.1, -M / 2, "F.Fab", 0.05)                 # the flex leaving the top edge (to the slot)
b += text("cam module (taped)", 0, M / 2 + 0.8, "F.Fab", 0.6) + text("${REFERENCE}", 0, 0, "F.Fab", 0.8)
b += rect(-M / 2 - 0.25, -M / 2 - 0.25, M / 2 + 0.25, M / 2 + 0.25, "F.CrtYd", 0.05)
b += model("${KIPRJMOD}/../lib/3dmodels/Camera_DVP24_Module.step")
open(f"{D}/Camera_DVP24_Module_8.5mm.kicad_mod", "w").write(
    fp("Camera_DVP24_Module_8.5mm", "24-pin DVP camera module (OV2640 / OV5640 style), 8.5 x 8.5, 21 mm flex; taped on, no pads", b,
       "board_only exclude_from_pos_files exclude_from_bom"))
# ---------------------------------------------------------------- FPC socket, SHOU HAN FPC 0.5-24P HYH2.0 (LCSC C6364666)
# Datasheet PCB layout: 24 pads 0.3 x 1.2 at 0.5 pitch (pad 1 at x -5.75), 2 mounting pads 1.8 x 2.0 centred 3.15 below the
# pad row at x +/-7.4; body 15.45 wide, 2.0 high, double-sided contacts (flip lock), the flex enters from +y.
b = "".join(smd(str(k + 1), -5.75 + 0.5 * k, 0, 0.3, 1.2) for k in range(24))
b += "".join(smd("MP", s * 7.4, 3.15, 1.8, 2.0) for s in (-1, 1))
b += rect(-7.725, 0.6, 7.725, 5.4, "F.Fab", 0.1) + text("${REFERENCE}", 0, 3.0, "F.Fab", 0.6) + text("flex in", 0, 4.7, "F.Fab", 0.5)
b += line(-7.85, 0.5, -6.3, 0.5, "F.SilkS", 0.12) + line(6.3, 0.5, 7.85, 0.5, "F.SilkS", 0.12) + circle(-5.75, -1.05, 0.1, "F.SilkS", 0.2)
b += rect(-8.6, -0.9, 8.6, 5.7, "F.CrtYd", 0.05)
b += model("${KIPRJMOD}/../lib/3dmodels/FPC_SHOUHAN_0.5-24P_HYH2.0.step")
open(f"{D}/FPC_SHOUHAN_0.5-24P_HYH2.0_Horizontal.kicad_mod", "w").write(
    fp("FPC_SHOUHAN_0.5-24P_HYH2.0_Horizontal", "FFC/FPC 24P 0.5 mm, double-sided contacts, flip lock, H 2.0 (SHOU HAN FPC 0.5-24P HYH2.0, LCSC C6364666)", b))
print("ok")
