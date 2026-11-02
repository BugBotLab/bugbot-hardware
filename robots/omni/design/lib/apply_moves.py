# KiCad python: shifts footprints by _place/legalize.json {ref: [dx, dy]} (robot frame, mm; KiCad y is flipped).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/apply_moves.py [board]
import sys, json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
mv = json.load(open(BB + "/design/schematics/Main/_place/legalize.json"))
b = pcbnew.LoadBoard(B)
for r, (dx, dy) in mv.items():
    f = b.FindFootprintByReference(r); f.SetPosition(f.GetPosition() + pcbnew.VECTOR2I(pcbnew.FromMM(dx), pcbnew.FromMM(-dy)))
pcbnew.SaveBoard(B, b); print("moved", len(mv), "parts:", ", ".join(f"{r} {dx:+.2f},{dy:+.2f}" for r, (dx, dy) in mv.items()))
