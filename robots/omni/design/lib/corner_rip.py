# Power switch v3 re-place, step 2 (KiCad python): rips the copper of the re-placed power corner.
#  - nets whose pads are all on moved parts (local nets): all their tracks and vias
#  - nets that also run elsewhere (3V3, 5V, VBUS, GND, VSYS ...): only the pieces in the corner (an end within 1.5 mm of
#    a moved part's old or new outline)
# Writes _route/corner_nets.json (local / global nets, moved parts) for corner_route.py.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/corner_rip.py
import json, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
D = BB + "/design/schematics/Main/"
new = json.load(open(D + "_place/placement_sw1.json"))["placement"]
cur = json.load(open(D + "_place/placement_v2.json"))
moved = sorted(r for r, v in new.items() if r in cur and (abs(cur[r][0] - v[0]) > 0.01 or abs(cur[r][1] - v[1]) > 0.01 or cur[r][2] != v[2] or cur[r][3] != v[3]))
moved.append("SW1")
import os
if os.path.exists(D + "_place/legalize.json"):           # parts nudged afterwards (legalize_corner.py) count too
    moved += [r for r in json.load(open(D + "_place/legalize.json")) if r not in moved]
mm = pcbnew.FromMM
b = pcbnew.LoadBoard(B)
boxes = []
for r in moved:
    f = b.FindFootprintByReference(r)
    bb = f.GetBoundingBox(False); bb.Inflate(mm(1.5)); boxes.append(bb)
    if r in cur:                                          # its old spot too
        x, y = cur[r][0], cur[r][1]
        ob = pcbnew.BOX2I(pcbnew.VECTOR2I(mm(100 + x - 3), mm(100 - y - 3)), pcbnew.VECTOR2L(mm(6), mm(6))); boxes.append(ob)
nets = {}
for f in b.GetFootprints():
    for p in f.Pads():
        n = p.GetNetname()
        if n and not n.startswith("unconnected"): nets.setdefault(n, set()).add(f.GetReference())
touched = {n for n, refs in nets.items() if refs & set(moved)}
local = sorted(n for n in touched if nets[n] <= set(moved))
glob = sorted(touched - set(local))
inside = lambda q: any(bx.Contains(q) for bx in boxes)
kill = {}
for t in b.GetTracks():
    n = t.GetNetname()
    if n in local: kill[t.m_Uuid.AsString()] = t; continue
    if n in glob:
        pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        if any(inside(q) for q in pts): kill[t.m_Uuid.AsString()] = t
for t in kill.values(): b.Remove(t)
pcbnew.SaveBoard(B, b)
json.dump({"moved": moved, "local": local, "global": glob}, open(D + "_route/corner_nets.json", "w"), indent=1)
print(f"moved parts {len(moved)}; local nets {len(local)}: {local}\nglobal nets {len(glob)}: {glob}\nremoved {len(kill)} tracks / vias")
