# NFC flex-ring antenna: the copper and outline geometry (approved 2D: mech/freecad/sketches/nfc_flex_ring.png).
#   C:/Python312/python.exe design/lib/nfc_flex_geom.py      (needs shapely; writes design/schematics/retired/NFCflex/flex_geom.json)
# then the KiCad board is built from that file by make_nfc_flex.py (KiCad's Python has no shapely).
# Robot frame, mm, looking down; the flex is glued flat under the floor plate, top copper facing up.
#   band   the floor outline 0.25 in, 1.34 wide: 3 turns of 0.18 trace / 0.15 gap, 0.25 margins
#   joint  at TAIL_A the turns step inward one pitch each (a 2 mm wide "step" zone), with the pitch opened to 0.9 so the
#          outer end's via fits; the outer end crosses under the turns on the bottom layer to the tail
#   tail   2.6 wide, 2 traces (0.3 / 0.7 gap) straight in to the round end (r 11, FR4 stiffener r 10.8 on top) with the
#          JST-SH 2 at the centre, in the old coil pocket
import json, math, os
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import substring, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "schematics", "retired", "NFCflex")
F = json.load(open(os.path.join(OUT, "floor_outline.json")))
O = Polygon(F["outer"]).buffer(0)
if not O.exterior.is_ccw:
    O = Polygon(list(O.exterior.coords)[::-1])

EDGE, MARG, TW, GAP, NT = 0.25, 0.25, 0.18, 0.15, 3
PITCH = TW + GAP
BAND = 2 * MARG + NT * TW + (NT - 1) * GAP              # 1.34
D0 = EDGE + MARG + TW / 2                                # outer turn centre-line, in from the body edge
TAIL_A = math.radians(128.0)
R = 40.58                                               # body edge radius round TAIL_A (a circle there; checked 118-138 deg)
PJ, SJ0, SJ1 = 0.90, 3.0, 6.0                            # joint pitch; full pitch to |s| 3, back to PITCH by |s| 6
SB = 0.5                                                 # the spiral starts at s = +SB, steps over s in [-SB, +SB]
LW, LS = 0.30, 1.0                                       # tail leads: width, centre spacing (leads at s = -0.5 and +0.5)
TAIL_W, DISC_R, STIFF_R = 2.6, 11.0, 10.8
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
V1_D = EDGE + 0.2 + VIA[0] / 2 + 0.06                  # the outer start's via: 0.2 copper-to-edge (+ the faceted edge)
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

# ---- the flex outline
band = O.buffer(-EDGE).difference(O.buffer(-EDGE - BAND))
jw = []                                                   # joint widening: inner edge out to d 3.9 for |s| <= 4, tapering to the band by |s| 7
for i in range(0, 141):
    s = -7 + 14 * i / 140
    a = abs(s)
    din = 3.9 if a <= 4 else EDGE + BAND + (3.9 - EDGE - BAND) * 0.5 * (1 + math.cos(math.pi * (a - 4) / 3))
    jw.append(polar(s, din))
jw += [polar(7 - 14 * i / 140, EDGE) for i in range(141)]
joint_poly = Polygon(jw).buffer(0)
tail = Polygon([tail_pt(DISC_R - 1, -TAIL_W / 2), tail_pt(R - 3.0, -TAIL_W / 2), tail_pt(R - 3.0, TAIL_W / 2), tail_pt(DISC_R - 1, TAIL_W / 2)])
flex = unary_union([band, joint_poly, tail, Point(0, 0).buffer(DISC_R, 128)])
flex = flex.buffer(0.4, 32).buffer(-0.8, 32).buffer(0.4, 32)          # round the inside corners (r 0.4) without growing it
flex = flex.intersection(O.buffer(-EDGE))
assert flex.geom_type == "Polygon", flex.geom_type
flex = flex.simplify(0.003)                               # no near-zero outline segments (KiCad: malformed outline)

# ---- checks against the floor: windows / screw holes must not be under copper
holes = [Polygon(h) for h in F["holes"] if Polygon(h).area > 1.0]
copper = unary_union([LineString(spiral).buffer(TW / 2), LineString(lead_a).buffer(LW / 2), LineString(lead_b).buffer(LW / 2)])
clear_cu = min(copper.distance(h) for h in holes if not h.contains(Point(0, 0)))
win = [h for h in holes if h.area > 300 and not h.contains(Point(0, 0))]     # wheel windows (the centre one is the coil pocket)
over_win = sum(flex.intersection(h).area for h in win)
geom = {
    "params": {"EDGE": EDGE, "BAND": BAND, "TW": TW, "GAP": GAP, "NT": NT, "PJ": PJ, "tail_deg": 128.0, "LW": LW,
               "TAIL_W": TAIL_W, "DISC_R": DISC_R, "STIFF_R": STIFF_R, "via": VIA},
    "outline": [list(flex.exterior.coords)] + [list(i.coords) for i in flex.interiors],
    "spiral": spiral, "lead_a": lead_a, "lead_b": lead_b, "vias": [v1, v2], "bottom": [v1, v2],
    "check": {"copper_to_nearest_hole_or_window_mm": round(clear_cu, 3), "flex_over_wheel_windows_mm2": round(over_win, 3),
              "copper_len_mm": round(LineString(spiral).length, 1), "flex_area_mm2": round(flex.area, 1),
              "flex_bbox": [round(v, 2) for v in flex.bounds]},
}
json.dump(geom, open(os.path.join(OUT, "flex_geom.json"), "w"), indent=0)
print(json.dumps(geom["check"]))
