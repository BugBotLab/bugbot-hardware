# Put the rear ID tag bar on the OPEN master, without a full rebuild (tag_mounts.py): removes the old tag plate's chassis
# and deck features and the TagPlate object, cuts the ring grooves in the rear deck posts, makes the TagBar (in SensorMast).
# Does NOT save the document. Then run build_fasteners.py (drops the old plate's 2 screws).
#   python fusionflow/ffclient.py run mech/freecad/add_tag_bar.py
import sys, importlib
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
sys.path.insert(0, BB + "/mech/freecad")
import tag_mounts; importlib.reload(tag_mounts)
doc = App.getDocument("BugBot_Base")
removed = {"chassis": tag_mounts.chassis_features(doc, doc.getObject("Chassis")),
           "deck": tag_mounts.deck_features(doc, doc.getObject("TopDeck"))}
tag_mounts.standoff_grooves(doc, doc.getObject("DeckStandoffs"))
tb = tag_mounts.tag_bar(doc)
doc.recompute()
so = doc.getObject("DeckStandoffs")
result = {"removed_features": removed, "tagplate_left": bool(doc.getObject("TagPlate")),
          "grooves": [o.Label for o in so.Group if o.Label.startswith("Tag")], "standoffs_valid": so.Shape.isValid(),
          "chassis_valid": doc.getObject("Chassis").Shape.isValid(), "deck_valid": doc.getObject("TopDeck").Shape.isValid(),
          "bar": {"valid": tb.Shape.isValid(), "solids": len(tb.Shape.Solids), "volume": round(tb.Shape.Volume, 1),
                  "bb": [round(v, 2) for v in (tb.Shape.BoundBox.XMin, tb.Shape.BoundBox.XMax, tb.Shape.BoundBox.YMin, tb.Shape.BoundBox.YMax,
                                               tb.Shape.BoundBox.ZMin, tb.Shape.BoundBox.ZMax)]},
          "in_SensorMast": tb in doc.getObject("SensorMast").Group}
