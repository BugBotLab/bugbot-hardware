# 3D model for the WS2812B-2020(-V6) (KiCad 10's library has none): 2.2 x 2.0 x 0.84 mm white body (V6 datasheet; 2.2 along the pad rows), a round clear lens on top,
# 4 tin pads underneath at the footprint's pad positions. Model frame = footprint frame (KiCad y down -> model y up).
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_ws2812b_2020.py
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib/3dmodels"
body = Part.makeBox(2.2, 2.0, 0.84, V(-1.1, -1.0, 0.0))
lens = Part.makeCylinder(0.72, 0.06, V(0, 0, 0.84))
body = body.cut(Part.makeCylinder(0.72, 0.3, V(0, 0, 0.6)))
lens = Part.makeCylinder(0.72, 0.24, V(0, 0, 0.6))
pads = [Part.makeBox(0.45, 0.45, 0.06, V(x - 0.225, y - 0.225, -0.01)) for x, y in ((-0.915, 0.55), (-0.915, -0.55), (0.915, -0.55), (0.915, 0.55))]
corner = Part.makeBox(0.3, 0.3, 0.02, V(-1.1, 0.7, 0.84))           # pin-1 mark
Part.makeCompound([body, lens, corner] + pads).exportStep(f"{D}/LED_WS2812B-2020_PLCC4_2.0x2.0mm.step")
print("ok")
