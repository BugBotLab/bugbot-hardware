# Placement helper 3/3 (KiCad python): puts every part where place_floorplan.py decided (schematics/Main/_place/placement.json):
# side, position (robot frame: KiCad x = 100 + X, y = 100 - Y) and turn. Fixed parts are not touched.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_apply.py
import json, shutil, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
pl = json.load(open(sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/_place/placement.json"))   # or placement_v2.json
shutil.copy(B, B + ".before-placement")
board = pcbnew.LoadBoard(B)
for ref, (x, y, rot, side, _) in pl.items():
    f = board.FindFootprintByReference(ref)
    f.SetPosition(pcbnew.VECTOR2I(0, 0))
    if f.IsFlipped() != (side == "B"):
        f.Flip(f.GetPosition(), False)
    f.SetOrientationDegrees(rot)                                # the same order as place_extract.py: flip, then turn
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + x), pcbnew.FromMM(100 - y)))
pcbnew.SaveBoard(B, board)
print("placed", len(pl))
