# Connector re-placement planner (user, 2026-10-26): each cable connector goes next to what its cable plugs into, with
# room for the plug and a clear run for the cable. Bottom-side connectors only (the problem ones). For each connector
# and each spot within REACH of its target, both a vertical (BM..B) and a side-entry (SM..B) JST-SH are tried:
#   - body clear of every other bottom-side courtyard (connectors being moved excepted), on the board, out of the
#     MCAD bottom keep-outs
#   - vertical: 8.5 mm free under the whole body (plug + cable bend), and not over a wheel (user: side entry there)
#   - side entry: 3.6 mm under the body (2.95 tall + 0.65) and under a 7 mm insertion lane in front of it
#   - the cable from the plug to the target: never over a wheel or roller; 2 mm free until the last 6 mm (it drops
#     down to the motor's end / the reader there)
#   - plug access: side-entry lane empty of parts; vertical: 1.5 mm finger ring clear of tall parts
# Score = cable length (+2 mm for a side-entry, vertical is easier to plug). -> _place/connector_plan.json
#   C:/Python312/python.exe design/lib/plan_connectors.py [reach_mm] [refs ...]
import json, math
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.prepared import prep
from matplotlib.path import Path as MPath
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
g = json.load(open(P + "board_geom.json")); F = {f["ref"]: f for f in g["fps"]}
fps = json.load(open(P + "jst_fps.json"))
d = np.load(P + "free_height.npz"); names = json.load(open(P + "free_height_names.json"))
RES, H = float(d["res"]), float(d["half"]); BEL, LAB = d["below"], d["lab_b"]
N = BEL.shape[0]
wheelish = np.array(["Wheel" in n or "Roller" in n for n in names] + [False])
OVER_WHEEL = wheelish[LAB] & (BEL < 20)
U = lambda ps: unary_union([Polygon(p).buffer(0) for p in ps if len(p) > 2]) if ps else Polygon()
# what each connector's cable plugs into (robot frame)
NFC_J1 = (-8.5 - 11.2 * math.cos(math.radians(117)), 19.5 - 11.2 * math.sin(math.radians(117)))   # the reader's J1 (pointing up)
CON = {"J14": ("Motor 1", 2, (-7.73, 3.95)), "J15": ("Motor 2", 2, (0.44, -8.67)), "J16": ("Motor 3", 2, (7.29, 4.72)),
       "J20": ("NFC reader", 8, NFC_J1), "J17": ("Underglow", 3, (0.0, -1.2))}     # J17: the floor PCB's J2 (robot centre, under the floor plate)
import sys
REACH, STEP = (float(sys.argv[1]) if len(sys.argv) > 1 else 14.0), 0.5
ONLY = set(sys.argv[2:])
MOVING = set(CON)
FPN = json.load(open(P + "fp_names.json"))
import re
LOW = re.compile(r"^(R|C|L|LED)_(0201|0402|0603)_")
import os
SMALL = 30.0                                      # LOCAL=1: parts under this courtyard area (mm2) may be nudged aside later
LOCAL = os.environ.get("LOCAL") == "1"
area = lambda f: U(f["crtB"]).area
smallp = [f for f in g["fps"] if f["ref"] not in MOVING and f["crtB"] and area(f) < SMALL and f["ref"][0] in "RC" and LOW.match(FPN.get(f["ref"], ""))] if LOCAL else []   # only small R / C get nudged
SMALLSET = {f["ref"] for f in smallp}
small_u = unary_union([U(f["crtB"]) for f in smallp]) if smallp else Polygon()
others = unary_union([U(f["crtB"]) for f in g["fps"] if f["ref"] not in MOVING and f["crtB"] and f["ref"] not in SMALLSET])
FULL = os.environ.get("FULL") == "1"              # FULL=1 (full re-place): only the parts that never move are obstacles
NEVER = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6", "J18", "J19", "J21", "J22", "SW2", "SW3", "LED1", "BZ1"}
if FULL:
    others = unary_union([U(f["crtB"]) for f in g["fps"] if f["crtB"] and (f["ref"] in NEVER or f["ref"].startswith("H"))])
    # through-hole pins stick out under the board (J18 servo header, sockets ...): obstacles for bodies and plug lanes
    others = others.union(unary_union([Point(p["pos"]).buffer(max(p["size"]) / 2 + 0.3) for f in g["fps"] if f["ref"] not in MOVING
                                       for p in f["pads"] if p["tht"]]))
# plug access (user, 2026-10-26: room to get the plug in, not blocked by tall parts): a side-entry plug lane must be
# empty of every part; round a vertical one a 1.5 mm finger ring clear of anything taller than ~1 mm (0201-0603 R / C,
# 0402 LEDs are low)
FPN = json.load(open(P + "fp_names.json"))
import re
LOW = re.compile(r"^(R|C|L|LED)_(0201|0402|0603)_")
tall = unary_union([U(f["crtB"]) for f in g["fps"] if f["ref"] not in MOVING and f["ref"] not in SMALLSET and f["crtB"] and not LOW.match(FPN.get(f["ref"], ""))])
if FULL: tall = others
tall_p = prep(tall); others_raw_p = prep(others)
others_p = prep(others.buffer(0.2))
keep = prep(unary_union([U(z["poly"]) for z in g["rules"] if "B.Cu" in z["layers"]]))
board = prep(Point(0, 0).buffer(38.6, 128).difference(Point(41.5, 0).buffer(18.9, 128)))
def cells(poly):
    x0, y0, x1, y1 = poly.bounds
    i0, i1 = int((x0 + H) / RES), int((x1 + H) / RES) + 1; j0, j1 = int((y0 + H) / RES), int((y1 + H) / RES) + 1
    i0, j0 = max(i0, 0), max(j0, 0); i1, j1 = min(i1, N), min(j1, N)
    xs = -H + (np.arange(i0, i1) + 0.5) * RES; ys = -H + (np.arange(j0, j1) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    m = MPath(np.asarray(poly.exterior.coords)).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
    return (slice(i0, i1), slice(j0, j1), m)
def min_h(poly):
    si, sj, m = cells(poly); a = BEL[si, sj][m]; return a.min() if a.size else 0
def any_wheel(poly):
    si, sj, m = cells(poly); return bool(OVER_WHEEL[si, sj][m].any())
DROP = {"J16": 99.0}                                # motor 3's end is boxed in by the module and the solenoid: its cable runs
REACH_REF = {"J16": 30.0}                          # under the module to a spot further out (user, 2026-10-26)
def path_ok(a, b_, drop=6.0):
    ln = LineString([a, b_]); n = max(2, int(ln.length / 0.5))
    for k in range(n + 1):
        p = ln.interpolate(k / n, normalized=True)
        i, j = int((p.x + H) / RES), int((p.y + H) / RES)
        if not (0 <= i < N and 0 <= j < N): return False
        if OVER_WHEEL[i, j]: return False                              # never over a wheel or roller
        if p.distance(Point(b_)) > drop and BEL[i, j] < 2.0: return False # room for the wire, except where it drops to its target
    return True
def place(poly, x, y, rot):                       # footprint coords (KiCad: y down) -> robot frame, turned rot deg CCW
    p = affinity.scale(poly, 1, -1, origin=(0, 0)); p = affinity.rotate(p, rot, origin=(0, 0)); return affinity.translate(p, x, y)
plan = {}
for ref, (what, n, T) in CON.items():
    if ONLY and ref not in ONLY: continue
    best = []
    RR = REACH_REF.get(ref, REACH)
    for kind in ("vertical", "side"):
        fn = f"JST_SH_{'BM' if kind == 'vertical' else 'SM'}0{n}B-SRSS-TB_1x0{n}-1MP_P1.00mm_{'Vertical' if kind == 'vertical' else 'Horizontal'}"
        body0 = Polygon(fps[fn]["crt"]).buffer(0)
        w = body0.bounds[2]
        lane0 = box(-w + 0.4, 3.27, w - 0.4, 3.27 + 7.0)              # side entry: plug + fingers in front (+y, KiCad)
        for dx in np.arange(-RR, RR + 1e-6, STEP):
            for dy in np.arange(-RR, RR + 1e-6, STEP):
                x, y = T[0] + dx, T[1] + dy
                if math.hypot(dx, dy) > RR or not board.contains(Point(x, y)): continue
                for rot in range(0, 360, 45):
                    body = place(body0, x, y, rot)
                    if not board.contains(body) or others_p.intersects(body) or keep.intersects(body): continue
                    if kind == "vertical":
                        if min_h(body) < 8.5 or any_wheel(body): continue
                        if tall_p.intersects(body.buffer(1.5)): continue          # finger room
                        exit_ = (x, y)
                    else:
                        lane = place(lane0, x, y, rot)
                        if min_h(body) < 3.6 or min_h(lane) < 3.6: continue
                        if others_raw_p.intersects(lane): continue                 # the plug lane is empty
                        exit_ = tuple(place(Point(0, 3.27 + 4.0), x, y, rot).coords[0])
                    if not path_ok(exit_, T, DROP.get(ref, 6.0)): continue
                    L = math.dist(exit_, T) + (2.0 if kind == "side" else 0.0)
                    if LOCAL:                                                    # each mm2 of small parts to push aside costs 0.5 mm
                        zone = body.buffer(1.5 if kind == "vertical" else 0.3)
                        if kind == "side": zone = zone.union(lane)
                        L += 0.5 * zone.intersection(small_u).area
                    best.append((round(float(L), 2), kind, float(round(x, 2)), float(round(y, 2)), rot, fn))
        print(ref, kind, "candidates so far", len(best), flush=True)
    best.sort()
    plan[ref] = {"what": what, "target": T, "now": F[ref]["pos"], "options": best[:400]}
    print(ref, what, "->", best[:3] if best else "NO SPOT")
try: old = json.load(open(P + ("connector_plan_full.json" if FULL else "connector_plan_local.json" if LOCAL else "connector_plan.json")))
except FileNotFoundError: old = {}
old.update(plan); json.dump(old, open(P + ("connector_plan_full.json" if FULL else "connector_plan_local.json" if LOCAL else "connector_plan.json"), "w"), indent=1)
