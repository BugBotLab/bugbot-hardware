# Power switch v3 re-place, step 3: re-routes the power corner on route_engine (local nets whole; the shared nets'
# pieces joined back to their main copper; GND / VSYS vias for the moved parts' pads). -> _route/corner.json
import json, time
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/_route/"
cn = json.load(open(R + "corner_nets.json"))
b = E.Board(R + "copper_corner.json")
ORDER_LOCAL = ["/SW33A", "/SW33B", "/SW5", "/FB33", "/FB5", "/BAT_F", "/FS_D", "/DW_VCC", "/DW_CS", "/DW_OD", "/DW_OC",
               "/Q1_G", "/Q2_G", "/VBAT_SW"]
ORDER_GLOBAL = ["/BAT_P", "/BAT_N", "/VBAT_P", "/SW_G", "/SW_ON", "/VBUS", "/5V", "/3V3", "/VBAT_SENSE", "/CHIP_PU"]
t0 = time.time()
for n in [x for x in ORDER_LOCAL if x in cn["local"]] + [x for x in cn["local"] if x not in ORDER_LOCAL]:
    d, f = b.route_net(n, None); print(f" {n:12s} joined {d} failed {f}", flush=True)
for n in [x for x in ORDER_GLOBAL if x in cn["global"]] + [x for x in cn["global"] if x not in ORDER_GLOBAL + ["/GND", "/VSYS"]]:
    d, f = b.complete_net(n); print(f" {n:12s} pieces joined {d} failed {f}", flush=True)
moved = set(cn["moved"])
keep = b.pads_of
b.pads_of = lambda n: [p for p in keep(n) if p["ref"] in moved]
for n, plane in (("/GND", "GND"), ("/VSYS", "VSYS")):
    d, f = b.plane_drops(n, plane); print(f" {n} plane vias {d} failed {f}", flush=True)
b.pads_of = keep
b.save(R + "corner.json"); print(f"corner: {len(b.out_tracks)} tracks, {len(b.out_vias)} vias, {time.time() - t0:.0f} s")
