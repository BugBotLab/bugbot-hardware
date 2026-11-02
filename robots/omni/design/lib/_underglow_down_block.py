# ---- underglow, routed by hand (Freerouting hangs on this board). Every LED gets the same pattern in its own frame
# (u along the data direction, v to the left): top copper = 5 V lane, GND lane (+-0.9) and the data line (centre);
# bottom = the LED, its 100 nF across the line at u -2.25, and short links to 5 vias:
#   Vc (0, 0) data in (centre of the LED, between its pads), Vd (+2.0, 0) data out, Vg1 (+1.6, GND side) for the LED's
#   GND pad, Vp / Vg2 (-3.0, -+0.9) for the cap's 5 V / GND pads; the LED's VDD pad goes to the cap's 5 V pad.
def bottom(f):
    f.SetLayerAndFlip(pcbnew.B_Cu)
    return f
PATH = [tuple(p) for p in UG["path"]] if str(UG.get("mode", "")).startswith("inner") else [tuple(p) for p in UG["feed"]] + [tuple(p) for p in UG["bus"][1:]]
R_RING = UG.get("R", 0)
def tangent_at(pt):
    """the path's direction at pt, from points 0.5-1.5 mm either side along it (the data direction)"""
    i = min(range(len(PATH)), key=lambda k: math.dist(PATH[k], pt))
    j0 = i
    while j0 > 0 and math.dist(PATH[j0], pt) < 0.8: j0 -= 1
    j1 = i
    while j1 < len(PATH) - 1 and math.dist(PATH[j1], pt) < 0.8: j1 += 1
    a, b = PATH[j0], PATH[j1]
    L_ = math.dist(a, b); return ((b[0] - a[0]) / L_, (b[1] - a[1]) / L_), i
def walk(i, ds):
    """point and unit tangent ds mm along PATH from vertex i (negative: backwards)"""
    step = 1 if ds >= 0 else -1; left = abs(ds); j = i
    while True:
        k = j + step
        if k < 0 or k >= len(PATH):
            a, b = (PATH[j - 1], PATH[j]) if step > 0 else (PATH[j], PATH[j + 1]); L_ = math.dist(a, b)
            t = ((b[0] - a[0]) / L_, (b[1] - a[1]) / L_); return (PATH[j][0] + step * left * t[0], PATH[j][1] + step * left * t[1]), t
        seg = math.dist(PATH[j], PATH[k])
        if seg >= left:
            f_ = left / seg if seg else 0; q = (PATH[j][0] + (PATH[k][0] - PATH[j][0]) * f_, PATH[j][1] + (PATH[k][1] - PATH[j][1]) * f_)
            a, b = (PATH[j], PATH[k]) if step > 0 else (PATH[k], PATH[j]); L_ = math.dist(a, b)
            return q, ((b[0] - a[0]) / L_, (b[1] - a[1]) / L_)
        left -= seg; j = k
def frame(pt):
    (tx, ty), i = tangent_at(pt)
    def Q(u, v):
        q, t = walk(i, u)
        return (q[0] - v * t[1], q[1] + v * t[0])
    return Q, (tx, ty), i
def local(fr_pt, t, q):                                        # robot xy -> (u, v)
    dx, dy = q[0] - fr_pt[0], q[1] - fr_pt[1]
    return (dx * t[0] + dy * t[1], -dx * t[1] + dy * t[0])
LEDS = []
SV = None                                                       # +1: GND lane on the left (+v), 5 V on the right
for i, l in enumerate(UG["leds"]):
    pt = (l["x"], l["y"]); P, t, idx = frame(pt)
    f = bottom(X.add_fp(f"D{i + 1}", pt[0], pt[1], 0))
    f.Models().clear(); m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KIPRJMOD}/../lib/3dmodels/LED_WS2812B-2020_PLCC4_2.0x2.0mm.step"; f.Models().push_back(m)
    ok = None
    for a in range(0, 360, 90):
        f.SetOrientationDegrees(math.degrees(math.atan2(t[1], t[0])) + a)
        pd = {p.GetNumber(): local(pt, t, X.xy(p)) for p in f.Pads()}
        if pd["3"][0] < 0 and pd["4"][0] < 0 and pd["1"][0] > 0 and pd["2"][0] > 0:      # DIN + VDD upstream, DOUT + GND downstream
            ok = (a, pd); break
    assert ok, f"D{i + 1}: no orientation with DIN upstream"
    sv = 1 if ok[1]["2"][1] > 0 else -1                         # the GND pad's side
    SV = sv if SV is None else SV
    assert sv == SV, "LED pad sides differ between LEDs"
    LEDS.append((i, pt, P, t, idx, f))
LANE5, LANEG = (UG["lane_a"], UG["lane_b"]) if SV > 0 else (UG["lane_b"], UG["lane_a"])   # lane_a is right of the path (-v)
if "lane_nets" in UG:                                           # the complete ring fixes them: GND outside (a), 5 V inside (b)
    assert (LANE5 is UG["lane_b"]) == (UG["lane_nets"]["b"] == "+5V"), "LED pads put 5 V on the other side"
X.track([tuple(p) for p in LANE5], "+5V", UG["lane_w"], pcbnew.F_Cu)
X.track([tuple(p) for p in LANEG], "GND", UG["lane_w"], pcbnew.F_Cu)
W_S, W_P, VIA_ = 0.2, 0.3, (0.55, 0.3)
padxy = lambda f, n: X.xy([p for p in f.Pads() if p.GetNumber() == n][0])
for i, pt, P, t, idx, f in LEDS:
    din, dout = f"D{i + 1}_DIN", (f"D{i + 2}_DIN" if i < len(LEDS) - 1 else None)
    cpt, ct = walk(idx, -2.25)
    cap = bottom(X.add_fp(f"C{i + 1}", *cpt, 0))
    for a in (90, -90):                                          # pads across the line, its 5 V pad on the 5 V side
        cap.SetOrientationDegrees(math.degrees(math.atan2(ct[1], ct[0])) + a)
        if local(cpt, ct, padxy(cap, "1"))[1] * SV < 0: break
    Vc, Vd, Vg1, Vp, Vg2 = P(0, 0), P(2.0, 0), P(1.6, 0.9 * SV), P(-3.0, -0.9 * SV), P(-3.0, 0.9 * SV)
    X.via(*Vc, din, *VIA_); X.via(*Vg1, "GND", *VIA_); X.via(*Vp, "+5V", *VIA_); X.via(*Vg2, "GND", *VIA_)
    X.track([padxy(f, "3"), Vc], din, W_S, pcbnew.B_Cu)
    X.track([padxy(f, "2"), Vg1], "GND", W_P, pcbnew.B_Cu)
    X.track([padxy(f, "4"), padxy(cap, "1")], "+5V", W_P, pcbnew.B_Cu)
    X.track([padxy(cap, "1"), Vp], "+5V", W_P, pcbnew.B_Cu)
    X.track([padxy(cap, "2"), Vg2], "GND", W_P, pcbnew.B_Cu)
    if dout:
        X.via(*Vd, dout, *VIA_)
        X.track([padxy(f, "1"), Vd], dout, W_S, pcbnew.B_Cu)
        nxt = LEDS[i + 1]
        seg = [p for p in PATH[idx:nxt[4] + 1] if math.dist(p, pt) > 2.05 and math.dist(p, nxt[1]) > 0.3]
        X.track([Vd] + seg + [nxt[1]], dout, W_S, pcbnew.F_Cu)          # data, top centre, to the next LED's Vc

# ---- centre (complete ring): J2 on top. 5 V and data go straight out on the TOP copper into the chain's gap (data enters
# at a_data, the 5 V lane begins at a_5v); GND drops through a via and runs on the bottom out to the gap at gap_gnd, then up
# onto the outer lane. C13 (10 uF, bottom) sits between J2's 5 V and GND vias. The level shifter is on the main board.
ring_pt = lambda r, deg: (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))
j2 = X.add_fp("J2", 0.0, -1.2, 0)
for a in (0, 180):
    j2.SetOrientationDegrees(a)
    jp = {n: padxy(j2, n) for n in ("1", "2", "3")}           # 1 5V, 2 DIN, 3 GND
    if jp["1"][0] > jp["2"][0] > jp["3"][0] and jp["2"][1] > -1.2: break
for p in j2.Pads():
    if p.GetNumber() == "MP": p.SetNetCode(0)
yd = -3.4                                                       # straight down from the pads, clear of J2's mounting tabs, then out
d_in, d_ring = ring_pt(6.3, UG["a_data"]), tuple(PATH[0])
X.track([jp["2"], (jp["2"][0], yd), d_in, d_ring], "D1_DIN", W_S, pcbnew.F_Cu)
X.track([d_ring] + [p for p in PATH[1:LEDS[0][4] + 1] if math.dist(p, LEDS[0][1]) > 0.3] + [LEDS[0][1]], "D1_DIN", W_S, pcbnew.F_Cu)
l5 = tuple(LANE5[0])
X.track([jp["1"], (jp["1"][0], yd + 0.5), ring_pt(6.6, UG["a_5v"]), l5], "+5V", W_P, pcbnew.F_Cu)
V5 = (jp["1"][0], jp["1"][1] - 1.35)
VG = (jp["3"][0], jp["3"][1] - 1.35)
X.via(*V5, "+5V", *VIA_); X.via(*VG, "GND", *VIA_)
X.track([jp["3"], VG], "GND", W_P, pcbnew.F_Cu)
c13 = bottom(X.add_fp("C13", 0.0, jp["2"][1] + 0.55, 0))
cp = {n: padxy(c13, n) for n in ("1", "2")}
if (cp["1"][0] - cp["2"][0]) * (V5[0] - VG[0]) < 0:
    c13.SetOrientationDegrees(180); cp = {n: padxy(c13, n) for n in ("1", "2")}
X.track([cp["1"], (V5[0], cp["1"][1]), V5], "+5V", W_P, pcbnew.B_Cu)
X.track([cp["2"], (VG[0], cp["2"][1]), VG], "GND", W_P, pcbnew.B_Cu)
g_out = ring_pt(R_RING + 0.9, UG["gap_gnd"])
X.via(*g_out, "GND", *VIA_)
X.track([VG, ring_pt(3.2, UG["gap_gnd"]), g_out], "GND", W_P, pcbnew.B_Cu)

