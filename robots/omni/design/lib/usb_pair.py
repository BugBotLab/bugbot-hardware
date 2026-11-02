# USB as a differential pair (user, 2026-10-25), on route_engine's grid. ~90 ohm: 0.15 mm tracks, 0.20 mm gap on the
# top layer, 0.099 mm over the solid GND of In1 (JLC06161H-3313, er ~4.1; microstrip estimate, IPC-2141).
#  1. J1 -> U2 (ESD chip), each line on its own: both of J1's pins (A / B side, either plug turn) and U2's near pin
#  2. U2 -> module pads 50 / 51: ONE centre line for the pair (0.5 mm wide: both tracks and the gap) on F.Cu only,
#     the two tracks offset 0.175 mm either side of it, fanned into vias in the pads at U2 pins 4 / 6 and U6 pads 50 / 51
#  3. a GND via beside each signal via (return path)
# Writes _work/usb_pair.json for route_fill_apply.py (add).
import json, math, sys
import numpy as np
from shapely.geometry import LineString
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
W = BB + "/design/schematics/Main/_work/"
TW, GAP = 0.15, 0.20
PITCH = TW + GAP
VIA = (0.45, 0.2)
b = E.Board(W + "copper_usb.json")
P = {(p["ref"], p["num"]): p for p in b.pads}

# ---- 1. J1 -> U2 near pins (short, any layer)
for net, pins in (("/USB_DP", [("J1", "A6"), ("J1", "B6"), ("U2", "1")]), ("/USB_DN", [("J1", "A7"), ("J1", "B7"), ("U2", "3")])):
    keep = b.pads_of
    b.pads_of = lambda n, pins=pins, keep=keep: [p for p in keep(n) if (p["ref"], p["num"]) in pins]
    d, f = b.route_net(net, None, margin=3.0)
    b.pads_of = keep
    print(f"{net} J1 -> U2: joined {d} failed {f}")

# ---- 2. the pair U2 -> U6 on F.Cu
a_dn, a_dp = P[("U2", "4")], P[("U2", "6")]
z_dn, z_dp = P[("U6", "50")], P[("U6", "51")]
A = ((a_dn["x"] + a_dp["x"]) / 2 + 1.2, (a_dn["y"] + a_dp["y"]) / 2)          # just beyond U2's pins
Z = ((z_dn["x"] + z_dp["x"]) / 2 - 1.6, (z_dn["y"] + z_dp["y"]) / 2)          # just inside the module's pads
wv = 2 * TW + GAP
def disc(c, r, l="F"):                                 # cells within r mm of a point (the search keeps only the free ones)
    i0, j0 = b.ij(*c); n = int(r / E.RES)
    return {(i0 + i, j0 + j, l) for i in range(-n, n + 1) for j in range(-n, n + 1) if i * i + j * j <= n * n}
s = disc(A, 2.5); g = disc(Z, 1.5)
r = b.search("/USB_DP", s, g, wv, (99, 99), None, margin=6.0, via_cost=1e6, esc=0.0)
if r is None:
    sys.exit("pair centre line: no room on F.Cu")
path, ok, off, _, dist = r
pts = b.pull([c for c in path], ok["F"], off)
centre = LineString([b.xy(i, j) for i, j in pts]).simplify(0.01)
# which side is D-: at the U2 end, D- (pin 4) must be on the side its pin is
lft = centre.offset_curve(PITCH / 2, join_style=2); rgt = centre.offset_curve(-PITCH / 2, join_style=2)
d0 = lambda ls, p: math.dist(ls.coords[0], (p["x"], p["y"]))
dn_line, dp_line = (lft, rgt) if d0(lft, a_dn) < d0(rgt, a_dn) else (rgt, lft)
print(f"pair centre line {centre.length:.1f} mm, {len(centre.coords) - 1} pieces; D- {dn_line.length:.2f} mm, D+ {dp_line.length:.2f} mm "
      f"(skew {abs(dn_line.length - dp_line.length):.2f} mm)")
out_t, out_v = [], []
for net, line, pa, pz in (("/USB_DN", dn_line, a_dn, z_dn), ("/USB_DP", dp_line, a_dp, z_dp)):
    c = list(line.coords)
    seq = [(pa["x"], pa["y"])] + c + [(pz["x"], pz["y"])]                       # fan from the pad via to the pair and back
    for (x0, y0), (x1, y1) in zip(seq, seq[1:]):
        out_t.append({"net": net, "l": "F", "x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": TW})
    for p in (pa, pz):
        out_v.append({"net": net, "x": p["x"], "y": p["y"], "d": VIA[0], "drill": VIA[1]})          # via in the pad (filled)
for t in out_t: b.out_tracks.append(t); b.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
for v in out_v:
    b.out_vias.append(v); b.add_via(v["x"], v["y"], v["d"], v["net"])
for v in out_v: b.return_via(v["x"], v["y"], rmax=1.2)                          # 3. GND return vias
b.save(W + "usb_pair.json")
print("tracks", len(b.out_tracks), "vias", len(b.out_vias))
