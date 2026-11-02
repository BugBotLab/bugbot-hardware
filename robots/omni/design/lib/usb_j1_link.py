# Joins J1's D+ / D- pins (both rows of the USB-C) to U2's J1-side pins, on route_engine's grid with other nets rippable
# but the USB pair kept (its tracks never ripped). -> _work/usb_j1.json (remove / add diff) for SRC=... usb_pair2_apply.py
#   python design/lib/usb_j1_link.py /USB_DN
import json, sys, math
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
E.NO_RIP = {"/USB_DP", "/USB_DN"}
nc = E.net_class                                          # J1's middle pins: a 0.3 / 0.15 via fits in the 0.3 mm pad
E.net_class = lambda n: (nc(n)[0], nc(n)[1], (0.3, 0.15)) if n in ("/USB_DP", "/USB_DN") else nc(n)
b = E.Board(R + "_route/copper_clash.json", rippable=True); b.node_cap = 10_000_000
P = {(p["ref"], p["num"]): p for p in b.pads}
near = lambda a, b_: min((a, b_), key=lambda pn: math.dist((P[("U2", pn)]["x"], P[("U2", pn)]["y"]), (P[("J1", "A6")]["x"], P[("J1", "A6")]["y"])))
PINS = {"/USB_DP": [("J1", "A6"), ("J1", "B6"), ("U2", near("1", "6"))], "/USB_DN": [("J1", "A7"), ("J1", "B7"), ("U2", near("3", "4"))]}
orig_t = {id(t): t for t in b.out_tracks}; orig_v = {id(v): v for v in b.out_vias}
for net in sys.argv[1:]:
    keep = b.pads_of; b.pads_of = lambda n, pins=PINS[net], keep=keep: [p for p in keep(n) if (p["ref"], p["num"]) in pins]
    print(net, "joined %d failed %d" % b.route_net(net, None, margin=3.0)); b.pads_of = keep
gone = {id(x) for x in b.out_tracks} | {id(x) for x in b.out_vias}
ripped = sorted({x["net"] for i, x in list(orig_t.items()) + list(orig_v.items()) if i not in gone})
for n in ripped:
    if n in E.NO_RIP or n == "/GND": continue
    print(" rejoin", n, b.complete_net(n))
json.dump({"remove_tracks": [t for i, t in orig_t.items() if i not in gone], "remove_vias": [v for i, v in orig_v.items() if i not in gone],
           "tracks": [t for t in b.out_tracks if id(t) not in orig_t], "vias": [v for v in b.out_vias if id(v) not in orig_v]}, open(R + "_work/usb_j1.json", "w"))
print("ripped", ripped)
