# Routing plan v2: replaces In4's VSYS island zones with _route/vsys_islands.json (plan_v2.py), e.g. after re-placing.
#   C:/Python312/python.exe design/lib/plan_v2.py && "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/update_islands.py
import json, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/schematics/Main/"
B = sys.argv[1] if len(sys.argv) > 1 else D + "BugBot_Main.kicad_pcb"     # or a working copy
mm = pcbnew.FromMM
b = pcbnew.LoadBoard(B)
old = [z for z in b.Zones() if z.GetZoneName().startswith("VSYS In4.Cu")]
for z in old: b.Remove(z)                    # (after a Remove KiCad 10's python returns bare SWIG objects: add only, then save)
for k, poly in enumerate(json.load(open(D + "_route/vsys_islands.json"))):
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.In4_Cu); z.SetNet(b.FindNet("/VSYS"))
    ol = z.Outline(); ol.NewOutline()
    for x, y in poly: ol.Append(pcbnew.VECTOR2I(mm(100 + x), mm(100 - y)))
    z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetAssignedPriority(1)
    z.SetZoneName(f"VSYS In4.Cu island {k + 1}"); b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print(f"In4 VSYS islands: {len(old)} removed, {k + 1} added")
