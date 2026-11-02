# U6, the Waveshare ESP32-P4 module, on the main board's underside centred at robot (5, 19) (approved option A,
# design/schematics/Main/p4_module_options.png: the only place a 25 x 25 x 3.3 part fits; ~1.3 mm over wheel 1, 0.9 over the
# NFC reader's corner). Robot frame: KiCad x = 100 + X, y = 100 - Y.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_module.py
import pcbnew, shutil
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
shutil.copy(B, B + ".before-module")
board = pcbnew.LoadBoard(B)
f = board.FindFootprintByReference("U6")
if not f.IsFlipped():
    f.Flip(f.GetPosition(), False)
f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(105.0), pcbnew.FromMM(81.0))); f.SetOrientationDegrees(0)
pcbnew.SaveBoard(B, board)
print("U6", "B" if f.IsFlipped() else "F", pcbnew.ToMM(f.GetPosition().x) - 100, 100 - pcbnew.ToMM(f.GetPosition().y))
