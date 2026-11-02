# KiCad python: removes every track and via from the main board (zones stay) before a full re-route.
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); g = list(b.GetTracks())
for t in g: b.Remove(t)
pcbnew.SaveBoard(B, b); print("removed", len(g), "tracks / vias")
