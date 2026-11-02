# Cable routing, step 3 of 3 (FreeCAD): builds the board-to-part cables from route_cables.py's paths (_cables/paths.json)
# as tubes along splines, puts base cables in the Electronics component and module cables in their module, checks each
# against the obstacles exactly (bbox prefilter + boolean common, 4 mm in from each end), and reports lengths and the
# pre-crimped JST lead to buy (length + 15 mm slack, rounded up to 50 / 100 / 150 / 200 / 300 mm).
# Steps: export_cable_scene.py (FreeCAD) -> route_cables.py (C:/Python312) -> build_cables.py (FreeCAD).
#   MotorCable1-3 J14-J16 -> gearmotor terminals; UnderglowCable J17 -> floor PCB J2; SolenoidCable solenoid -> J19;
#   ServoCable SG90 -> J18. (LEDCable: build_cable.py; NFCCable / NFCLinkCable: build_nfc.py; encoders and the front
#   board plug straight into J11-J13 / J6.)
#   python fusionflow/ffclient.py run mech/freecad/build_cables.py
import json
import Part
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/mech/freecad/_cables/"
paths = json.load(open(D + "paths.json"))
SH = (50, 100, 150, 200, 300)


def gshape(o):
    s = Part.getShape(o)
    p = o.getParentGeoFeatureGroup() if hasattr(o, "getParentGeoFeatureGroup") else None
    if p is not None: s = s.copy(); s.transformShape(p.getGlobalPlacement().toMatrix())
    return s


for name in paths:                                         # old copies first, or they become obstacles to themselves
    old = doc.getObject(name)
    if old:
        for q in list(old.InList):
            if hasattr(q, "removeObject"): q.removeObject(old)
        doc.removeObject(name)
doc.recompute()
OBST = []
for name in ("Frame_1", "DriveUnit_1", "DriveUnit_2", "DriveUnit_3", "Electronics_1", "SensorMast_1", "NFC_1", "Fasteners_1",
             "Kicker", "GripperMount", "Gripper", "Ball"):
    o = doc.getObject(name)
    if o:
        try: OBST += [(name, s) for s in gshape(o).Solids]
        except Exception: pass
result = {}
built = []                                                 # cables made so far: they must not cross each other either
for name, p in paths.items():
    if not p.get("ok"):
        result[name] = {"route": p["label"], "ok": False}; continue
    way = [V(*q) for q in p["points"]]
    pts = [way[0]]                                         # densified (every ~1 mm) and fitted (0.15 mm): smooth, no overshoot
    for a_, b_ in zip(way, way[1:]):
        n = max(1, int((b_ - a_).Length / 1.0))
        pts += [a_ + (b_ - a_) * (k / n) for k in range(1, n + 1)]
    sh = None
    for tol in (0.08, 0.15, 0.3):
        try:
            bs = Part.BSplineCurve(); bs.approximate(Points=pts, DegMin=3, DegMax=5, Tolerance=tol)
            t0 = bs.tangent(bs.FirstParameter)[0]
            sh = Part.Wire([bs.toShape()]).makePipeShell([Part.Wire([Part.makeCircle(p["radius"], pts[0], t0)])], True, True)
            break
        except Exception:
            sh = None
    if sh is None:
        result[name] = {"route": p["label"], "ok": False, "why": "sweep failed"}; continue
    o = doc.addObject("Part::Feature", name); o.Label = name; o.Shape = sh
    host = doc.getObject(p["module"]) if p.get("module") else doc.getObject("Electronics")
    if host and hasattr(host, "addObject"): host.addObject(o)
    if App.GuiUp: o.ViewObject.ShapeColor = (0.12, 0.12, 0.13)
    L = bs.length()
    a = bs.parameterAtDistance(4.0, bs.FirstParameter); c = bs.parameterAtDistance(L - 4.0, bs.FirstParameter)
    seg = bs.copy(); seg.segment(a, c)
    mid = Part.Wire([seg.toShape()]).makePipeShell([Part.Wire([Part.makeCircle(p["radius"], seg.value(seg.FirstParameter), seg.tangent(seg.FirstParameter)[0])])], True, True)
    bb = mid.BoundBox; hits = {}
    for gname, s in OBST + built:
        if not bb.intersect(s.BoundBox): continue
        try: v = mid.common(s).Volume
        except Exception: continue
        if v > 0.15: hits[gname] = round(hits.get(gname, 0) + v, 2)
    built.append((name, sh))
    result[name] = {"route": p["label"], "length_mm": round(L, 1), "wires": p["wires"], "clear": not hits, "hits": hits,
                    "buy_mm": next((s for s in SH if s >= L + 15), None), "via_z_mm": [round(min(q.z for q in pts), 1), round(max(q.z for q in pts), 1)]}
doc.recompute()
