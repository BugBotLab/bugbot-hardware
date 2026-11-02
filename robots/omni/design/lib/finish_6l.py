# Routing plan v2, last step (KiCad python): GND pours on the outer layers (tied to In1 / In4 GND through the plane and
# stitching vias), refill every zone, save. Run after route_stage.py 5 has been applied.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/finish_6l.py
import shutil, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
mm = pcbnew.FromMM
shutil.copy(B, B + ".before-pours")
b = pcbnew.LoadBoard(B)
bb = b.GetBoardEdgesBoundingBox()
edge = [pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()), pcbnew.VECTOR2I(bb.GetRight(), bb.GetTop()),
        pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()), pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())]
have = {z.GetZoneName() for z in b.Zones()}
for layer, name in ((pcbnew.F_Cu, "GND F.Cu"), (pcbnew.B_Cu, "GND B.Cu")):
    if name in have: continue
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet("/GND"))
    ol = z.Outline(); ol.NewOutline()
    for p in edge: ol.Append(p)
    # 0.3 mm from other copper (a little more than the 0.15 rule: keeps the pour off the switching nodes' edges),
    # islands smaller than the minimum width dropped by the filler
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetAssignedPriority(0)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName(name); b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("outer GND pours added; zones:", len(list(b.Zones())))
