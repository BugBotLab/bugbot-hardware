# BugBot "Ant" variant: the ball carrier. The BugBot's gripper, no kicker (its solenoid, bracket, capacitor charge and
# screws are left out). No new parts.
# Builds a SEPARATE document BugBot_Ant (saved as mech/freecad/BugBot_Ant.FCStd): the shared base robot (variants.py)
# + the BugBot's gripper (Gripper:1) + the ball. The BugBot document is read only.
#   python fusionflow/ffclient.py run mech/freecad/build_ant.py
# Check: with the kick disc gone nothing stops the held ball from behind except the base itself; the result reports how far
# it can roll back before it touches something.
import sys, importlib, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Ant.FCStd"
src = App.getDocument("BugBot_Base")
sys.path.insert(0, BB + "/mech/freecad")
import variants; importlib.reload(variants)
keep = variants.base_parts(src)                        # base (servo mount, arm, kicker, ball: modules)
keep += variants.module_leaves(src, "GripperMount")    # the servo mount module (SG90, servo block, pivot bracket + screws)
arm = [(n, s, c, sc) for n, (s, c, sc) in variants.parts_of(src, "Gripper:1").items()]
ball = [(n, s, c, sc) for n, (s, c, sc) in variants.parts_of(src, "Ball:1").items()]
# ---------------- check: the ball's free roll backwards (gripper down) ----------------
# Conservative advancement: move the ball back by its current gap to the nearest part (it can't hit anything sooner), so a
# handful of distance checks find the contact (0.1 mm steps took 701 checks, ~53 s). Only parts in the ball's path count;
# the whole check is cached while those shapes are unchanged (variants.cached).
import math
bsh = Part.makeCompound([s for _, s, _, _ in ball])
lane = bsh.BoundBox; lane.enlarge(0.5); lane.XMin -= 25                 # the ball's sweep, 25 mm back
others = [(n, s) for n, s, _, _ in keep + arm if s.BoundBox.intersect(lane)]
start = {n: round(variants.distance(bsh, s), 2) for n, s in others}


def roll():
    cand = [(n, s) for n, s in others if start[n] >= 0.05]   # (touching at rest: the gripper sleeve, the floor: not obstacles)
    t = 0.0
    while t < 25.0:
        b = bsh.copy(); b.translate(V(-t, 0, 0))
        dn, n = min((b.distToShape(s)[0], n) for n, s in cand)
        if dn < 0.01:
            return [round(math.ceil(t / 0.1 - 1e-6) * 0.1, 1), n]   # (reported on the old 0.1 mm grid)
        t += max(dn, 0.05)
    return [None, None]


back, hit = variants.cached("antroll", [bsh] + [s for _, s in others], roll)
touching = sorted(n for n, d in start.items() if d < 0.05)
# ---------------- document ----------------
if "BugBot_Ant" in App.listDocuments(): App.closeDocument("BugBot_Ant")
d = App.newDocument("BugBot_Ant")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot (static copy of BugBot; kicker removed)"
g_arm = d.addObject("App::DocumentObjectGroup", "Gripper"); g_arm.Label = "Gripper (as BugBot) + ball"
root = d.addObject("App::DocumentObjectGroup", "Ant"); root.Label = "Ant"; root.addObject(g_base); root.addObject(g_arm)   # render root
objs = []
for grp, rows, pre in ((g_base, keep, "B_"), (g_arm, arm + ball, "A_")):
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
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read()); recolour(d, "Ant")   # this style's printed colour
d.saveAs(OUTF)
variants.save_checks()
App.setActiveDocument("BugBot_Base")
result = {"ball_touching_at_rest": touching, "ball_free_roll_back_mm": back, "first_hit": hit,
          "parts": {"base": len(keep), "gripper": len(arm), "ball": len(ball)}, "file": OUTF}
