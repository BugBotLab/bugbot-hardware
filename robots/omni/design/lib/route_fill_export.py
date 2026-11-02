# Finishing the main board's routing 1/3 (KiCad python): exports the copper as obstacles for route_fill.py, in KiCad mm
# (x, y as on the board). Layers used for the finishing tracks: F.Cu, In2.Cu (mixed: the VSYS pour fills round them), B.Cu.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_fill_export.py
import json, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B)
mm = pcbnew.ToMM
LAY = {pcbnew.F_Cu: "F", pcbnew.In2_Cu: "I2", pcbnew.In3_Cu: "I3", pcbnew.B_Cu: "B"}   # plan v2: 4 routing layers
out = {"tracks": [], "vias": [], "pads": [], "holes": [], "edge": []}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        out["vias"].append({"net": t.GetNetname(), "x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y), "d": mm(t.GetWidth(pcbnew.F_Cu)),
                             "drill": mm(t.GetDrillValue())})
    elif t.GetLayer() in LAY:
        out["tracks"].append({"net": t.GetNetname(), "l": LAY[t.GetLayer()], "x0": mm(t.GetStart().x), "y0": mm(t.GetStart().y),
                              "x1": mm(t.GetEnd().x), "y1": mm(t.GetEnd().y), "w": mm(t.GetWidth())})
for f in b.GetFootprints():
    for p in f.Pads():
        layers = [LAY[l] for l in LAY if p.IsOnLayer(l)]
        poly = p.GetEffectivePolygon(pcbnew.ERROR_INSIDE)
        pts = []
        if poly.OutlineCount():
            c = poly.COutline(0); pts = [(mm(c.CPoint(j).x), mm(c.CPoint(j).y)) for j in range(c.PointCount())]
        ent = {"ref": f.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(), "layers": layers, "poly": pts,
               "x": mm(p.GetPosition().x), "y": mm(p.GetPosition().y)}
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) and p.GetDrillSize().x > 0:
            out["holes"].append({"x": ent["x"], "y": ent["y"], "d": mm(p.GetDrillSize().x),
                                 "pth": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH})
        if layers: out["pads"].append(ent)
for d in b.GetDrawings():
    if b.GetLayerName(d.GetLayer()) == "Edge.Cuts":
        out["edge"].append({"cx": mm(d.GetCenter().x), "cy": mm(d.GetCenter().y), "r": mm(d.GetRadius())})
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else BB + "/design/schematics/Main/_route/copper.json", "w"))
print({k: len(v) for k, v in out.items()})
