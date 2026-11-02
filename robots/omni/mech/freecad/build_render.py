# Scorpion in Blender (FusionFlow render link): the material of every part, the views and the look. Run after build_scorpion.py
# (the Scorpion is a static document rebuilt from the base: rerun this after a rebuild).
#   python fusionflow/ffclient.py run mech/freecad/build_render.py
# FreeCAD sets the colours (apply_colours.py); this says what each part is made of. Then: RENDER > Render / Open in Blender.
import importlib
from fusionflow import render
importlib.reload(render)

doc = App.getDocument("BugBot_Scorpion")
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad/render"
for o in render.scenes(doc):                  # rebuildable
    doc.removeObject(o.Name)
rs = render.make(doc, doc.getObject("Scorpion"), OUT, "RenderScene")
rs.Materials = {
    r"Roller|KickDisc": "tpu",                                  # black TPU
    r"/HoopSleeve$": "pla",
    r"\(KiCad\)": "pcb",                                        # green mask, gold pads, black ICs, white silk
    r"/LEDCable$": "plastic_matte",                             # the LED ring's 3-wire lead
    r"/Dome$": "frosted",                                       # clear PLA, printed: frosted over the LED ring
    r"^Ball": "ball",                                           # orange ping-pong ball
    r"/FrontBar$|BrassLiner|PivotTube|PivotBushing": "brass",
    r"Fasteners|Screws|BarScrew|BarNut|WheelPin|M3ThinNut|/Solenoid$|SolenoidPlunger|SolenoidSpring": "steel",
    r"/Gearmotor$": "aluminium",
    r"/SolenoidCoil$": "plastic_gloss",                         # the coil's tape
    r"/Servo$|ServoHorn": "plastic_matte",
    r"/Antenna$": "brass",
}
rs.DefaultMaterial = "pla"                                      # every other part: printed PLA, in the style colour
rs.Emitters = {r"/Dome$": "1,0.97,0.92,1.2"}                    # the LED ring on (warm white): the dome glows
rs.Views = ["hero 62 24 1.0", "front 90 10 1.05", "side 0 14 1.0", "top 90 82 1.0", "rear 235 28 0.82"]   # front is +X
rs.LayerHeight = 0.2
rs.Width, rs.Height, rs.Samples = 1600, 1200, 160
rs.AutoSync = False
doc.recompute()
result = render.export(rs)
