# KiCad python: applies usb_pair2.py's result (_work/usb_pair2.json): removes the ripped track pieces / vias (matched by
# net and end points), adds the pair and the re-joined pieces, refills and saves.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/usb_pair2_apply.py [board]
import json, shutil, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
import os
d = json.load(open(os.environ.get("SRC", BB + "/design/schematics/Main/_work/usb_pair2.json")))   # SRC: another diff file
shutil.copy(B, B + ".before-usb-pair")
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
L = {"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "I3": pcbnew.In3_Cu, "B": pcbnew.B_Cu}
r3 = lambda v: (round(v[0], 3), round(v[1], 3))
kt = {}
for t in d["remove_tracks"]:
    a, c = r3((t["x0"], t["y0"])), r3((t["x1"], t["y1"])); kt[(t["net"], L[t["l"]], min(a, c), max(a, c))] = 1
kv = {(v["net"], r3((v["x"], v["y"]))) for v in d["remove_vias"]}
gone = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        if (t.GetNetname(), r3((tm(t.GetPosition().x), tm(t.GetPosition().y)))) in kv: gone.append(t)
    else:
        a, c = r3((tm(t.GetStart().x), tm(t.GetStart().y))), r3((tm(t.GetEnd().x), tm(t.GetEnd().y)))
        if (t.GetNetname(), t.GetLayer(), min(a, c), max(a, c)) in kt: gone.append(t)
want = len(d["remove_tracks"]) + len(d["remove_vias"])
for t in gone: b.Remove(t)
for t in d["tracks"]:
    tr = pcbnew.PCB_TRACK(b); tr.SetLayer(L[t["l"]]); tr.SetWidth(mm(t["w"])); tr.SetNet(b.FindNet(t["net"]))
    tr.SetStart(pcbnew.VECTOR2I(mm(t["x0"]), mm(t["y0"]))); tr.SetEnd(pcbnew.VECTOR2I(mm(t["x1"]), mm(t["y1"]))); b.Add(tr)
for v in d["vias"]:
    vi = pcbnew.PCB_VIA(b); vi.SetPosition(pcbnew.VECTOR2I(mm(v["x"]), mm(v["y"]))); vi.SetWidth(mm(v["d"]))
    vi.SetDrill(mm(v["drill"])); vi.SetNet(b.FindNet(v["net"])); b.Add(vi)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
print(f"removed {len(gone)} of {want}; added {len(d['tracks'])} tracks, {len(d['vias'])} vias")
