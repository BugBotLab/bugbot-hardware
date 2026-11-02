# V tapers where a track changes width (C:/Python312/python.exe, private pcbnew via pns_client): KiCad's teardrop
# generator, track-to-track only (no pad / via teardrops), with the board's straight-sided setting (td_curve_segcount 0),
# so every thin-to-thick step is a straight V (user, 2026-10-26). Saves the copy and closes the private pcbnew.
#   C:/Python312/python.exe design/lib/teardrops.py <work copy .kicad_pcb>
import glob, os, sys
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/design/tools/pns_api")
from pns_client import PNS
for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "~*.lck")): os.remove(f)   # a killed pcbnew leaves locks: its next start would stop on a dialog
p = PNS.open(sys.argv[1])
r = p.set_teardrops(enable=True, vias=False, pth_pads=False, smd_pads=False, track_to_track=True)
p.save(); p.close()
print(f"teardrops: {r['teardrop_zones']} V tapers ({r['items_changed']} items changed)")
