# 3D model for the WS2812B-4020(-V6) side-view LED (KiCad 10's library has none; land pattern from JLC/EasyEDA): body 4.0 x 1.66 x 1.7 mm
# (footprint y -0.3 .. 1.36), the light out of the -y face (clear lens strip there), 4 tin pads in a row. Model frame = footprint frame
# (KiCad y down -> model y up).    "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_ws2812b_4020.py
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib/3dmodels"
body = Part.makeBox(4.0, 1.66, 1.7, V(-2.0, -1.36, 0.0))                  # model y -1.36 .. 0.3 (= footprint y 1.36 .. -0.3)
lens = Part.makeBox(2.8, 0.06, 1.1, V(-1.4, 0.3, 0.3))                    # on the emitting face (footprint -y = model +y)
pads = [Part.makeBox(w, 1.3, 0.06, V(x - w / 2, -0.65, -0.01)) for x, w in ((-1.68, 0.9), (-0.43, 0.7), (0.60, 0.45), (1.68, 0.9))]
Part.makeCompound([body, lens] + pads).exportStep(f"{D}/LED_WS2812B-4020_SideView.step")
print("ok")
