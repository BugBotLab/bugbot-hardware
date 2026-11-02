# Floor plan v2 (6-layer board): re-places the movable parts by where their wires go. Crossings are free on 6 layers, so
# the placer only shortens connections: total pin-to-pin length (half-perimeter per net, the planes' GND / VSYS left out)
# with the module's pads and the fixed connectors as anchors, plus
#   - each small part attracted to its chip (decoupling, charge pump, pull-ups, feedback), on EITHER side: directly
#     behind the chip on the other side is allowed and cheap (vias may sit in pads)
#   - switching parts (converters' inductors / chips, kicker boost, motor drivers) kept away from the IMU and sense parts
# Hard rules, as floor plan v1: inside the board (0.8 mm in), 0.5 mm between courtyards (1 mm round the bigger chips),
# the module's escape ring (1.5 mm now: its pins may drop straight into vias), every style's keep-outs and height limits
# per side; through-hole parts block both sides. Connectors, buttons, the status LED and the battery stay where they are.
# Simulated annealing from the current placement (moves: shift, turn, flip side, swap twins).
# Reads _place/{shapes.json, free_area.pkl, board_map.json, placement.json}, _route/nets.json, place_floorplan's GROUPS;
# writes _place/placement_v2.json + floorplan_v2.png for approval. Nothing is applied.
#   C:/Python312/python.exe design/lib/place_v2.py [iterations]
import json, pickle, math, random, re, sys, time
from shapely.geometry import Polygon, Point
from shapely import affinity
from shapely.strtree import STRtree

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
RT = BB + "/design/schematics/Main/_route/"
ITER = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
random.seed(7)
shapes = json.load(open(P + "shapes.json"))
free = pickle.load(open(P + "free_area.pkl", "rb"))
placed = {r: list(v) for r, v in json.load(open(P + "placement.json")).items()}
bmap = {f["ref"]: f for f in json.load(open(P + "board_map.json"))["fps"]}
nets = {n: p for g in json.load(open(RT + "nets.json")).values() for n, p in g.items()}
src = open(BB + "/design/lib/place_floorplan.py").read()
GROUPS = eval(src[src.index("GROUPS = [") + 9:src.index("]\nFIXED") + 1])
SIDE = {"top": "F", "bottom": "B"}
FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"}
STAY = {r for r in placed if re.match(r"(J|SW|LED)\d", r)} | {"BZ1"}      # cable / finger / eye positions: not moved
GAP, BIG_GAP, RING = 0.5, 1.0, 1.5
BIG = {"U4", "U5", "U7", "U8", "U9", "U11"}
margin = lambda r: BIG_GAP if r in BIG else GAP
board = Point(0, 0).buffer(40.6 - 0.8, 128).difference(Point(41.5, 0).buffer(18.6 + 0.8, 128))
hard = {SIDE[k]: board.difference(v[0]).buffer(0) for k, v in free.items()}
limits = {SIDE[k]: v[1] for k, v in free.items()}
HEIGHT = [("CP_Elec_10x10.5", 10.6), ("PinSocket_2x06", 8.6), ("PinHeader_1x03", 8.6), ("JST_PH", 6.0), ("JST_SH_BM", 4.3),
          ("JST_SH_SM", 3.0), ("ZX-QC4545", 4.3), ("MLT-8530", 3.0), ("SWPA4030", 3.0), ("SWPA4020", 2.1), ("D_SMB", 2.4),
          ("D_SMA", 2.3), ("C_1206", 1.8), ("C_0805", 1.35), ("R_1206", 0.7), ("R_0805", 0.6), ("TSSOP", 1.2), ("SOT-23", 1.45),
          ("SOT-363", 1.1), ("SOT-563", 0.6), ("LGA-14", 0.9), ("VSON", 1.0), ("LED_0603", 0.8), ("D_SOD-123", 1.35),
          ("Fuse_1206", 0.9), ("0603", 0.9), ("0402", 0.55)]
height = lambda fp: next((h for k, h in HEIGHT if k in fp), 3.0)
THT = {r for r, s in shapes.items() if s["tht"] and "ThermalVias" not in s["fp"]}
MOVE = sorted(r for r in placed if r not in FIXED and r not in STAY)
# only resistors and capacitors may change side (to sit behind their chip); chips, inductors, diodes and transistors keep
# theirs, so no switching loop (converter chip - inductor - caps) is split across the board. C34 (10 mm tall) stays.
# converter / boost caps stay on their chip's side: they close the switching loops (no vias in a hot loop)
HOT = {"U4", "U5", "U11"}
PASSIVE = [r for r in MOVE if re.match(r"[RC]\d", r)]
FLIP_OK = {r for r in MOVE if re.match(r"[RC]\d", r) and r != "C34" and r not in THT}

# ---- pins: offset of each pad from its part, in the part's own frame (unturned, top side)
def rot(x, y, a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a)); return x * c - y * s, x * s + y * c
pins = {}                                            # ref -> [(net, lx, ly)]
fixed_pin = {}                                       # net -> [xy] of pins on fixed parts
for n, pads in nets.items():
    if n in ("/GND", "/VSYS"): continue
    for p in pads:
        r = p["ref"]
        if r in placed and r not in FIXED:
            px, py, a, side, _ = placed[r]
            ox, oy = rot(p["xy"][0] - px, p["xy"][1] - py, -a)
            if side == "B": oy = -oy
            pins.setdefault(r, []).append((n, ox, oy))
        else:
            fixed_pin.setdefault(n, []).append(tuple(p["xy"]))
def pin_xy(r, st):
    x, y, a, side = st
    for n, ox, oy in pins.get(r, []):
        if side == "B": oy = -oy
        dx, dy = rot(ox, oy, a); yield n, x + dx, y + dy
chip_pins = {}                                       # (fixed chip, net) -> its pin positions (the module's 3V3 pads ...)
for n, pads in nets.items():
    for p in pads:
        if p["ref"] in FIXED: chip_pins.setdefault((p["ref"], n), []).append(tuple(p["xy"]))
NET_W = {n: (0.15 if n in ("/3V3", "/5V") else 1.0) for n in nets}       # rails: trunks / planes, little pull

# ---- groups: each small part's chip (from floor plan v1's "REF@ANCHOR")
anchor = {}
for _, _, parts in GROUPS:
    for it in parts:
        r, _, a = it.partition("@")
        if a: anchor[r] = a
anchor.update({"C16": "U6", "C17": "U6", "C18": "U6", "C41": "J6", "C42": "J6",     # decoupling with no chip in v1's list
               "R17": "U6", "R18": "U6", "R19": "U6", "R20": "U6", "R21": "U6", "R45": "U6", "R46": "J6"})
chip_of = {}
for r, a in anchor.items():
    while a in anchor and not re.match(r"(U|J)\d", a): a = anchor[a]
    chip_of[r] = a
SWITCHING = {"L1", "L2", "L3", "U4", "U5", "U11", "D2", "U8", "U9"}
QUIET = {"U15", "C39", "C40", "R6", "R7", "C2", "R36", "R37", "C35", "R30", "C29", "U10"}
FLIP_OK -= {r for r, ch in chip_of.items() if ch in HOT}

# ---- state and geometry
state = {r: (placed[r][0], placed[r][1], int(placed[r][2]), placed[r][3]) for r in MOVE}
def outline(r, st=None):
    if r in FIXED: return Polygon(bmap[r]["crt"]).buffer(0)
    x, y, a, side = st or state.get(r) or (placed[r][0], placed[r][1], int(placed[r][2]), placed[r][3])
    return affinity.translate(Polygon(shapes[r]["v"][f"{side}{a}"]), x, y)
def sides_of(r, side):
    return {"F", "B"} if r in THT else {side}
static = {"F": [], "B": []}                          # fixed / stay parts: (geom, margin, ref)
for r in FIXED | STAY:
    side = shapes[r]["placed"][3] if r in FIXED else placed[r][3]
    g = outline(r)
    if r == "BT1":
        for px, py, rr in ((-23.8, -18.91, 1.6), (-23.8, 18.91, 1.6), (-31.9, -18.91, 1.3)):
            static["B"].append((Point(px, py).buffer(rr), GAP, r))
        static["F"].append((g, GAP, r)); continue
    for s in sides_of(r, side) | ({"F", "B"} if r in ("SW1", "J1") else set()):
        static[s].append((g, GAP, r))
    if r == "U6": static["B"].append((g.buffer(RING - 0.25), 0.0, r))
stat_tree = {s: STRtree([g for g, _, _ in static[s]]) for s in "FB"}

def legal_hard(r, st):
    """board, keep-outs, height limits and the parts that never move"""
    x, y, a, side = st
    g = outline(r, st)
    if not board.contains(g): return False
    h = height(shapes[r]["fp"]); m = margin(r)
    for s in sides_of(r, side):
        if g.buffer(0.1).intersects(hard[s]): return False
        for mh, poly in limits[s].items():
            if h + 0.3 > mh and g.intersects(poly) and g.intersection(poly).area > 0.01: return False
        gb = g.buffer(max(m, BIG_GAP) + 0.01)
        for k in stat_tree[s].query(gb):
            o, mo, _ = static[s][k]
            if g.distance(o) < max(m, mo) - 1e-6: return False
    return True


def pair_gap(r, o):
    """0.3 mm between a chip and its own small parts (tight decoupling / switching loops), else the routing gaps"""
    if chip_of.get(r) == o or chip_of.get(o) == r: return 0.3
    return max(margin(r), margin(o))


def overlap_of(r, geoms, skip=()):
    """how much this part crowds the other movable parts: area inside each other's gap-grown outlines (mm2)"""
    g, side = geoms[r]; cx, cy = g.centroid.x, g.centroid.y
    tot = 0.0
    for o in MOVE:
        if o == r or o in skip: continue
        og, oside = geoms[o]
        if not (sides_of(r, side) & sides_of(o, oside)): continue
        if abs(og.centroid.x - cx) > 14 or abs(og.centroid.y - cy) > 14: continue
        m = pair_gap(r, o) / 2
        if g.distance(og) < 2 * m - 0.01:
            tot += g.buffer(m).intersection(og.buffer(m)).area + 0.05
    return tot


def legal(r, st, geoms):
    return legal_hard(r, st) and overlap_of(r, geoms) == 0


def cost_parts():
    """total cost of the current state"""
    pos = {}
    for r in MOVE:
        for n, px, py in pin_xy(r, state[r]): pos.setdefault(n, []).append((px, py))
    c = 0.0
    for n, pts in pos.items():
        pts = pts + fixed_pin.get(n, [])
        if len(pts) < 2: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        c += NET_W.get(n, 1.0) * ((max(xs) - min(xs)) + (max(ys) - min(ys)))
    for r in PASSIVE:                                 # each resistor / cap pin near the nearest other pin of its net
        for n, px, py in pin_xy(r, state[r]):
            if n in ("/3V3", "/5V"): continue
            others = [q for q in pos.get(n, []) + fixed_pin.get(n, []) if abs(q[0] - px) + abs(q[1] - py) > 1e-6]
            if others: c += 0.6 * min(abs(q[0] - px) + abs(q[1] - py) for q in others)
    for r, chip in chip_of.items():                   # small part -> the chip pin it serves (nearest pin on a shared net)
        if r not in state: continue
        mine = {n: (px, py) for n, px, py in pin_xy(r, state[r])}
        if chip in state: theirs = [(n, px, py) for n, px, py in pin_xy(chip, state[chip])]
        else: theirs = [(n, xy[0], xy[1]) for n in mine for xy in chip_pins.get((chip, n), [])]
        ds = [math.hypot(mine[n][0] - px, mine[n][1] - py) for n, px, py in theirs if n in mine]
        if ds: c += (6.0 if chip in HOT else 2.0) * min(ds)      # converter loop parts pulled hardest
        elif chip in state or chip in FIXED:
            cx, cy = (state[chip][0], state[chip][1]) if chip in state else tuple(bmap[chip]["pos"])
            c += (6.0 if chip in HOT else 1.5) * math.hypot(state[r][0] - cx, state[r][1] - cy)   # (VSYS caps: no shared pin net)
    for a in SWITCHING & set(state):
        for q in QUIET & set(state):
            d = math.hypot(state[a][0] - state[q][0], state[a][1] - state[q][1])
            if d < 8: c += 12 * (8 - d)
    return c

geoms = {r: (outline(r), state[r][3]) for r in MOVE}
bad0 = [r for r in MOVE if not legal(r, state[r], geoms)]
print("parts that move:", len(MOVE), "| not legal at the start (allowed to stay until moved):", bad0)
c0 = cost = cost_parts()
T0, T1 = 6.0, 0.05
t_start = time.time()
twins = {}
for r in MOVE: twins.setdefault(shapes[r]["fp"], []).append(r)
sats = {}
for r0, ch in chip_of.items():
    if r0 in state and ch in state: sats.setdefault(ch, []).append(r0)
ov = sum(overlap_of(r, geoms) for r in MOVE) / 2
wire = cost
best = None
for it in range(ITER):
    frac = it / ITER
    T = T0 * (T1 / T0) ** frac
    W_OV = 2.0 * (400.0 ** frac)                     # overlap weight: small early (parts may pass each other), huge at the end
    r = random.choice(MOVE)
    x, y, a, side = state[r]
    mv = random.random()
    sig = 0.3 + 6.0 * (1 - frac)
    if mv < 0.15 and r in sats:                     # a chip and its small parts together
        dx, dy = random.gauss(0, sig * 1.5), random.gauss(0, sig * 1.5)
        new = {k: (state[k][0] + dx, state[k][1] + dy, state[k][2], state[k][3]) for k in [r] + sats[r]}
    elif mv < 0.6: new = {r: (x + random.gauss(0, sig), y + random.gauss(0, sig), a, side)}
    elif mv < 0.75: new = {r: (x, y, (a + random.choice((90, 180, 270))) % 360, side)}
    elif mv < 0.9:
        if r not in FLIP_OK: continue
        new = {r: (x, y, a, "B" if side == "F" else "F")}
    else:
        tw = [o for o in twins[shapes[r]["fp"]] if o != r]
        if not tw: continue
        o = random.choice(tw)
        if state[o][3] != side and not (r in FLIP_OK and o in FLIP_OK): continue     # a swap must not break a side lock
        new = {r: (state[o][0], state[o][1], state[o][2], state[o][3]), o: (x, y, a, side)}
    new = {k: (round(v[0] / 0.05) * 0.05, round(v[1] / 0.05) * 0.05, v[2], v[3]) for k, v in new.items()}
    if not all(legal_hard(k, v) for k, v in new.items()): continue
    old = {k: state[k] for k in new}; oldg = {k: geoms[k] for k in new}
    ov_before = sum(overlap_of(k, geoms, skip=list(new)[:i]) for i, k in enumerate(new))
    for k, v in new.items(): state[k] = v; geoms[k] = (outline(k, v), v[3])
    ov_after = sum(overlap_of(k, geoms, skip=list(new)[:i]) for i, k in enumerate(new))
    w2 = cost_parts()
    d = (w2 - wire) + W_OV * (ov_after - ov_before)
    if d <= 0 or random.random() < math.exp(-d / T):
        wire, ov = w2, ov + ov_after - ov_before
        if ov < 1e-6 and (best is None or wire < best[0]): best = (wire, dict(state))
    else:
        for k in new: state[k] = old[k]; geoms[k] = oldg[k]
    if it % 10000 == 0:
        print(f" {it:6d}  T {T:5.2f}  wire {wire:8.1f}  overlap {ov:7.2f} mm2  best legal {best[0] if best else float('nan'):8.1f}  {time.time() - t_start:5.0f} s", flush=True)
if best is None:                                     # legalise: parts still crowding move to the nearest legal spot
    for r in sorted(MOVE, key=lambda q: -outline(q).area):
        if overlap_of(r, geoms) == 0: continue
        x, y, a, side = state[r]; done = False
        for rad in [k * 0.25 for k in range(1, 41)]:
            for t in range(0, 360, 15):
                st = (round((x + rad * math.cos(math.radians(t))) / 0.05) * 0.05, round((y + rad * math.sin(math.radians(t))) / 0.05) * 0.05, a, side)
                if not legal_hard(r, st): continue
                keep = (state[r], geoms[r]); state[r] = st; geoms[r] = (outline(r, st), side)
                if overlap_of(r, geoms) == 0: done = True; break
                state[r], geoms[r] = keep
            if done: break
        print(f" legalised {r}: {'moved' if done else 'NO LEGAL SPOT'}")
    best = (cost_parts(), dict(state))
state = best[1]
print(f"cost {c0:.0f} -> {best[0]:.0f}  ({time.time() - t_start:.0f} s)")
out = {r: list(v) for r, v in placed.items()}
for r, (x, y, a, side) in state.items(): out[r] = [round(x, 2), round(y, 2), a, side, 0]
json.dump(out, open(P + "placement_v2.json", "w"), indent=0)
moved = {r: (placed[r][3] != state[r][3], round(math.hypot(state[r][0] - placed[r][0], state[r][1] - placed[r][1]), 1)) for r in state}
print("flipped side:", sorted(r for r, (f, d) in moved.items() if f))
print("moved > 3 mm:", sorted((r, d) for r, (f, d) in moved.items() if d > 3))
