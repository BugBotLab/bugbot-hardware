# Joins back the nets clash_rip.py cut (and any other nets given), and drops plane vias for the pads given as REF.PAD
# on the GND / VSYS planes. -> _route/clash.json for route_fill_apply.py (add).
#   python design/lib/clash_route.py [/NET ...] [@REF.PAD ...]
import sys, json
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/_route/"
b = E.Board(R + "copper_clash.json")
nets = json.load(open(R + "clash_nets.json")) + [a for a in sys.argv[1:] if a.startswith("/")]
drops = [a[1:] for a in sys.argv[1:] if a.startswith("@")]
for n in dict.fromkeys(nets):
    if n in ("/GND", "/VSYS"): continue
    d, f = b.complete_net(n); print(f" {n:14s} pieces joined {d} failed {f}", flush=True)
keep = b.pads_of
for n, plane in (("/GND", "GND"), ("/VSYS", "VSYS")):
    b.pads_of = lambda nn: [p for p in keep(nn) if f"{p['ref']}.{p['num']}" in drops]
    if b.pads_of(n): d, f = b.plane_drops(n, plane); print(f" {n} plane vias {d} failed {f}", flush=True)
b.pads_of = keep
b.save(R + "clash.json"); print(f"clash: {len(b.out_tracks)} tracks, {len(b.out_vias)} vias")
