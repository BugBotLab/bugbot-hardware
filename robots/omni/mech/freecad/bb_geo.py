# BugBot build helpers in robot (global) coordinates, so each OpenSCAD part ports almost line for line.
# Exec'd into a build script after bb_lib.py; uses that script's `doc` and current `body`.
# Every number is an expression; bare parameter names are fine ("pcb_top + 2 mm").
import math
import Part, Sketcher
from fusionflow import extrude as _X

AX = {"XY": ((0, 1), 2, +1), "XZ": ((0, 2), 1, -1), "YZ": ((1, 2), 0, +1)}   # sketch u, v -> global axes; normal axis, sign


def E(expr):
    return _X.expand(str(expr), doc)


def num(expr):
    return ev(E(expr))


def neg(expr):
    return f"-({expr})"


def sk(name, plane, at="0 mm"):
    """Sketch on an origin plane, moved along its normal so it lies at global coordinate `at`."""
    s = H.sketch(body, plane, name)
    sign = AX[plane][2]
    off = E(at) if sign > 0 else neg(E(at))
    s.AttachmentOffset = App.Placement(Vector(0, 0, ev(off)), App.Rotation())
    s.setExpression(".AttachmentOffset.Base.z", off)
    return s


def plane_of(s):
    r = s.Placement.Rotation.multVec(Vector(0, 0, 1))
    return "XY" if abs(r.z) > 0.9 else ("XZ" if abs(r.y) > 0.9 else "YZ")


def uv(s, g):
    """Global point (x, y, z) expressions -> sketch (u, v) expressions."""
    (a, b), _, _ = AX[plane_of(s)]
    return E(g[a]), E(g[b])


def _dim(s, i_from, name, expr):
    s.renameConstraint(i_from, name)
    s.setExpression(f"Constraints.{name}", expr)


def box2d(s, tag, lo, size):
    """Rectangle from a global corner `lo` and global `size` (both 3-tuples of expressions)."""
    (a, b), _, _ = AX[plane_of(s)]
    rect(s, tag, E(lo[a]), E(lo[b]), E(size[a]), E(size[b]))


def circle2d(s, tag, c, d):
    u, v = uv(s, c)
    circ(s, tag, u, v, E(d))


def _pt(s, gi, pos, x, y, tag):
    """Pin a sketch point to expressions (DistanceX / DistanceY from the origin)."""
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("DistanceX", -1, 1, gi, pos, ev(x)), Sketcher.Constraint("DistanceY", -1, 1, gi, pos, ev(y))])
    _dim(s, c0, f"{tag}_x", x); _dim(s, c0 + 1, f"{tag}_y", y)


def slot2d(s, tag, c1, r1, c2, r2):
    """Hull of two circles (an obround, or a tapered one when r1 != r2): 2 arcs + 2 tangent lines."""
    u1, v1 = uv(s, c1); u2, v2 = uv(s, c2); R1, R2 = E(r1), E(r2)
    p1 = Vector(ev(u1), ev(v1), 0); p2 = Vector(ev(u2), ev(v2), 0); q1, q2 = ev(R1), ev(R2)
    d = p2 - p1; L = d.Length; a = math.atan2(d.y, d.x); f = math.acos((q1 - q2) / L)
    g0 = s.GeometryCount
    A1 = s.addGeometry(Part.ArcOfCircle(Part.Circle(p1, Vector(0, 0, 1), q1), a + f, a + 2*math.pi - f), False)
    A2 = s.addGeometry(Part.ArcOfCircle(Part.Circle(p2, Vector(0, 0, 1), q2), a - f, a + f), False)
    P = lambda c, r, t: c + Vector(r*math.cos(t), r*math.sin(t), 0)
    Lt = s.addGeometry(Part.LineSegment(P(p1, q1, a + f), P(p2, q2, a + f)), False)
    Lb = s.addGeometry(Part.LineSegment(P(p2, q2, a - f), P(p1, q1, a - f)), False)
    s.addConstraint([Sketcher.Constraint("Tangent", Lt, 1, A1, 1), Sketcher.Constraint("Tangent", Lt, 2, A2, 2),
                     Sketcher.Constraint("Tangent", Lb, 1, A2, 1), Sketcher.Constraint("Tangent", Lb, 2, A1, 2)])
    c0 = s.ConstraintCount
    s.addConstraint([Sketcher.Constraint("Radius", A1, q1), Sketcher.Constraint("Radius", A2, q2)])
    _dim(s, c0, f"{tag}_r1", R1); _dim(s, c0 + 1, f"{tag}_r2", R2)
    _pt(s, A1, 3, u1, v1, f"{tag}_c1"); _pt(s, A2, 3, u2, v2, f"{tag}_c2")


def hull2d(s, tag, c, r, pts):
    """Hull of a circle and some points (rectangle corners): one arc, tangent lines, straight edges between corners.
    Which corners lie on the hull is decided from today's values; the outline then follows the parameters."""
    cu, cv = uv(s, c); R = E(r)
    P2 = [uv(s, p) for p in pts]
    cn = (ev(cu), ev(cv)); rn = ev(R)
    cand = [(ev(u), ev(v), i) for i, (u, v) in enumerate(P2)]
    samp = [(cn[0] + rn*math.cos(2*math.pi*k/720), cn[1] + rn*math.sin(2*math.pi*k/720), -1) for k in range(720)]
    allp = sorted(set(cand + samp))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for p in allp:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 1e-9: lower.pop()
        lower.append(p)
    for p in reversed(allp):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 1e-9: upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]                       # CCW
    k = next(i for i, p in enumerate(hull) if p[2] >= 0 and hull[(i + 1) % len(hull)][2] < 0)
    hull = hull[k + 1:] + hull[:k + 1]                   # starts with the arc, ends with corners
    arc = [p for p in hull if p[2] < 0]; corners = [p for p in hull if p[2] >= 0]
    t0 = math.atan2(arc[0][1] - cn[1], arc[0][0] - cn[0]); t1 = math.atan2(arc[-1][1] - cn[1], arc[-1][0] - cn[0])
    while t1 <= t0: t1 += 2*math.pi
    A = s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(cn[0], cn[1], 0), Vector(0, 0, 1), rn), t0, t1), False)
    seq = [Vector(math.cos(t1)*rn + cn[0], math.sin(t1)*rn + cn[1], 0)] + [Vector(p[0], p[1], 0) for p in corners] + \
          [Vector(math.cos(t0)*rn + cn[0], math.sin(t0)*rn + cn[1], 0)]
    lines = [s.addGeometry(Part.LineSegment(seq[i], seq[i + 1]), False) for i in range(len(seq) - 1)]
    con = [Sketcher.Constraint("Tangent", lines[0], 1, A, 2), Sketcher.Constraint("Tangent", lines[-1], 2, A, 1)]
    con += [Sketcher.Constraint("Coincident", lines[i], 2, lines[i + 1], 1) for i in range(len(lines) - 1)]
    s.addConstraint(con)
    c0 = s.ConstraintCount
    s.addConstraint(Sketcher.Constraint("Radius", A, rn)); _dim(s, c0, f"{tag}_r", R)
    _pt(s, A, 3, cu, cv, f"{tag}_c")
    for j, p in enumerate(corners):
        u, v = P2[p[2]]
        _pt(s, lines[j], 2, u, v, f"{tag}_p{j}")


def ext(s, op, length, toward=+1, label=None, mid=False, kind="Length"):
    """Pad (op 'add') or Pocket (op 'cut') a sketch `length` along the global normal axis, toward +1 or -1."""
    _, _, sign = AX[plane_of(s)]
    doc.recompute()
    f = body.newObject("PartDesign::Pad" if op == "add" else "PartDesign::Pocket", label or ("Add" if op == "add" else "Cut"))
    f.Profile = s
    f.Type = kind
    if kind == "Length":
        f.setExpression("Length", E(length))
    f.Midplane = mid
    natural = sign if op == "add" else -sign
    f.Reversed = (not mid) and (toward != natural)
    doc.recompute()
    H.settle_sketch(s)
    s.ViewObject.Visibility = False
    return f


def zbox(name, lo, size, op="add"):
    s = sk(name + "Sketch", "XY", lo[2]); box2d(s, name, lo, size)
    return ext(s, op, size[2], +1, name)


def zcyl(name, pts, z, d, h, op="add", toward=+1):
    s = sk(name + "Sketch", "XY", z)
    for i, p in enumerate(pts):
        circle2d(s, f"{name}{i}", (p[0], p[1], "0 mm"), d)
    return ext(s, op, h, toward, name)


def ycyl(name, pts, y0, d, length, op="add", toward=+1, mid=False, kind="Length"):
    """Cylinders along Y from y0 (points are (x, z))."""
    s = sk(name + "Sketch", "XZ", y0)
    for i, p in enumerate(pts):
        circle2d(s, f"{name}{i}", (p[0], "0 mm", p[1]), d)
    return ext(s, op, length, toward, name, mid=mid, kind=kind)


def xcyl(name, pts, x0, d, length, op="add", toward=+1):
    """Cylinders along X from x0 (points are (y, z))."""
    s = sk(name + "Sketch", "YZ", x0)
    for i, p in enumerate(pts):
        circle2d(s, f"{name}{i}", ("0 mm", p[0], p[1]), d)
    return ext(s, op, length, toward, name)


def new_body(name, colour=None):
    global body
    old = doc.getObject(name)
    if old:
        try:
            old.removeObjectsFromDocument()
        except Exception:
            pass
        if doc.getObject(name):
            doc.removeObject(name)
    body = H.body(name)
    if colour:
        body.ViewObject.ShapeColor = colour
    return body


def poly2d(s, tag, pts):
    """Closed polygon through global points, every vertex pinned by expressions."""
    P2 = [uv(s, p) for p in pts]
    V = [Vector(ev(u), ev(v), 0) for u, v in P2]
    n = len(V)
    L = [s.addGeometry(Part.LineSegment(V[i], V[(i + 1) % n]), False) for i in range(n)]
    s.addConstraint([Sketcher.Constraint("Coincident", L[i], 2, L[(i + 1) % n], 1) for i in range(n)])
    for i, (u, v) in enumerate(P2):
        _pt(s, L[i], 1, u, v, f"{tag}_v{i}")
    return L


def hex2d(s, tag, c, af):
    """Regular hexagon, across-flats `af`, centred on a global point, corners on the sketch's v axis (flats parallel to v)."""
    u, v = uv(s, c); cu, cv = ev(u), ev(v); R = ev(E(af)) / math.sqrt(3)
    pts = [Vector(cu + R*math.cos(math.radians(30 + 60*k)), cv + R*math.sin(math.radians(30 + 60*k)), 0) for k in range(6)]
    L = [s.addGeometry(Part.LineSegment(pts[k], pts[(k + 1) % 6]), False) for k in range(6)]
    C = s.addGeometry(Part.Circle(Vector(cu, cv, 0), Vector(0, 0, 1), R), True)
    con = [Sketcher.Constraint("Coincident", L[k], 2, L[(k + 1) % 6], 1) for k in range(6)]
    con += [Sketcher.Constraint("PointOnObject", L[k], 1, C) for k in range(6)]
    con += [Sketcher.Constraint("Equal", L[0], L[k]) for k in range(1, 6)]
    con += [Sketcher.Constraint("Vertical", L[2])]
    s.addConstraint(con)
    c0 = s.ConstraintCount
    s.addConstraint(Sketcher.Constraint("Diameter", C, 2*R)); _dim(s, c0, f"{tag}_dia", f"2 * ({E(af)}) / sqrt(3)")
    _pt(s, C, 3, u, v, f"{tag}_c")


def rbox(name, ang, lo, size, op="add"):
    """Box in a frame turned by `ang` about Z (lo / size in that frame)."""
    s = rotated_sketch(body, name + "Sketch", E(ang), E(lo[2]))
    rect(s, name, E(lo[0]), E(lo[1]), E(size[0]), E(size[1]))
    return ext(s, op, size[2], +1, name)


def fillet(feat, radius, pick, label="Fillet"):
    """PartDesign fillet on the edges of the body's current shape chosen by pick(edge)."""
    names = H.edges(feat, pick)
    f = body.newObject("PartDesign::Fillet", label)
    f.Base = (feat, names)
    f.setExpression("Radius", E(radius))
    doc.recompute()
    return f, names


def hull_circles2d(s, tag, circles):
    """Exact hull of several circles [(x, y, r) global expressions]: arcs joined by tangent lines, all bound.
    Which circles lie on the hull, and their order, is taken from today's values."""
    C = []
    for (x, y, r) in circles:
        u, v = uv(s, (x, y, "0") if plane_of(s) == "XY" else (x, "0", y))
        C.append((u, v, E(r), ev(u), ev(v), ev(E(r))))
    samp = []
    for k, c in enumerate(C):
        samp += [(c[3] + c[5]*math.cos(2*math.pi*j/720), c[4] + c[5]*math.sin(2*math.pi*j/720), k) for j in range(720)]
    pts = sorted(samp)
    cross = lambda o, a, b: (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    seq = []
    for p in lo[:-1] + up[:-1]:
        if not seq or seq[-1] != p[2]: seq.append(p[2])
    if len(seq) > 1 and seq[0] == seq[-1]: seq.pop()
    n = len(seq)
    def tan(i, j):
        (_, _, _, x1, y1, r1), (_, _, _, x2, y2, r2) = C[i], C[j]
        a = math.atan2(y2 - y1, x2 - x1); f = math.acos((r1 - r2) / math.hypot(x2 - x1, y2 - y1)); return a - f
    T = [tan(seq[i], seq[(i + 1) % n]) for i in range(n)]
    arcs = []
    for i in range(n):
        c = C[seq[i]]; t0, t1 = T[i - 1], T[i]
        while t1 <= t0: t1 += 2*math.pi
        arcs.append(s.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(c[3], c[4], 0), Vector(0, 0, 1), c[5]), t0, t1), False))
    lines = []
    for i in range(n):
        a, b = C[seq[i]], C[seq[(i + 1) % n]]; t = T[i]
        p = Vector(a[3] + a[5]*math.cos(t), a[4] + a[5]*math.sin(t), 0); q = Vector(b[3] + b[5]*math.cos(t), b[4] + b[5]*math.sin(t), 0)
        lines.append(s.addGeometry(Part.LineSegment(p, q), False))
    con = []
    for i in range(n):
        con += [Sketcher.Constraint("Tangent", lines[i], 1, arcs[i], 2), Sketcher.Constraint("Tangent", lines[i], 2, arcs[(i + 1) % n], 1)]
    s.addConstraint(con)
    for i in range(n):
        c = C[seq[i]]
        c0 = s.ConstraintCount
        s.addConstraint(Sketcher.Constraint("Radius", arcs[i], c[5])); _dim(s, c0, f"{tag}_r{i}", c[2])
        _pt(s, arcs[i], 3, c[0], c[1], f"{tag}_c{i}")
    return arcs, lines


def rot_xy(x, y, ang):
    """Expressions for the point (x, y) turned by ang about Z."""
    return (f"(({x}) * cos({ang}) - ({y}) * sin({ang}))", f"(({x}) * sin({ang}) + ({y}) * cos({ang}))")
