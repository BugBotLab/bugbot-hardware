# Routes the given nets on route_engine's grid (F / In2 / In3 / B) with the board's other tracks rippable (they are
# re-joined afterwards) and the small 0.45 / 0.2 via so they can leave fine-pitch pins (motor lines out of U8 / U9).
# -> _work/rip_route.json (remove / add diff) for SRC=... usb_pair2_apply.py
#   python design/lib/rip_route.py /NET [/NET ...] [--gnd]      (--gnd: also drop GND pads that lost their plane via)
import json, sys
import route_engine as E
NETS = [a for a in sys.argv[1:] if a.startswith("/")]
GND_DROPS = "--gnd" in sys.argv
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
nc = E.net_class
E.net_class = lambda n: (nc(n)[0], nc(n)[1], (0.45, 0.2)) if n in NETS else nc(n)
E.NO_RIP = {"/USB_DP", "/USB_DN"}                # never rip the impedance-controlled USB pair
b = E.Board(R + "_route/copper_clash.json", rippable=True)
b.node_cap = 10_000_000
orig_t = {id(t): t for t in b.out_tracks}; orig_v = {id(v): v for v in b.out_vias}
for net in NETS:
    d, f = b.complete_net(net) if any(t["net"] == net for t in b.out_tracks) else b.route_net(net, None, margin=8.0)
    print(net, "joined", d, "failed", f, flush=True)
ripped = sorted({t["net"] for i, t in orig_t.items() if i not in {id(x) for x in b.out_tracks}} | {v["net"] for i, v in orig_v.items() if i not in {id(x) for x in b.out_vias}})
fails = []
for n in ripped:
    if n in ("/GND", "/USB_DP", "/USB_DN") or n in NETS: continue
    dd, ff = b.complete_net(n); print(f" {n:14s} rejoined {dd} failed {ff}", flush=True)
    if ff: fails.append(n)
if "/GND" in ripped or GND_DROPS: print(" GND plane vias", b.plane_drops("/GND", "GND"))
new_t = [t for t in b.out_tracks if id(t) not in orig_t]; new_v = [v for v in b.out_vias if id(v) not in orig_v]
keep = {id(x) for x in b.out_tracks} | {id(x) for x in b.out_vias}
json.dump({"remove_tracks": [t for i, t in orig_t.items() if i not in keep], "remove_vias": [v for i, v in orig_v.items() if i not in keep],
           "tracks": new_t, "vias": new_v}, open(R + "_work/rip_route.json", "w"))
print(f"rip_route: ripped {ripped}; +{len(new_t)} tracks +{len(new_v)} vias; still open {fails}")
