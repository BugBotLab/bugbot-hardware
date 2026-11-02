# The 24 mm omni wheel (micro_omni_wheel.scad) rebuilt as true solids, headless:
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" mech/freecad/wheel_brep.py
# Writes bought/Wheel.brep (frame halves, 6 rollers, 6 pins as separate solids) and bought/Wheel.colors.json.
# Same frame as the OpenSCAD assembly(): axle along Z, outer half at z 0..W/2, motor half below.
import json, math, os, time
T0 = time.time()
log = lambda m: print(f'[{time.time() - T0:6.1f} s] {m}', flush=True)
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/bought"

wheel_d = 24; s = wheel_d / 11.5; R = wheel_d / 2; d = 4.0 * s
L = 2 * d * math.tan(math.radians(30)) + 0.25; row_gap = 0.35; W = 2 * (2 * (R - d) + 2 * row_gap)
pin_d, pin_wall, pin_fit = 1.0, 0.8, -0.05
roller_hole = pin_d + 0.2
clr_rad, clr_end, rim_gap = 0.2, 0.25, 0.15
boss_t, fillet, fillet_in, edge_r = 1.5, 0.8, 0.3, 0.6
bore, bore_flat = 1.95, 0.5
screw_circle, screw_clear, screw_pilot, head_d, head_h, pilot_floor = 3.0, 2.3, 1.6, 3.9, 1.8, 1.2
zc = W / 4; frame_r = R - rim_gap
pin_end = math.sqrt(frame_r ** 2 - (d + pin_d / 2 + pin_wall) ** 2); pin_len = 2 * pin_end
rr = lambda t: math.sqrt(R * R - t * t) - d
h = W / 2


def rot(shape, ang):
    sh = shape.copy(); sh.rotate(V(), V(0, 0, 1), ang); return sh


def barrel(length, hole):
    """Roller: revolve the barrel profile (a smooth B-spline) about Z, then lay it along Y."""
    n = 24
    pts = [V(max(rr(-length / 2 + length * i / n), 0.05), 0, -length / 2 + length * i / n) for i in range(n + 1)]
    bs = Part.BSplineCurve(); bs.interpolate(pts)
    a, b = V(hole / 2, 0, length / 2), V(hole / 2, 0, -length / 2)
    w = Part.Wire([bs.toShape(), Part.LineSegment(pts[-1], a).toShape(), Part.LineSegment(a, b).toShape(), Part.LineSegment(b, pts[0]).toShape()])
    sol = Part.Face(w).revolve(V(), V(0, 0, 1), 360)
    sol = Part.Solid(sol) if sol.ShapeType == "Shell" else sol
    sol.rotate(V(), V(1, 0, 0), 90)
    return sol


def circle_hull(circles):
    """Exact 2D convex hull of circles [(x, y, r)]: arcs joined by common tangents, as a face."""
    samp = []
    for k, (x, y, r) in enumerate(circles):
        samp += [(x + r * math.cos(2 * math.pi * j / 720), y + r * math.sin(2 * math.pi * j / 720), k) for j in range(720)]
    pts = sorted(samp)
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    hull = lo[:-1] + up[:-1]                               # CCW
    seq = []
    for p in hull:
        if not seq or seq[-1] != p[2]: seq.append(p[2])
    if len(seq) > 1 and seq[0] == seq[-1]: seq.pop()
    def tangent(c1, c2):                                   # outer tangent on the right of c1 -> c2 (CCW hull)
        (x1, y1, r1), (x2, y2, r2) = c1, c2
        dx, dy = x2 - x1, y2 - y1; L_ = math.hypot(dx, dy); a = math.atan2(dy, dx); f = math.acos((r1 - r2) / L_)
        t = a - f
        return V(x1 + r1 * math.cos(t), y1 + r1 * math.sin(t), 0), V(x2 + r2 * math.cos(t), y2 + r2 * math.sin(t), 0), t
    cs = [circles[k] for k in seq]; n = len(cs)
    tans = [tangent(cs[i], cs[(i + 1) % n]) for i in range(n)]
    edges = []
    for i in range(n):
        x, y, r = cs[i]
        _, end_prev, t_in = tans[i - 1]; start_next, _, t_out = tans[i]
        while t_out <= t_in: t_out += 2 * math.pi
        if t_out - t_in > 1e-6:
            edges.append(Part.ArcOfCircle(Part.Circle(V(x, y, 0), V(0, 0, 1), r), t_in, t_out).toShape())
        edges.append(Part.LineSegment(start_next, tans[i][1]).toShape())
    return Part.Face(Part.Wire(Part.__sortEdges__(edges)))


def pin_boss_circles(sign, ang):
    y0 = L / 2 + clr_end; out = []
    for y in (y0, pin_end):
        p = V(d, sign * y, 0); p = App.Rotation(V(0, 0, 1), ang).multVec(p)
        out.append((p.x, p.y, pin_d / 2 + boss_t))
    return out


def pocket_face(ang):
    y0 = L / 2 + clr_end; n = 24
    inboard = [V(-(rr(-y0 + 2 * y0 * i / n) + clr_rad), -y0 + 2 * y0 * i / n, 0) for i in range(n + 1)]
    bs = Part.BSplineCurve(); bs.interpolate(inboard)
    xo = R + 3
    a, b = V(xo, y0, 0), V(xo, -y0, 0)
    w = Part.Wire([bs.toShape(), Part.LineSegment(inboard[-1], a).toShape(), Part.LineSegment(a, b).toShape(), Part.LineSegment(b, inboard[0]).toShape()])
    f = Part.Face(w); f.translate(V(d, 0, 0)); f.rotate(V(), V(0, 0, 1), ang)
    return f


def frame_face():
    rim = Part.Face(Part.Wire(Part.makeCircle(frame_r)))
    hub = (0, 0, d - (R - d) + 0.5)
    lobes = [circle_hull([hub] + pin_boss_circles(+1, i * 120) + pin_boss_circles(-1, (i + 1) * 120)) for i in range(3)]
    f = rim.common(lobes[0].fuse([lobes[1], lobes[2]]).removeSplitter())
    for i in range(3):
        f = f.cut(pocket_face(i * 120))
    f = f.removeSplitter()
    f = f.Faces[0]
    for dist, join in ((fillet_in, 2), (-fillet_in, 0), (-fillet, 2), (fillet, 0)):   # round the concave, then the convex corners
        f = f.makeOffset2D(dist, join=join); f = f if f.ShapeType == "Face" else f.Faces[0]
    return f


def half(kind):
    sol = frame_face().extrude(V(0, 0, h)); log(f'{kind} half outline')
    # (the OpenSCAD part rounds the outer face edges 0.6 mm; an OCC fillet on these B-spline edges takes many minutes,
    #  so the CAD model keeps them sharp: cosmetic only, every fit and clearance is unchanged)
    cut = []
    if kind == "motor":
        c = Part.makeCylinder(bore / 2, 3 * W, V(0, 0, -1.5 * W))
        flat = Part.makeBox(bore, 2 * bore, 4 * W, V(bore / 2 - bore_flat, -bore, -2 * W)); flat.rotate(V(), V(0, 0, 1), 30)
        cut.append(c.cut(flat))
    sa = 30 if kind == "outer" else -30
    for i in range(3):
        a = math.radians(sa + i * 120); p = V(screw_circle * math.cos(a), screw_circle * math.sin(a), 0)
        if kind == "outer":
            cut += [Part.makeCylinder(screw_clear / 2, h + 2, p + V(0, 0, -1)), Part.makeCylinder(head_d / 2, head_h + 1, p + V(0, 0, h - head_h))]
        else:
            cut.append(Part.makeCylinder(screw_pilot / 2, h - pilot_floor + 1, p + V(0, 0, -1)))
        pin = Part.makeCylinder((pin_d + pin_fit) / 2, 4 * R, V(d, 2 * R, zc), V(0, -1, 0)); pin.rotate(V(), V(0, 0, 1), i * 120)
        cut.append(pin)
    for c in cut:
        sol = sol.cut(c)
    log(f'{kind} half holes'); return sol.removeSplitter()


def with_rollers(kind):
    parts = [("frame", half(kind))]
    for i in range(3):
        r = barrel(L, roller_hole); r.translate(V(d, 0, zc)); r.rotate(V(), V(0, 0, 1), i * 120)
        p = Part.makeCylinder(pin_d / 2, pin_len, V(d, pin_len / 2, zc), V(0, -1, 0)); p.rotate(V(), V(0, 0, 1), i * 120)
        parts += [("roller", r), ("pin", p)]
    return parts


COL = {"frame": (0.62, 0.63, 0.65), "roller": (0.08, 0.08, 0.09), "pin": (0.72, 0.72, 0.75)}   # grey PETG, black TPU, steel
parts = with_rollers("outer")
for k, sh in with_rollers("motor"):
    m = sh.mirror(V(), V(0, 0, 1)); m.rotate(V(), V(0, 0, 1), 60)
    parts.append((k, m))
comp = Part.makeCompound([sh for _, sh in parts])
comp.exportBrep(os.path.join(OUT, "Wheel.brep"))
json.dump([[list(COL[k]), len(sh.Faces)] for k, sh in parts], open(os.path.join(OUT, "Wheel.colors.json"), "w"))
print("wheel:", len(parts), "solids, valid", comp.isValid(), "volume %.1f" % comp.Volume, "faces", len(comp.Faces),
      "bbox", [round(v, 2) for v in (comp.BoundBox.XMin, comp.BoundBox.YMin, comp.BoundBox.ZMin, comp.BoundBox.XMax, comp.BoundBox.YMax, comp.BoundBox.ZMax)])
