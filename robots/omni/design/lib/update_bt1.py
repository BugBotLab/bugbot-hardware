# Swap BT1 on BugBot_Main for the library footprint (keeps position, rotation, side, reference, value, pad nets).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/update_bt1.py
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
LIB = BB + "/design/lib/BugBot.pretty"
board = pcbnew.LoadBoard(B)
old = board.FindFootprintByReference("BT1")
new = pcbnew.FootprintLoad(LIB, "BatteryHolder_Keystone_1051_1xCR123A")
new.SetParent(board)
nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
fid = old.GetFPID(); new.SetFPID(fid)
new.SetReference(old.GetReference()); new.SetValue(old.GetValue())
new.Reference().SetPosition(old.Reference().GetPosition()); new.Value().SetPosition(old.Value().GetPosition())
if old.IsFlipped() != new.IsFlipped():
    new.Flip(new.GetPosition(), False)
new.SetOrientation(old.GetOrientation()); new.SetPosition(old.GetPosition())
new.SetPath(old.GetPath())
try: new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
except Exception: pass
for p in new.Pads():
    if p.GetNumber() in nets: p.SetNet(nets[p.GetNumber()])
pos, ang = old.GetPosition(), old.GetOrientation().AsDegrees()
board.Remove(old); board.Add(new)
pcbnew.SaveBoard(B, board)
print("BT1 at", pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), ang, "pads", [(p.GetNumber(), p.GetNetname(), round(pcbnew.ToMM(p.GetDrillSize().x), 2)) for p in new.Pads()])
