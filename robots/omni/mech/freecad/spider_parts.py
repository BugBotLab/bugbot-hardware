# Clean arm plate profile for the Spider (one constant-width L, rounded bends, round axle end), joined to the old
# gripper arm's pivot end (x < JOIN: pivot boss + servo-horn interface, unchanged). Used by build_spider.py.
import FreeCAD as App, Part, math
V = App.Vector

def _edge_at(sh, x, z, tol=0.05):
    """the straight edge parallel to Y through (x, z)"""
    for e in sh.Edges:
        if not isinstance(e.Curve, Part.Line): continue
        a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
        if abs(a.x - b.x) < 1e-6 and abs(a.z - b.z) < 1e-6 and abs(a.x - x) < tol and abs(a.z - z) < tol:
            return e
    return None

def plate(old_arm, y0, y1, axle_x, axle_z, join=20.0, top=(33.7, 39.7), drop_x=(36.5, 42.5), run_z=(4.0, 12.0),
          r_out=6.0, r_heel=4.0, r_in_top=1.5, r_in_low=3.0):
    w = y1 - y0
    zt0, zt1 = top; dx0, dx1 = drop_x; rz0, rz1 = run_z
    body = Part.makeBox(dx1 - (join - 1.0), w, zt1 - zt0, V(join - 1.0, y0, zt0))                     # top run
    body = body.fuse(Part.makeBox(dx1 - dx0, w, zt1 - rz0, V(dx0, y0, rz0)))                          # drop
    body = body.fuse(Part.makeBox(axle_x - dx0, w, rz1 - rz0, V(dx0, y0, rz0)))                       # lower run
    body = body.fuse(Part.makeCylinder((rz1 - rz0) / 2, w, V(axle_x, y0, (rz0 + rz1) / 2), V(0, 1, 0)))   # round end
    body = body.removeSplitter()
    for (x, z), r in (((dx1, zt1), r_out), ((dx0, rz0), r_heel), ((dx0, zt0), r_in_top), ((dx1, rz1), r_in_low)):
        e = _edge_at(body, x, z)
        if e is not None and r > 0:
            body = body.makeFillet(r, [e])
    keep = old_arm.common(Part.makeBox(join + 100, 200, 200, V(-100, -100, -100)))                   # pivot end, x < join
    return keep.fuse(body).removeSplitter()


def _vline_at(sh, x, y, tol=0.08):
    """vertical straight edges through (x, y)"""
    out = []
    for e in sh.Edges:
        if not isinstance(e.Curve, Part.Line): continue
        a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
        if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and abs(a.x - x) < tol and abs(a.y - y) < tol:
            out.append(e)
    return out


def _fillet(sh, r, edges):
    if not edges: return sh, 0
    try:
        f = sh.makeFillet(r, edges)
        if f.isValid(): return f, len(edges)
    except Exception:
        pass
    return sh, 0


def magazine(MC, R_in, R_out, z_bot, z_top, floor_top, slot, lip_t=1.6, lip_out=1.2, lip_extra_deg=8.0,
             tab_x=(37.5, 44.0), tab_y=(11.0, 21.0), r_tab=1.5, r_tab_out=1.0, r_lip=0.8, tab_top=None):
    """Tube + floor + front lip + one side tab each side, with fillets where they meet the tube. Holes are cut later."""
    tube = Part.makeCylinder(R_out, z_top - floor_top, V(MC, 0, floor_top))
    tube = tube.fuse(Part.makeCylinder(R_out, floor_top - z_bot, V(MC, 0, z_bot)))               # floor
    # lip: a band hugging the tube over the slot, rounded ends; its underside is the slot's roof
    half = math.degrees(math.asin(min(1.0, (R_in - 0.5) / R_out))) + lip_extra_deg
    zl = floor_top + slot
    ring = Part.makeCylinder(R_out + lip_out, lip_t, V(MC, 0, zl)).cut(Part.makeCylinder(R_out - 0.5, lip_t + 1, V(MC, 0, zl - 0.5)))
    wedge = Part.makePolygon([V(MC, 0, zl - 1)] + [V(MC + 40 * math.cos(math.radians(a)), 40 * math.sin(math.radians(a)), zl - 1)
                                                for a in (-half, -half / 2, 0, half / 2, half)] + [V(MC, 0, zl - 1)])
    wedge = Part.Face(wedge).extrude(V(0, 0, lip_t + 2))
    lip = ring.common(wedge)
    for s in (1, -1):                                                                              # round the ends
        a = math.radians(s * half); rm = R_out + lip_out / 2 - 0.25
        lip = lip.fuse(Part.makeCylinder(lip_out / 2 + 0.25, lip_t, V(MC + rm * math.cos(a), rm * math.sin(a), zl)))
    tabs = []
    for s in (1, -1):
        y0 = tab_y[0] if s > 0 else -tab_y[1]
        tabs.append(Part.makeBox(tab_x[1] - tab_x[0], tab_y[1] - tab_y[0], (tab_top or z_top) - z_bot, V(tab_x[0], y0, z_bot)))
    mag = tube.fuse([lip] + tabs).removeSplitter()
    nf = 0
    # concave fillets where the tabs meet the tube, small rounds on the tabs' outer corners
    for x in tab_x:
        yc = math.sqrt(max(0.0, R_out ** 2 - (x - MC) ** 2))
        for s in (1, -1):
            mag, k = _fillet(mag, r_tab, _vline_at(mag, x, s * yc)); nf += k
            mag, k = _fillet(mag, r_tab_out, _vline_at(mag, x, s * tab_y[1])); nf += k
    # round the tabs' back-top edge (closest to the board edge when the arm is parked): a cut, clear of the tube wall
    if tab_top:
        r = 2.0
        for sd in (1, -1):
            y0 = 14.3 if sd > 0 else -(tab_y[1] + 0.5)
            blk = Part.makeBox(r, tab_y[1] + 0.5 - 14.3, r, V(tab_x[0], y0, tab_top - r))
            blk = blk.cut(Part.makeCylinder(r, 60, V(tab_x[0] + r, -30, tab_top - r), V(0, 1, 0)))
            mag = mag.cut(blk); nf += 1
    # the lip's top edge into the tube wall
    top_edges = [e for e in mag.Edges if e.Curve.TypeId == "Part::GeomCircle" and abs(e.Curve.Radius - R_out) < 1e-3
                 and abs(e.Vertexes[0].Point.z - (zl + lip_t)) < 1e-3]
    mag, k = _fillet(mag, r_lip, top_edges); nf += k
    return mag, nf
