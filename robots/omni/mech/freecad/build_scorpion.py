# BugBot "Scorpion" variant: the all-rounder. The base + the servo mount, the gripper, the kicker and the ball (the modules in the master).
# Builds a SEPARATE document BugBot_Scorpion (saved as mech/freecad/BugBot_Scorpion.FCStd): the shared base robot
# (variants.py) + the GripperMount, Gripper, Kicker and Ball modules, as they sit on the robot (gripper at grip_ang). The base master
# (BugBot_Base) is read only.
#   python fusionflow/ffclient.py run mech/freecad/build_scorpion.py
# Until 2026-10-22 the Scorpion was the master itself; the user made the base the master (every style = base + edits).
import sys, importlib, Part
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Scorpion.FCStd"
src = App.getDocument("BugBot_Base")
sys.path.insert(0, BB + "/mech/freecad")
import variants; importlib.reload(variants)
keep = variants.base_parts(src)
mods = {m: variants.module_leaves(src, m) for m in ("GripperMount", "Gripper", "Kicker", "Ball")}
# ---------------- check: the modules against the base (they were one robot: no overlaps expected) ----------------
clash = []
for m, rows in mods.items():
    for n, s, _, _ in rows:
        for kn, ks, _, _ in keep:
            kb = ks.BoundBox; kb.enlarge(0.5)
            if not s.BoundBox.intersect(kb) or not ks.Solids:
                continue
            ov = variants.common_volume(s, ks)      # solid by solid (a whole KiCad compound gives false overlaps); cached while
                                                    # both shapes are unchanged (it was 20 s of every update)
            if ov > 1e-3:
                clash.append((n, kn, round(ov, 3)))
# ---------------- document ----------------
if "BugBot_Scorpion" in App.listDocuments(): App.closeDocument("BugBot_Scorpion")
d = App.newDocument("BugBot_Scorpion")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot (static copy of BugBot_Base)"
root = d.addObject("App::DocumentObjectGroup", "Scorpion"); root.Label = "Scorpion"; root.addObject(g_base)   # render root
groups = {}
for m, lab in (("GripperMount", "Servo mount (module)"), ("Gripper", "Gripper (module)"), ("Kicker", "Kicker (module)"), ("Ball", "Ball (module)")):
    g = d.addObject("App::DocumentObjectGroup", m); g.Label = lab; root.addObject(g); groups[m] = g
objs = []
for grp, rows, pre in [(g_base, keep, "B_")] + [(groups[m], mods[m], "".join(ch for ch in m if ch.isupper()) + "_") for m in mods]:
    for kn, ks, col, sc in rows:
        o = d.addObject("Part::Feature", pre + "".join(ch if ch.isalnum() else "_" for ch in kn)[:48]); o.Label = kn; o.Shape = ks
        grp.addObject(o); objs.append((o, col, sc))
d.recompute()
if App.GuiUp:
    for o, col, sc in objs:
        try:
            if col and len(col) == len(o.Shape.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read()); recolour(d, "Scorpion")   # this style's printed colour
d.saveAs(OUTF)
variants.save_checks()
App.setActiveDocument("BugBot_Base")
result = {"clashes": clash, "parts": {"base": len(keep), **{m: len(r) for m, r in mods.items()}},
          "solids": sum(len(o.Shape.Solids) for o, _, _ in objs), "volume": round(sum(o.Shape.Volume for o, _, _ in objs), 1), "file": OUTF}
