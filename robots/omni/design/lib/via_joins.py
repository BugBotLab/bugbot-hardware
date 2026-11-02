# Clean via joins (KiCad python; user, 2026-10-26 "do via track clean-up too"):
#   1. a track end inside a via but off its centre gets a short piece to the centre (hidden under the via's copper),
#      no wider than the via
#   2. a stitching via (no track ends on it) within 0.8 mm of another via of its net is removed (near-duplicates)
# Locked pieces (frozen hand edits) and the USB pair are left alone.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/via_joins.py [board]
import collections, os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copper_fit import mm
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
SKIP = {"/USB_DP", "/USB_DN"}
b = pcbnew.LoadBoard(B)
vias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
bynet = collections.defaultdict(list)
for t in tracks: bynet[t.GetNetname()].append(t)
centred, joined = 0, collections.Counter()
have = {(t.GetLayer(), (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)) for t in tracks}
have |= {(l, e, a) for l, a, e in have}                  # a piece from the end to the centre already there: skip
for v in vias:
    if v.GetNetname() in SKIP: continue
    c, r, d = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2, v.GetWidth(pcbnew.F_Cu)
    for t in bynet[v.GetNetname()]:
        for q in (t.GetStart(), t.GetEnd()):
            dist = (q - c).EuclideanNorm()
            if dist <= r: joined[id(v)] += 1
            if dist <= r and dist > mm(0.01) and not t.IsLocked() and (t.GetLayer(), (q.x, q.y), (c.x, c.y)) not in have:
                n = pcbnew.PCB_TRACK(b); n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet()); n.SetWidth(min(t.GetWidth(), d))
                n.SetStart(q); n.SetEnd(c); b.Add(n); centred += 1
                have |= {(t.GetLayer(), (q.x, q.y), (c.x, c.y)), (t.GetLayer(), (c.x, c.y), (q.x, q.y))}
removed, gone = 0, set()
for i, a in enumerate(vias):
    if a.GetNetname() in SKIP or joined[id(a)] or id(a) in gone: continue
    for o in vias:
        if o is a or id(o) in gone or o.GetNetname() != a.GetNetname(): continue
        if (o.GetPosition() - a.GetPosition()).EuclideanNorm() < mm(0.8):
            gone.add(id(a)); b.Remove(a); removed += 1
            break
pcbnew.SaveBoard(B, b)
print(f"via_joins: {centred} track ends taken to their via's centre, {removed} near-duplicate stitching vias removed")
