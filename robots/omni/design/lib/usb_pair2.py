# USB as a ~90 ohm differential pair, take 2 (user, 2026-10-25): usb_pair.py found no free lane for the pair on F.Cu, so
# this one clears one. On route_engine's grid with the board's tracks rippable:
#  1. J1 -> U2 (ESD chip): each line on its own, as before
#  2. the pair's centre line U2 -> U6 pads 48 / 49 (high speed) on B.Cu (U2 and the module are both on the bottom, so no vias), over
#     In4's GND fill and never over its VSYS islands (0.15 tracks, 0.20 gap, 0.0994 mm to In4: ~90 ohm, the same
#     microstrip as on top). F.Cu has no lane at all past its pads; In2 / In3 sit 0.11 mm from each other (crosstalk).
#     Searched past other nets' B.Cu tracks / vias (each cell through them costs) but never through pads
#  3. the other nets' pieces in the lane are ripped, the pair laid, and each ripped net joined back (complete_net)
# Writes _work/usb_pair2.json {"remove": [...], "tracks": [...], "vias": [...]} for usb_pair2_apply.py.
#   python design/lib/usb_pair2.py   (reads _work/copper_usb.json from route_fill_export.py)
import json, math, sys, os
from shapely.geometry import LineString, Point
import route_engine as E
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
W = BB + "/design/schematics/Main/_work/"
TW, GAP = 0.15, 0.20
PITCH = TW + GAP
VIA = (0.45, 0.2)
b = E.Board(W + "copper_usb.json", rippable=True)
# Q2's own VSYS island (one pad, its fill isolated anyway: Q2.2 has a track) sits where the pair leaves U2: let the pair
# pass; plan_v2.py then cuts every island back from the pair's lane (_work/usb_lane.json)
q2 = next(p for p in b.pads if p["ref"] == "Q2" and p["num"] == "2")
# (floor plan v3: no longer needed, U2 moved away from Q2)
# b.island[(b.xs[:, None] - q2["x"]) ** 2 + (b.ys[None, :] - q2["y"]) ** 2 < 4.5 ** 2] = False
b.node_cap = 40_000_000                                    # the soft search (rip costs) explores far more cells
orig_t = {id(t): t for t in b.out_tracks}; orig_v = {id(v): v for v in b.out_vias}
P = {(p["ref"], p["num"]): p for p in b.pads}

# ---- 1. J1 -> U2 near pins (skipped with KEEP_J1=1: already on the board)
import os
# USBLC6 is a pass-through (pins 1 = 6 = D+, 3 = 4 = D-): J1 wires into the U2 side that faces J1, the pair leaves from the
# other side (floor plan v3 turned U2 so that pins 4 / 6 face J1)
_near = lambda a, b_: min((a, b_), key=lambda pn: math.dist((P[("U2", pn)]["x"], P[("U2", pn)]["y"]), (P[("J1", "A6")]["x"], P[("J1", "A6")]["y"])))
DP_J, DN_J = _near("1", "6"), _near("3", "4"); DP_P, DN_P = ({"1", "6"} - {DP_J}).pop(), ({"3", "4"} - {DN_J}).pop()
print("U2: J1 side pins", DP_J, DN_J, "| pair from pins", DP_P, DN_P)
for net, pins in [] if os.environ.get("KEEP_J1") else (("/USB_DP", [("J1", "A6"), ("J1", "B6"), ("U2", DP_J)]), ("/USB_DN", [("J1", "A7"), ("J1", "B7"), ("U2", DN_J)])):
    keep = b.pads_of
    b.pads_of = lambda n, pins=pins, keep=keep: [p for p in keep(n) if (p["ref"], p["num"]) in pins]
    d, f = b.route_net(net, None, margin=3.0)
    b.pads_of = keep
    print(f"{net} J1 -> U2: joined {d} failed {f}", flush=True)

# ---- 2. the pair's centre line
a_dn, a_dp = P[("U2", DN_P)], P[("U2", DP_P)]
z_dn, z_dp = P[("U6", "48")], P[("U6", "49")]          # the P4's high-speed USB (was GPIO24/25 on pads 50 / 51)
# U2 end (floor plan v3, 2026-10-26: U2 sits at the west edge, turned): the pair leaves along U2's own exit direction
# (from its pin-1/3 row to its pin-4/6 row); each line goes straight out past the middle pin 5, then 45 deg onto the pair
# at +/- PITCH/2. Module end: pads 48 / 49 on the module's east edge, reached heading +x (as before).
h = PITCH / 2
_u = lambda v: (v[0] / math.hypot(*v), v[1] / math.hypot(*v))
P13 = ((P[("U2", DP_J)]["x"] + P[("U2", DN_J)]["x"]) / 2, (P[("U2", DP_J)]["y"] + P[("U2", DN_J)]["y"]) / 2)   # the J1-side row
P46 = ((a_dn["x"] + a_dp["x"]) / 2, (a_dn["y"] + a_dp["y"]) / 2)
ua = _u((P46[0] - P13[0], P46[1] - P13[1])); va = (-ua[1], ua[0])
def fan_a(p):
    o = (p["x"] - P46[0]) * va[0] + (p["y"] - P46[1]) * va[1]; sg = 1 if o > 0 else -1; d = abs(o) - h
    p1 = (p["x"] + 0.86 * ua[0], p["y"] + 0.86 * ua[1])
    return (p["x"], p["y"]), p1, (p1[0] + d * ua[0] - sg * d * va[0], p1[1] + d * ua[1] - sg * d * va[1])
fa = {"/USB_DN": fan_a(a_dn), "/USB_DP": fan_a(a_dp)}
_d = abs((a_dn["x"] - P46[0]) * va[0] + (a_dn["y"] - P46[1]) * va[1]) - h
a0 = (P46[0] + (0.86 + _d) * ua[0], P46[1] + (0.86 + _d) * ua[1])
A = (a0[0] + 0.3 * ua[0], a0[1] + 0.3 * ua[1])
# module end: Z_FROM=east (default since floor plan v3): the pair comes in heading -x from outside the module's east edge,
# so D+ stays on the left all the way from U2 (west: heading +x from under the module, as before)
ZE = os.environ.get("Z_FROM", "east") == "east"; zs = 1 if ZE else -1
yz = (z_dn["y"] + z_dp["y"]) / 2; xz = z_dn["x"] + zs * 1.5
fz = {n: ((xz + zs * (abs(p["y"] - yz) - h), yz + (h if p["y"] > yz else -h)), (xz, p["y"]), (p["x"], p["y"])) for n, p in (("/USB_DN", z_dn), ("/USB_DP", z_dp))}
Z = ((max if ZE else min)(q[0][0] for q in fz.values()) + zs * 0.3, yz)
wv = 2 * TW + GAP
def disc(c, r, l="F"):
    i0, j0 = b.ij(*c); n = int(r / E.RES)
    return {(i0 + i, j0 + j, l) for i in range(-n, n + 1) for j in range(-n, n + 1) if i * i + j * j <= n * n}
r = b.search("/USB_DP", disc(A, 0.15, "B"), disc(Z, 0.15, "B"), wv, (99, 99), None, margin=6.0, via_cost=1e6, esc=0.0, soft=True)
if r is None: sys.exit("pair centre line: no lane even past other tracks")
path, ok, off, _, dist = r
pts = b.pull([c for c in path], ok["B"], off)
mid = [b.xy(i, j) for i, j in pts]
z0 = ((max if ZE else min)(q[0][0] for q in fz.values()), yz)
centre = LineString([a0, A] + mid[1:-1] + [Z, z0]).simplify(0.01)
lft = centre.offset_curve(h, join_style=2); rgt = centre.offset_curve(-h, join_style=2)
# D- is the offset line that starts where D-'s fan ends
dn_line, dp_line = (lft, rgt) if math.dist(lft.coords[0], fa["/USB_DN"][-1]) < math.dist(rgt.coords[0], fa["/USB_DN"][-1]) else (rgt, lft)
skew = dp_line.length - dn_line.length + sum(math.dist(*z) for z in zip(fa["/USB_DP"], fa["/USB_DP"][1:])) + sum(math.dist(*z) for z in zip(fz["/USB_DP"], fz["/USB_DP"][1:]))        - sum(math.dist(*z) for z in zip(fa["/USB_DN"], fa["/USB_DN"][1:])) - sum(math.dist(*z) for z in zip(fz["/USB_DN"], fz["/USB_DN"][1:]))
json.dump(list(centre.coords), open(W + "usb_lane.json", "w"))
print(f"pair centre line {centre.length:.1f} mm; skew pad to pad {skew:+.2f} mm (D+ minus D-)", flush=True)

out_t, out_v = [], []
# a pair keeps its left / right order: if D- arrives on D+'s side of the module pads, swap them there (floor plan v3: U2
# leaves north, the pads are reached from the west): D+ goes straight on B, D- steps away, drops to In2 under D+ and comes
# back up just before pad 48 (two standard vias, ~1.5 mm on In2)
e_dn, e_dp = dn_line.coords[-1], dp_line.coords[-1]
SWAP = math.dist(e_dn, fz["/USB_DN"][0]) > math.dist(e_dn, fz["/USB_DP"][0])
ends = {}
if SWAP and not ZE:
    p_dp, p_dn = (z_dp["x"], z_dp["y"]), (z_dn["x"], z_dn["y"])
    dy = abs(p_dp[1] - e_dp[1])
    ends["/USB_DP"] = ([(e_dp[0] + 0.5, e_dp[1]), (e_dp[0] + 0.5 + dy, p_dp[1]), p_dp], None)
    sg = 1 if e_dn[1] > e_dp[1] else -1
    v1 = (e_dn[0] + 0.7, e_dn[1] + sg * 0.4); v2 = (p_dn[0] - 1.1, p_dn[1])
    ends["/USB_DN"] = ([(e_dn[0] + 0.3, e_dn[1]), v1], (v1, v2, p_dn))
    out_v += [{"net": "/USB_DN", "x": v[0], "y": v[1], "d": 0.45, "drill": 0.2} for v in (v1, v2)]
    print("module end: D+ / D- swapped through In2 (vias at", [round(c, 2) for c in v1], [round(c, 2) for c in v2], ")")
for net, line, pa, pz in (("/USB_DN", dn_line, a_dn, z_dn), ("/USB_DP", dp_line, a_dp, z_dp)):
    tail, under = ends.get(net, (list(fz[net][1:]), None))
    seq = list(fa[net][:-1]) + list(line.coords) + tail
    for (x0, y0), (x1, y1) in zip(seq, seq[1:]):
        out_t.append({"net": net, "l": "B", "x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": TW})
    if under:
        v1, v2, pd = under
        out_t.append({"net": net, "l": "I2", "x0": v1[0], "y0": v1[1], "x1": v2[0], "y1": v2[1], "w": TW})
        out_t.append({"net": net, "l": "B", "x0": v2[0], "y0": v2[1], "x1": pd[0], "y1": pd[1], "w": TW})

# ---- 3. rip what is in the lane (B.Cu tracks and every via within clearance of the pair's copper), lay the pair, rejoin
lane_f = LineString([(t["x0"], t["y0"]) for t in out_t[:1]] + [(t["x1"], t["y1"]) for t in out_t if t["net"] == "/USB_DN"])
pair_geo = [LineString([(t["x0"], t["y0"]), (t["x1"], t["y1"])]).buffer(TW / 2) for t in out_t] + \
           [Point(v["x"], v["y"]).buffer(VIA[0] / 2) for v in out_v]
from shapely.ops import unary_union
pg = unary_union(pair_geo) if pair_geo else None
cl = E.CLR - 0.07 + 0.005                                   # the real 0.15 rule (+ a hair), not the grid's padded one
hit_t = [t for t in b.out_tracks if t["net"] not in ("/USB_DP", "/USB_DN") and t["l"] == "B"
         and LineString([(t["x0"], t["y0"]), (t["x1"], t["y1"])]).buffer(t["w"] / 2).distance(pg) < cl]
hit_v = [v for v in b.out_vias if v["net"] not in ("/USB_DP", "/USB_DN") and Point(v["x"], v["y"]).buffer(v["d"] / 2).distance(pg) < cl]
ripped = sorted({t["net"] for t in hit_t} | {v["net"] for v in hit_v})
print(f"in the lane: {len(hit_t)} track pieces, {len(hit_v)} vias of {ripped}", flush=True)
ids = {id(x) for x in hit_t + hit_v}
b.out_tracks = [t for t in b.out_tracks if id(t) not in ids]; b.out_vias = [v for v in b.out_vias if id(v) not in ids]
xs = [t[k] for t in hit_t for k in ("x0", "x1")] + [v["x"] for v in hit_v]
ys = [t[k] for t in hit_t for k in ("y0", "y1")] + [v["y"] for v in hit_v]
if xs:
    i0, j0, i1, j1 = b.window(min(xs), min(ys), max(xs), max(ys), 1.0)
    for l in E.LAYERS: b.grid[l][i0:i1, j0:j1] = b.hard[l][i0:i1, j0:j1]
    b._rebuild(min(xs), min(ys), max(xs), max(ys))
for t in out_t: b.out_tracks.append(t); b.add_track(t["l"], t["x0"], t["y0"], t["x1"], t["y1"], t["w"], t["net"])
for v in out_v: b.out_vias.append(v); b.add_via(v["x"], v["y"], v["d"], v["net"])
for v in out_v: b.return_via(v["x"], v["y"], rmax=1.2)
b.hard = {l: b.grid[l].copy() for l in E.LAYERS}          # the pair is fixed from here on
fails = []
for n in ripped:
    if n == "/GND": continue
    d, f = b.complete_net(n); print(f" {n:16s} pieces joined {d} failed {f}", flush=True)
    if f: fails.append(n)
if "/GND" in ripped:
    d, f = b.plane_drops("/GND", "GND"); print(f" /GND plane vias {d} failed {f}")
new_t = [t for t in b.out_tracks if id(t) not in orig_t]; new_v = [v for v in b.out_vias if id(v) not in orig_v]
gone_t = [t for i, t in orig_t.items() if i not in {id(x) for x in b.out_tracks}]
gone_v = [v for i, v in orig_v.items() if i not in {id(x) for x in b.out_vias}]
json.dump({"remove_tracks": gone_t, "remove_vias": gone_v, "tracks": new_t, "vias": new_v}, open(W + "usb_pair2.json", "w"))
print(f"usb pair 2: -{len(gone_t)} tracks -{len(gone_v)} vias, +{len(new_t)} tracks +{len(new_v)} vias; still open: {fails}")
