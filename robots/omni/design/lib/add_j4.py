# J4 on the main board: the LED ring lead (JST-SH 3-pin vertical, BM03B-SRSS-TB), 1.2 mm along X from the original spot to clear the deck leg (H8).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/add_j4.py
# Pins (match the LED board's J1): 1 = +5V, 2 = LED_DIN (ESP32 GPIO, 3.3 V), 3 = GND. The main board has no schematic yet:
# J4 is placed with its reference and value only, as the other starter footprints.
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
X, Y, ROT = -5.3, 14.0, 0                  # robot frame; KiCad x = 100 + X, y = 100 - Y
board = pcbnew.LoadBoard(B)
old = board.FindFootprintByReference("J4")
if old:
    board.Remove(old)
f = pcbnew.FootprintLoad("C:/Program Files/KiCad/10.0/share/kicad/footprints/Connector_JST.pretty", "JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical")
f.SetFPIDAsString("Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical")
f.SetReference("J4"); f.SetValue("LED ring (5V DIN GND)")
f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + X), pcbnew.FromMM(100 - Y))); f.SetOrientationDegrees(ROT)
board.Add(f)
pcbnew.SaveBoard(B, board)
print("J4 placed", [(p.GetNumber(), round(pcbnew.ToMM(p.GetPosition().x) - 100, 2), round(100 - pcbnew.ToMM(p.GetPosition().y), 2)) for p in f.Pads()])
