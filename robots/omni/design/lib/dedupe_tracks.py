# Remove duplicate track pieces (KiCad python): same net, layer and end points (either way round) -> keep one.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/dedupe_tracks.py [board]
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); seen, kill = set(), []
for t in b.GetTracks():
    if t.GetClass() != "PCB_TRACK": continue
    a, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    k = (t.GetNetname(), t.GetLayer(), min(a, e), max(a, e))
    if k in seen and not t.IsLocked(): kill.append(t)
    seen.add(k)
for t in kill: b.Remove(t)
pcbnew.SaveBoard(B, b); print("dedupe_tracks:", len(kill), "duplicate pieces removed")
