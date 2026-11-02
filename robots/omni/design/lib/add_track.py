# KiCad python: adds one track: NET LAYER X0 Y0 X1 Y1 W [board]  (KiCad mm, layer name e.g. In2.Cu)
import sys, pcbnew
net, lay = sys.argv[1], sys.argv[2]; x0, y0, x1, y1, w = map(float, sys.argv[3:8])
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[8] if len(sys.argv) > 8 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm = pcbnew.FromMM
t = pcbnew.PCB_TRACK(b); t.SetLayer(b.GetLayerID(lay)); t.SetWidth(mm(w)); t.SetNet(b.FindNet(net))
t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1))); b.Add(t); pcbnew.SaveBoard(B, b); print("track", net, lay)
