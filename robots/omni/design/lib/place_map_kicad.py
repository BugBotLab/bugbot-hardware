# Placement map 1/2 (KiCad python): the main board's keep-out zones, the MCAD 'max height' outlines and their labels, and
# every footprint's courtyard, in the robot frame (KiCad x = 100 + X, y = 100 - Y) -> schematics/Main/_place/board_map.json.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_map_kicad.py
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
b = pcbnew.LoadBoard(BB + "/design/schematics/Main/BugBot_Main.kicad_pcb")
R = lambda v: (round(pcbnew.ToMM(v.x) - 100, 2), round(100 - pcbnew.ToMM(v.y), 2))
out = {"zones": [], "fps": [], "shapes": [], "texts": []}
for z in b.Zones():
    o = z.Outline()
    polys = [[R(o.COutline(i).CPoint(j)) for j in range(o.COutline(i).PointCount())] for i in range(o.OutlineCount())]
    out["zones"].append({"name": z.GetZoneName(), "rule": z.GetIsRuleArea(), "fp": z.GetDoNotAllowFootprints(),
                         "layers": [b.GetLayerName(l) for l in z.GetLayerSet().Seq()][:4], "polys": polys})
for f in b.GetFootprints():
    cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    pts = [R(cy.COutline(0).CPoint(j)) for j in range(cy.COutline(0).PointCount())] if cy.OutlineCount() else []
    out["fps"].append({"ref": f.GetReference(), "val": f.GetValue(), "side": "B" if f.IsFlipped() else "F",
                       "pos": R(f.GetPosition()), "crt": pts})
for d in b.GetDrawings():
    ln = b.GetLayerName(d.GetLayer())
    if ln != "MCAD": continue
    if d.GetClass() == "PCB_TEXT":
        out["texts"].append((ln, d.GetText()[:80], R(d.GetPosition())))
    elif d.GetClass() == "PCB_SHAPE" and d.GetShape() == pcbnew.SHAPE_T_POLY:
        ps = d.GetPolyShape(); out["shapes"].append((ln, d.GetShape(), [R(ps.COutline(0).CPoint(j)) for j in range(ps.COutline(0).PointCount())]))
json.dump(out, open(BB + "/design/schematics/Main/_place/board_map.json", "w"))
print(len(out["zones"]), "zones,", len(out["shapes"]), "height outlines,", len(out["fps"]), "footprints")
