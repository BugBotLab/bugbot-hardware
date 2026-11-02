# Floor plan v3 (user, 2026-10-26: full re-place with the cable connectors first and their plug rules built in): runs
# place_v2.py's placer on the board as it is now, with
#   - J14 / J15 / J16 / J17 / J20 fixed at their planned spots (_place/connector_choice_full.json: next to what each
#     cable plugs into, design/lib/plan_connectors.py FULL=1 + draw_connector_plan.py)
#   - a side-entry connector's plug lane kept empty of every part; round a vertical one a 1.5 mm finger ring that no
#     part taller than 1 mm may enter
#   - every other part free (the parts that never move stay: module, USB-C, switch, sockets, buttons, LED, buzzer, battery)
# -> _place/placement_v3.json (+ the connector choice) for the 2D plan and place_apply.py. Nothing is applied.
#   C:/Python312/python.exe design/lib/place_v3.py [iterations]
import sys, json, math
ITER = sys.argv[1] if len(sys.argv) > 1 else "150000"
sys.argv = [sys.argv[0], ITER]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
src = open(BB + "/design/lib/place_v2.py").read()
ch = json.load(open(P + "connector_choice_full.json"))["choice"]
fpsj = json.load(open(P + "jst_fps.json"))
# start from the board as it is (shapes.json carries every part's current spot)
src = src.replace('placed = {r: list(v) for r, v in json.load(open(P + "placement.json")).items()}',
                  'placed = {r: [s["placed"][0], s["placed"][1], int(round(s["placed"][2] / 90.0) * 90) % 360, s["placed"][3], 0] for r, s in shapes.items()}')
src = src.replace('FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"}',
                  'FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"} | set(CH)')
src = src.replace('json.dump(out, open(P + "placement_v2.json", "w"), indent=0)',
                  'json.dump(out, open(P + "placement_v3.json", "w"), indent=0)')
# the connectors' outlines and pads where the plan puts them
src = src.replace('''def outline(r, st=None):
    if r in FIXED: return Polygon(bmap[r]["crt"]).buffer(0)''', '''def outline(r, st=None):
    if r in CH: return CH_BODY[r]
    if r in FIXED: return Polygon(bmap[r]["crt"]).buffer(0)''')
src = src.replace('''# ---- pins: offset of each pad''', '''# ---- the planned connectors (robot frame): body, pads, plug lane / finger ring
from shapely.geometry import box as _box
def _place(poly, x, y, a):
    p = affinity.scale(poly, 1, -1, origin=(0, 0)); p = affinity.rotate(p, a, origin=(0, 0)); return affinity.translate(p, x, y)
CH_BODY, CH_ZONE, CH_PAD = {}, {}, {}
for r, (L, kind, x, y, a, fn) in CH.items():
    b0 = Polygon(fpsj[fn]["crt"]).buffer(0); w = b0.bounds[2]
    CH_BODY[r] = _place(b0, x, y, a)
    CH_ZONE[r] = (_place(_box(-w + 0.4, 3.27, w - 0.4, 10.27), x, y, a), "all") if kind == "side" else (CH_BODY[r].buffer(1.5), "tall")
    CH_PAD[r] = {n: _place(Point(px, py), x, y, a).coords[0] for n, px, py in fpsj[fn]["pads"]}
for n, pads in nets.items():                         # the connectors' pads move with them
    for p in pads:
        if p["ref"] in CH and p["pad"] in CH_PAD[p["ref"]]: p["xy"] = list(CH_PAD[p["ref"]][p["pad"]])
for r in CH: placed[r] = [CH[r][2], CH[r][3], 0, "B", 0]
# ---- pins: offset of each pad''')
# plug lanes and finger rings as hard rules for the movable parts (bottom side)
src = src.replace('''    return True


def pair_gap(r, o):''', '''    for zr, (zg, who) in CH_ZONE.items():
        if "B" in sides_of(r, side) and (who == "all" or height(shapes[r]["fp"]) > 1.0) and g.intersects(zg): return False
    return True


def pair_gap(r, o):''')
src = src.replace("import json, pickle, math, random, re, sys, time", "import json, pickle, math, random, re, sys, time\nCH = json.load(open(BB + "/design/schematics/Main/_place/connector_choice_full.json"))['choice']\nfpsj = json.load(open(BB + "/design/schematics/Main/_place/jst_fps.json"))")
# a wider last-resort legaliser: up to 30 mm away, any turn (the v2 one looked 10 mm round the same turn); it always runs,
# from the best legal state if there was one
OLD_LOOP = ("        for rad in [k * 0.25 for k in range(1, 41)]:\n            for t in range(0, 360, 15):\n"
            "                st = (round((x + rad * math.cos(math.radians(t))) / 0.05) * 0.05, round((y + rad * math.sin(math.radians(t))) / 0.05) * 0.05, a, side)")
NEW_LOOP = ("        for rad in [k * 0.25 for k in range(1, 121)]:\n"
            "            for t, a2 in [(t, a2) for t in range(0, 360, 15) for a2 in (a, (a + 90) % 360, (a + 180) % 360, (a + 270) % 360)]:\n"
            "                st = (round((x + rad * math.cos(math.radians(t))) / 0.05) * 0.05, round((y + rad * math.sin(math.radians(t))) / 0.05) * 0.05, a2, side)")
assert OLD_LOOP in src
src = src.replace(OLD_LOOP, NEW_LOOP)
OLD_IF = "if best is None:                                     # legalise"
assert OLD_IF in src
src = src.replace(OLD_IF, "if True:\n    if best is not None:\n        state.update(best[1]); geoms.update({r: (outline(r), state[r][3]) for r in MOVE})\n    # legalise")
# a part still inside a plug lane / finger ring (it started there) costs a lot, so the placer pushes it out
OLD_RET = "            if d < 8: c += 12 * (8 - d)\n    return c"
assert OLD_RET in src
src = src.replace(OLD_RET, "            if d < 8: c += 12 * (8 - d)\n    for _r in MOVE:\n        _x, _y = state[_r][0], state[_r][1]\n        for _zg, _who, (_x0, _y0, _x1, _y1) in CH_ZB:\n            if _x < _x0 - 6 or _x > _x1 + 6 or _y < _y0 - 6 or _y > _y1 + 6: continue\n            if 'B' in sides_of(_r, state[_r][3]) and (_who == 'all' or height(shapes[_r]['fp']) > 1.0):\n                _g = outline(_r)\n                if _g.intersects(_zg): c += 300.0 + 100.0 * _g.intersection(_zg).area\n    return c")
src = src.replace("# ---- pins: offset of each pad", "CH_ZB = [(z, w, z.bounds) for z, w in CH_ZONE.values()]\n# ---- pins: offset of each pad", 1)
# ... and it also moves parts that break a hard rule (inside a connector zone, a keep-out), not only crowding ones
OLD_SKIP = "        if overlap_of(r, geoms) == 0: continue"
assert OLD_SKIP in src
src = src.replace(OLD_SKIP, "        if overlap_of(r, geoms) == 0 and legal_hard(r, state[r]): continue")
import os
if os.environ.get("REFINE") == "1":               # refine a legal v3 placement: start there, cool, never allow overlap
    src = src.replace("geoms = {r: (outline(r), state[r][3]) for r in MOVE}",
                      "_v3 = json.load(open(P + 'placement_v3_legal1.json'))\n"
                      "for _r in MOVE: state[_r] = (_v3[_r][0], _v3[_r][1], int(_v3[_r][2]), _v3[_r][3])\n"
                      "geoms = {r: (outline(r), state[r][3]) for r in MOVE}", 1)
    src = src.replace("T0, T1 = 6.0, 0.05", "T0, T1 = " + os.environ.get("T0", "1.5") + ", 0.02")
    if os.environ.get("FOCUS"):                   # FOCUS=U7:15 -> only the parts within 15 mm of U7 move (a local reshuffle)
        _f, _rad = os.environ["FOCUS"].split(":")
        src = src.replace("geoms = {r: (outline(r), state[r][3]) for r in MOVE}",
                          "geoms = {r: (outline(r), state[r][3]) for r in MOVE}\n"
                          f"MOVE = [r for r in MOVE if math.hypot(state[r][0] - state['{_f}'][0], state[r][1] - state['{_f}'][1]) <= {_rad}]\n"
                          "print('focus: moving', len(MOVE), 'parts')", 1)
    src = src.replace("    W_OV = 2.0 * (400.0 ** frac)", "    W_OV = float(os.environ.get('W_OV', '5000')) * (1.0 if os.environ.get('W_OV') is None else (400.0 ** frac))")
    src = src.replace("    sig = 0.3 + 6.0 * (1 - frac)", "    sig = 0.2 + 3.0 * (1 - frac)")
# the motor drivers' thermal pad has copper and vias on BOTH sides: nothing may sit behind them on the other side
# (2026-10-26: C23 / C26 landed on it); and their own small parts keep 1.4 mm off them, where the router puts the pins'
# escape stubs (C24 shorted to one)
OLD_THT = 'THT = {r for r, s in shapes.items() if s["tht"] and "ThermalVias" not in s["fp"]}'
assert OLD_THT in src
# (not by making U8 / U9 through-hole: that also held them to the top-side keep-outs and the battery holder)
OLD_LH_END = "    for zr, (zg, who) in CH_ZONE.items():"
assert OLD_LH_END in src
src = src.replace(OLD_LH_END, "    if 'geoms' in globals():\n"
                              "        _behind = [q for q in ('U8', 'U9') if q != r and q in geoms]\n"
                              "        if side == 'F' and r not in THT and any(g.intersects(geoms[q][0]) for q in _behind): return False\n"
                              "        if r in ('U8', 'U9') and any(geoms[o][1] == 'F' and o not in THT and g.intersects(geoms[o][0]) for o in geoms if o != r): return False\n"
                              + OLD_LH_END, 1)
OLD_PG = "    if chip_of.get(r) == o or chip_of.get(o) == r: return 0.3"
assert OLD_PG in src
NEW_PG = "    if (chip_of.get(r) == o and o in ('U8', 'U9')) or (chip_of.get(o) == r and r in ('U8', 'U9')): return 1.4\n"
src = src.replace(OLD_PG, NEW_PG + OLD_PG)
exec(compile(src, "place_v2(v3)", "exec"))
