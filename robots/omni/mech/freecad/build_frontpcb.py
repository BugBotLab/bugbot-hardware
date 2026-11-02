# BugBot in FreeCAD: the front sensor board's mechanical definition (outline + 2 M2 holes), parametric, hidden.
# It is the outline source of the KiCad front board (FrontSensorBoard), which stands vertically behind the mast.
import os
from fusionflow import params as P, helpers as H, ecad
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad"
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
new_body("FrontPCB", (0.08, 0.3, 0.55))
s = sk("FrontPCBSketch", "YZ", "fsb_x")
# outline with an ear on the +Y side beside the camera (FPC socket + flex slot), the flex slot above the camera, one M2 hole
YL, ZT = "fsb_y0 + fsb_w", "fsb_z0 + fsb_h"
poly2d(s, "fpcb", [("fsb_x", "fsb_y0", "fsb_z0"), ("fsb_x", YL, "fsb_z0"), ("fsb_x", YL, "fsb_ear_z0"), ("fsb_x", "fsb_ear_y", "fsb_ear_z0"),
                   ("fsb_x", "fsb_ear_y", "fsb_ear_z1"), ("fsb_x", YL, "fsb_ear_z1"), ("fsb_x", YL, ZT), ("fsb_x", "fsb_y0", ZT)])
box2d(s, "fslot", ("fsb_x", "-fsb_slot_w / 2", "fsb_slot_z0"), ("fsb_t", "fsb_slot_w", "fsb_slot_h"))
circle2d(s, "fh1", ("0", "fsb_y0 + 2 mm", "fsb_z0 + fsb_h - 2 mm"), "2.2 mm")
ext(s, "add", "fsb_t", +1, "Board")
body.ViewObject.Visibility = False
doc.recompute()
FRAME = E("placement(vector(fsb_x; 0 mm; 0 mm); rotation(vector(1; 1; 1); 120))")   # board (x, y, z) -> robot (fsb_x + z, x, y)
pl = doc.Params.evalExpression(FRAME)
mcad = ecad.mcad_from_sketch(s, num("fsb_t"), pl)
import json; json.dump(mcad, open(BB + "/design/schematics/Front/mcad.json", "w"))
result = {"outline": mcad["outline"], "holes": mcad["holes"], "frame": str(pl)}
