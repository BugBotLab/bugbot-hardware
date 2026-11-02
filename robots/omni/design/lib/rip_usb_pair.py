# KiCad python: removes the USB pair's tracks / vias east of U2 (x > 76.3 mm, KiCad), keeping J1 -> U2 and U2's links.
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); X = pcbnew.FromMM(176.3) - pcbnew.FromMM(100)
gone = [t for t in b.GetTracks() if t.GetNetname() in ("/USB_DP", "/USB_DN")
        and (max(t.GetStart().x, t.GetEnd().x) > X if t.GetClass() != "PCB_VIA" else t.GetPosition().x > X)]
for t in gone: b.Remove(t)
pcbnew.SaveBoard(B, b); print("removed", len(gone), "USB pair pieces")
