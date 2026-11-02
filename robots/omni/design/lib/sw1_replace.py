# Power switch v3 near 231 deg: local re-placement of the power corner round the switch (user, 2026-10-25). Runs
# place_v2.py's placer on the current placement (placement_v2.json) with
#   - SW1 as a fixed part: the shared C&K OS102011MA1QN1 / SK-12D07 footprint at ANGLE (slider tip r 40.3)
#   - only the power-corner parts free to move (power path, both converters, Q6 group), the rest fixed
# -> _place/placement_sw1.json (+ the angle) for draw_sw1_room.py and the apply step. Nothing is applied.
#   C:/Python312/python.exe design/lib/sw1_replace.py [iterations] [angle]
import sys, json, math
ITER = sys.argv[1] if len(sys.argv) > 1 else "120000"
ANGLE = float(sys.argv[2]) if len(sys.argv) > 2 else 233.0
sys.argv = [sys.argv[0], ITER]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
src = open(BB + "/design/lib/place_v2.py").read()
POWER = ["Q1", "Q2", "Q3", "Q6", "F1", "U1", "U3", "D1", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "C1", "C2",
         "U4", "L1", "C7", "C8", "C9", "C10", "R12", "R13", "U5", "L2", "C3", "C4", "C5", "C11", "C12", "C13", "C14", "C15",
         "R15", "R16"]
# start from the current placement; the switch's outline at ANGLE replaces the board map's
src = src.replace('placed = {r: list(v) for r, v in json.load(open(P + "placement.json")).items()}',
                  'placed = {r: list(v) for r, v in json.load(open(P + "placement_v2.json")).items()}')
src = src.replace('MOVE = sorted(r for r in placed if r not in FIXED and r not in STAY)',
                  'MOVE = sorted(r for r in placed if r not in FIXED and r not in STAY and r in POWER_SET)')
src = src.replace('out = {r: list(v) for r, v in placed.items()}', 'out = {r: list(v) for r, v in placed.items()}\nOUT_ANGLE = ANGLE')
src = src.replace('json.dump(out, open(P + "placement_v2.json", "w"), indent=0)',
                  'json.dump({"angle": ANGLE, "placement": out}, open(P + "placement_sw1.json", "w"), indent=0)')
src = src.replace('# ---- pins:', '''# ---- the switch at ANGLE (shared footprint: body+tabs 10.6 x 5.0, slider sweep 4.5 x 4.1, tip at r 40.3)
from shapely.ops import unary_union as _uu
_a = math.radians(ANGLE); _V = (math.cos(_a), math.sin(_a)); _U = (_V[1], -_V[0]); _c = ((40.3 - 6.5) * _V[0], (40.3 - 6.5) * _V[1])
_L = lambda x, y: (_c[0] + x * _U[0] + y * _V[0], _c[1] + x * _U[1] + y * _V[1])
_sw = _uu([Polygon([_L(-5.3, -2.5), _L(5.3, -2.5), _L(5.3, 2.5), _L(-5.3, 2.5)]), Polygon([_L(-2.25, 2.4), _L(2.25, 2.4), _L(2.25, 6.5), _L(-2.25, 6.5)])])
bmap["SW1"]["crt"] = list(_sw.exterior.coords)
# ---- pins:''')
POWER_SET = set(POWER)
exec(compile(src, "place_v2(sw1)", "exec"))
