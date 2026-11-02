# KiCad python: dumps every footprint's courtyards (robot frame, mm), pads (with drills) and the MCAD rule areas to
# _place/board_geom.json, for placement checks / legalising in plain Python (shapely).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/export_geom.py [board]
import sys, json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
tm = pcbnew.ToMM
R = lambda p: (round(tm(p.x) - 100, 4), round(100 - tm(p.y), 4))
def polys(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i); out.append([R(o.CPoint(j)) for j in range(o.PointCount())])
    return out
b = pcbnew.LoadBoard(B)
fps = []
for f in b.GetFootprints():
    pads = []
    for p in f.Pads():
        sz = p.GetSize(pcbnew.F_Cu); d = p.GetDrillSize()
        pads.append({"n": p.GetNumber(), "net": p.GetNetname(), "pos": R(p.GetPosition()), "size": (tm(sz.x), tm(sz.y)),
                     "drill": (tm(d.x), tm(d.y)), "rot": p.GetOrientationDegrees(), "tht": p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH),
                     "poly": polys(p.GetEffectivePolygon(pcbnew.B_Cu if f.IsFlipped() else pcbnew.F_Cu, pcbnew.ERROR_INSIDE))})
    fps.append({"ref": f.GetReference(), "side": "B" if f.IsFlipped() else "F", "pos": R(f.GetPosition()), "rot": f.GetOrientationDegrees(),
                "crtF": polys(f.GetCourtyard(pcbnew.F_CrtYd)), "crtB": polys(f.GetCourtyard(pcbnew.B_CrtYd)), "pads": pads})
rules = []
for z in b.Zones():
    if z.GetIsRuleArea():
        rules.append({"name": z.GetZoneName(), "layers": [b.GetLayerName(l) for l in z.GetLayerSet().Seq()], "poly": polys(z.Outline())})
json.dump({"fps": fps, "rules": rules}, open(B.rsplit("/", 1)[0] + "/_place/board_geom.json", "w"))
print(len(fps), "footprints,", len(rules), "rule areas")
