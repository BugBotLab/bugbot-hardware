# Placement helper 1/3 (KiCad python): every footprint's courtyard (or body outline if it has none) for each side and
# rotation, relative to its position, in the robot frame (x right = front, y up). Writes schematics/Main/_place/shapes.json.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_extract.py
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
board = pcbnew.LoadBoard(B)
out = {}
for f in board.GetFootprints():
    ref = f.GetReference()
    if ref.startswith("H"): continue
    pos0, rot0, flip0 = f.GetPosition(), f.GetOrientationDegrees(), f.IsFlipped()
    ent = {"fp": f.GetFPIDAsString(), "tht": any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in f.Pads()),
           "placed": [pcbnew.ToMM(pos0.x) - 100, 100 - pcbnew.ToMM(pos0.y), rot0, "B" if flip0 else "F"], "v": {}}
    f.SetPosition(pcbnew.VECTOR2I(0, 0))
    for side in ("F", "B"):
        if f.IsFlipped() != (side == "B"):
            f.Flip(f.GetPosition(), False)
        for rot in (0, 90, 180, 270):
            f.SetOrientationDegrees(rot)
            cy = f.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
            if cy.OutlineCount():
                c = cy.COutline(0); pts = [(pcbnew.ToMM(c.CPoint(j).x), -pcbnew.ToMM(c.CPoint(j).y)) for j in range(c.PointCount())]
            else:
                bb = f.GetBoundingBox(False)
                x0, x1, y0, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom()))
                pts = [(x0, -y0), (x1, -y0), (x1, -y1), (x0, -y1)]
            ent["v"][f"{side}{rot}"] = pts
    if f.IsFlipped() != flip0:
        f.Flip(f.GetPosition(), False)
    f.SetOrientationDegrees(rot0); f.SetPosition(pos0)
    out[ref] = ent
json.dump(out, open(BB + "/design/schematics/Main/_place/shapes.json", "w"))
print(len(out), "footprints")
