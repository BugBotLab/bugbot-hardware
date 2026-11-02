# Finishing the main board's routing 3/3 (KiCad python): adds route_fill.py's tracks and vias (_route/fill.json) to the
# board, refills the zones (In2's VSYS pour flows round the new In2 tracks) and saves.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_fill_apply.py
import json, shutil, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[3] if len(sys.argv) > 3 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"   # (argv 2: "replace" or "add")
SRC = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/_route/fill.json"   # or a route_stage.py stage file
fill = json.load(open(SRC))
shutil.copy(B, B + ".before-" + SRC.replace("\\", "/").split("/")[-1].split(".")[0])
b = pcbnew.LoadBoard(B)
if len(sys.argv) > 2 and sys.argv[2] == "replace":     # the file holds the whole routing: clear the old first
    for t in list(b.GetTracks()): b.Remove(t)
L = {"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "I3": pcbnew.In3_Cu, "B": pcbnew.B_Cu}
mm = pcbnew.FromMM
for t in fill["tracks"]:
    tr = pcbnew.PCB_TRACK(b); tr.SetLayer(L[t["l"]]); tr.SetWidth(mm(t["w"])); tr.SetNet(b.FindNet(t["net"]))
    tr.SetStart(pcbnew.VECTOR2I(mm(t["x0"]), mm(t["y0"]))); tr.SetEnd(pcbnew.VECTOR2I(mm(t["x1"]), mm(t["y1"]))); b.Add(tr)
for v in fill["vias"]:
    vi = pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(mm(v["x"]), mm(v["y"]))); vi.SetWidth(mm(v["d"]))
    vi.SetDrill(mm(v["drill"])); vi.SetNet(b.FindNet(v["net"])); b.Add(vi)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print("added", len(fill["tracks"]), "tracks,", len(fill["vias"]), "vias")
