# Remove the track / via pieces in a board's DRC shorts and clearance errors (KiCad python), any board: the piece of each
# pair that is a track or via (if both are, the one NOT in the keep set), and write the nets touched to a JSON list for
# the router. Used after parts move onto old routing (battery-path rework, 2026-10-26).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/clash_rip_any.py board drc.json out_nets.json [keep_net ...]
import json, sys, pcbnew
B, DRC, OUT = sys.argv[1:4]; KEEP = set(sys.argv[4:])
d = json.load(open(DRC))
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
net_of = lambda it: it["description"].split("[", 1)[1].split("]", 1)[0] if "[" in it["description"] else ""
is_cu = lambda it: it["description"].startswith(("Track", "Via"))
targets = []
for v in d.get("violations", []):
    if v["type"] not in ("shorting_items", "clearance", "tracks_crossing", "hole_clearance"): continue
    items = v["items"]; cu = [it for it in items if is_cu(it)]
    if not cu: continue
    pick = [it for it in cu if net_of(it) not in KEEP] or cu
    targets.append(pick[0])
uuids = {t["uuid"] for t in targets}
kill = [t for t in b.GetTracks() if t.m_Uuid.AsString() in uuids]
nets = sorted({t.GetNetname() for t in kill})
for t in kill: b.Remove(t)
pcbnew.SaveBoard(B, b)
json.dump(nets, open(OUT, "w"))
print(f"clash_rip_any: {len(kill)} pieces removed; nets {nets}")
