# J6 on the main board: the front sensor board's socket, 2 x 10 1.27 mm SMD female (HX PM1.27-2x10P TP, LCSC C41397119),
# under the front board's right-angle header (kicad/BugBot_Front, J1). Robot frame: KiCad x = 100 + X, y = 100 - Y.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/add_j6.py
# Centre = Params fsb_sock_x / fsb_sock_y (17.5, -4.5): between the header's two rows of pins (1.06 / 2.33 behind the board).
# Turned 180 so socket pin n takes header pin n (checked below against design/schematics/Front/_route/j1_pins.json).
# The main board has no schematic yet: J6 is placed with its reference and value; the pin-out (same as the front board's J1):
#   1 SDA  3 SCL  5 VSYNC  7 GND  9 HREF  11 D9  13 XCLK  15 D8  17 D7  19 PCLK
#   2 3V3  4 3V3  6 GND    8 GND 10 GND   12 D6  14 D2    16 D5  18 D3  20 D4
#   (I2C pull-ups 2.2k to 3V3 belong on the main board; the ToF INT is not wired, the ToF is polled.)
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
X, Y, ROT = 17.5, -4.5, 180
board = pcbnew.LoadBoard(B)
old = board.FindFootprintByReference("J6")
if old:
    board.Remove(old)
f = pcbnew.FootprintLoad("C:/Program Files/KiCad/10.0/share/kicad/footprints/Connector_PinSocket_1.27mm.pretty", "PinSocket_2x10_P1.27mm_Vertical_SMD")
f.SetFPIDAsString("Connector_PinSocket_1.27mm:PinSocket_2x10_P1.27mm_Vertical_SMD")
f.SetReference("J6"); f.SetValue("Front sensor board (2x10 1.27)")
for k, v in (("MPN", "HX PM1.27-2x10P TP"), ("LCSC", "C41397119")):
    f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + X), pcbnew.FromMM(100 - Y))); f.SetOrientationDegrees(ROT)
board.Add(f)
pcbnew.SaveBoard(B, board)
# check: each socket contact (pad pulled in to its row, +/-0.635 from the centre) under the header pin of the same number
tips = json.load(open(BB + "/design/schematics/Front/_route/j1_pins.json"))
FAR, NEAR = 19.2 - 2.33, 19.2 - 1.06
bad = []
for p in f.Pads():
    px, py = pcbnew.ToMM(p.GetPosition().x) - 100, 100 - pcbnew.ToMM(p.GetPosition().y)
    cx = X + (0.635 if px > X else -0.635)
    ty, row = tips[p.GetNumber()]
    if abs(py - ty) > 0.01 or abs(cx - (FAR if row == "far" else NEAR)) > 0.05:
        bad.append((p.GetNumber(), round(cx, 3), round(py, 3), ty, row))
print("J6 placed;", "all 20 pins match the header" if not bad else f"MISMATCH {bad}")
