# BugBot NFC flex-ring antenna (approved 2D: mech/freecad/sketches/nfc_flex_ring.png), generated.
#   C:/Python312/python.exe design/lib/nfc_flex_geom.py                                   (geometry, needs shapely)
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_nfc_flex.py              (this: the KiCad project)
# BugBot_NFCflex  JLC 2-layer flex PCB, 0.12 mm (25 um PI, 1 oz), yellow coverlay, glued flat under the floor plate:
#                 a 3-turn loop round the floor edge, a tail at 128 deg and a round end (r 11) at the robot centre with an
#                 upright JST-SH 2 on top; FR4 stiffener 0.8 on top of the round end (in the old coil pocket), with a
#                 window for the connector. Replaces BugBot_NFCcoil; the reader board (BugBot_NFC) and its cable are unchanged.
import json, math, os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "make_nfc_boards.py"), encoding="utf-8").read()
exec(_src[:_src.index("# ================================================================== the reader board")])   # Design + helpers

GEO = json.load(open(f"{ROOTDIR}/schematics/retired/NFCflex/flex_geom.json"))
PR = GEO["params"]
X = Design("BugBot_NFCflex", "BugBot NFC flex-ring antenna",
           [f"JLC flex 2-layer 0.12 mm (25 um PI, 1 oz), yellow coverlay; FR4 stiffener 0.8 on top of the round end (User.1)",
            f"{PR['NT']}-turn loop {PR['TW']} / {PR['GAP']} round the floor edge, glued under the floor plate; replaces BugBot_NFCcoil",
            "One copper path J1 pin 1 -> loop -> pin 2 (net COIL). L ~2.7-3 uH (lib/coil_inductance.py): retune the reader"], {})
X.part("J1", "Connector_Generic:Conn_01x02", "Antenna (JST-SH 2)",
       "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical", {"1": "COIL", "2": "COIL"}, (60, 60),
       ("BM02B-SRSS-TB(LF)(SN)", "C160388"))
X.schematic(flags=())
X.new_board(0.12)
ds = X.board.GetDesignSettings()
ds.m_CopperEdgeClearance = mm(0.2); ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15)
nc = ds.m_NetSettings.GetDefaultNetclass(); nc.SetTrackWidth(mm(PR["TW"])); nc.SetClearance(mm(0.15))
nc.SetViaDiameter(mm(PR["via"][0])); nc.SetViaDrill(mm(PR["via"][1]))

# outline (exterior + the one hole between the ring, the tail and the round end)
for ring in GEO["outline"]:
    pts = [tuple(p) for p in ring]
    if math.dist(pts[0], pts[-1]) < 1e-6: pts = pts[:-1]
    keep = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, keep[-1]) > 0.01: keep.append(p)
    if math.dist(keep[0], keep[-1]) <= 0.01: keep.pop()
    X.edge_poly(keep)

# the connector: its two pins face up the tail
ta = math.radians(PR["tail_deg"]); ux, uy = math.cos(ta), math.sin(ta)
best = None
for rot in range(0, 360, 15):
    f = X.add_fp("J1", 0.0, 0.0, rot) if best is None else X.fps["J1"]
    f.SetOrientationDegrees(rot)
    pp = {p.GetNumber(): X.xy(p) for p in f.Pads() if p.GetNumber() in ("1", "2")}
    mx, my = (pp["1"][0] + pp["2"][0]) / 2, (pp["1"][1] + pp["2"][1]) / 2
    score = mx * ux + my * uy
    if best is None or score > best[0]: best = (score, rot)
j = X.fps["J1"]; j.SetOrientationDegrees(best[1])
for pd in j.Pads():
    if pd.GetNumber() == "MP": pd.SetNetCode(0)
pads = {p.GetNumber(): X.xy(p) for p in j.Pads() if p.GetNumber() in ("1", "2")}

# copper
X.track([tuple(p) for p in GEO["spiral"]], "COIL", PR["TW"], pcbnew.F_Cu)
X.via(*GEO["vias"][0], "COIL", *PR["via"]); X.via(*GEO["vias"][1], "COIL", *PR["via"])
X.track([tuple(p) for p in GEO["bottom"]], "COIL", PR["LW"], pcbnew.B_Cu)
la, lb = [tuple(p) for p in GEO["lead_a"]], [tuple(p) for p in GEO["lead_b"]]
# each lead to the nearer pad (they are 1.0 apart, as the pins)
pa = min(pads, key=lambda n: math.dist(pads[n], la[-1])); pb = "2" if pa == "1" else "1"
X.track(la + [pads[pa]], "COIL", PR["LW"], pcbnew.F_Cu)
X.track(lb + [pads[pb]], "COIL", PR["LW"], pcbnew.F_Cu)

# stiffener (FR4 0.8, top side, on the round end) on User.1, with a window round the connector's courtyard
def user_poly(pts, layer=pcbnew.User_1):
    for a, b in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(X.board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer)
        s.SetStart(X.P(*a)); s.SetEnd(X.P(*b)); s.SetWidth(mm(0.1)); X.board.Add(s)
user_poly([(PR["STIFF_R"] * math.cos(2 * math.pi * k / 96), PR["STIFF_R"] * math.sin(2 * math.pi * k / 96)) for k in range(96)])
cy = j.GetCourtyard(pcbnew.F_CrtYd).BBox()
x0, x1 = pcbnew.ToMM(cy.GetLeft()) - 100 - 0.15, pcbnew.ToMM(cy.GetRight()) - 100 + 0.15
y0, y1 = 100 - pcbnew.ToMM(cy.GetBottom()) - 0.15, 100 - pcbnew.ToMM(cy.GetTop()) + 0.15
user_poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
for txt, (tx, ty), layer, sz in (("STIFFENER FR4 0.8 TOP (User.1): round end r 10.8, window round J1", (0, -13.5), pcbnew.User_1, 0.8),
                                  ("NFC loop", (PR["STIFF_R"] - 3.5, 0), pcbnew.F_SilkS, 0.6)):
    t = pcbnew.PCB_TEXT(X.board); t.SetText(txt); t.SetPosition(X.P(tx, ty)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(sz), mm(sz))); t.SetTextThickness(mm(0.1)); X.board.Add(t)
X.save(None); X.project_rules()
pro = f"{X.out}/{X.prj}.kicad_pro"; dj = json.load(open(pro))
dj["board"]["design_settings"]["rules"].update(min_copper_edge_clearance=0.2)
json.dump(dj, open(pro, "w"), indent=2)
g = X.jlc_files()
json.dump({"flex": {"thickness": 0.12, "stiffener": {"r": PR["STIFF_R"], "t": 0.8, "window": [x0, x1, y0, y1]},
                    "connector_rot": best[1], "pads": pads}}, open(f"{X.out}/mcad.json", "w"), indent=1)
print("flex board: J1 rot", best[1], "pads", {k: [round(v, 2) for v in p] for k, p in pads.items()}, "BOM lines", len(g))
