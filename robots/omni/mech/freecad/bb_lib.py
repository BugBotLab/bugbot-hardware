# Shared sketch helpers for the BugBot build scripts (exec'd into each script, so they use its `doc` and `body`).
from fusionflow import helpers as H


def ev(expr):
    """Value of an expression in mm or deg, for a sketch's starting geometry (the expression then drives it)."""
    try:
        v = doc.Params.evalExpression(expr)
        return float(getattr(v, "Value", v))           # plain numbers (w_n) have no .Value
    except Exception:
        return 1.0


def dims(s, c0, names, exprs):
    for k, (n, e) in enumerate(zip(names, exprs)):
        s.renameConstraint(c0 + k, n)
        s.setExpression(f"Constraints.{n}", e)


def rect(s, tag, x, y, w, l):
    """Rectangle driven by expressions: corner (x, y), size w along X, l along Y."""
    c0 = s.ConstraintCount
    H.rect(s, ev(x), ev(y), max(ev(w), 0.5), max(ev(l), 0.5))
    dims(s, c0 + 8, [f"{tag}_w", f"{tag}_l", f"{tag}_x", f"{tag}_y"], [w, l, x, y])


def circ(s, tag, x, y, dia):
    c0 = s.ConstraintCount
    H.circle(s, ev(x), ev(y), max(ev(dia), 0.5))
    dims(s, c0, [f"{tag}_dia", f"{tag}_x", f"{tag}_y"], [dia, x, y])


def rotated_sketch(b, name, ang, z):
    """Sketch on XY turned by an angle parameter about Z and lifted to z (both expressions)."""
    s = H.sketch(b, "XY", name)
    s.AttachmentOffset = App.Placement(Vector(0, 0, ev(z)), App.Rotation(Vector(0, 0, 1), ev(ang)))
    s.setExpression(".AttachmentOffset.Rotation.Angle", ang)
    s.setExpression(".AttachmentOffset.Base.z", z)
    return s


def frame_sketch(b, lcs, name, mode, off):
    s = b.newObject("Sketcher::SketchObject", name)
    s.AttachmentSupport = [(lcs, "")]
    s.MapMode = mode
    s.AttachmentOffset = App.Placement(Vector(0, 0, ev(off)), App.Rotation())
    s.setExpression(".AttachmentOffset.Base.z", off)
    return s


def pocket(s, kind="ThroughAll", length=None, reverse=False, mid=False, label=None):
    p = body.newObject("PartDesign::Pocket", label or "Cut")
    p.Profile = s
    p.Type = kind
    if length:
        p.setExpression("Length", length)
    p.Reversed = reverse
    p.Midplane = mid
    doc.recompute()
    H.settle_sketch(s)
    s.ViewObject.Visibility = False
    return p
