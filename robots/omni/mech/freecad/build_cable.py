# BugBot in FreeCAD: the LED ring's 3-wire lead (JST-SH pre-crimped, 30 AWG), parametric from the Params sheet.
# From the 3 solder holes in the middle of the LED board (wires come up through them from below), down through the
# deck's 6.5 wire hole, over the servo, down into J4 (JST-SH 3-pin vertical) on the main board.
import os, math
import Part
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad"
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
zdeck, zpcb = num("mast_top"), num("pcb_top")
J4 = (-5.3, 14.0)                      # design/lib/add_j4.py (robot frame)
J4_TOP = zpcb + 4.35                   # BM03B-SRSS-TB: 4.31 above the board in KiCad's model
PLUG_Y = J4[1] - 0.3                   # the plug's wire entry, over the pins
pts = [V(0, -1.2, zdeck + num("deck_t") - 0.2),   # under the board, at the middle solder hole
       V(0, -1.2, zdeck - 1.5),                    # out of the deck's wire hole
       V(-0.6, 1.5, zdeck - 6.0),
       V(-3.0, 8.0, zdeck - 12.0),                 # over the servo
       V(J4[0], PLUG_Y - 0.5, J4_TOP + 7.0),
       V(J4[0], PLUG_Y, J4_TOP + 2.5)]
bs = Part.BSplineCurve(); bs.interpolate(pts)
spine = Part.Wire([bs.toShape()])
t0 = bs.tangent(bs.FirstParameter)[0]
prof = Part.Wire([Part.makeCircle(0.8, pts[0], t0)])          # 3 x 30 AWG side by side: about a 1.6 bundle
lead = spine.makePipeShell([prof], True, True)
plug = Part.makeBox(4.0, 3.0, 2.6, V(J4[0] - 2.0, PLUG_Y - 1.5, J4_TOP))   # the JST-SH plug on J4 (the part inside the receptacle is not modelled)
cable = lead.fuse(plug).removeSplitter() if lead.isValid() else Part.makeCompound([lead, plug])
old = doc.getObject("LEDCable")
if old:
    for p in list(old.InList):
        if hasattr(p, "removeObject"): p.removeObject(old)
    doc.removeObject("LEDCable")
o = doc.addObject("Part::Feature", "LEDCable"); o.Label = "LEDCable"; o.Shape = cable
if App.GuiUp:
    o.ViewObject.ShapeColor = (0.12, 0.12, 0.13)
doc.recompute()
result = {"length_mm": round(spine.Length, 1), "valid": cable.isValid(), "solids": len(cable.Solids)}
