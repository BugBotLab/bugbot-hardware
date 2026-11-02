# KiCad python: removes the tracks / vias in the last DRC's shorts and clearance errors (_route/drc_final.json), the
# foreign side first (a net not re-routed with the corner), and lists their nets in _route/clash_nets.json so
# clash_route.py can join them back.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/clash_rip.py
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/schematics/Main/"
B = D + "BugBot_Main.kicad_pcb"
drc = json.load(open(D + "_route/drc_final.json"))
cn = json.load(open(D + "_route/corner_nets.json")); mine = set(cn["local"]) | set(cn["global"])
net = lambda it: it["description"].split("[", 1)[1].split("]", 1)[0] if "[" in it["description"] else ""
is_cu = lambda it: it["description"].startswith(("Track", "Via"))
kill, nets = set(), set()
for v in drc["violations"]:
    if v["type"] not in ("shorting_items", "clearance", "hole_clearance"): continue
    cu = [it for it in v["items"] if is_cu(it)]
    if len(cu) == 2: cu = [it for it in cu if net(it) not in mine] or cu
    for it in cu: kill.add(it["uuid"]); nets.add(net(it))
b = pcbnew.LoadBoard(B)
gone = [t for t in b.GetTracks() if t.m_Uuid.AsString() in kill]
for t in gone: b.Remove(t)
pcbnew.SaveBoard(B, b)
json.dump(sorted(nets), open(D + "_route/clash_nets.json", "w"))
print(f"removed {len(gone)} tracks / vias of {sorted(nets)}")
