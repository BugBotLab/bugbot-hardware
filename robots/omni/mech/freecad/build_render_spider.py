# Spider v2 in Blender (FusionFlow render link). Run after build_spider.py (needs its "Spider" root group).
#   python fusionflow/ffclient.py run mech/freecad/build_render_spider.py
import importlib
from fusionflow import render
importlib.reload(render)

doc = App.getDocument("BugBot_Spider")
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/render_spider"
for o in render.scenes(doc):
    doc.removeObject(o.Name)
rs = render.make(doc, doc.getObject("Spider"), OUT, "RenderScene")
rs.Materials = {
    r"Roller|KickDisc|tyre \(TPU\)": "tpu",
    r"\(KiCad\)": "pcb",
    r"/LEDCable$": "plastic_matte",
    r"/Dome$": "frosted",
    r"BrassLiner|PivotTube|PivotBushing": "brass",
    r"Fasteners|Screws|screw|Axle 3 mm|WheelPin|M3ThinNut|/Solenoid$|SolenoidPlunger|SolenoidSpring": "steel",
    r"/Gearmotor$": "aluminium",
    r"/SolenoidCoil$": "plastic_gloss",
    r"/Servo$|ServoHorn": "plastic_matte",
    r"/Antenna$": "brass",
    r"^Tag ": "plastic_matte",                                  # NTAG213 PVC coins
}
rs.DefaultMaterial = "pla"
rs.Emitters = {r"/Dome$": "1,0.97,0.92,1.2"}
rs.Views = ["hero 62 24 1.0", "front 90 10 1.05", "side 0 14 1.0", "low 40 6 0.9"]
rs.LayerHeight = 0.2
rs.Width, rs.Height, rs.Samples = 1600, 1200, 160
rs.AutoSync = False
doc.recompute()
result = render.export(rs)
