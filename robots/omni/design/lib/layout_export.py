# Board layout in the ROBOT frame for 2D planning drawings (KiCad python): footprints (courtyard box, side, pads with nets),
# tracks (layer, net, width) and vias, mm, robot frame (x = kicad_x - 100, y = 100 - kicad_y, so y points to the back).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/layout_export.py [board] [out.json]
import json, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
OUT = sys.argv[2] if len(sys.argv) > 2 else BB + "/design/schematics/Main/_work/layout_robot.json"
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
R = lambda v: [round(tm(v.x) - 100, 3), round(100 - tm(v.y), 3)]
fps = []
for f in b.GetFootprints():
    c = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd); bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    pads = []
    for p in f.Pads():
        poly = p.GetEffectivePolygon(pcbnew.ERROR_INSIDE)
        pads.append({"n": p.GetNumber(), "net": p.GetNetname(), "c": R(p.GetPosition()),
                     "poly": [[R(poly.Outline(i).CPoint(j)) for j in range(poly.Outline(i).PointCount())] for i in range(poly.OutlineCount())],
                     "tht": p.GetDrillSize().x > 0})
    fps.append({"ref": f.GetReference(), "val": f.GetValue(), "side": "B" if f.IsFlipped() else "F", "c": R(f.GetPosition()),
                "box": [round(tm(bb.GetLeft()) - 100, 2), round(100 - tm(bb.GetBottom()), 2), round(tm(bb.GetRight()) - 100, 2), round(100 - tm(bb.GetTop()), 2)], "pads": pads})
trk = [{"l": b.GetLayerName(t.GetLayer()), "net": t.GetNetname(), "a": R(t.GetStart()), "b": R(t.GetEnd()), "w": tm(t.GetWidth())}
       for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = [{"net": v.GetNetname(), "c": R(v.GetPosition()), "d": tm(v.GetWidth(pcbnew.F_Cu))} for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
json.dump({"fps": fps, "tracks": trk, "vias": vias}, open(OUT, "w"))
print("layout_export:", len(fps), "footprints,", len(trk), "tracks,", len(vias), "vias")
