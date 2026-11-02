# BugBot "Wasp" variant: no gripper; the kicker carries a striker ram in place of the kick disc, so it can tap other robots.
# The ram's head is the kick disc itself (same Ø12 x 3, M3 thin nut pocket, still the plunger's return stop) with a Ø10 PETG
# rod in front of it ending in a knob; a TPU 95A cap stretches over the knob (+ CA glue). Retracted, the cap's face is on the
# body outline; fired, it is a stroke (6.4) past it. Everything round, so turning on the plunger thread doesn't matter.
# Builds a SEPARATE document BugBot_Wasp (saved as mech/freecad/BugBot_Wasp.FCStd): the shared base robot (variants.py)
# + the BugBot's kicker without its kick disc + the ram and cap. The base master (BugBot_Base) is read only.
#   python fusionflow/ffclient.py run mech/freecad/build_wasp.py
# Approved 2D: mech/freecad/sketches/wasp_ram.png (draw_wasp_ram.py).
import sys, importlib, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUTF = BB + "/mech/freecad/BugBot_Wasp.FCStd"
src = App.getDocument("BugBot_Base"); P = src.Params
q = lambda n: P.get(n).Value
# ---------------- parameters (robot frame, mm) ----------------
W = dict(
    rod_d=10.0, rod_x1=34.6,                 # PETG rod from the kick disc face to here
    neck_d=7.0, neck_l=1.0,                  # neck behind the knob (the cap's lip sits on it)
    knob_d=10.0, knob_l=2.0, knob_ch=1.0,    # knob; front edge chamfer so the cap's lip rides over it
    cap_d=16.0, cap_lip_d=7.4, cap_face_r=1.5,   # TPU cap: outside, lip hole (0.2 a side round the neck), face edge round
)
X1 = V(1, 0, 0)
y0, z0 = -q("sol_dy"), q("sol_z")                      # plunger axis
x_face = q("sol_tip_x")                                # kick disc front face (retracted)
x_body = q("body_r")                                   # body outline
stroke = q("sol_stroke")
# ---------------- the base robot + the kicker (less its kick disc) ----------------
sys.path.insert(0, BB + "/mech/freecad")
import variants; importlib.reload(variants)
keep = variants.base_parts(src)                        # base (the arm, kicker and ball are modules)
kick = variants.parts_of(src, "Kicker:1")             # the kicker module, its screws included
kd, kd_col, kd_sc = kick.pop("Kicker:1/KickDisc")
for n, (s, c, sc) in kick.items():
    keep.append((n, s, c, sc))
# ---------------- ram + cap ----------------
def cyl(d, x0, x1): return Part.makeCylinder(d / 2, x1 - x0, V(x0, y0, z0), X1)
x_neck = W["rod_x1"]; x_knob = x_neck + W["neck_l"]; x_knob1 = x_knob + W["knob_l"]
knob = cyl(W["knob_d"], x_knob, x_knob1)
e = [ed for ed in knob.Edges if abs(ed.BoundBox.XMin - x_knob1) < 1e-6]
knob = knob.makeChamfer(W["knob_ch"], e)
ram = kd.fuse([cyl(W["rod_d"], x_face, x_neck), cyl(W["neck_d"], x_neck - 0.01, x_knob + 0.01), knob]).removeSplitter()
cap = cyl(W["cap_d"], x_neck, x_body)
e = [ed for ed in cap.Edges if abs(ed.BoundBox.XMin - x_body) < 1e-6]
cap = cap.makeFillet(W["cap_face_r"], e)
cap = cap.cut(cyl(W["cap_lip_d"], x_neck - 1, x_knob + 0.01)).cut(knob).removeSplitter()
new = [("Ram (PETG)", ram, tuple(kick["Kicker:1/KickBracket"][2][:3])),         # BugBot yellow, as the printed parts
("Ram cap (TPU 95A)", cap, tuple(kd_sc[:3]))]
# ---------------- checks: clearances retracted and fired ----------------
own = ("Kicker:1/Solenoid", "Kicker:1/SolenoidPlunger", "Kicker:1/M3ThinNut")   # the ram's own seat (as the kick disc)
clear = {}
for tag, dx in (("retracted", 0.0), ("fired", stroke)):
    rows = []
    for nn, ns, _ in new:
        sh = ns.copy(); sh.translate(V(dx, 0, 0))
        for kn, ks, _, _ in keep:
            kb = ks.BoundBox; kb.enlarge(2.0)
            if kn in own or ks.BoundBox.XMax < 15 or not sh.BoundBox.intersect(kb):   # light: only parts near the ram
                continue
            dmin = variants.distance(sh, ks)          # cached while both shapes are unchanged
            rows.append((round(dmin, 2), nn, kn))
    rows.sort(); clear[tag] = rows[:5]
clashes = [r for t in clear.values() for r in t if r[0] < 0.4]
fit = {"ram_vs_cap_overlap_mm3": round(ram.common(cap).Volume, 3),
       "cap_face_x": round(cap.BoundBox.XMax, 2), "fired_face_x": round(cap.BoundBox.XMax + stroke, 2), "body_r": x_body}
mass = {"ram_g": round(ram.Volume / 1000 * 1.27, 2), "cap_g": round(cap.Volume / 1000 * 1.21, 2), "kick_disc_g": round(kd.Volume / 1000 * 1.21, 2)}
# ---------------- document ----------------
if "BugBot_Wasp" in App.listDocuments(): App.closeDocument("BugBot_Wasp")
d = App.newDocument("BugBot_Wasp")
g_base = d.addObject("App::DocumentObjectGroup", "BaseRobot"); g_base.Label = "Base robot + kicker module, less its kick disc (static copy of BugBot_Base)"
g_new = d.addObject("App::DocumentObjectGroup", "Ram"); g_new.Label = "Striker ram (Wasp)"
root = d.addObject("App::DocumentObjectGroup", "Wasp"); root.Label = "Wasp"; root.addObject(g_base); root.addObject(g_new)   # render root
objs = []
for kn, ks, col, sc in keep:
    o = d.addObject("Part::Feature", "B_" + "".join(ch if ch.isalnum() else "_" for ch in kn)[:48]); o.Label = kn; o.Shape = ks; g_base.addObject(o)
    objs.append((o, col, sc))
for nn, ns, colour in new:
    o = d.addObject("Part::Feature", "W_" + "".join(ch if ch.isalnum() else "_" for ch in nn)[:48]); o.Label = nn; o.Shape = ns; g_new.addObject(o)
    objs.append((o, None, colour))
d.recompute()
if App.GuiUp:
    for o, col, sc in objs:
        try:
            if col and len(col) == len(o.Shape.Faces): o.ViewObject.DiffuseColor = col
            else: o.ViewObject.ShapeColor = tuple(sc[:3])
        except Exception: pass
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read()); recolour(d, "Wasp")   # this style's printed colour
d.saveAs(OUTF)
variants.save_checks()
App.setActiveDocument("BugBot_Base")
result = {"clashes": clashes, "clearances": clear, "fit": fit, "mass": mass,
          "parts": {"kept": len(keep), "new": len(new)}, "valid": [ram.isValid(), cap.isValid()], "file": OUTF}
