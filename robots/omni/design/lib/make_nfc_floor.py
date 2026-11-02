# BugBot NFC antenna as a standard PCB under the floor (approved 2D: mech/freecad/sketches/nfc_floor_pcb.png), generated.
#   C:/Python312/python.exe design/lib/nfc_floor_geom.py                                  (geometry, needs shapely)
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_nfc_floor.py             (this: the KiCad project)
# BugBot_NFCfloor  JLC 2-layer FR4 1.6 mm, one-sided assembly (every part on the BOTTOM face): the floor outline with the
#                  wheel windows and ball notch cut out, a 3-turn loop round the edge on the top copper (against the floor),
#                  3 holes for the existing nylon clamp screws (M2 x 5).
#                  + the NFC READER (2026-10-31, approved 2D: mech/freecad/sketches/nfc_reader_on_floor.png; circuit in
#                  nfc_reader_circuit.py, refs +100): its parts packed in a block beside the loop's feed, the loop's two
#                  ends straight into the matching network. Replaces the reader board BugBot_NFC, its tray and coil cable.
#                  + J1: 12 plated solder holes at the centre, in the floor plate's opening: the reader cable (main J20,
#                  8 wires) and the underglow cable (main J17, 3 wires), hand-soldered.
#                  + underglow (complete inner ring, approved 2D: sketches/underglow_full_ring.png; design/lib/inner_ring_geom.py):
#                  7 x WS2812B-4020-V6 side-view on the BOTTOM face on r 9, 51.4 deg apart; 100 nF beside each LED; 10 uF;
#                  DIN arrives at 5 V level (the shifter is on the main board).
#                  5 V / GND lanes (top copper) follow the LED line as one open chain: no copper ring inside the NFC loop.
#                  All routed here (Freerouting hangs on the long lanes): a fixed pattern per LED, see the underglow block.
import json, math, os, re, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "make_nfc_boards.py"), encoding="utf-8").read()
exec(_src[:_src.index("# ================================================================== the reader board")])   # Design + helpers

sys.path.insert(0, HERE)
from nfc_reader_circuit import add_reader, SIGNALS
GEO = json.load(open(f"{ROOTDIR}/schematics/NFCfloor/floor_geom.json"))
PR = GEO["params"]
X = Design("BugBot_NFCfloor", "BugBot NFC floor PCB: antenna loop + reader + underglow",
           ["JLC 2-layer FR4 1.6 mm, parts on the bottom only; screwed under the floor plate by the 3 nylon clamp screws (M2 x 5)",
            f"{PR['NT']}-turn loop {PR['TW']} / {PR['GAP']} round the edge (top copper); its two ends into the reader's matching (both on net COIL: the loop is copper)",
            "J1 = 12 plated solder holes: 1 RST 2 MISO 3 SCK 4 MOSI 5 GND 6 NSS 7 3V3 8 IRQ (to main J20), 9 GND 10 5V 12 DIN (to main J17)"], {})
# the reader: the routed layout of the reader board (BugBot_NFC by make_nfc_boards.py, DRC clean) copied onto the bottom in
# the free patch beside the loop's feed (approved 2D: draw_nfc_reader_on_floor.py). window: the part of the reader board
# taken (its frame: x from the cut through the cable tracks to the antenna end, y); it is mirrored (bottom side), turned
# by rot and its middle put on centre: the antenna end toward the loop's feed, the cut end toward the ring (pose from a
# search for the most room, 0.54 mm, with the two loop leads apart)
READER = {"src": f"{ROOTDIR}/schematics/retired/NFC/BugBot_NFC.kicad_pcb", "window": (-7.0, 13.8, -8.7, 9.1), "centre": (-10.2, 22.0), "rot": -51.0,
          "left_behind": ("J1", "J2", "H1"), "ant_nets": ("/ANT_A", "/ANT_B")}
RREF = lambda r: re.sub(r"\d+", lambda m: str(int(m.group()) + 100), r)          # reader refs + 100 (the floor has its own C1...)
add_reader(X, custom_symbol, ref=RREF, ant=("COIL", "COIL"), sch=(350, 0))
# J1: a 2 x 6 1.27 mm header footprint used as 12 solder holes (no part). Pins 1-8 (upper rows, toward the reader): the
# reader cable, in the order its tracks arrive from the reader (left column from the left, right column round the top;
# the wires are hand-soldered, so the order is free; legend on the silk); 9 GND, 10 5V, 12 DIN (lower rows, toward the
# underglow feed); 11 spare
READER_PINS = {"1": "RST", "3": "SCK", "5": "GND", "7": "3V3", "2": "MISO", "4": "MOSI", "6": "NSS", "8": "IRQ"}
assert sorted(READER_PINS.values()) == sorted(SIGNALS)
UG_PINS = {"GND": "9", "+5V": "10", "D1_DIN": "12"}
CABLE = {**READER_PINS, **{v: k for k, v in UG_PINS.items()}}
X.part("J1", "Connector_Generic:Conn_02x06_Odd_Even", "Cables (solder): reader 1-8, underglow 9-12",
       "Connector_PinHeader_1.27mm:PinHeader_2x06_P1.27mm_Vertical", CABLE, (60, 60), None, dnp=True)
X.NC.add(("J1", "11"))
UG = json.load(open(f"{ROOTDIR}/schematics/NFCfloor/underglow.json"))
JLCP = {"D": ("WS2812B-2020-V6", "C52917434"), "C13": ("CL10A106KP8NNNC", "C19702"), "C": ("CL05B104KO5NNNC", "C1525")}
NL = len(UG["leds"])
X.part("C13", "Device:C", "10uF", "Capacitor_SMD:C_0603_1608Metric", {"1": "+5V", "2": "GND"}, (60, 120), JLCP["C13"])
SIDE = UG.get("mode") == "inner_side"
if SIDE:                                                       # WS2812B-4020-V6 side-view: pads 1 DIN, 2 VDD, 3 DOUT, 4 GND
    JLCP["D"] = ("WS2812B-4020-V6", "C52941387")
    X.custom["BugBot:WS2812B-4020"] = custom_symbol("BugBot:WS2812B-4020", "D", [("1", "DIN", "input"), ("2", "VDD", "power_in")],
                                                   [("3", "DOUT", "output"), ("4", "VSS", "power_in")], fp="BugBot:LED_WS2812B-4020_SideView")
for k in range(NL):
    dout = f"D{k + 2}_DIN" if k < NL - 1 else f"D{NL}_DOUT"
    if SIDE:
        X.part(f"D{k + 1}", "BugBot:WS2812B-4020", "WS2812B-4020", "BugBot:LED_WS2812B-4020_SideView",
               {"1": f"D{k + 1}_DIN", "2": "+5V", "3": dout, "4": "GND"}, (180 + 30 * (k % 6), 90 + 40 * (k // 6)), JLCP["D"])
    else:
        X.part(f"D{k + 1}", "LED:WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
               {"1": dout, "2": "GND", "3": f"D{k + 1}_DIN", "4": "+5V"}, (180 + 30 * (k % 6), 90 + 40 * (k // 6)), JLCP["D"])
    X.part(f"C{k + 1}", "Device:C", "100nF", "Capacitor_SMD:C_0402_1005Metric", {"1": "+5V", "2": "GND"}, (180 + 30 * (k % 6), 170 + 25 * (k // 6)), JLCP["C"])
X.NC.add((f"D{NL}", "3" if SIDE else "1"))
X.schematic(flags=("+5V", "GND"))
X.new_board(PR["thickness"])
ds = X.board.GetDesignSettings()
ds.m_CopperEdgeClearance = mm(0.3); ds.m_TrackMinWidth = mm(0.127); ds.m_MinClearance = mm(0.15)   # 0.127: JLC 2-layer, as the reader board
# GREEN solder mask, white silk (user, 2026-10-23; it was white for the underglow): written into the stackup below
nc = ds.m_NetSettings.GetDefaultNetclass(); nc.SetTrackWidth(mm(PR["TW"])); nc.SetClearance(mm(0.15))
nc.SetViaDiameter(mm(PR["via"][0])); nc.SetViaDrill(mm(PR["via"][1]))

for loop in GEO["outline_edges"]:                             # exact lines and arcs: the outside + the three wheel windows
    for e in loop:
        sh = pcbnew.PCB_SHAPE(X.board); sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(mm(0.05))
        if e["t"] == "arc":
            sh.SetShape(pcbnew.SHAPE_T_ARC); sh.SetArcGeometry(X.P(*e["a"]), X.P(*e["m"]), X.P(*e["b"]))
        else:
            sh.SetShape(pcbnew.SHAPE_T_SEGMENT); sh.SetStart(X.P(*e["a"])); sh.SetEnd(X.P(*e["b"]))
        X.board.Add(sh)
for cx, cy in GEO["clamps"]:                                   # clamp screw holes (unplated, routed)
    s = pcbnew.PCB_SHAPE(X.board); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetCenter(X.P(cx, cy)); s.SetEnd(X.P(cx + PR["clamp_d"] / 2, cy)); s.SetWidth(mm(0.05)); X.board.Add(s)

# J1: the 12 solder holes, centred on the robot axis (in the floor plate's 7.6 x 8.4 opening), no part fitted
j = X.add_fp("J1", 0.0, 0.0, 0)
pc = [X.xy(p) for p in j.Pads()]; cx_, cy_ = sum(p[0] for p in pc) / len(pc), sum(p[1] for p in pc) / len(pc)
jx, jy = X.xy(j); j.SetPosition(X.P(jx - cx_, jy - cy_))
j.SetDNP(True); j.SetExcludedFromPosFiles(True)
j.Models().clear()                                             # the wires are soldered in: no 3D model
for p in j.Pads():
    p.SetDrillSize(pcbnew.VECTOR2I(mm(PR["cable_hole"][0]), mm(PR["cable_hole"][0]))); p.SetSize(pcbnew.VECTOR2I(mm(PR["cable_hole"][1]), mm(PR["cable_hole"][1])))
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
for g in list(j.GraphicalItems()):                             # header outline / courtyard off: there is no part
    if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_Fab, pcbnew.F_CrtYd): j.Remove(g)
cable_xy = {p.GetNumber(): X.xy(p) for p in j.Pads()}

LIBDIR = f"{ROOTDIR}/lib/BugBot"                               # the project footprints (add_fp looks here for "BugBot:")
if SIDE:
    exec(open(os.path.join(HERE, "_underglow_side_block.py"), encoding="utf-8").read())
else:
    exec(open(os.path.join(HERE, "_underglow_down_block.py"), encoding="utf-8").read())

X.track([tuple(p) for p in GEO["spiral"]], "COIL", PR["TW"], pcbnew.F_Cu)
X.via(*GEO["vias"][0], "COIL", *PR["via"]); X.via(*GEO["vias"][1], "COIL", *PR["via"])
X.track([tuple(p) for p in GEO["bottom"]], "COIL", PR["LW"], pcbnew.B_Cu)

# ---- the reader (bottom): the reader board's parts, tracks and vias through T (mirror, turn, move); layers swap. Cable
# tracks are cut at the window's x0 (the router takes them on to J1); the antenna tracks to its J2 are left behind.
SRC = pcbnew.LoadBoard(READER["src"])
WX0, WX1, WY0, WY1 = READER["window"]
WC, TH = ((WX0 + WX1) / 2, (WY0 + WY1) / 2), math.radians(READER["rot"])
def T(p):
    x, y = -(p[0] - WC[0]), p[1] - WC[1]
    return (READER["centre"][0] + x * math.cos(TH) - y * math.sin(TH), READER["centre"][1] + x * math.sin(TH) + y * math.cos(TH))
src_xy = lambda v: (pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y))
FLIP = {pcbnew.F_Cu: pcbnew.B_Cu, pcbnew.B_Cu: pcbnew.F_Cu}
for sf in SRC.GetFootprints():
    r = sf.GetReference()
    if r in READER["left_behind"]: continue
    want = {p.GetNumber(): T(src_xy(p.GetPosition())) for p in sf.Pads() if p.GetNumber()}     # (unnumbered: paste-only pads)
    f = X.add_fp(RREF(r), *T(src_xy(sf.GetPosition())), 0); f.SetLayerAndFlip(pcbnew.B_Cu)
    err = lambda: max(math.dist(X.xy(p), want[p.GetNumber()]) for p in f.Pads() if p.GetNumber())
    best = min(range(360), key=lambda a: (f.SetOrientationDegrees(a), err())[1])
    f.SetOrientationDegrees(best); assert err() < 0.01, f"{r}: pads do not land ({err():.3f} mm)"
def cut(a, b):
    """the part of segment a-b (reader frame) at x >= WX0, or None"""
    if a[0] >= WX0 and b[0] >= WX0: return a, b
    if a[0] < WX0 and b[0] < WX0: return None
    t = (WX0 - a[0]) / (b[0] - a[0]); q = (WX0, a[1] + t * (b[1] - a[1]))
    return (q, b) if a[0] < WX0 else (a, q)
EXIT_STUB = 0.3                                                # cut cable tracks go on this far past the window (the router starts there)
exits = []
for st in SRC.GetTracks():
    n = st.GetNetname()
    if n in READER["ant_nets"]: continue
    if st.GetClass() == "PCB_VIA":
        p = src_xy(st.GetPosition())
        if p[0] >= WX0: X.via(*T(p), n, pcbnew.ToMM(st.GetWidth(pcbnew.F_Cu)), pcbnew.ToMM(st.GetDrillValue()))
        continue
    a0, b0 = src_xy(st.GetStart()), src_xy(st.GetEnd()); seg = cut(a0, b0)
    if not seg: continue
    X.track([T(seg[0]), T(seg[1])], n, pcbnew.ToMM(st.GetWidth()), FLIP[st.GetLayer()])
    if seg != (a0, b0):                                        # cut: a stub out of the window, straight on
        q = seg[0] if seg[0][0] == WX0 else seg[1]
        X.track([T(q), T((WX0 - EXIT_STUB, q[1]))], n, pcbnew.ToMM(st.GetWidth()), FLIP[st.GetLayer()])
        exits.append((*T((WX0 - EXIT_STUB, q[1])), n, FLIP[st.GetLayer()], pcbnew.ToMM(st.GetWidth())))
block_poly = [T(p) for p in ((WX0, WY0), (WX1, WY0), (WX1, WY1), (WX0, WY1))]
# the loop's two ends (inner end, and the via at the step) to R4 / R5 (antenna side, pad 2): on the top copper to a via just
# past the pad (along the resistor), then into the pad on the bottom. Fixed here so the router never joins the ends to
# each other or to the loop
ends = [tuple(GEO["lead_a"][0]), tuple(GEO["lead_b"][0])]
rp = {r: X.xy(X.fps[RREF(r)].FindPadByNumber("2")) for r in ("R4", "R5")}
pairs = min((list(zip(ends, o)) for o in (("R4", "R5"), ("R5", "R4"))), key=lambda z: sum(math.dist(e, rp[r]) for e, r in z))
ANT_VIA, CLR = (0.8, 1.6), 0.15                                 # the lead's via: this far from R4 / R5's pad 2; copper clearance
def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))
def room(pt, r, net):
    """free copper room round pt (both layers): distance to the nearest other-net pad / track / via, less r"""
    d = []
    for f in X.board.GetFootprints():
        for pd in f.Pads():
            if pd.GetNetname() == "/" + net: continue
            bb = pd.GetBoundingBox(); c = X.xy(pd); hw, hh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
            d.append(math.hypot(max(0, abs(pt[0] - c[0]) - hw), max(0, abs(pt[1] - c[1]) - hh)))
    for t in X.board.GetTracks():
        if t.GetNetname() == "/" + net: continue
        if t.GetClass() == "PCB_VIA": d.append(math.dist(pt, X.xy(t)) - pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2)
        else: d.append(seg_dist(pt, src_xy(t.GetStart()), src_xy(t.GetEnd())) - pcbnew.ToMM(t.GetWidth()) / 2)
    return min(d) - r
for e, r in pairs:
    p2 = rp[r]
    cand = [(p2[0] + rr * math.cos(math.radians(a)), p2[1] + rr * math.sin(math.radians(a))) for rr in (ANT_VIA[0], (ANT_VIA[0] + ANT_VIA[1]) / 2, ANT_VIA[1]) for a in range(0, 360, 10)]
    ok = [c for c in cand if room(c, PR["via"][0] / 2 + CLR, "COIL") >= 0 and all(room(q, PR["LW"] / 2 + CLR, "COIL") >= 0 for q in (c, ((c[0] + p2[0]) / 2, (c[1] + p2[1]) / 2)))]
    assert ok, f"no room for the loop lead's via at {RREF(r)}"
    vpt = min(ok, key=lambda c: math.dist(c, e))
    X.track([e, vpt], "COIL", PR["LW"], pcbnew.F_Cu); X.via(*vpt, "COIL", *PR["via"]); X.track([vpt, p2], "COIL", PR["LW"], pcbnew.B_Cu)
X.board.BuildConnectivity()
X.save(None)
if os.environ.get("FLOOR_PLACE_ONLY"):
    raise SystemExit("placed only (not routed)")
X.passes, X.route_timeout = PR["route_passes"], PR["route_timeout"]
# the router sees neither the loop (it hangs on its segments) nor the underglow copper (it loops on the long 5 V lane):
# no-copper zones stand in for the ring: on the top a band over the lanes and the data line, on the bottom one outline
# per LED round its pads, cap, stubs and vias (local u along the ring, o outwards), so the gaps between LEDs stay open
# for the reader's cable tracks. The short fixed links inside the ring (holes to stubs) stay. It routes the reader,
# the cable holes and C13.
UG_NETS = {"/+5V", "/GND", f"/D{NL}_DOUT"} | {f"/D{k + 1}_DIN" for k in range(NL)}
UG_INNER, UG_OUTER, UG_BAND, KO_M = 5.6, 12.0, (5.6, 10.8), 0.25   # underglow copper between these radii goes; top band; margin
LED_KO = [(-3.1, 1.6), (3.2, 1.6), (3.2, 0.7), (2.7, 0.7), (2.7, -3.4), (-0.8, -3.4), (-0.8, -1.6), (-2.2, -1.6), (-2.2, 0.7), (-3.1, 0.7)]
def grow(poly, m):                                             # outward offset of a simple polygon by m (miter, fine for these)
    n = len(poly); cw = sum((poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]) for i in range(n)) < 0
    out = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        def nrm(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]; L_ = math.hypot(dx, dy); return (dy / L_, -dx / L_) if not cw else (-dy / L_, dx / L_)
        n1, n2 = nrm(a, b), nrm(b, c); bx_, by_ = n1[0] + n2[0], n1[1] + n2[1]; d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        out.append((b[0] + m * bx_ / d, b[1] + m * by_ / d))
    return out
def band(r0, r1, a0, a1, n=48):
    return [(r1 * math.cos(math.radians(a0 + (a1 - a0) * k / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)] + \
           [(r0 * math.cos(math.radians(a1 - (a1 - a0) * k / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * k / n))) for k in range(n + 1)]
TOP, BOT = pcbnew.LSET(), pcbnew.LSET(); TOP.AddLayer(pcbnew.F_Cu); BOT.AddLayer(pcbnew.B_Cu)
BOTH = pcbnew.LSET(); BOTH.AddLayer(pcbnew.F_Cu); BOTH.AddLayer(pcbnew.B_Cu)
BLOCK_KO = 0.4                                                 # the copied reader (fixed) is kept out of, this far inside its window
ko = [(TOP, band(*UG_BAND, -1, 181)), (TOP, band(*UG_BAND, 179, 361)), (BOTH, grow(block_poly, -BLOCK_KO))]
for cx, cy in GEO["clamps"]:                                   # the clamp screw holes: the router misses their edge clearance
    rc = PR["clamp_d"] / 2 + ds.m_CopperEdgeClearance / 1e6 + KO_M
    ko.append((BOTH, [(cx + rc * math.cos(math.radians(a_)), cy + rc * math.sin(math.radians(a_))) for a_ in range(0, 360, 15)]))
for i, pt, P, *_ in LEDS:
    ko.append((BOT, grow([P(u, o) for u, o in LED_KO], KO_M)))
g0, g1 = ring_pt(3.2, UG["gap_gnd"]), ring_pt(UG["R"] + UG["v_gnd"], UG["gap_gnd"])          # the GND stub (bottom) to its via
gd = (g1[0] - g0[0], g1[1] - g0[1]); gl = math.hypot(*gd); gn = (-gd[1] / gl * (0.15 + KO_M + 0.3), gd[0] / gl * (0.15 + KO_M + 0.3))
ko.append((BOT, [(g0[0] + gn[0], g0[1] + gn[1]), (g1[0] + gn[0], g1[1] + gn[1]), (g1[0] - gn[0], g1[1] - gn[1]), (g0[0] - gn[0], g0[1] - gn[1])]))
def r_max(t):
    if t.GetClass() == "PCB_VIA": return math.hypot(*X.xy(t))
    return max(math.hypot(pcbnew.ToMM(q.x) - 100, 100 - pcbnew.ToMM(q.y)) for q in (t.GetStart(), t.GetEnd()))
def mid(t):
    if t.GetClass() == "PCB_VIA": return X.xy(t)
    a_, b_ = src_xy(t.GetStart()), src_xy(t.GetEnd()); return ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
def in_poly(pt, poly):
    sgn = [((b_[0] - a_[0]) * (pt[1] - a_[1]) - (b_[1] - a_[1]) * (pt[0] - a_[0])) > 0 for a_, b_ in zip(poly, poly[1:] + poly[:1])]
    return all(sgn) or not any(sgn)
# the copied reader is fixed: on the router's copy only its exit stubs stay (it would try to fan out all its pads)
reader_refs = {RREF(sf.GetReference()) for sf in SRC.GetFootprints() if sf.GetReference() not in READER["left_behind"]}
j.SetDNP(False)                                                # (DNP parts are left out of the router's file: J1 must be in)
X.route_without(["COIL"], remove=lambda t: (t.GetNetname() in UG_NETS and UG_INNER < r_max(t) < UG_OUTER) or in_poly(mid(t), block_poly),
                remove_refs={f"{p_}{k + 1}" for k in range(NL) for p_ in ("D", "C")} | reader_refs, keepouts=ko, terminals=exits)
j.SetDNP(True)
X.clean_route()
X.pour(pcbnew.B_Cu, block_poly); X.pour(pcbnew.F_Cu, block_poly)
LEG = [f"{k} {CABLE[k].lstrip('+').replace('D1_DIN', 'DIN')}" for k in sorted(CABLE, key=int)]
LEG_ROWS, LEG_AT, LEG_DY, LEG_SZ = 4, (-15, -24.0), 1.3, 0.7                         # J1's legend: 4 holes a line, under the title
TEXTS = [("J1", (0, 5.0), 0.7), ("BugBot NFC floor v3", (-15, -22), 1.2)] +         [(("J1: " if i == 0 else "") + "  ".join(LEG[i:i + LEG_ROWS]), (LEG_AT[0], LEG_AT[1] - LEG_DY * (i // LEG_ROWS)), LEG_SZ) for i in range(0, len(LEG), LEG_ROWS)]
for txt, (tx, ty), sz in TEXTS:
    layer = pcbnew.B_SilkS
    t = pcbnew.PCB_TEXT(X.board); t.SetText(txt); t.SetPosition(X.P(tx, ty)); t.SetLayer(layer); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(sz), mm(sz))); t.SetTextThickness(mm(0.15)); X.board.Add(t)
X.board.BuildConnectivity()
X.save(None)
_fb = pcbnew.LoadBoard(X.pcb); pcbnew.ZONE_FILLER(_fb).Fill(_fb.Zones()); pcbnew.SaveBoard(X.pcb, _fb)   # fill on a fresh load (it crashes in-place)
X.project_rules()                                              # (after the last save: saving rewrites the project's rules)
_t = open(X.pcb, encoding="utf-8").read()                      # stackup with the colours: green mask, white silk
if "(stackup" not in _t:
    STACKUP = ['(layer "F.SilkS" (type "Top Silk Screen") (color "White"))', '(layer "F.Paste" (type "Top Solder Paste"))',
               '(layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))', '(layer "F.Cu" (type "copper") (thickness 0.035))',
               '(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))',
               '(layer "B.Cu" (type "copper") (thickness 0.035))', '(layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))',
               '(layer "B.Paste" (type "Bottom Solder Paste"))', '(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))',
               '(copper_finish "HAL SnPb")', '(dielectric_constraints no)']
    block = "\t(setup\n\t\t(stackup\n" + "".join("\t\t\t" + l_ + "\n" for l_ in STACKUP) + "\t\t)\n"
    _t = _t.replace("\t(setup\n", block, 1)
    open(X.pcb, "w", encoding="utf-8").write(_t)
    print("stackup: green mask written" if "(stackup" in _t else "stackup: (setup not found")
pro = f"{X.out}/{X.prj}.kicad_pro"; dj = json.load(open(pro))
dj["board"]["design_settings"]["rules"].update(min_copper_edge_clearance=0.3)
json.dump(dj, open(pro, "w"), indent=2)
g = X.jlc_files()
json.dump({"floor_pcb": {"thickness": PR["thickness"], "clamps": GEO["clamps"], "cable_holes": [cable_xy[k] for k in sorted(cable_xy, key=int)],
                         "reader_block": block_poly}},
          open(f"{X.out}/mcad.json", "w"), indent=1)
tr = [t for t in X.board.GetTracks() if t.GetClass() == "PCB_TRACK"]
print("floor pcb:", len(X.fps), "parts,", len(tr), "tracks")
