# Rear ID tag (every robot): a snap-on bar just behind the two rear deck posts carries a 9.5 mm ArUco 4x4 sticker at
# z 49.2-58.7, ~24 mm inside the back of the body. Approved 2D: sketches/tag_bar_v2.png (draw_tag_bar_v2.py).
#   * the posts (DeckStandoffs) get a 0.5 mm ring groove; the bar's C-clips (open to the front) snap into it from behind,
#     so the bar always sits at the same height and square. No screws.
#   * read sharply at ~10-14 cm (the camera is focused far); heal / backstab = tag seen behind within the last ~1 s AND the
#     reader's front ToF sees the bar / deck edge within ~3-5 cm AND both shared poses agree (user, 2026-10-22, option 1)
#   * the earlier rear tag plate (wall pads / pockets / pilots, a slotted deck boss, 2 screws) is gone: chassis_features()
#     and deck_features() now only remove those features, so a master that still has them is cleaned on its next build
# Used by build_chassis.py, build_printed.py and add_tag_bar.py (on an open master, without a full rebuild). Every
# feature / object here is labelled "Tag..." so it can be redone.
import math
import FreeCAD as App
import Part

V = App.Vector
TAG = dict(
    post=(-11.5, 15.5),         # rear deck posts at (x, +-y): deck_leg_x, deck_leg_y
    groove_d=0.5,               # ring groove depth in each post (Ø5.6 -> Ø4.6)
    groove_z=(48.5, 59.2),      # groove: 0.2 above and below the clips
    clip_bore=5.0, clip_wall=1.6, clip_mouth=3.8,   # C-clip on the 4.6 groove core: 0.2 a side; the mouth snaps over it
    bar_x=(-15.6, -14.1),       # bar: 1.5 thick; its back face is flush with the clips' back (tangent): a smooth joint (user)
    led_notch=(-14.7, -3.4, 3.85, 56.6),   # notch in the bar's top front round the LED-board nut boss (x0, y0, y1, z0): 0.4 clear
    bar_z=(48.7, 58.9),         # bar height (clips the same); top 0.5 under the antenna strip under the deck
    tag_size=9.5, tag_z=(49.2, 58.7),   # ArUco 4x4 sticker on the bar's back face, centred at y 0
    tag_recess=(10.1, 0.25),    # where the sticker goes (approved 2D: sketches/tag_recess_v1.png): 0.3 a side, the bar's full
                                # height; only 0.25 deep: the LED-boss notch at the front leaves 0.9 there (0.65 after it)
    fillet_front=1.5,           # bar-to-clip front inside corners
)


def q(doc, e):
    return float(doc.Params.evalExpression("Params." + e).Value)


def screw_points(doc):
    """no screws: the bar snaps on (kept for build_fasteners.py)"""
    return []


def _remove_tag_features(body):
    doc = body.Document
    feats = [o for o in body.Group if o.Label.startswith("Tag")]
    if not feats:
        return 0
    keep = [o for o in body.Group if o not in feats and o.isDerivedFrom("PartDesign::Feature")]
    for o in reversed(feats):
        body.removeObject(o)
        doc.removeObject(o.Name)
    if keep:
        body.Tip = keep[-1]
        keep[-1].Visibility = True        # the body shows its tip: a hidden tip hides the whole body
    doc.recompute()
    return len(feats)


def _remove_object(doc, name):
    o = doc.getObject(name)
    if not o:
        return False
    for p in list(o.InList):
        if hasattr(p, "removeObject"):
            p.removeObject(o)
    doc.removeObject(name)
    return True


def chassis_features(doc, body):
    """the old rear tag plate's wall pads / pockets / pilots: removed (the bar needs nothing in the chassis)"""
    return _remove_tag_features(body)


def deck_features(doc, body):
    """the old rear tag plate's slotted deck boss: removed"""
    return _remove_tag_features(body)


def standoff_grooves(doc, body):
    """a ring groove round each rear deck post, where the bar's C-clips sit"""
    _remove_tag_features(body)
    T = TAG; r = q(doc, "standoff_d") / 2; z0, z1 = T["groove_z"]
    import Sketcher
    xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")
    sk = body.newObject("Sketcher::SketchObject", "TagGrooveSketch")
    sk.AttachmentSupport = [(xy, "")]; sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(V(0, 0, z1), App.Rotation())
    for s in (1, -1):                                   # an annulus round each post: groove core .. 1 mm outside the post
        c = V(T["post"][0], s * T["post"][1], 0)
        sk.addGeometry(Part.Circle(c, V(0, 0, 1), r + 1.0), False)
        sk.addGeometry(Part.Circle(c, V(0, 0, 1), r - T["groove_d"]), False)
    sk.Label = "TagGrooveSketch"; sk.Visibility = False
    pk = body.newObject("PartDesign::Pocket", "TagGroove")
    pk.Profile = sk; pk.Type = "Length"; pk.Length = z1 - z0          # down from the groove top
    pk.Label = "TagGroove"
    doc.recompute()


def bar_shape(doc):
    """the tag bar: a flat bar behind the posts joining two C-clips (open to +x, the front)"""
    T = TAG; (x0, x1), (z0, z1) = T["bar_x"], T["bar_z"]; px, py = T["post"]
    ro, ri = T["clip_bore"] / 2 + T["clip_wall"], T["clip_bore"] / 2
    bar = Part.makeBox(x1 - x0, 2 * py, z1 - z0, V(x0, -py, z0))
    for s in (1, -1):
        c = V(px, s * py, z0)
        ring = Part.makeCylinder(ro, z1 - z0, c).cut(Part.makeCylinder(ri, z1 - z0 + 2, c - V(0, 0, 1)))
        mouth = Part.makeBox(ro + 1, T["clip_mouth"], z1 - z0 + 2, V(px, s * py - T["clip_mouth"] / 2, z0 - 1))
        bar = bar.fuse(ring.cut(mouth))
        bar = bar.cut(Part.makeCylinder(ri, z1 - z0 + 2, c - V(0, 0, 1)))     # keep the clip bore clear of the bar
    bar = bar.removeSplitter()
    # front inside corners where the bar meets the clips: real fillets (the back face is tangent to the clips: no corner)
    yf = py - math.sqrt(ro ** 2 - (x1 - px) ** 2)                            # front face meets the clip's outside
    es = [e for e in bar.Edges if e.Curve.TypeId == "Part::GeomLine" and abs(e.Curve.Direction.z) > 0.999
          and abs(e.Vertexes[0].X - x1) < 0.05 and abs(abs(e.Vertexes[0].Y) - yf) < 0.05]
    if es:
        bar = bar.makeFillet(T["fillet_front"], es)
    nx, ny0, ny1, nz = T["led_notch"]                                        # clear the LED-board nut boss
    bar = bar.cut(Part.makeBox(x1 + 1 - nx, ny1 - ny0, z1 + 1 - nz, V(nx, ny0, nz)))
    rw, rd = T["tag_recess"]                                                 # the sticker's recess in the back face
    bar = bar.cut(Part.makeBox(1 + rd, rw, z1 - z0 + 2, V(x0 - 1, -rw / 2, z0 - 1)))
    return bar.removeSplitter()


def tag_bar(doc, colour=None):
    """(re)make the TagBar object in the SensorMast component (and drop the old TagPlate); colour: the master's printed
    (Base) colour, so each variant's recolour() swaps it for its own style colour (style_colours.py)"""
    _remove_object(doc, "TagPlate")
    _remove_object(doc, "TagBar")
    if colour is None:
        g = {}
        import os as _os                                  # repo-relative paths: see .bugbot-root
        _d = _os.path.dirname(_os.path.abspath(__file__))
        while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
        BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
        exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read(), g)
        colour = g["rgb"](g["STYLES"]["Base"][0])
    o = doc.addObject("Part::Feature", "TagBar")
    o.Label = "TagBar"
    o.Shape = bar_shape(doc)
    if App.GuiUp:
        o.ViewObject.ShapeColor = colour
    comp = doc.getObject("SensorMast")
    if comp and comp.TypeId == "App::Part":
        comp.addObject(o)
    return o
