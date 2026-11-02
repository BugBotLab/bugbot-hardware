# KiCad python: removes the via of NET at X,Y (KiCad mm, within 0.02).   rm_via.py NET X Y [board]
import sys, pcbnew
net, x, y = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[4] if len(sys.argv) > 4 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
g = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == net
     and abs(tm(t.GetPosition().x) - x) < 0.02 and abs(tm(t.GetPosition().y) - y) < 0.02]
for t in g: b.Remove(t)
pcbnew.SaveBoard(B, b); print("removed", len(g), "via(s)")
