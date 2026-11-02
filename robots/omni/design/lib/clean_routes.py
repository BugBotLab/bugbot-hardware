# Route clean-up on a pns work copy (C:/Python312/python.exe): KiCad's router optimiser on every net except the USB pair,
# keeping topology: merges collinear pieces, smooths to 45 deg, removes staircases, cleans pad exits. The optimiser can
# drop a connection now and then, so each net's unrouted count is checked after it and the net undone if it went up.
# Saves the copy and closes the private pcbnew.
#   C:/Python312/python.exe design/lib/clean_routes.py <work copy .kicad_pcb>
import glob, os, sys
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/design/tools/pns_api")
from pns_client import PNS
W = sys.argv[1]
for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "~*.lck")): os.remove(f)   # a killed pcbnew leaves locks: its next start would stop on a dialog
p = PNS.open(W)
nets = sorted({t.net.name for t in p.tracks()} - {"/USB_DP", "/USB_DN", ""})
tot, undone = 0, []
for n in nets:
    before = p.get_unrouted([n])["unconnected"]
    r = p.optimize_tracks([n], keep_topology=True)
    if not r.get("added") and not r.get("removed"): continue
    if p.get_unrouted([n])["unconnected"] > before:
        p.undo(); undone.append(n); continue
    tot += len(r.get("added", []))
p.save(); p.close()
print("clean_routes:", len(nets), "nets;", tot, "pieces rewritten; undone (would open a connection):", undone or "none")
