# Re-routes /M1_B (U8.4 -> J14.2) off In4, where it crossed under the USB pair: route_engine's grid (F / In2 / In3 / B),
# the board's other tracks rippable (they are re-joined), the small 0.45 / 0.2 via so it can leave U8's pins.
# -> _work/m1b.json (remove / add diff) for SRC=... usb_pair2_apply.py
import json
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
nc = E.net_class
E.net_class = lambda n: ("Power", 0.4, (0.45, 0.2)) if n == "/M1_B" else nc(n)
b = E.Board(R + "_route/copper_clash.json", rippable=True)
b.node_cap = 10_000_000
orig_t = {id(t): t for t in b.out_tracks}; orig_v = {id(v): v for v in b.out_vias}
d, f = b.route_net("/M1_B", None, margin=8.0); print("M1_B joined", d, "failed", f, flush=True)
ripped = sorted({t["net"] for i, t in orig_t.items() if i not in {id(x) for x in b.out_tracks}} | {v["net"] for i, v in orig_v.items() if i not in {id(x) for x in b.out_vias}})
fails = []
for n in ripped:
    if n in ("/GND", "/USB_DP", "/USB_DN"): continue
    dd, ff = b.complete_net(n); print(f" {n:14s} rejoined {dd} failed {ff}", flush=True)
    if ff: fails.append(n)
if "/GND" in ripped: print(" GND plane vias", b.plane_drops("/GND", "GND"))
new_t = [t for t in b.out_tracks if id(t) not in orig_t]; new_v = [v for v in b.out_vias if id(v) not in orig_v]
keep = {id(x) for x in b.out_tracks} | {id(x) for x in b.out_vias}
json.dump({"remove_tracks": [t for i, t in orig_t.items() if i not in keep], "remove_vias": [v for i, v in orig_v.items() if i not in keep],
           "tracks": new_t, "vias": new_v}, open(R + "_work/m1b.json", "w"))
print(f"m1b: ripped {ripped}; +{len(new_t)} tracks +{len(new_v)} vias; still open {fails}")
