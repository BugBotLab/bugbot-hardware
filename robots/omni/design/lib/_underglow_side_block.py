# ---- underglow, SIDE-emitting ring (UG mode "inner_side"; exec'd by make_nfc_floor.py). Per LED, in its own frame
# (u along the data direction, o outwards): top copper = 5 V lane (o -2.0), GND lane (o -3.0), data line (o +1.2);
# bottom = the WS2812B-4020 (pads in a row: 1 DIN, 2 VDD, 3 DOUT, 4 GND; body inwards, lens facing out), its 100 nF at
# (u 0.75, o -2.55) and short links to: Vdin (-2.75, +1.0), Vdout (+2.85, +1.0), V5 (-0.43, -2.0), VG (+2.25, -3.0).
def bottom(f):
    f.SetLayerAndFlip(pcbnew.B_Cu)
    return f
PATH = [tuple(p) for p in UG["path"]]
def walk(i, ds):
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
    i = min(range(len(PATH)), key=lambda k: math.dist(PATH[k], pt))
    def P(u, o):                                                  # o outwards = right of the counter-clockwise path
        q, t = walk(i, u)
        return (q[0] + o * t[1], q[1] - o * t[0])
    _, t = walk(i, 0.0)
    return P, t, i
def local(pt, t, q):
    dx, dy = q[0] - pt[0], q[1] - pt[1]
    return (dx * t[0] + dy * t[1], dx * t[1] - dy * t[0])          # (u, o)
padxy = lambda f, n: X.xy([p for p in f.Pads() if p.GetNumber() == n][0])
W_S, W_P, VIA_ = 0.2, 0.3, (0.55, 0.3)
LEDS = []
for i, l in enumerate(UG["leds"]):
    pt = (l["x"], l["y"]); P, t, idx = frame(pt)
    f = bottom(X.add_fp(f"D{i + 1}", pt[0], pt[1], 0))
    ok = None
    for a in range(0, 360, 90):
        f.SetOrientationDegrees(math.degrees(math.atan2(t[1], t[0])) + a)
        pd = {n: local(pt, t, padxy(f, n)) for n in "1234"}
        cy = f.GetCourtyard(pcbnew.B_CrtYd).BBox(); cc = local(pt, t, (pcbnew.ToMM(cy.GetCenter().x) - 100, 100 - pcbnew.ToMM(cy.GetCenter().y)))
        if pd["1"][0] < pd["3"][0] < pd["4"][0] and abs(pd["1"][1] - pd["4"][1]) < 0.05 and cc[1] < 0:   # DIN upstream, body inwards
            ok = a; break
    assert ok is not None, f"D{i + 1}: no orientation with DIN upstream and the body inwards"
    LEDS.append((i, pt, P, t, idx, f))
X.track([tuple(p) for p in UG["lane_5v"]], "+5V", UG["lane_w"], pcbnew.F_Cu)
X.track([tuple(p) for p in UG["lane_gnd"]], "GND", UG["lane_w"], pcbnew.F_Cu)
DL = [tuple(p) for p in UG["data_line"]]
def dl_between(a, b):
    """the data line (top) between two points on it"""
    ia = min(range(len(DL)), key=lambda k: math.dist(DL[k], a)); ib = min(range(len(DL)), key=lambda k: math.dist(DL[k], b))
    return [a] + DL[ia + 1:ib] + [b]
VDIN = []
for i, pt, P, t, idx, f in LEDS:
    din, dout = f"D{i + 1}_DIN", (f"D{i + 2}_DIN" if i < len(LEDS) - 1 else None)
    OD = UG["v_data"]
    Vdin, Vdout, V5, VG = P(-2.75, OD), P(2.85, OD), P(-0.43, UG["v_5v"]), P(2.25, UG["v_gnd"])
    cpt = P(0.75, -2.55)
    cap = bottom(X.add_fp(f"C{i + 1}", *cpt, 0))
    for a in (0, 180):                                           # along u; its 5 V pad towards V5
        cap.SetOrientationDegrees(math.degrees(math.atan2(t[1], t[0])) + a)
        if math.dist(padxy(cap, "1"), V5) < math.dist(padxy(cap, "2"), V5): break
    X.via(*Vdin, din, *VIA_); X.via(*V5, "+5V", *VIA_); X.via(*VG, "GND", *VIA_)
    X.track([padxy(f, "1"), Vdin], din, W_S, pcbnew.B_Cu)
    X.track([padxy(f, "2"), V5], "+5V", W_P, pcbnew.B_Cu)
    X.track([padxy(f, "4"), P(1.68, -1.6), P(1.9, -2.4), VG], "GND", W_P, pcbnew.B_Cu)
    X.track([padxy(cap, "1"), V5], "+5V", W_P, pcbnew.B_Cu)
    X.track([padxy(cap, "2"), VG], "GND", W_P, pcbnew.B_Cu)
    VDIN.append(Vdin)
    if dout:
        X.via(*Vdout, dout, *VIA_)
        X.track([padxy(f, "3")] + [P(0.60 + (2.85 - 0.60) * k / 10, OD) for k in range(11)], dout, W_S, pcbnew.B_Cu)   # follows the arc
        LEDS[i] = LEDS[i] + (Vdout,)
for i in range(len(LEDS) - 1):                                   # data, top: Vdout(i) -> Vdin(i+1) along the data line
    X.track(dl_between(LEDS[i][6], VDIN[i + 1]), f"D{i + 2}_DIN", W_S, pcbnew.F_Cu)

# ---- centre: the cable's solder holes are J1 (make_nfc_floor.py, cable_xy). Fixed stubs from the ring inwards: 5 V and data
# on the TOP copper from the feed gap (radials at a_5v / a_data), GND on the bottom from gap_gnd up onto the GND lane; the
# router joins them to the holes. C13 (10 uF, bottom) beside the 5 V / GND holes.
ring_pt = lambda r, deg: (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))
X.track([ring_pt(5.5, UG["a_data"]), DL[0]] + dl_between(DL[0], VDIN[0])[1:], "D1_DIN", W_S, pcbnew.F_Cu)
X.track([ring_pt(5.0, UG["a_5v"]), tuple(UG["lane_5v"][0])], "+5V", W_P, pcbnew.F_Cu)
g_in = ring_pt(UG["R"] + UG["v_gnd"], UG["gap_gnd"])
X.via(*g_in, "GND", *VIA_)
X.track([ring_pt(3.2, UG["gap_gnd"]), g_in], "GND", W_P, pcbnew.B_Cu)
# the holes to the stubs, fixed (the router keeps off the underglow): data and 5 V on the top, 5 V jogging out first so it
# passes the data hole wide; GND straight down on the bottom
JOG_5V = 0.97
p5 = cable_xy[UG_PINS["+5V"]]
X.track([cable_xy[UG_PINS["D1_DIN"]], ring_pt(5.5, UG["a_data"])], "D1_DIN", W_S, pcbnew.F_Cu)
X.track([p5, (p5[0] + JOG_5V, p5[1]), ring_pt(5.0, UG["a_5v"])], "+5V", W_P, pcbnew.F_Cu)
X.track([cable_xy[UG_PINS["GND"]], ring_pt(3.2, UG["gap_gnd"])], "GND", W_P, pcbnew.B_Cu)
C13_OFS = (1.9, 0.0)                                             # 10 uF: this far from the 5 V hole, upright
c5 = next(cable_xy[n] for n, net in CABLE.items() if net == "+5V")
bottom(X.add_fp("C13", c5[0] + C13_OFS[0], c5[1] + C13_OFS[1], 90))
