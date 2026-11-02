# Underglow on the NFC floor PCB: SIDE-emitting ring (approved 2D: mech/freecad/sketches/underglow_side.png): 7 x
# WS2812B-4020-V6 on r 9.0, 51.4 deg apart, lens facing OUT, on a WHITE solder-mask board. Per LED (make_nfc_floor.py,
# mode inner_side): both lanes on the top copper INSIDE the ring (5 V at -2.0, GND at -3.0), the data line on the top copper
# just outside (+1.0); LED, 100 nF and short links to 5 vias on the bottom.
#   - the chain breaks in the gap at GAP_FEED: 5 V and data come in there on the TOP copper straight from J2
#   - GND is fed into its (outer) lane through the gap at GAP_GND, on the bottom copper
#   - the NFC antenna's 2 wires run on the top only down to r 12.6, then through 2 vias and on the bottom across the
#     ring in the gap at GAP_NFC to their plated holes
#   C:/Python312/python.exe design/lib/inner_ring_geom.py     (writes design/schematics/NFCfloor/underglow.json)
import json, math, os
from shapely.geometry import LineString, Point, Polygon
HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "..", "schematics", "NFCfloor", "floor_geom.json")))
R, N, A0 = 9.0, 7, 10.2
LANE_W = 0.4
V_5V, V_GND, V_DATA = -2.0, -3.0, 1.2                     # lane / data-line offsets from the LED line (+ = outwards)
U_UP, U_DN = 3.05, 3.15                                 # one LED's pattern along the ring (incl. via radii): upstream / downstream
xy = lambda a, r=R: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
mm2deg = lambda mm, r=None: math.degrees(mm / (r or R))
led_angs = [A0 + 360 / N * k for k in range(N)]
# data runs counter-clockwise; the gaps' free arcs (between one LED's downstream end and the next one's upstream end)
gaps = []
for k in range(N):
    a, b = led_angs[k], led_angs[(k + 1) % N] + (360 if k == N - 1 else 0)
    lo, hi = a + mm2deg(U_DN), b - mm2deg(U_UP)
    gaps.append(((lo + hi) / 2 % 360, lo % 360, hi % 360, (hi - lo)))
near = lambda target: min(gaps, key=lambda g: abs(((g[0] - target) + 180) % 360 - 180))
GAP_FEED, GAP_NFC = near(289.0), near(135.0)
GAP_GND = near(241.0)
assert len({GAP_FEED[0], GAP_NFC[0], GAP_GND[0]}) == 3
gf_lo, gf_hi = GAP_FEED[1], GAP_FEED[2]
A_DATA = gf_lo + mm2deg(0.6, R + V_DATA)                # data comes in radially (top) to the data line here
A_5V = gf_lo + mm2deg(1.4, R + V_5V)                    # the 5 V lane begins here (radial entry from J2, top); GND is fed via GAP_GND
first = min(led_angs, key=lambda a: (a - gf_hi) % 360)
order = sorted(led_angs, key=lambda a: (a - first) % 360)
last = order[-1]
A_END = last + mm2deg(U_DN)                             # everything ends with the last LED's pattern
span = (A_END - A_DATA) % 360
PATH = [xy(A_DATA + span * t / (N * 120)) for t in range(N * 120 + 1)]
pl = LineString(PATH)
off = lambda d: list(pl.offset_curve(-d, join_style=1).coords)          # + = outwards (right of a counter-clockwise path)
after = lambda pts, a0: [p for p in pts if (math.degrees(math.atan2(p[1], p[0])) - a0) % 360 < (A_END - a0) % 360 + 0.01]
data_line = off(V_DATA)
A_LANE_END = last + mm2deg(2.6)                          # the lanes end just past the last LED's GND via (u 2.25)
lane_cut = lambda pts, a0: [p for p in pts if (math.degrees(math.atan2(p[1], p[0])) - a0) % 360 < (A_LANE_END - a0) % 360 + 0.01]
lane_5v = lane_cut(off(V_5V), A_5V)
lane_gnd = lane_cut(off(V_GND), A_5V + mm2deg(1.2, R + V_GND))   # starts after the 5 V radial has crossed its radius
leds = [{"n": i + 1, "x": round(xy(a)[0], 4), "y": round(xy(a)[1], 4), "ang": round(a + 90, 3), "slot_deg": round(a % 360, 2)} for i, a in enumerate(order)]
# NFC wires: the top part of each lead stays outside r 12.6; vias there; bottom across GAP_NFC (the two 1.0 apart) to the holes
R_V = 12.6
c = GAP_NFC[0]
holes = [tuple(h) for h in G["wire_holes"]]                # (-1.27, 3.0), (1.27, 3.0)
cut = []
for k, lead in enumerate((G["lead_a"], G["lead_b"])):
    pts = [tuple(p) for p in lead]
    top = [p for p in pts if math.hypot(*p) > R_V]
    # where the lead's straight run crosses r R_V
    q0, q1 = top[-1], next(p for p in pts if math.hypot(*p) <= R_V)
    t = 0.0
    for i in range(200):
        t = i / 199; p = (q0[0] + (q1[0] - q0[0]) * t, q0[1] + (q1[1] - q0[1]) * t)
        if math.hypot(*p) <= R_V: break
    cut.append((top + [p], p))
# the via whose angle is smaller crosses at the smaller angle; that one goes to the hole further round (x > 0), over the top
(ta, va), (tb, vb) = cut
ang = lambda p: math.degrees(math.atan2(p[1], p[0])) % 360
lo_lead, hi_lead = (0, 1) if ang(va) < ang(vb) else (1, 0)
bottoms = [None, None]
far_hole = max(holes, key=lambda h: h[0]); near_hole = min(holes, key=lambda h: h[0])
for idx, dang, hole, via in ((lo_lead, -mm2deg(0.5), far_hole, cut[lo_lead][1]), (hi_lead, mm2deg(0.5), near_hole, cut[hi_lead][1])):
    pts = [via, xy(c + dang, 10.6), xy(c + dang, 5.3)]          # straight in past the LED ring and its inner vias (r 6-7)
    if hole is far_hole: pts += [(0.0, 4.6), hole]
    else: pts += [hole]
    bottoms[idx] = pts
gnd_c = GAP_GND[0]
chk = {"leds": len(leds), "spacing_mm": round(2 * math.pi * R / N, 2), "gap_mm": round(math.radians(GAP_FEED[3]) * R, 2),
       "gap_feed_deg": round(GAP_FEED[0], 1), "gap_nfc_deg": round(GAP_NFC[0], 1), "gap_gnd_deg": round(GAP_GND[0], 1),
       "nfc_cross_deg": [round(c - mm2deg(0.5), 1), round(c + mm2deg(0.5), 1)]}
json.dump({"mode": "inner_side", "R": R, "N": len(leds), "leds": leds, "path": PATH, "feed": [], "bus": PATH,
           "data_line": data_line, "lane_5v": lane_5v, "lane_gnd": lane_gnd, "lane_w": LANE_W,
           "v_5v": V_5V, "v_gnd": V_GND, "v_data": V_DATA, "a_data": A_DATA, "a_5v": A_5V, "gap_gnd": gnd_c,
           "nfc_top": [cut[0][0], cut[1][0]], "nfc_bottom": bottoms, "nfc_vias": [cut[0][1], cut[1][1]], "check": chk},
          open(os.path.join(HERE, "..", "schematics", "NFCfloor", "underglow.json"), "w"), indent=0)
print(json.dumps(chk), "LED slots (data order):", [l["slot_deg"] for l in leds])
