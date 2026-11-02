# NFC antenna as a standard 1.6 mm PCB under the floor (approved 2D: mech/freecad/sketches/nfc_floor_pcb.png).
#   C:/Python312/python.exe design/lib/nfc_floor_geom.py     (needs shapely; writes design/schematics/NFCfloor/floor_geom.json)
# then make_nfc_floor.py builds the KiCad board from it. Robot frame, mm, looking down; top copper faces the floor.
#   outline  the floor outline (flush), the three wheel windows and the ball notch cut out, 3 holes for the clamp screws
#   loop     3 turns of 0.18 / 0.15, 0.35 in from the edge, same joint as the flex version (nfc_flex_geom.py): at TAIL_A the
#            turns step inward, the outer end crosses under them on the bottom copper
#   leads    2 traces straight in along TAIL_A to 2 plated holes at the centre (the cable's wires, hand-soldered)
import json, math, os
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import substring, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "schematics", "NFCfloor")
F = json.load(open(os.path.join(HERE, "..", "schematics", "retired", "NFCflex", "floor_outline.json")))
O = Polygon(F["outer"]).buffer(0)
if not O.exterior.is_ccw:
    O = Polygon(list(O.exterior.coords)[::-1])

EDGE, MARG, TW, GAP, NT = 0.0, 0.35, 0.18, 0.15, 3          # flush with the body edge; 0.35 copper to it
PITCH = TW + GAP
BAND = 2 * MARG + NT * TW + (NT - 1) * GAP              # 1.34
D0 = EDGE + MARG + TW / 2                                # outer turn centre-line, in from the body edge
TAIL_A = math.radians(128.0)
R = 40.58                                               # body edge radius round TAIL_A (a circle there; checked 118-138 deg)
PJ, SJ0, SJ1 = 0.90, 3.0, 6.0                            # joint pitch; full pitch to |s| 3, back to PITCH by |s| 6
SB = 0.5                                                 # the spiral starts at s = +SB, steps over s in [-SB, +SB]
LW, LS = 0.30, 1.0                                       # tail leads: width, centre spacing (leads at s = -0.5 and +0.5)
HOLE_X, HOLE_DRILL, HOLE_PAD = 1.27, 0.9, 1.6                    # the 2 wire holes (2.54 apart)
CLAMP_R, CLAMP_A1, CLAMP_D = 12.2, 36.0, 2.4                    # the 3 existing nylon clamps (M2 clearance)
VIA = (0.55, 0.3)                                        # JLC flex standard via


def pitch(s):
    a = abs(s)
    if a <= SJ0: return PJ
    if a >= SJ1: return PITCH
    t = (a - SJ0) / (SJ1 - SJ0)
    return PITCH + (PJ - PITCH) * 0.5 * (1 + math.cos(math.pi * t))


def dk(k, s):
    return D0 + k * pitch(s)


def polar(s, d):
    """joint frame -> robot xy: s along the edge (mm, CCW +) from TAIL_A, d in from the body edge"""
    th = TAIL_A + s / (R - 1.5)
    return ((R - d) * math.cos(th), (R - d) * math.sin(th))


def ring_arc(d, s_from, s_to_wrap):
    """the constant-offset ring d (shapely, so it follows the notch and corners), CCW from s_from round to
    360 deg + s_to_wrap (both in the joint frame)"""
    ring = O.buffer(-d).exterior
    if not ring.is_ccw:
        ring = LineString(list(ring.coords)[::-1])
    ring = LineString(ring.coords)
    def loc(s):
        th = TAIL_A + s / (R - 1.5)
        ray = LineString([(0, 0), (60 * math.cos(th), 60 * math.sin(th))])
        return ring.project(ring.intersection(ray) if ring.intersection(ray).geom_type == "Point" else list(ring.intersection(ray).geoms)[0])
    a, b = loc(s_from), loc(s_to_wrap)
    L = ring.length
    if b > a:
        pts = list(substring(ring, a, b).coords)
    else:
        pts = list(substring(ring, a, L).coords) + list(substring(ring, 0, b).coords)[1:]
    return pts


def joint(k, s0, s1, n=24):
    return [polar(s0 + (s1 - s0) * i / n, dk(k, s0 + (s1 - s0) * i / n)) for i in range(n + 1)]


# ---- the spiral (top copper), one polyline from the outer start to the inner end
V1_D = EDGE + 0.3 + VIA[0] / 2 + 0.06                  # the outer start's via: 0.3 copper-to-edge (+ the faceted edge)
spiral = [polar(SB, V1_D)]                               # starts on the via, then eases out onto the outer turn
for k in range(NT):
    part = joint(k, SB + (0.8 if k == 0 else 0), SJ1) + ring_arc(D0 + k * PITCH, SJ1, -SJ1)[1:-1] + joint(k, -SJ1, -SB)
    spiral += part
    if k < NT - 1:
        spiral.append(polar(SB, dk(k + 1, SB)))           # step: (-SB, d_k) -> (+SB, d_k+1)
# remove exact duplicates
sp = [spiral[0]]
for p in spiral[1:]:
    if math.dist(p, sp[-1]) > 1e-4: sp.append(p)
spiral = sp
inner_end = spiral[-1]                                   # (-SB, d_2)
v1 = polar(SB, V1_D)                                     # outer start: via down
v2 = polar(SB, dk(NT - 1, SB) + PJ)                      # ... under the turns ... and back up
# tail leads: straight, parallel to the tail axis, at -LS/2 and +LS/2 across it
ux, uy = math.cos(TAIL_A), math.sin(TAIL_A); nx, ny = -uy, ux
def tail_pt(r, off): return (r * ux + off * nx, r * uy + off * ny)
r_join = R - dk(NT - 1, 0) - PJ - 0.6
lead_a = [inner_end, tail_pt(r_join, -LS / 2), tail_pt(5.2, -LS / 2)]
lead_b = [v2, tail_pt(r_join - 0.2, LS / 2), tail_pt(5.2, LS / 2)]

# ---- the board outline: the floor (flush) minus the wheel windows; the clamp holes
holes = [Polygon(h) for h in F["holes"] if Polygon(h).area > 1.0]
win = [h for h in holes if h.area > 300 and not h.contains(Point(0, 0))]      # wheel windows (the centre one is the coil pocket)
board = O
for w in win: board = board.difference(w)
assert board.geom_type == "Polygon", board.geom_type
# the exact edges (arcs + lines) for the KiCad outline: the outside, and the wheel windows
win_edges = [F["hole_edges"][i] for i, h in enumerate(F["holes"]) if Polygon(h).area > 300 and not Polygon(h).contains(Point(0, 0))]
CLAMPS = [(CLAMP_R * math.cos(math.radians(CLAMP_A1 + 120 * k)), CLAMP_R * math.sin(math.radians(CLAMP_A1 + 120 * k))) for k in range(3)]
HOLES = [(-HOLE_X, 3.0), (HOLE_X, 3.0)]                       # moved up 3: the underglow's JST-SH 3 sits below them
ha = min(HOLES, key=lambda h: math.dist(h, lead_a[-1])); hb = HOLES[1] if ha == HOLES[0] else HOLES[0]
lead_a = lead_a + [ha]; lead_b = lead_b + [hb]

copper = unary_union([LineString(spiral).buffer(TW / 2), LineString(lead_a).buffer(LW / 2), LineString(lead_b).buffer(LW / 2)])
edge_clear = copper.distance(board.exterior)
win_clear = min(copper.distance(w) for w in win)
clamp_clear = min(copper.distance(Point(c).buffer(CLAMP_D / 2)) for c in CLAMPS)
geom = {
    "params": {"EDGE": EDGE, "TW": TW, "GAP": GAP, "NT": NT, "PJ": PJ, "tail_deg": 128.0, "LW": LW, "via": VIA,
               "hole": [HOLE_DRILL, HOLE_PAD], "clamp_d": CLAMP_D, "thickness": 1.6,
               # reader on the floor PCB (2026-10-31, make_nfc_floor.py): the 12 cable solder holes (1.27 pitch: drill, pad;
               # 28 AWG wire), Freerouting passes and time limit (s)
               "cable_hole": [0.65, 1.0], "route_passes": 300, "route_timeout": 1500},
    "outline": [list(board.exterior.coords)] + [list(i.coords) for i in board.interiors],
    "outline_edges": [F["outer_edges"]] + win_edges,
    "clamps": CLAMPS, "wire_holes": HOLES,
    "spiral": spiral, "lead_a": lead_a, "lead_b": lead_b, "vias": [v1, v2], "bottom": [v1, v2],
    "check": {"copper_to_edge_mm": round(edge_clear, 3), "copper_to_windows_mm": round(win_clear, 3), "copper_to_clamp_holes_mm": round(clamp_clear, 3),
              "copper_len_mm": round(LineString(spiral).length, 1), "board_area_mm2": round(board.area, 1),
              "board_bbox": [round(v, 2) for v in board.bounds]},
}
os.makedirs(OUT, exist_ok=True)
json.dump(geom, open(os.path.join(OUT, "floor_geom.json"), "w"), indent=0)
print(json.dumps(geom["check"]))
