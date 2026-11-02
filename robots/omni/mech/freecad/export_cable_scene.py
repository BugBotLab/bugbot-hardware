# Cable routing, step 1 of 3 (run in FreeCAD): exports the obstacles (the positioned assembly + the modules, without the
# board-to-part cables) as STL meshes and the cable end points / directions to _cables/scene.json, for route_cables.py
# (step 2, plain Python: voxel grid + A*) and build_cables.py (step 3, back in FreeCAD: tubes + check).
#   python fusionflow/ffclient.py run mech/freecad/export_cable_scene.py
import json, math, os
import Part, MeshPart
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/_cables"
os.makedirs(OUT, exist_ok=True)
CABLE_NAMES = ("MotorCable1", "MotorCable2", "MotorCable3", "UnderglowCable", "SolenoidCable", "ServoCable")
for n in CABLE_NAMES:                                     # old routed cables would block their own new routes
    o = doc.getObject(n)
    if o:
        for p in list(o.InList):
            if hasattr(p, "removeObject"): p.removeObject(o)
        doc.removeObject(n)
doc.recompute()
pf = lambda n: float(doc.Params.get(n).Value) if hasattr(doc.Params.get(n), "Value") else float(doc.Params.get(n))
PCB_Z = pf("pcb_z"); PCB_TOP = PCB_Z + pf("pcb_t"); Z_SIDE = PCB_Z - 1.45
DU_ANG = {1: 40.0, 2: 160.0, 3: 280.0}
rot = lambda p, a: [p[0] * math.cos(math.radians(a)) - p[1] * math.sin(math.radians(a)), p[0] * math.sin(math.radians(a)) + p[1] * math.cos(math.radians(a)), p[2]]
gm = doc.getObject("Gearmotor").Shape.BoundBox
gyc, gzc = (gm.YMin + gm.YMax) / 2, (gm.ZMin + gm.ZMax) / 2
fl = doc.getObject("NFCFloor").Shape.BoundBox
sol = doc.getObject("Solenoid").Shape.BoundBox
srv = doc.getObject("Servo").Shape.BoundBox
# motor leads: soldered to the tabs on the motor's rear face, then straight up (behind each rear face is the next
# motor's side: no room to come in from behind), so they arrive from above
cables = {   # start (back of the plug), its outward direction, end (the part's terminals), direction into them, radius, wires, module
    "MotorCable1": ([-19.5, 4.22, Z_SIDE], [1, 0, 0], rot([gm.XMin - 0.8, gyc, gm.ZMax + 0.8], DU_ANG[1]), [0, 0, -1], 0.7, 2, None, "J14 -> motor 1"),
    "MotorCable2": ([-19.5, -11.36, Z_SIDE], [1, 0, 0], rot([gm.XMin - 0.8, gyc, gm.ZMax + 0.8], DU_ANG[2]), [0, 0, -1], 0.7, 2, None, "J15 -> motor 2"),
    "MotorCable3": ([-19.5, 11.01, Z_SIDE], [1, 0, 0], rot([gm.XMin - 0.8, gyc, gm.ZMax + 0.8], DU_ANG[3]), [0, 0, -1], 0.7, 2, None, "J16 -> motor 3"),
    "UnderglowCable": ([-19.5, -3.56, Z_SIDE], [1, 0, 0], [0.0, -1.2, fl.ZMax + 0.5], [0, 0, -1], 1.0, 4, None, "J17 -> floor PCB J2"),
    "SolenoidCable": ([sol.XMin + (sol.XMax - sol.XMin) / 2 - 1.0, sol.YMax, sol.ZMin + 1.5], [0, 1, 0], [19.0, -29.4, PCB_TOP + 7.0], [0, 0, -1], 0.8, 2, "Kicker", "solenoid -> J19 (top)"),
    "ServoCable": ([srv.XMin + 2.0, (srv.YMin + srv.YMax) / 2, srv.ZMin + 2.0], [-1, 0, 0], [-6.0, -15.96, PCB_TOP + 8.5], [0, 0, -1], 0.8, 3, "GripperMount", "SG90 -> J18"),
}


def gshape(o):
    s = Part.getShape(o)
    p = o.getParentGeoFeatureGroup() if hasattr(o, "getParentGeoFeatureGroup") else None
    if p is not None: s = s.copy(); s.transformShape(p.getGlobalPlacement().toMatrix())
    return s


groups = {}
for name in ("Frame_1", "DriveUnit_1", "DriveUnit_2", "DriveUnit_3", "Electronics_1", "SensorMast_1", "NFC_1", "Fasteners_1",
             "Kicker", "GripperMount", "Gripper", "Ball"):
    o = doc.getObject(name)
    if not o: continue
    s = gshape(o)
    if s.isNull(): continue
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.25, AngularDeflection=0.5)
    fn = f"{OUT}/{name}.stl"; m.write(fn); groups[name] = {"stl": fn, "tris": m.CountFacets}
json.dump({"cables": cables, "groups": groups, "pcb_z": PCB_Z, "pcb_top": PCB_TOP}, open(f"{OUT}/scene.json", "w"), indent=1)
result = {"groups": {k: v["tris"] for k, v in groups.items()}, "cables": list(cables)}
