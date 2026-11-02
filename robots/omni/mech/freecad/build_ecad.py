# BugBot in FreeCAD: the KiCad boards (ECAD link). Run after build_pcb_caps.py, before build_structure.py.
#   MainBoard (KiCad)  follows design/schematics/Main/BugBot_Main.kicad_pcb: saving in KiCad updates it here.
#                      Its outline + mounting holes come from the parametric MainPCB sketch (push to KiCad).
import os
from fusionflow import ecad, extrude as X
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
E = lambda s: X.expand(s, doc)
#   FrontSensorBoard (KiCad)  follows design/schematics/Front/BugBot_Front.kicad_pcb; stands vertically behind the mast
#                      (board frame x, y, z = robot Y, Z, X - fsb_x); outline from the parametric FrontPCB sketch.
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
K = BB + "/design"
OUTD = BB + "/mech/freecad"
BOARDS = [("MainBoard", "MainBoard (KiCad)", K + "/schematics/Main/BugBot_Main.kicad_pcb", "MainPCB", "PCBSketch",
           "translationm(0 mm; 0 mm; pcb_z)"),
          ("FrontSensorBoard", "FrontSensorBoard (KiCad)", K + "/schematics/Front/BugBot_Front.kicad_pcb", "FrontPCB", "FrontPCBSketch",
           "placement(vector(fsb_x; 0 mm; 0 mm); rotation(vector(1; 1; 1); 120))")]
# (the LED ring board is retired since 2026-10-31: the beacon is a bought 7-LED jewel, build_ledpcb.py)
result = {}
for name, label, pcb, mech, sketch, frame in BOARDS:
    old = doc.getObject(name)
    if old:
        ecad.stop(old)
        parents = [p for p in old.InList if hasattr(p, "removeObject")]
        for p in parents:
            p.removeObject(old)
        doc.removeObject(name)
    else:
        parents = []
    sk = [o for o in doc.getObject(mech).Group if o.Label == sketch][0]
    b = ecad.make(doc, name, pcb, outline_sketch=sk, placement_expr=E(frame))
    b.Label = label
    for p in parents:                                       # back where it was (e.g. the Electronics component)
        p.addObject(b)
    b.KeepoutHook = OUTD + "/keepouts.py"                  # printed parts touching the board -> KiCad keep-outs
    b.SubstrateColour = (0.11, 0.40, 0.22)                    # green solder mask (all boards)
    ecad.sync(b, wait=True)                                   # again: make() loaded it before the colour was set
    doc.getObject(mech).ViewObject.Visibility = False      # the board's mechanical definition: its outline source
    bb = b.Shape.BoundBox
    result[name] = {"status": b.Status, "bbox": [round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]}
doc.recompute(); doc.save()
