# Routing plan v2 step 1 (KiCad python): turns the placed, unrouted main board into the 6-layer board.
#   L1 F.Cu signals | L2 In1.Cu GND (solid) | L3 In2.Cu signals | L4 In3.Cu signals | L5 In4.Cu VSYS islands + GND | L6 B.Cu
# Starts from BugBot_Main.kicad_pcb.before-stage1 (placement, no tracks); the stackup itself (JLC06161H-3313) is written
# into the file by set_stackup() afterwards (text, as KiCad's python cannot edit dielectric layers).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_6layer.py
import json, shutil, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/schematics/Main/"
B = D + "BugBot_Main.kicad_pcb"
mm = pcbnew.FromMM
shutil.copy(B + ".before-stage1", B)
b = pcbnew.LoadBoard(B)
bb = b.GetBoardEdgesBoundingBox()          # (before any Remove: after one, KiCad 10's python returns bare SWIG objects)
edge = [pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()), pcbnew.VECTOR2I(bb.GetRight(), bb.GetTop()),
        pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()), pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())]
for t in list(b.GetTracks()): b.Remove(t)
for z in [z for z in b.Zones() if not z.GetIsRuleArea() or z.GetZoneName().startswith("In2 ")]: b.Remove(z)
b.SetCopperLayerCount(6)
b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER); b.SetLayerType(pcbnew.In4_Cu, pcbnew.LT_POWER)
b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_SIGNAL); b.SetLayerType(pcbnew.In3_Cu, pcbnew.LT_SIGNAL)
b.SetLayerName(pcbnew.In1_Cu, "In1.Cu"); b.SetLayerName(pcbnew.In4_Cu, "In4.Cu")


def zone(layer, net, pts, prio, name):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet(net))
    ol = z.Outline(); ol.NewOutline()
    for p in pts: ol.Append(p)
    z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetAssignedPriority(prio)
    z.SetZoneName(name); b.Add(z)


zone(pcbnew.In1_Cu, "/GND", edge, 0, "GND In1.Cu")
zone(pcbnew.In4_Cu, "/GND", edge, 0, "GND In4.Cu")
for k, poly in enumerate(json.load(open(D + "_route/vsys_islands.json"))):      # plan_v2.py
    zone(pcbnew.In4_Cu, "/VSYS", [pcbnew.VECTOR2I(mm(100 + x), mm(100 - y)) for x, y in poly], 1, f"VSYS In4.Cu island {k + 1}")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("6 layers; zones:", [z.GetZoneName() for z in b.Zones()])
