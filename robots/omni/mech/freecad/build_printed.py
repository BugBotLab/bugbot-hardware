# BugBot in FreeCAD: the printed parts (each its own PartDesign body, all driven by the Params sheet).
# Built in place (robot coordinates, gripper closed), as in bugbot_chassis.scad, so the assembly can join them as they sit.
# Run after build_chassis.py / build_pcb_caps.py:  python fusionflow/ffclient.py run mech/freecad/build_printed.py
import os, traceback
from fusionflow import params as P, helpers as H, extrude as X

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = _os.path.join(BB, "bugbot_freecad")
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())

doc = App.getDocument("BugBot_Base")
App.setActiveDocument("BugBot_Base")
P.set_params(PARAMS, doc)
ONLY = globals().get("ONLY")          # set ONLY = ["Mast"] before exec to rebuild just some parts

ORANGE, GREY, RED, WHITE, BLACK = (0.95, 0.55, 0.2), (0.85, 0.85, 0.85), (0.95, 0.3, 0.25), (1.0, 1.0, 1.0), (0.15, 0.15, 0.17)
BIG = "200 mm"


def sector2d(s, tag, r1, r2, a0, a1):
    """Annular sector about the origin: r1..r2 (expressions), angles a0..a1 (deg, numbers)."""
    import Part, Sketcher
    q1, q2 = ev(E(r1)), ev(E(r2)); t0, t1 = math.radians(a0), math.radians(a1)
    o = App.Vector(0, 0, 0); n = App.Vector(0, 0, 1)
    A2 = s.addGeometry(Part.ArcOfCircle(Part.Circle(o, n, q2), t0, t1), False)
    A1 = s.addGeometry(Part.ArcOfCircle(Part.Circle(o, n, q1), t0, t1), False)
    P = lambda r, t: App.Vector(r * math.cos(t), r * math.sin(t), 0)
    L0 = s.addGeometry(Part.LineSegment(P(q1, t0), P(q2, t0)), False)
    L1 = s.addGeometry(Part.LineSegment(P(q2, t1), P(q1, t1)), False)
    s.addConstraint([Sketcher.Constraint("Coincident", A1, 3, -1, 1), Sketcher.Constraint("Coincident", A2, 3, -1, 1),
                     Sketcher.Constraint("Coincident", L0, 1, A1, 1), Sketcher.Constraint("Coincident", L0, 2, A2, 1),
                     Sketcher.Constraint("Coincident", L1, 1, A2, 2), Sketcher.Constraint("Coincident", L1, 2, A1, 2)])
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("Radius", A1, q1), Sketcher.Constraint("Radius", A2, q2)])
    _dim(s, c0, f"{tag}_r1", E(r1)); _dim(s, c0 + 1, f"{tag}_r2", E(r2))


def bayonet_angles():
    """notch centres and the channel / wedge spans (deg) from the parameters"""
    rm = num("dome_d / 2 + bay_lug_out / 2")
    a0, turn = num("bay_a0"), num("bay_turn")
    n = int(round(float(getattr(doc.Params.get("bay_n"), "Value", doc.Params.get("bay_n")))))   # a plain count (no unit)
    nh = math.degrees(num("bay_notch_w") / 2 / rm); lh = math.degrees(num("bay_lug_w") / 2 / rm)
    ra = num("bay_ramp_a")
    rs = turn + lh - ra / 2                          # ramp start: a nominal print locks the lug half way down
    end = rs + ra + 1.0                              # channel end
    return [a0 + 360 * k / n for k in range(n)], nh, lh, end, rs


def kick_bracket():
    new_body("KickBracket", ORANGE)
    y0 = "(-sol_depth / 2 - sol_dy)"; zb = "(sol_z - sol_height / 2)"
    zbox("SidePlate", ("sol_x0 - 0.5 mm", f"{y0} - kb_t", f"{zb} + 0.5 mm"),
         ("max(sol_len + 1 mm; kb_front_x + 3 mm - (sol_x0 - 0.5 mm))", "kb_t - 0.05 mm", f"pcb_z - {zb} - 0.5 mm"))
    for nm, xr, wr, boss in (("RearTab", "sol_x0 - 0.5 mm", "3 mm", ("kb_rear_x", "kb_rear_y")),
                             ("FrontTab", "sol_x0 + sol_len - 1.5 mm", "2 mm", ("kb_front_x", "kb_front_y"))):
        s = sk(nm + "Sketch", "XY", "pcb_z - 4 mm")
        ya, yb = f"{y0} - kb_t", f"{y0} - 0.05 mm"
        hull2d(s, nm, (boss[0], boss[1], "0"), "2.5 mm",
               [(xr, ya, "0"), (f"{xr} + {wr}", ya, "0"), (f"{xr} + {wr}", yb, "0"), (xr, yb, "0")])
        ext(s, "add", "4 mm", +1, nm)
    zbox("FlatInnerFace", ("-60 mm", f"{y0} - 0.05 mm", "0 mm"), ("120 mm", "60 mm", "60 mm"), "cut")   # nothing past the plate's inner face
    s = sk("M3SlotsSketch", "XZ", f"{y0} + 1 mm")
    for k, x in ((1, "sol_x0 + sol_len / 2 - 5.5 mm"), (2, "sol_x0 + sol_len / 2 + 5.5 mm")):
        zc = f"{zb} + sol_height / 2"
        slot2d(s, f"m3s{k}", (f"{x} - 3 mm", "0", zc), "1.7 mm", (f"{x} + 3 mm", "0", zc), "1.7 mm")
    ext(s, "cut", "kb_t + 2 mm", -1, "M3Slots")
    zcyl("Pilots", [("kb_rear_x", "kb_rear_y"), ("kb_front_x", "kb_front_y")], "pcb_z - 4.6 mm", "1.6 mm", "5 mm", "cut")
    # the front M3 head: sunk 0.5 into the plate (it was touching wheel 3's hub), and a relief under the front tab
    xf = "sol_x0 + sol_len / 2 + 5.5 mm"
    ycyl("HeadSeat", [(xf, "sol_z")], f"{y0} - kb_t", "6.4 mm", "0.5 mm", "cut", +1)   # ISO 7380 button head 5.7
    ycyl("HeadRelief", [(xf, "sol_z")], f"{y0} - kb_t - 4 mm", "6.2 mm", "4 mm", "cut", +1)


def kick_disc():
    new_body("KickDisc", BLACK)
    x0 = "(sol_x0 + sol_len)"; c = ("0", "-sol_dy", "sol_z")
    xcyl("Disc", [("-sol_dy", "sol_z")], x0, "kd_d", "sol_out")
    s = sk("NutPocketSketch", "YZ", f"{x0} - 0.01 mm"); hex2d(s, "nut", c, "kd_nut_af")
    ext(s, "cut", "kd_nut_t", +1, "NutPocket")
    xcyl("StudHole", [("-sol_dy", "sol_z")], f"{x0} - 1 mm", "2 mm", "5 mm", "cut")


def batt_cradle():
    new_body("BattCradle", GREY)
    zbox("Block", ("batt_x - cell_d / 2 - cradle_t", "-cell_l / 2 - cradle_gap - cradle_t", "pcb_top"),
         ("cell_d + 2 * cradle_t", "cell_l + 2 * cradle_gap + 2 * cradle_t", "cell_d * 0.6"))
    ycyl("CellSeat", [("batt_x", "pcb_top + cradle_t + cell_d / 2")], "-cell_l / 2 - cradle_gap", "cell_d + 0.4 mm", "cell_l + 2 * cradle_gap", "cut", +1)
    zbox("StrapSlot", ("batt_x - cell_d / 2 - 5 mm", "-4 mm", "pcb_top + cradle_t + 2 mm"), ("cell_d + 10 mm", "8 mm", "1.6 mm"), "cut")
    zbox("LeadExit", ("batt_x - 2 mm", "-cell_l / 2 - 5 mm", "pcb_top + cradle_t + cell_d / 2 - 2 mm"), ("4 mm", "6 mm", "4 mm"), "cut")   # both leads pass
    zcyl("Pilots", [("batt_sc1_x", "batt_sc1_y"), ("batt_sc2_x", "batt_sc2_y")], "pcb_top - 1 mm", "1.6 mm", "5 mm", "cut")
    zcyl("ScrewRelief", [("boss_r * cos(boss_a3)", "boss_r * sin(boss_a3)")], "pcb_top - 1 mm", "4.4 mm", "3 mm", "cut")
    rbox("SwitchRelief", "sw_ang", ("sw_r - 7.3 mm + 0.3 mm", "-10.2 mm", "pcb_top - 1 mm"), ("2.8 mm", "20.4 mm", "2.4 mm"), "cut")


def dome():
    new_body("Dome", WHITE)
    z = E("mast_top + deck_t - dome_groove")             # the rim, in the groove
    zc = f"{z} + {E('dome_skirt')}"                         # the hemisphere starts above the bayonet collar
    for nm, typ, r in (("Shell", "PartDesign::AdditiveSphere", "dome_d / 2"), ("Hollow", "PartDesign::SubtractiveSphere", "dome_d / 2 - dome_wall")):
        o = body.newObject(typ, nm)
        o.setExpression("Radius", E(r)); o.setExpression(".Placement.Base.z", zc)
    b = body.newObject("PartDesign::SubtractiveBox", "BelowEquator")
    for p, e in (("Length", "2 * dome_d"), ("Width", "2 * dome_d"), ("Height", "dome_d")):
        b.setExpression(p, E(e))
    b.setExpression(".Placement.Base.x", E("-dome_d")); b.setExpression(".Placement.Base.y", E("-dome_d"))
    b.setExpression(".Placement.Base.z", f"{zc} - {E('dome_d')}")
    doc.recompute()
    c = body.newObject("PartDesign::AdditiveCylinder", "Skirt")
    c.setExpression("Radius", E("dome_d / 2")); c.setExpression("Height", E("dome_skirt")); c.setExpression(".Placement.Base.z", z)
    c = body.newObject("PartDesign::SubtractiveCylinder", "SkirtBore")
    c.setExpression("Radius", E("dome_d / 2 - dome_wall")); c.setExpression("Height", f"{E('dome_skirt')} + 0.02 mm"); c.setExpression(".Placement.Base.z", f"{z} - 0.01 mm")
    doc.recompute()
    # bayonet lugs on the rim, shown turned and locked (bay_turn past each notch)
    cen, nh, lh, end, ra = bayonet_angles()
    s = sk("LugSketch", "XY", "mast_top + deck_t + bay_lug_z")
    for k, a in enumerate(cen):
        sector2d(s, f"lug{k}", "dome_d / 2 - 0.3 mm", "dome_d / 2 + bay_lug_out", a + num("bay_turn") - lh, a + num("bay_turn") + lh)
    ext(s, "add", "bay_lug_h", +1, "Lugs")


def mast():
    new_body("Mast", GREY)
    hgt = "mast_top - pcb_top"
    zbox("Base", ("mast_x - 3.5 mm", "-mast_w / 2", "pcb_top"), ("6.5 mm", "mast_w", "2 mm"))
    zbox("Plate", ("mast_x", "-mast_w / 2", "pcb_top"), ("3 mm", "mast_w", hgt))
    # full-height corner columns at both plate ends: they brace the plate and give the M2 screws (board below, deck above)
    # solid plastic all round instead of the 3 mm plate
    zbox("ColumnR", ("mast_x - 3.5 mm", "-mast_w / 2", "pcb_top"), ("6.5 mm", "mast_col_w", hgt))
    zbox("ColumnL", ("mast_x - 3.5 mm", "mast_w / 2 - mast_col_w", "pcb_top"), ("6.5 mm", "mast_col_w", hgt))
    zbox("EarBoss", ("servo_x0 + servo_l + 0.3 mm", "ear_y + 0.15 mm", "pcb_top"), ("mast_x - (servo_x0 + servo_l + 0.3 mm)", "4 mm", "servo_t"))
    zbox("CameraWindow", ("mast_x - 1 mm", "-cam_win / 2", "cam_z - cam_win / 2"), ("5 mm", "cam_win", "cam_win"), "cut")
    zbox("ToFWindow", ("mast_x - 1 mm", "-tof_win_w / 2", "tof_z - tof_win_h / 2"), ("5 mm", "tof_win_w", "tof_win_h"), "cut")
    # relief on the inside face over the camera flex's bend into the board slot (0.4 clear all round for a rough print)
    zbox("FlexRelief", ("mast_x - 0.1 mm", "-fsb_slot_w / 2 - 0.2 mm", "cam_z + cam_mod / 2 - 0.6 mm"),
         ("1 mm", "fsb_slot_w + 0.4 mm", "fsb_slot_z0 + fsb_slot_h - (cam_z + cam_mod / 2) + 1 mm"), "cut")
    zbox("PinPocket", ("mast_x - 0.1 mm", "fsb_sock_y - hdr_n * 0.635 mm - 0.8 mm", "hdr_zm - 2.07 mm"), ("1.3 mm", "hdr_n * 1.27 mm + 1.6 mm", "2.87 mm"), "cut")
    xcyl("BoardPilots", [("fsb_y0 + 2 mm", "fsb_z0 + fsb_h - 2 mm")],                      # one M2 screw holds the board
         "mast_x - 1 mm", "1.6 mm", "3.2 mm", "cut", +1)
    zbox("SocketCut", ("fsb_sock_x - 3.4 mm", "fsb_sock_y - hdr_n * 0.635 mm - 1.0 mm", "pcb_top - 1 mm"), ("mast_x + 0.2 mm - (fsb_sock_x - 3.4 mm)", "hdr_n * 1.27 mm + 2.0 mm", "fsb_z0 - pcb_top + 1 mm"), "cut")
    zbox("BallClear", ("mast_x - 1 mm", "-13.5 mm", "pcb_top - 1 mm"), ("5 mm", "27 mm", "34.5 mm - pcb_top + 1 mm"), "cut")
    ycyl("EarScrew", [("ear_x1", "pivot_z")], "ear_y - 1 mm", "1.6 mm", "6 mm", "cut", +1)
    zbox("EarNotch", ("servo_x0 + servo_l + 0.2 mm", "ear_y - 2.8 mm", "pcb_top - 1 mm"), ("mast_x + 0.8 mm - (servo_x0 + servo_l + 0.2 mm)", "3.1 mm", "servo_t + 2 mm"), "cut")
    screws = [("mast_screw_x", "-mast_screw_y"), ("mast_screw_x", "mast_screw_y")]
    zcyl("BaseScrews", screws, "pcb_top - 1 mm", "1.6 mm", "7 mm", "cut")
    for sg in (1, -1):        # spigots: the column tops behind the front plate, they locate the deck
        zbox(f"Spigot{'L' if sg > 0 else 'R'}", ("mast_x - 3.5 mm", "mast_w / 2 - mast_col_w" if sg > 0 else "-mast_w / 2", "mast_top - 0.01 mm"),
             ("3.5 mm", "mast_col_w", "mast_spigot + 0.01 mm"))
    zcyl("DeckPilots", screws, "mast_top - 6 mm", "1.6 mm", "8 mm", "cut")
    xs = (num("mast_x + 3 mm"),); yw = num("mast_w / 2")          # front corners only: the back stays square (the user's choice)
    pick = lambda e: (e.Curve.TypeId == "Part::GeomLine" and abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) > 1 and
                      all(min(abs(v.Point.x - x) for x in xs) < 1e-3 and abs(abs(v.Point.y) - yw) < 1e-3 for v in e.Vertexes))
    fillet(body.Tip, "mast_r", pick, "Corners")


def top_deck():
    new_body("TopDeck", GREY)
    s = sk("DeckSketch", "XY", "mast_top")
    # symmetric: the round part, lugs round the two rear standoffs, and the mast top (corners r 0.6) as wide as the mast
    c, cb = "mast_r", "0.05 mm"                 # front corners R0.6 like the mast's; back corners square, flush with it
    hull_circles2d(s, "deck", [("0 mm", "0 mm", "deck_r"),
                               ("deck_leg_x", "deck_leg_y", "deck_lug_r"), ("deck_leg_x", "-deck_leg_y", "deck_lug_r"),
                               (f"mast_x + 3 mm - {c}", f"mast_w / 2 - {c}", c), (f"mast_x + 3 mm - {c}", f"-mast_w / 2 + {c}", c),
                               (f"mast_x - 3.5 mm + {cb}", f"mast_w / 2 - {cb}", cb), (f"mast_x - 3.5 mm + {cb}", f"-mast_w / 2 + {cb}", cb)])
    ext(s, "add", "deck_t", +1, "Deck")
    legs = [("deck_leg_x", "deck_leg_y"), ("deck_leg_x", "-deck_leg_y")]
    zcyl("StandoffSockets", legs, "mast_top - 1 mm", "standoff_d + 2 * fit_loc", "1.5 mm", "cut")     # 0.5 mm locating sockets
    zcyl("StandoffScrews", legs, "mast_top - 1 mm", "m2_clear", "deck_t + 2 mm", "cut")
    zcyl("MastScrews", [("mast_screw_x", "-mast_screw_y"), ("mast_screw_x", "mast_screw_y")], "mast_top - 1 mm", "m2_clear", "deck_t + 2 mm", "cut")
    zcyl("WireHole", [("0", "0")], "mast_top - 1 mm", "6.5 mm", "deck_t + 2 mm", "cut")
    # the LED ring board: 2 bosses under the deck, a 2.4 hole through deck + boss, and a slot open to -Y for an M2 nut
    for sg, nm in ((1, "R"), (-1, "L")):
        x = f"{sg} * led_screw_r"
        zbox(f"LedBoss{nm}", (f"{x} - led_boss_w / 2", "led_boss_dy - led_boss_d / 2", "mast_top - led_boss_h"), ("led_boss_w", "led_boss_d", "led_boss_h + 0.01 mm"))
        zcyl(f"LedScrewHole{nm}", [(x, "0 mm")], "mast_top - led_boss_h - 1 mm", "2.4 mm", "led_boss_h + deck_t + 2 mm", "cut")
        zbox(f"LedNutSlot{nm}", (f"{x} - led_slot_w / 2", "led_boss_dy - led_boss_d / 2 - 1 mm", "mast_top - led_boss_h + led_slot_z"),
             ("led_slot_w", "led_boss_d / 2 - led_boss_dy + 1 mm + led_slot_end", "led_slot_h"), "cut")
    for sg in (1, -1):        # pockets over the mast spigots: 0.1 clear, walled behind, in front and inside, open to the side
        zbox(f"SpigotPocket{'L' if sg > 0 else 'R'}", ("mast_x - 3.5 mm - fit_loc", "mast_w / 2 - mast_col_w - fit_loc" if sg > 0 else "-mast_w / 2 - 1 mm", "mast_top - 0.01 mm"),
             ("3.5 mm + 2 * fit_loc", "mast_col_w + fit_loc + 1 mm", "mast_spigot + fit_loc"), "cut")
    s = sk("DomeGrooveSketch", "XY", "mast_top + deck_t - dome_groove")
    circle2d(s, "gro", ("0", "0", "0"), "dome_d + 2 * fit_loc + 0.1 mm"); circle2d(s, "gri", ("0", "0", "0"), "dome_d - 2 * dome_wall - 2 * fit_loc - 0.1 mm")
    ext(s, "cut", "1 mm", +1, "DomeGroove")
    # dome bayonet: a collar round the groove; per lug an entry notch, a channel under a lip, and a wedge at its end
    ro = "dome_d / 2 + fit_loc + 0.05 mm"; rch = "dome_d / 2 + bay_lug_out + bay_ch_clr"; rc = f"{rch} + bay_skin"
    s = sk("CollarSketch", "XY", "mast_top + deck_t")
    circle2d(s, "col_o", ("0", "0", "0"), f"2 * ({rc})"); circle2d(s, "col_i", ("0", "0", "0"), f"2 * ({ro})")
    ext(s, "add", "bay_ch_h + bay_lip", +1, "Collar")
    cen, nh, lh, end, rs = bayonet_angles()
    s = sk("NotchSketch", "XY", "mast_top + deck_t - 0.01 mm")
    for k, a in enumerate(cen):
        sector2d(s, f"notch{k}", f"{ro} - 0.2 mm", f"{rc} + 0.5 mm", a - nh, a + nh)
    ext(s, "cut", "bay_ch_h + bay_lip + 0.02 mm", +1, "Notches")
    s = sk("ChannelSketch", "XY", "mast_top + deck_t - 0.01 mm")
    for k, a in enumerate(cen):
        sector2d(s, f"chan{k}", f"{ro} - 0.2 mm", rch, a + nh - 0.5, a + end)
    ext(s, "cut", "bay_ch_h + 0.01 mm", +1, "Channels")
    ra = num("bay_ramp_a"); steps = 5
    for i in range(steps):                         # the ramp: 5 steps of bay_ramp / 5 (each under one layer, so it prints as a slope)
        s = sk(f"RampSketch{i}", "XY", f"mast_top + deck_t + bay_ch_h - (bay_ramp) * {(i + 1) / steps:.3f}")
        for k, a in enumerate(cen):
            sector2d(s, f"ramp{i}_{k}", f"{ro} - 0.01 mm", f"{rch} + 0.01 mm", a + rs + ra * i / steps, a + end)
        ext(s, "add", f"(bay_ramp) / {steps} + 0.01 mm", +1, f"Ramp{i}")


def servo_block():
    new_body("ServoBlock", GREY)
    zbox("Block", ("servo_x0 - 4.6 mm + 0.2 mm", "ear_y + 0.15 mm", "pcb_top"), ("4.2 mm", "4 mm", "servo_t"))
    ycyl("EarScrew", [("ear_x0", "pivot_z")], "ear_y - 1 mm", "1.6 mm", "6 mm", "cut", +1)
    zcyl("BoardScrew", [("servo_x0 - 2.3 mm", "ear_y + 2.15 mm")], "pcb_top - 1 mm", "1.6 mm", "6 mm", "cut")


def hoop_bracket():
    new_body("HoopBracket", GREY)
    y1 = "(-hoop_y - arm_t / 2 - 0.4 mm)"; yb = "-29.5 mm"
    rect_pts = [("pivot_x - 4 mm", "0", "pcb_top"), ("pivot_x + 4 mm", "0", "pcb_top"),
                ("pivot_x + 4 mm", "0", "pcb_top + 2 mm"), ("pivot_x - 4 mm", "0", "pcb_top + 2 mm")]
    zbox("Base", ("pivot_x - 4 mm", yb, "pcb_top"), ("8 mm", f"{y1} - ({yb})", "2 mm"))
    s = sk("PostSketch", "XZ", y1)
    hull2d(s, "post", ("pivot_x", "0", "pivot_z"), "3.5 mm", rect_pts)
    ext(s, "add", "3.2 mm", -1, "Post")
    # the hull's sloping back: a ruled loft from the post's back face down to the far end of the base
    s1 = sk("ButtressEnd", "XZ", yb)
    box2d(s1, "bend", ("pivot_x - 4 mm", "0", "pcb_top"), ("8 mm", "0", "2 mm"))
    s2 = sk("ButtressStart", "XZ", f"{y1} - 3.2 mm")
    hull2d(s2, "bst", ("pivot_x", "0", "pivot_z"), "3.5 mm", rect_pts)
    doc.recompute()
    lo = body.newObject("PartDesign::AdditiveLoft", "Buttress")
    lo.Profile = s2; lo.Sections = [s1]; lo.Ruled = True
    doc.recompute()
    s1.ViewObject.Visibility = False; s2.ViewObject.Visibility = False
    ycyl("Axle", [("pivot_x", "pivot_z")], f"{y1} + 1 mm", "m2_clear", "10 mm", "cut", -1)
    ycyl("HeadSeat", [("pivot_x", "pivot_z")], f"{y1} - 3.2 mm", "4.4 mm", "5 mm", "cut", -1)   # the M2 head seats on the post
    zcyl("BoardScrews", [("pivot_x - hoopbr_dx", "hoopbr_y"), ("pivot_x + hoopbr_dx", "hoopbr_y")], "pcb_top - 1 mm", "1.6 mm", "6 mm", "cut")


def hoop_arm(side):
    nm = "HoopArmL" if side > 0 else "HoopArmR"     # robot's left (+Y, servo side) / right (-Y)
    new_body(nm, RED)
    sg = "" if side > 0 else "-"
    yc = f"{sg}hoop_y"; w2 = "arm_w / 2"
    px, pz, sx, gx, gz = "pivot_x", "pivot_z", "step_x", "grip_x", "grip_z"
    pts = [(px, 0, f"{pz} - {w2}"), (f"{sx} - {w2}", 0, f"{pz} - {w2}"), (f"{sx} - {w2}", 0, f"{gz} - {w2}"), (gx, 0, f"{gz} - {w2}"),
           (gx, 0, f"{gz} + {w2}"), (f"{sx} + {w2}", 0, f"{gz} + {w2}"), (f"{sx} + {w2}", 0, f"{pz} + {w2}"), (px, 0, f"{pz} + {w2}")]
    s = sk("ArmSketch", "XZ", yc); poly2d(s, "arm", pts)
    arm = ext(s, "add", "arm_t", +1, "Arm", mid=True)
    # round the step: inside corners r 2, outside corners r 1
    cx = [(num(f"{sx} - {w2}"), num(f"{pz} - {w2}"), 2), (num(f"{sx} + {w2}"), num(f"{gz} + {w2}"), 2),
          (num(f"{sx} - {w2}"), num(f"{gz} - {w2}"), 1), (num(f"{sx} + {w2}"), num(f"{pz} + {w2}"), 1)]
    last = arm
    for r in (2, 1):
        pick = lambda e, r=r: (e.Curve.TypeId == "Part::GeomLine" and abs(e.Vertexes[0].Point.y - e.Vertexes[-1].Point.y) > 1 and
                               any(abs(e.Vertexes[0].Point.x - x) < 1e-3 and abs(e.Vertexes[0].Point.z - z) < 1e-3 for x, z, rr in cx if rr == r))
        last, names = fillet(last, f"{r} mm", pick, f"Step{'Inside' if r == 2 else 'Outside'}")
    s = sk("BossesSketch", "XZ", yc)
    circle2d(s, "tip", (gx, 0, gz), "tip_boss_d")
    if side < 0:
        circle2d(s, "piv", (px, 0, pz), "pivot_boss_d")
    ext(s, "add", "arm_t", +1, "Bosses", mid=True)
    # the root: a taper from the pivot boss into the arm, no sharp step (the servo-stall stress concentrated there)
    s = sk("RootSketch", "XZ", yc)
    slot2d(s, "root", (px, 0, pz), "drive_boss_d / 2" if side > 0 else "pivot_boss_d / 2", (f"{px} + arm_root_l", 0, pz), "arm_w / 2")
    ext(s, "add", "arm_t", +1, "Root", mid=True)
    if side > 0:
        # the horn pad: the SG90 horn's outline + horn_fit + horn_wall, on the arm, the pad and a pocket wall round the horn
        out = [(px, pz, "horn_hub_r + horn_fit + horn_wall"),
               (px, f"{pz} + horn_grip", "horn_hub_r - (horn_hub_r - horn_tip_r) * horn_grip / horn_len + horn_fit + horn_wall_tip")]
        pocket = [(px, pz, "horn_hub_r + horn_fit"), (px, f"{pz} + horn_len", "horn_tip_r + horn_fit")]
        s = sk("DriveSketch", "XZ", yc)       # pivot boss + the horn-pad outline, so the pad prints on solid arm
        hull_circles2d(s, "drv", out)
        ext(s, "add", "arm_t", +1, "HornBack", mid=True)
        s = sk("DriveBossSketch", "XZ", yc); circle2d(s, "dboss", (px, 0, pz), "drive_boss_d")
        ext(s, "add", "arm_t", +1, "DriveBoss", mid=True)
        s = sk("HornPadSketch", "XZ", "horn_y")
        hull_circles2d(s, "pad", out)
        ext(s, "add", "hoop_y - arm_t / 2 - horn_y + 0.01 mm", +1, "HornPad")
        s = sk("HornWallSketch", "XZ", "horn_y - horn_seat")          # the wall round the horn: it locates and drives it
        hull_circles2d(s, "pko", out)
        ext(s, "add", "horn_seat + 0.01 mm", +1, "HornWall")
        s = sk("HornPocketSketch", "XZ", "horn_y - horn_seat - 0.01 mm") # the horn's own outline + fit, open past horn_grip
        hull_circles2d(s, "pki", pocket)
        ext(s, "cut", "horn_seat + 0.01 mm", +1, "HornPocket")
    ycyl("PinBoss", [(gx, gz)], f"{sg}(hoop_y - arm_t / 2)", "tip_boss_d", "tip_boss_l", "add", -side)
    ycyl("PivotHole", [(px, pz)], "0 mm", "4.5 mm" if side > 0 else "bush_hole", "0", "cut", mid=True, kind="ThroughAll")
    if side < 0:              # the bronze bushing's flange sits in a recess in the outer face
        ycyl("FlangeRecess", [(px, pz)], "-(hoop_y + arm_t / 2)", "bush_fl_d + 2 * fit_loc", "bush_recess", "cut", +1)
    if side > 0:
        ycyl("HornPilots", [(px, f"{pz} + 4.5 mm"), (px, f"{pz} + 8.5 mm")], "horn_y - 0.01 mm", "1 mm", "4 mm", "cut", +1)
        # the walls round the horn end square at horn_grip (no thin crescents where the open pocket runs on)
        zbox("HornWallEnd", ("pivot_x - 10 mm", "horn_y - horn_seat - 0.02 mm", "pivot_z + horn_grip"), ("20 mm", "horn_seat + 0.02 mm", "20 mm"), "cut")
    # front bar: M3 through both tips, the brass tube seated bar_seat deep in each boss, the nut captive in arm L
    ycyl("BarHole", [(gx, gz)], "0 mm", "bar_hole_d", "0", "cut", mid=True, kind="ThroughAll")
    if side > 0:
        s = sk("NutPocketSketch", "XZ", "hoop_y + arm_t / 2")
        hex2d(s, "nut", (gx, 0, gz), "bar_nut_af + 0.3 mm")
        ext(s, "cut", "bar_nut_depth", -1, "NutPocket")
    else:
        ycyl("HeadSeat", [(gx, gz)], "-(hoop_y + arm_t / 2)", "bar_cb_d", "bar_cb_h", "cut", +1)   # the head sinks in flush


def deck_standoffs():
    """Printed PLA standoffs (board to deck): M2 self-tappers from under the board and from the deck top. Print lying down."""
    new_body("DeckStandoffs", (1.0, 0.77, 0.0))
    body.AllowCompound = True
    legs = [("deck_leg_x", "deck_leg_y"), ("deck_leg_x", "-deck_leg_y")]
    zcyl("Standoff", legs, "pcb_top", "standoff_d", "mast_top - pcb_top")
    zcyl("ThreadLow", legs, "pcb_top - 0.01 mm", "1.6 mm", "6 mm", "cut")
    zcyl("ThreadHigh", legs, "mast_top - 6 mm", "1.6 mm", "6.01 mm", "cut")


def hoop_sleeve():
    """PETG / nylon sleeve on the front bar's steel dowel: a clearance fit, so it spins and a ball pressed by the bar
    rolls in under it (a fixed, grippy sleeve wedged the ball in the simulator)."""
    new_body("HoopSleeve", (0.25, 0.27, 0.3))
    ycyl("Tube", [("grip_x", "grip_z")], "-sleeve_l / 2", "sleeve_d", "sleeve_l", "add", +1)
    ycyl("Bore", [("grip_x", "grip_z")], "0 mm", "sleeve_bore", "0", "cut", mid=True, kind="ThroughAll")


PARTS = [("KickBracket", kick_bracket), ("KickDisc", kick_disc), ("Dome", dome), ("Mast", mast),
         ("TopDeck", top_deck), ("ServoBlock", servo_block), ("HoopBracket", hoop_bracket),
         ("HoopArmL", lambda: hoop_arm(+1)), ("HoopArmR", lambda: hoop_arm(-1)), ("HoopSleeve", hoop_sleeve),
         ("DeckStandoffs", deck_standoffs)]
report = {}
for name, fn in PARTS:
    if ONLY and name not in ONLY:
        continue
    try:
        fn()
        doc.recompute()
        if name == "DeckStandoffs":      # the rear ID tag bar: ring grooves in the rear posts, and the bar (tag_mounts.py)
            import sys as _sys, importlib as _il
            _sys.path.insert(0, OUT)
            import tag_mounts as _tm; _il.reload(_tm)
            _tm.standoff_grooves(doc, doc.getObject("DeckStandoffs"))
            _tm.tag_bar(doc)
        b = doc.getObject(name)
        bad = [o.Label for o in b.Group if hasattr(o, "isValid") and not o.isValid()]
        report[name] = {"bad": bad, **H.info(b)}
    except Exception:
        report[name] = {"error": traceback.format_exc()[-600:]}
doc.save()
result = report
