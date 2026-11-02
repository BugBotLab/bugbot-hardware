# KiCad python: adds a through via (via-in-pad style, filled) at x,y (KiCad mm) on a net.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/add_via.py NET X Y [DIA DRILL] [board]
import sys, pcbnew
net, x, y = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
dia, drill = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.4, 0.2)
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[6] if len(sys.argv) > 6 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm = pcbnew.FromMM
v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(dia)); v.SetDrill(mm(drill))
v.SetNet(b.FindNet(net)); b.Add(v); pcbnew.SaveBoard(B, b); print("via", net, x, y)
