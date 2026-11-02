# Via joins report (KiCad python): track ends near a via but not on its centre, tracks wider than the via they end on,
# vias of one net closer than 1 mm (doubles), and tracks of one net overlapping end-to-end at a via (duplicates).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/via_quality.py [board]
import collections, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); tm, mm = pcbnew.ToMM, pcbnew.FromMM
vias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
off, wide, dup = [], [], []
ends = collections.defaultdict(set)                    # (net, layer) -> track ends, to see if an end links on to the centre
segs = collections.defaultdict(set)
for t in tracks:
    a, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    segs[(t.GetNetname(), t.GetLayer())] |= {(a, e), (e, a)}
for v in vias:
    c, r = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2
    for t in tracks:
        if t.GetNetname() != v.GetNetname(): continue
        for q in (t.GetStart(), t.GetEnd()):
            d = (q - c).EuclideanNorm()
            if d <= r:
                ck = (c.x, c.y); qk = (q.x, q.y)
                if d > mm(0.01) and (qk, ck) not in segs[(t.GetNetname(), t.GetLayer())]: off.append((v.GetNetname(), round(tm(c.x), 2), round(tm(c.y), 2), round(tm(d), 3)))
                if t.GetWidth() > v.GetWidth(pcbnew.F_Cu) + mm(0.01): wide.append((v.GetNetname(), round(tm(c.x), 2), round(tm(c.y), 2), tm(t.GetWidth())))
close = []
for i, a in enumerate(vias):
    for c in vias[i + 1:]:
        if a.GetNetname() == c.GetNetname() and (a.GetPosition() - c.GetPosition()).EuclideanNorm() < mm(1.0):
            close.append((a.GetNetname(), round(tm(a.GetPosition().x), 2), round(tm(a.GetPosition().y), 2), round(tm((a.GetPosition() - c.GetPosition()).EuclideanNorm()), 2)))
print(f"{len(vias)} vias: {len(off)} track ends off-centre, {len(wide)} track ends wider than the via, {len(close)} same-net via pairs < 1 mm")
for name, L in (("off-centre", off), ("wider", wide), ("close pairs", close)):
    c = collections.Counter(x[0] for x in L); print(f"  {name:12s} {dict(c.most_common(8))}")
