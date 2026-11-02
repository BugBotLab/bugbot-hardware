# KiCad python: the USB pair's B.Cu pieces as segments (robot frame) -> _work/usb_lane_segs.json, so plan_v2.py keeps
# every VSYS island off the whole pair, fans included.
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"; b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
R = lambda p: (tm(p.x) - 100, 100 - tm(p.y))
segs = [[R(t.GetStart()), R(t.GetEnd())] for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"
        and t.GetNetname() in ("/USB_DP", "/USB_DN") and t.GetLayer() == pcbnew.B_Cu]
json.dump(segs, open(BB + "/design/schematics/Main/_work/usb_lane_segs.json", "w")); print(len(segs), "pair segments")
