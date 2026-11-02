# KiCad python: removes duplicate vias (same net, same spot) left by repeated plane-drop runs.
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); seen, dup = set(), []
for t in b.GetTracks():
    if t.GetClass() != "PCB_VIA": continue
    k = (t.GetNetname(), t.GetPosition().x // 1000, t.GetPosition().y // 1000)
    if k in seen: dup.append(t)
    else: seen.add(k)
for t in dup: b.Remove(t)
pcbnew.SaveBoard(B, b); print("removed", len(dup), "duplicate vias")
