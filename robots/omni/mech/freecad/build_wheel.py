# BugBot in FreeCAD: the 24 mm omni wheel, parametric, from micro_omni_wheel.scad (same parameters and formulas,
# all on the Params sheet: wheel_r, roller_axis_r, roller_l, wpin_d, w_* ...).
#   Wheel (component, in the DriveUnit at the axle)
#     WheelFrame       the frame both halves share (hidden): lobes, pockets, pin holes, rounded corners
#     WheelHalfOuter   WheelFrame + screw clearances + counterbores
#     WheelHalfMotor   WheelFrame + D-bore + blind pilots, placed below the mating face and turned 60 deg
#     Roller  + 5 links      TPU barrel: an arc of the rolling circle, revolved
#     WheelPin + 5 links     1 mm steel pins
# Local frame (as in the OpenSCAD assembly): axle along Z, mating face at z = 0, outer half above.
import os, math
from fusionflow import params as P, helpers as H, extrude as X
import Part, Sketcher

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = _os.path.join(BB, "bugbot_freecad")
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())
_ov = globals().get("PARAM_OVERRIDE", {})           # trial builds: {"roller_axis_r": "8 mm", ...}
PARAMS = [(n, _ov.get(n, v), *rest) for (n, v, *rest) in PARAMS]
DOCNAME = globals().get("DOC", "BugBot_Base")        # DOC = "BugBotTrial" builds the wheel in a trial copy
doc = App.getDocument(DOCNAME); App.setActiveDocument(DOCNAME)
P.set_params(PARAMS, doc)
GREY, BLACK, STEEL = (0.62, 0.63, 0.65), (0.08, 0.08, 0.09), (0.72, 0.72, 0.75)   # PETG frame, TPU rollers, steel pins
log = []

old = doc.getObject("Wheel")
if old:
    if old.TypeId == "App::Part":
        for o in list(old.Group):
            if o.isDerivedFrom("App::Link"): doc.removeObject(o.Name)
            elif not o.isDerivedFrom("App::Origin"): old.removeObject(o)
    for p in list(old.InList):
        if hasattr(p, "removeObject"): p.removeObject(old)
    doc.removeObject("Wheel")
doc.recompute()


def polar(feats, name):
    pp = body.newObject("PartDesign::PolarPattern", name)
    pp.Originals = feats
    pp.Axis = (next(o for o in body.Origin.OriginFeatures if o.Role == "Z_Axis"), [""])
    pp.Angle = 360; pp.Occurrences = int(round(num("w_n"))); pp.setExpression("Occurrences", E("w_n"))
    body.Tip = pp
    doc.recompute()
    return pp


def _unused_corner_edges(sh, convex):
    """Vertical corner edges of an extruded outline, convex or concave (tangent seams skipped)."""
    out = []
    for i, e in enumerate(sh.Edges):
        if e.Curve.TypeId != "Part::GeomLine" or abs(e.Vertexes[0].Point.x - e.Vertexes[-1].Point.x) > 1e-6 \
                or abs(e.Vertexes[0].Point.y - e.Vertexes[-1].Point.y) > 1e-6:
            continue
        fs = sh.ancestorsOfType(e, Part.Face)
        if len(fs) != 2:
            continue
        m = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
        n = [f.normalAt(*f.Surface.parameter(m)) for f in fs]
        if (n[0] - n[1]).Length < 1e-3:
            continue
        dz = Vector(0, 0, 1); steps = []
        for f, nn in zip(fs, n):            # a step along each face, away from the edge
            tv = nn.cross(dz); tv.normalize()
            if f.distToShape(Part.Vertex(m + tv * 0.01))[0] > 1e-5:
                tv = -tv
            steps.append(tv)
        b = steps[0] + steps[1]; b.normalize()
        outside = sh.isInside(m + b * 0.005, 1e-7, False)   # material between the faces = a convex corner
        if outside == convex:
            out.append(f"Edge{i + 1}")
    return out


def frame_base():
    """The frame shared by both halves: lobes, rim, roller pockets, pin holes, rounded corners (z 0 .. w_half).
    It is symmetric about its mid-plane (the pin row sits at w_zc = w_half / 2), so the motor half reuses it."""
    kind, sg = "frame", +1
    new_body("WheelFrame", GREY)
    a1 = "360 deg / w_n"
    b1 = rot_xy("roller_axis_r", "-w_y0", a1); b2 = rot_xy("roller_axis_r", "-w_pin_end", a1)
    if num("w_spoke") > 0:
        # a hub ring and one solid spoke per pin end (w_spoke thick along the pin, hub to rim): nothing in between
        s = sk("HubSketch", "XY", "0 mm"); circle2d(s, "hub", ("0 mm", "0 mm", "0"), "2 * w_hub_ring")
        ext(s, "add", "w_half", sg, "Hub")
        # a shell w_spoke thick round each roller pocket (the pocket outline offset by w_spoke): 3 mm round the
        # inner side and round each roller end where the pin sits, open windows everywhere else
        s = sk("ShellSketch", "XY", "0 mm")
        R2 = num("wheel_r + w_spoke"); cx2 = num("2 * roller_axis_r - w_clr_rad"); y2 = num("w_y0 + w_support"); xo2 = num("wheel_r + 1 mm")
        al2 = math.asin(y2 / R2)
        A2 = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(cx2, 0, 0), Vector(0, 0, 1), R2), math.pi - al2, math.pi + al2), False)
        qa = Vector(cx2 - R2 * math.cos(al2), y2, 0); qb = Vector(cx2 - R2 * math.cos(al2), -y2, 0)
        M1 = s.addGeometry(Part.LineSegment(qb, Vector(xo2, -y2, 0)), False)
        M2 = s.addGeometry(Part.LineSegment(Vector(xo2, -y2, 0), Vector(xo2, y2, 0)), False)
        M3 = s.addGeometry(Part.LineSegment(Vector(xo2, y2, 0), qa), False)
        s.addConstraint([Sketcher.Constraint("Coincident", A2, 2, M1, 1), Sketcher.Constraint("Coincident", M1, 2, M2, 1),
                         Sketcher.Constraint("Coincident", M2, 2, M3, 1), Sketcher.Constraint("Coincident", M3, 2, A2, 1),
                         Sketcher.Constraint("Horizontal", M1), Sketcher.Constraint("Horizontal", M3), Sketcher.Constraint("Vertical", M2)])
        c0 = s.ConstraintCount
        s.addConstraint(Sketcher.Constraint("Radius", A2, R2)); _dim(s, c0, "sh_r", E("wheel_r + w_spoke"))
        _pt(s, A2, 3, E("2 * roller_axis_r - w_clr_rad"), "0 mm", "sh_c")
        c0 = s.ConstraintCount
        s.addConstraint([Sketcher.Constraint("DistanceY", -1, 1, A2, 1, y2), Sketcher.Constraint("DistanceY", -1, 1, A2, 2, -y2),
                         Sketcher.Constraint("DistanceX", -1, 1, M2, 1, xo2)])
        _dim(s, c0, "sh_y1", E("w_y0 + w_support")); _dim(s, c0 + 1, "sh_y2", E("-(w_y0 + w_support)")); _dim(s, c0 + 2, "sh_xo", E("wheel_r + 1 mm"))
        spk = ext(s, "add", "w_half", sg, "PocketShell")
        polar([spk], "ShellPattern")
        if num("w_band") > 0:
            # a ring w_band wide inside the rim: the roller pockets cut it away at each roller, so what is left is a band
            # between neighbouring pin supports that braces them (the other row's roller runs under it, cleared below)
            s = sk("BandSketch", "XY", "0 mm")
            circle2d(s, "band_i", ("0 mm", "0 mm", "0"), "2 * (w_frame_r - w_band)"); circle2d(s, "band_o", ("0 mm", "0 mm", "0"), "2 * wheel_r + 2 mm")
            ext(s, "add", "w_half", sg, "Band")
    else:
        s = sk("LobeSketch", "XY", "0 mm")
        hull_circles2d(s, "lobe", [("0 mm", "0 mm", "w_hub_r"), ("roller_axis_r", "w_y0", "w_boss_r"), ("roller_axis_r", "w_pin_end", "w_boss_r"),
                                   (b1[0], b1[1], "w_boss_r"), (b2[0], b2[1], "w_boss_r")])
        lobe = ext(s, "add", "w_half", sg, "Lobe")
        polar([lobe], "Lobes")
    s = sk("RimSketch", "XY", "0 mm")
    circle2d(s, "rim_in", ("0 mm", "0 mm", "0"), "2 * w_frame_r"); circle2d(s, "rim_out", ("0 mm", "0 mm", "0"), "2 * wheel_r + 10 mm")
    ext(s, "cut", "0", +1, "RimTrim", mid=True, kind="ThroughAll")
    # roller pocket: inboard side follows the roller's arc (+ clearance), open through the rim
    s = sk("PocketSketch", "XY", "0 mm")
    R = num("wheel_r"); cx = num("2 * roller_axis_r - w_clr_rad"); y0 = num("w_y0"); xo = num("wheel_r + 3 mm")
    al = math.asin(y0 / R)
    A = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(cx, 0, 0), Vector(0, 0, 1), R), math.pi - al, math.pi + al), False)
    pa = Vector(cx - R*math.cos(al), y0, 0); pb = Vector(cx - R*math.cos(al), -y0, 0)
    L1 = s.addGeometry(Part.LineSegment(pb, Vector(xo, -y0, 0)), False)
    L2 = s.addGeometry(Part.LineSegment(Vector(xo, -y0, 0), Vector(xo, y0, 0)), False)
    L3 = s.addGeometry(Part.LineSegment(Vector(xo, y0, 0), pa), False)
    s.addConstraint([Sketcher.Constraint("Coincident", A, 2, L1, 1), Sketcher.Constraint("Coincident", L1, 2, L2, 1),
                     Sketcher.Constraint("Coincident", L2, 2, L3, 1), Sketcher.Constraint("Coincident", L3, 2, A, 1),
                     Sketcher.Constraint("Horizontal", L1), Sketcher.Constraint("Horizontal", L3), Sketcher.Constraint("Vertical", L2)])
    c0 = s.ConstraintCount
    s.addConstraint(Sketcher.Constraint("Radius", A, R)); _dim(s, c0, "pk_r", E("wheel_r"))
    _pt(s, A, 3, E("2 * roller_axis_r - w_clr_rad"), "0 mm", "pk_c")
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("DistanceY", -1, 1, A, 1, y0), Sketcher.Constraint("DistanceY", -1, 1, A, 2, -y0),
                     Sketcher.Constraint("DistanceX", -1, 1, L2, 1, xo)])   # arc runs CCW from the top end (+y0) round the inboard side
    _dim(s, c0, "pk_y1", E("w_y0")); _dim(s, c0 + 1, "pk_y2", E("-w_y0")); _dim(s, c0 + 2, "pk_xo", E("wheel_r + 3 mm"))
    pocket_ = ext(s, "cut", "0", +1, "RollerPocket", mid=True, kind="ThroughAll")
    pin = ycyl("PinHole", [("roller_axis_r", f"{'' if sg > 0 else '-'}w_zc")], "0 mm", "wpin_d + wpin_fit", "0", "cut", mid=True, kind="ThroughAll")
    # beyond w_groove_y the pin rises above the rim: open the hole into a groove (down to the pin's centre line), no thin lip
    feats = [pocket_, pin]
    if num("w_y0 + w_support") > num("w_pin_end") + 0.05:
        # past each pin end the support is cut back to the underside of the pin: the hole comes out square on that step
        # (push the pin in along its axis from outside), and there is no wedge between the pin and the rim to go thin
        s = sk("PinStepSketch", "XY", "0 mm")
        box2d(s, "stp1", ("roller_axis_r - (wpin_d + wpin_fit) / 2", "w_pin_end", "0"), ("wheel_r + 3 mm - roller_axis_r", "w_support + 3 mm", "0"))
        box2d(s, "stp2", ("roller_axis_r - (wpin_d + wpin_fit) / 2", "-(w_pin_end + w_support + 3 mm)", "0"), ("wheel_r + 3 mm - roller_axis_r", "w_support + 3 mm", "0"))
        feats.append(ext(s, "cut", "0", +1, "PinSteps", mid=True, kind="ThroughAll"))
    if num("w_groove_y") < num("wheel_r"):
        # only a slot the width of the pin hole, at the pin row: the plastic either side of it (and the lobe round the pin end
        # out to the rim) stays solid, so nothing thin is left beside the pin end
        s = sk("PinGrooveSketch", "XY", "w_zc")
        box2d(s, "grv1", ("roller_axis_r", "w_groove_y", "0"), ("wheel_r + 3 mm - roller_axis_r", "w_spoke + 2 mm", "0"))
        box2d(s, "grv2", ("roller_axis_r", "-(w_groove_y + w_spoke + 2 mm)", "0"), ("wheel_r + 3 mm - roller_axis_r", "w_spoke + 2 mm", "0"))
        ends = ext(s, "cut", "wpin_d + wpin_fit", +1, "PinGrooves", mid=True)
        feats.append(ends)
    _f = num("w_y0 + w_support"); _ph = math.pi / num("w_n"); _T1 = math.hypot(_f / math.tan(_ph) + num("w_arm_r") / math.tan(_ph), _f)
    _fits = num("w_band") <= 0 or _T1 < num("w_frame_r - w_band") - 0.3
    _fits = _fits and num("w_hub_ring") < num("w_frame_r - w_band")          # hub grown out to the band: no windows   # with a band the window must fit inside it, else there is nothing to cut
    if num("w_spoke") > 0 and _fits:
        # between this roller's +end support and the next roller's -end support: cut away everything beyond both supports'
        # outer faces, the corner where they meet rounded r w_arm_r (the curved arm joining the two pin supports)
        s = sk("GapSketch", "XY", "0 mm")
        F = "(w_y0 + w_support)"; PH = "(180 deg / w_n)"; ph = math.pi / num("w_n"); rf = num("w_arm_r"); f = num(F)
        u1 = Vector(1, 0, 0); u2 = Vector(math.cos(2 * ph), math.sin(2 * ph), 0); ub = Vector(math.cos(ph), math.sin(ph), 0)
        P = Vector(f / math.tan(ph), f, 0); Q = P + ub * (rf / math.sin(ph)); tq = rf / math.tan(ph)
        pA = Vector(num("wheel_r + 6 mm"), f, 0); pB = P + ub * 14; pC = P + u2 * 12
        T1 = P + u1 * tq; T2 = P + u2 * tq
        G = s.addGeometry(Part.ArcOfCircle(Part.Circle(Q, Vector(0, 0, 1), rf), 2 * ph - 1.5 * math.pi, -0.5 * math.pi), False)
        c0 = s.ConstraintCount
        s.addConstraint(Sketcher.Constraint("Radius", G, rf)); _dim(s, c0, "gap_r", E("w_arm_r"))
        Px = f"{F} / tan{PH}"
        _pt(s, G, 3, E(f"{Px} + w_arm_r / sin{PH} * cos{PH}"), E(f"{F} + w_arm_r / sin{PH} * sin{PH}"), "gap_c")
        if num("w_band") > 0:
            # keep a band w_band wide inside the rim joining the two supports (braces them); the window is only inside it
            ri = num("w_frame_r - w_band"); al = math.atan2(f, math.sqrt(ri * ri - f * f))
            pA = Vector(ri * math.cos(al), ri * math.sin(al), 0); pC = Vector(ri * math.cos(2 * ph - al), ri * math.sin(2 * ph - al), 0)
            g1 = s.addGeometry(Part.LineSegment(T1, pA), False)
            O = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(), Vector(0, 0, 1), ri), al, 2 * ph - al), False)
            g4 = s.addGeometry(Part.LineSegment(pC, T2), False)
            s.addConstraint([Sketcher.Constraint("Tangent", g1, 1, G, 2), Sketcher.Constraint("Coincident", g1, 2, O, 1),
                             Sketcher.Constraint("Coincident", O, 2, g4, 1), Sketcher.Constraint("Tangent", g4, 2, G, 1),
                             Sketcher.Constraint("Coincident", O, 3, -1, 1), Sketcher.Constraint("Horizontal", g1)])
            c0 = s.ConstraintCount
            s.addConstraint([Sketcher.Constraint("Radius", O, ri), Sketcher.Constraint("Angle", g4, 2 * ph + math.pi)])
            _dim(s, c0, "band_r", E("w_frame_r - w_band")); _dim(s, c0 + 1, "band_ang", E("360 deg / w_n + 180 deg"))
        else:
            g1 = s.addGeometry(Part.LineSegment(T1, pA), False); g2 = s.addGeometry(Part.LineSegment(pA, pB), False)
            g3 = s.addGeometry(Part.LineSegment(pB, pC), False); g4 = s.addGeometry(Part.LineSegment(pC, T2), False)
            s.addConstraint([Sketcher.Constraint("Tangent", g1, 1, G, 2), Sketcher.Constraint("Coincident", g1, 2, g2, 1),
                             Sketcher.Constraint("Coincident", g2, 2, g3, 1), Sketcher.Constraint("Coincident", g3, 2, g4, 1),
                             Sketcher.Constraint("Tangent", g4, 2, G, 1)])
            _pt(s, g2, 1, E("wheel_r + 6 mm"), E(F), "gap_a")
            _pt(s, g3, 1, E(f"{Px} + 14 mm * cos{PH}"), E(f"{F} + 14 mm * sin{PH}"), "gap_b")
            _pt(s, g4, 1, E(f"{Px} + 12 mm * cos(2 * {PH})"), E(f"{F} + 12 mm * sin(2 * {PH})"), "gap_d")
        feats.append(ext(s, "cut", "0", +1, "GapCut", mid=True, kind="ThroughAll"))
    pat = polar(feats, "Pockets")
    # corners: concave r w_fillet_in, convex r w_fillet (the OpenSCAD offset() pairs), as rule fillets: re-found on every
    # recompute, so they never lose their edges when a parameter changes
    from fusionflow import rulefillet
    f1 = rulefillet.make(body, "InsideCorners", E("w_fillet_in"), "ConcaveCorners")
    f2 = rulefillet.make(body, "OutsideCorners", E("w_fillet"), "ConvexCorners")
    log.append((kind, "corners rounded", f1.Rounded, f2.Rounded, "left sharp", f1.LeftSharp + f2.LeftSharp))
    log.append(("frame", "valid", body.Shape.isValid(), round(body.Shape.Volume, 2)))
    return body


def half(kind, base):
    sg = +1 if kind == "outer" else -1
    new_body("WheelHalfOuter" if kind == "outer" else "WheelHalfMotor", GREY)
    body.BaseFeature = base                 # both halves start from the shared frame (z 0 .. w_half in the body)
    old = doc.getObject("WheelFrameBelow")
    if old: doc.removeObject(old.Name)
    doc.recompute()
    if kind == "outer":
        n = int(round(num("w_n"))); pts = [rot_xy("w_screw_r", "0 mm", f"({k} + 0.5) * 360 deg / w_n") for k in range(n)]
        zcyl("ScrewClear", pts, "-1 mm", "w_screw_clear", "w_half + 2 mm", "cut")
        zcyl("Counterbore", pts, "w_half - w_head_h", "w_head_d", "w_head_h + 1 mm", "cut")
    else:
        n = int(round(num("w_n"))); pts = [rot_xy("w_screw_r", "0 mm", f"({k} - 0.5) * 360 deg / w_n") for k in range(n)]
        # modelled with the mating face on top (z = w_half): the body is placed one half-thickness down (the mirror in OpenSCAD)
        zcyl("ScrewPilots", pts, "w_half + 1 mm", "w_screw_pilot", "w_half - w_pilot_floor + 1 mm", "cut", toward=-1)
        s = sk("BoreSketch", "XY", "1 mm")
        r = num("w_bore / 2"); dd = num("w_bore / 2 - w_bore_flat"); be = math.acos(dd / r); a = math.radians(30)
        A = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(), Vector(0, 0, 1), r), a + be, a + 2*math.pi - be), False)
        Lf = s.addGeometry(Part.LineSegment(Vector(r*math.cos(a - be), r*math.sin(a - be), 0), Vector(r*math.cos(a + be), r*math.sin(a + be), 0)), False)
        s.addConstraint([Sketcher.Constraint("Coincident", A, 3, -1, 1), Sketcher.Constraint("Coincident", A, 2, Lf, 1),
                         Sketcher.Constraint("Coincident", Lf, 2, A, 1), Sketcher.Constraint("Angle", Lf, math.radians(120))])
        c0 = s.ConstraintCount
        s.addConstraint([Sketcher.Constraint("Radius", A, r), Sketcher.Constraint("Distance", -1, 1, Lf, dd)])
        _dim(s, c0, "bore_r", E("w_bore / 2")); _dim(s, c0 + 1, "bore_flat", E("w_bore / 2 - w_bore_flat"))
        ext(s, "cut", "0", -1, "DBore", mid=True, kind="ThroughAll")
        body.setExpression("Placement", E("placement(vector(0 mm; 0 mm; -w_half); rotation(vector(0; 0; 1); 180 / w_n))"))   # half a pitch round, below the mating face
    doc.recompute()
    log.append((kind, "valid", body.Shape.isValid(), round(body.Shape.Volume, 2)))
    return body


def one_piece(base):
    """Both layers as one printed part: the frame, plus a copy turned half a pitch and moved one layer down, fused;
    then the D-bore (through, drill 2.0) and nothing else: no screws."""
    global body
    for nm in ("WheelHalfOuter", "WheelHalfMotor"):     # the two-half frame, if the model had it
        o = doc.getObject(nm)
        if o:
            o.removeObjectsFromDocument(); doc.removeObject(o.Name)
    for nm in ("WheelFrameLower", "WheelFrameFuse"):
        o = doc.getObject(nm)
        if o: doc.removeObject(o.Name)
    low = doc.addObject("App::Link", "WheelFrameLower"); low.LinkedObject = base
    low.setExpression("LinkPlacement", E("placement(vector(0 mm; 0 mm; 0 mm); rotation(180 / w_n; 0; 180))"))   # mirrored below the mating face, half a pitch round
    fu = doc.addObject("Part::MultiFuse", "WheelFrameFuse"); fu.Shapes = [base, low]; fu.Refine = True
    doc.recompute()
    # where the rows overlap along the axle, each roller also reaches into the other layer: cut its running clearance
    # (the roller barrel + w_clr_rad, its length + w_clr_end) there too
    n = int(round(num("w_n"))); a = num("roller_axis_r"); R = num("wheel_r"); cr = num("w_clr_rad"); hl = num("roller_l / 2 + w_clr_end")
    zc = num("w_zc"); env = []
    if num("wheel_r - roller_axis_r + w_row_gap") > num("w_zc") + 1e-6 or True:
        prof = [Vector(0, -hl, 0)] + [Vector(math.sqrt(R * R - y * y) - a + cr, y, 0) for y in [-hl + 2 * hl * i / 40 for i in range(41)]] + [Vector(0, hl, 0)]
        one = Part.Face(Part.makePolygon(prof + [prof[0]])).revolve(Vector(), Vector(0, 1, 0), 360)
        for k in range(n):
            for ang, z in ((360.0 / n * k, zc), (360.0 / n * (k + 0.5), -zc)):
                m = App.Placement(Vector(), App.Rotation(Vector(0, 0, 1), ang)).multiply(App.Placement(Vector(a, 0, z), App.Rotation())).toMatrix()
                env.append(one.transformGeometry(m))
    for nm in ("RollerClearance", "WheelFrameCut"):
        o = doc.getObject(nm)
        if o: doc.removeObject(o.Name)
    rc = doc.addObject("Part::Feature", "RollerClearance"); rc.Label = "Wheel pocket clearance"; rc.Shape = env[0].multiFuse(env[1:]) if len(env) > 1 else env[0]; rc.ViewObject.Visibility = False
    cu = doc.addObject("Part::Cut", "WheelFrameCut"); cu.Base = fu; cu.Tool = rc; cu.Refine = True
    doc.recompute()
    new_body("WheelFrameOne", GREY)
    body.BaseFeature = cu
    doc.recompute()
    s = sk("BoreSketch", "XY", "0 mm")
    r = num("w_bore / 2"); dd = num("w_bore / 2 - w_bore_flat"); be = math.acos(dd / r); a = math.radians(30)
    A = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(), Vector(0, 0, 1), r), a + be, a + 2*math.pi - be), False)
    Lf = s.addGeometry(Part.LineSegment(Vector(r*math.cos(a - be), r*math.sin(a - be), 0), Vector(r*math.cos(a + be), r*math.sin(a + be), 0)), False)
    s.addConstraint([Sketcher.Constraint("Coincident", A, 3, -1, 1), Sketcher.Constraint("Coincident", A, 2, Lf, 1),
                     Sketcher.Constraint("Coincident", Lf, 2, A, 1), Sketcher.Constraint("Angle", Lf, math.radians(120))])
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("Radius", A, r), Sketcher.Constraint("Distance", -1, 1, Lf, dd)])
    _dim(s, c0, "bore_r", E("w_bore / 2")); _dim(s, c0 + 1, "bore_flat", E("w_bore / 2 - w_bore_flat"))
    fb = ext(s, "cut", "0", -1, "DBore", mid=True, kind="ThroughAll"); fb.Refine = False   # refine fails on the fused frame
    doc.recompute()
    log.append(("one piece", "valid", body.Shape.isValid(), round(body.Shape.Volume, 2), "solids", len(body.Shape.Solids)))
    for o in (low, fu, rc, cu): o.ViewObject.Visibility = False
    return body, low, fu, rc, cu


def roller():
    new_body("Roller", BLACK)
    s = sk("BarrelSketch", "XY", "0 mm")
    R = num("wheel_r"); dax = num("roller_axis_r"); hl = num("roller_l / 2"); hr = num("roller_hole / 2")
    al = math.asin(hl / R); xe = R*math.cos(al) - dax
    A = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(-dax, 0, 0), Vector(0, 0, 1), R), -al, al), False)
    T = s.addGeometry(Part.LineSegment(Vector(xe, hl, 0), Vector(hr, hl, 0)), False)
    Vl = s.addGeometry(Part.LineSegment(Vector(hr, hl, 0), Vector(hr, -hl, 0)), False)
    B = s.addGeometry(Part.LineSegment(Vector(hr, -hl, 0), Vector(xe, -hl, 0)), False)
    s.addConstraint([Sketcher.Constraint("Coincident", A, 2, T, 1), Sketcher.Constraint("Coincident", T, 2, Vl, 1),
                     Sketcher.Constraint("Coincident", Vl, 2, B, 1), Sketcher.Constraint("Coincident", B, 2, A, 1),
                     Sketcher.Constraint("Horizontal", T), Sketcher.Constraint("Horizontal", B), Sketcher.Constraint("Vertical", Vl)])
    c0 = s.ConstraintCount
    s.addConstraint(Sketcher.Constraint("Radius", A, R)); _dim(s, c0, "barrel_r", E("wheel_r"))
    _pt(s, A, 3, E("-roller_axis_r"), "0 mm", "barrel_c")
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("DistanceY", -1, 1, A, 2, hl), Sketcher.Constraint("DistanceY", -1, 1, A, 1, -hl),
                     Sketcher.Constraint("DistanceX", -1, 1, Vl, 1, hr)])
    _dim(s, c0, "barrel_y2", E("roller_l / 2")); _dim(s, c0 + 1, "barrel_y1", E("-roller_l / 2")); _dim(s, c0 + 2, "barrel_hole", E("roller_hole / 2"))
    doc.recompute()
    rv = body.newObject("PartDesign::Revolution", "Barrel")
    rv.Profile = s; rv.ReferenceAxis = (s, ["V_Axis"]); rv.Angle = 360
    doc.recompute(); H.settle_sketch(s); s.ViewObject.Visibility = False
    log.append(("roller", rv.isValid(), round(body.Shape.Volume, 2)))
    return body


def liner():
    """brass tube 2.0 x 1.1 through each TPU roller: the roller turns on the hardened pin on brass, not on TPU"""
    new_body("BrassLiner", (0.79, 0.64, 0.30))
    ycyl("Tube", [("0 mm", "0 mm")], "-roller_l / 2", "liner_d", "roller_l", "add", +1)
    ycyl("Bore", [("0 mm", "0 mm")], "0 mm", "liner_id", "0", "cut", mid=True, kind="ThroughAll")
    return body


def pin():
    new_body("WheelPin", STEEL)
    ycyl("Pin", [("0 mm", "0 mm")], "-w_pin_end", "wpin_d", "2 * w_pin_end", "add", +1)
    return body


base = frame_base()
ONE = num("w_one_piece") > 0.5
if ONE:
    _one, *_aids = one_piece(base)          # the printed frame; the link / fuse / clearance / cut it is made from stay outside the Wheel part
    frames = [_one]
    aid = doc.getObject("WheelBuildAids") or doc.addObject("App::DocumentObjectGroup", "WheelBuildAids")
    for o in _aids:
        for p in list(o.InList):
            if p.isDerivedFrom("App::Part"): p.removeObject(o)
        aid.addObject(o)
    aid.Label = "Wheel build aids (hidden)"
else:
    frames = [half("outer", base), half("motor", base)]
rol, pn, ln = roller(), pin(), liner()

wheel = doc.addObject("App::Part", "Wheel"); wheel.Label = "Wheel"
for b in [base] + frames + [rol, pn, ln]:
    wheel.addObject(b)
base.ViewObject.Visibility = False   # the shared frame: shown through the two halves
SLOT = "rotationz({a}) * translationm(roller_axis_r; 0 mm; {z})"
rol.setExpression("Placement", E(SLOT.format(a="0 deg", z="w_zc")))
pn.setExpression("Placement", E(SLOT.format(a="0 deg", z="w_zc")))
ln.setExpression("Placement", E(SLOT.format(a="0 deg", z="w_zc")))
for src, nm in ((rol, "Roller"), (pn, "Pin"), (ln, "Liner")):
    n = int(round(num("w_n")))
    slots = [(f"{k} * 360 deg / w_n", "w_zc") for k in range(1, n)] + [(f"({k} + 0.5) * 360 deg / w_n", "-w_zc") for k in range(n)]
    for k, (a, z) in enumerate(slots):
        l = wheel.newObject("App::Link", f"{nm}{k + 2}")
        l.LinkedObject = src; l.Label = f"{src.Label} {k + 2}"
        l.setExpression("LinkPlacement", E(SLOT.format(a=a, z=z)))
# in the drive unit: at the axle, outer half facing out along the radial line
wheel.setExpression("Placement", E("translationm(wf - wheel_w / 2; pinwheel_e; axle_z) * rotationy(90)"))
doc.recompute()
bad = [o.Label for o in doc.Objects if hasattr(o, "isValid") and not o.isValid()]
doc.save()
result = {"log": log, "invalid": bad}
