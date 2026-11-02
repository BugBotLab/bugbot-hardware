# BugBot variants: the master is the BASE (BugBot_Base.FCStd); every style is the base + its own class modules.
#   base     = everything in the master's base assembly (Assembly): chassis, drive, boards, mast, deck, tag bar, fasteners.
#   modules  = class parts in the same file (they share the Params), outside the base assembly, in the "Modules" folder:
#              GripperMount (SG90, servo block, pivot bracket + tube + screws: the arm drive), Gripper (arms, front bar,
#              sleeve, horn + screws), Kicker (solenoid, kick disc, bracket + screws), Ball.
#              Built in place (robot frame); the gripper component turns by grip_ang.
#   Scorpion = base + GripperMount + Gripper + Kicker + Ball     -> build_scorpion.py  -> BugBot_Scorpion.FCStd
#   Ant      = base + GripperMount + Gripper + Ball              -> build_ant.py       -> BugBot_Ant.FCStd
#   Wasp     = base + Kicker (ram, not the disc)  -> build_wasp.py      -> BugBot_Wasp.FCStd
#   Beetle   = base + shield (gripper pivot ends) -> build_beetle.py    -> BugBot_Beetle.FCStd
#   Spider   = base + tag-dispenser arm           -> build_spider.py    -> BugBot_Spider.FCStd
# FusionFlow's Variants object in BugBot_Base.FCStd reruns them when the base is saved (or: right-click > Update variants now).
import FreeCAD as App
import Part

MODULES = ("GripperMount", "Gripper", "Kicker", "Ball")                 # module names; their parts are named "<Module>:1/<part label>"
DEFINITIONS = {"MainPCB", "FrontPCB", "WheelFrame", "WheelFrameCut", "WheelFrameFuse", "WheelFrameLower", "RollerClearance"} # hidden definitions shown through other parts (build_structure.py
                                                                # HIDDEN): never parts. Anything else counts even when hidden in the
                                                                # view (hiding a board to look inside must not change a variant)


def _plain(sh):
    """a copy without FreeCAD's topological-naming table: the style files are static copies and don't need it, and mixed
    tables (master + style document) printed ~470 "hasher mismatch" lines per sim export"""
    c = sh.copy()
    c.ElementMap = {}
    return c


# ---------- check cache: a clash / clearance result is reused while the shapes involved are unchanged ----------
import hashlib, json, os
_CHECKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_check_cache.json")


_SIGS = {}                                              # id(shape) -> (shape, sig): one fingerprint per shape per run


def sig(sh):
    """a shape's identity for the check cache: volume, area, face count, bound box (to 1 um). Memoised per shape object
    (a KiCad board's volume / area is slow, and a clash loop asks for it once per pair)"""
    hit = _SIGS.get(id(sh))
    if hit is not None and hit[0] is sh:
        return hit[1]
    b = sh.BoundBox
    s = hashlib.sha1(repr((round(sh.Volume, 3) if sh.Solids else 0, round(sh.Area, 3), len(sh.Faces),
                           tuple(round(v, 3) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))).encode()).hexdigest()[:16]
    _SIGS[id(sh)] = (sh, s)
    return s


def _store():
    st = getattr(App, "_bugbot_checks", None)          # (kept on App: the build scripts reload this module)
    if st is None:
        try:
            st = json.load(open(_CHECKS))
        except Exception:
            st = {}
        App._bugbot_checks = st
    return st


def cached(tag, shapes, fn):
    """fn() once per (tag, shapes): later updates with the same shapes reuse the stored result (JSON values only)"""
    st = _store()
    key = tag + ":" + ":".join(sig(s) for s in shapes)
    if key not in st:
        st[key] = fn()
    return st[key]


def save_checks():
    """write the check cache (call once at the end of a build script)"""
    st = _store()
    if len(st) > 20000:                               # (a bound: old entries pile up over many edits)
        for k in list(st)[:len(st) - 20000]:
            del st[k]
    with open(_CHECKS + ".tmp", "w") as f:
        json.dump(st, f)
    os.replace(_CHECKS + ".tmp", _CHECKS)


def common_volume(a, b):
    """overlap volume of two shapes, solid by solid (whole KiCad compounds gave false overlaps), cached"""
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    return cached("common", (a, b), lambda: sum(x.common(y).Volume for x in a.Solids for y in b.Solids
                                                 if x.BoundBox.intersect(y.BoundBox)))


def distance(a, b):
    """closest distance between two shapes, cached"""
    return cached("dist", (a, b), lambda: a.distToShape(b)[0])


def _colours(o):
    try:
        return list(o.ViewObject.DiffuseColor), tuple(o.ViewObject.ShapeColor)
    except Exception:
        return None, (0.8, 0.8, 0.8)


def leaves(doc, assembly="Assembly"):
    """[(name, shape, diffuse colours, shape colour)] for every part of the base assembly (hidden or not, not DEFINITIONS);
    name = full assembly path (Occurrence:1/Sub/Part), the same names SimLink and the render link use."""
    asm = doc.getObject(assembly)
    out = []
    for occ in asm.Group:
        if not occ.isDerivedFrom("App::Link"):
            continue

        def walk(path, obj, prefix):
            tgt = obj.getLinkedObject(True) if obj.isDerivedFrom("App::Link") else obj
            if tgt.isDerivedFrom("App::Part"):
                for c in tgt.Group:
                    if c.isDerivedFrom("App::Origin") or c.isDerivedFrom("App::DocumentObjectGroup") or c.Name in DEFINITIONS:
                        continue
                    walk(path + c.Name + ".", c, prefix + "/" + c.Label)
            elif hasattr(tgt, "Shape") and not tgt.Shape.isNull():
                sh = _plain(Part.getShape(asm, path, needSubElement=False, transform=True))
                col, sc = _colours(tgt)
                out.append((prefix, sh, col, sc))
        walk(occ.Name + ".", occ, occ.Label)
    return out


def module_leaves(doc, module):
    """[(name, shape, diffuse colours, shape colour)] of one class module (outside the base assembly), placed as it sits on
    the robot (its component's placement applied: the gripper's grip_ang); names "<module>:1/<part label>"."""
    obj = doc.getObject(module)
    if obj is None:
        return []
    if not obj.isDerivedFrom("App::Part"):                       # a single body (the Ball)
        return [(f"{module}:1", _plain(obj.Shape), *_colours(obj))]
    out = []
    for c in obj.Group:
        if c.isDerivedFrom("App::Origin") or c.isDerivedFrom("App::DocumentObjectGroup") or c.Name in DEFINITIONS:
            continue
        if not hasattr(c, "Shape") or c.Shape.isNull():
            continue
        sh = _plain(Part.getShape(obj, c.Name + ".", needSubElement=False, transform=True))
        out.append((f"{module}:1/{c.Label}", sh, *_colours(c)))
    return out


def base_parts(doc):
    """the base robot's parts: the whole base assembly"""
    return leaves(doc)


def parts_of(doc, occurrence):
    """{name: (shape, diffuse, colour)} of one module ("Gripper:1", "Kicker:1", "Ball:1") or base occurrence, for a
    variant to reuse"""
    mod = occurrence.split(":")[0]
    rows = module_leaves(doc, mod) if mod in MODULES else [r for r in leaves(doc) if r[0].split("/")[0] == occurrence]
    return {n: (s, c, sc) for n, s, c, sc in rows}
