# The plain base robot in the simulator (SimLink): wheels only, no servo, gripper, kicker or ball.
#   python fusionflow/ffclient.py run mech/freecad/build_sim_base.py
#   then: C:/Python312/python.exe simlink/SimLink/simlink/sim/build_scene.py mech/freecad/sim_base
# The base has no style document (the master IS the base), so this copies the base parts into a scratch document
# "BugBot_BaseSim" (never saved: the master is only read), exports from it and closes it.
import sys, importlib
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import sim_style as S; importlib.reload(S)
import variants; importlib.reload(variants)
src = App.getDocument("BugBot_Base")
if "BugBot_BaseSim" in App.listDocuments(): App.closeDocument("BugBot_BaseSim")
doc = App.newDocument("BugBot_BaseSim")
root = doc.addObject("App::DocumentObjectGroup", "Base")
for name, sh, col, sc in variants.base_parts(src):
    o = doc.addObject("Part::Feature", "B_" + "".join(ch if ch.isalnum() else "_" for ch in name)[:48]); o.Label = name; o.Shape = sh
    root.addObject(o)
    if App.GuiUp:                              # the scene takes its colours from the view
        try:
            if col and len(col) == len(sh.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
doc.recompute()
r = S.robot(doc, root, BB + "/mech/freecad/sim_base", "Base")
s = S.finish(r)
App.closeDocument("BugBot_BaseSim")
App.setActiveDocument("BugBot_Base")
result = {"export": s}
