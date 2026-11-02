# Merge collinear track pieces (KiCad python): two pieces of one net, layer and width meeting in a straight line at a point
# with nothing else there (no third piece, pad or via) become one piece. One round per run (KiCad python hands back
# removed tracks): run it again until it merges 0. USB pair and locked pieces skipped.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/merge_collinear.py [board]
import collections, math, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B)
key = lambda p: (p.x, p.y)
vias = {(v.GetNetname(), key(v.GetPosition())) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"}
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)
merged = 0
for _ in range(1):
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() not in ("/USB_DP", "/USB_DN")]
    ends = collections.defaultdict(list)
    for t in tracks:
        for q in (t.GetStart(), t.GetEnd()): ends[(t.GetNetname(), t.GetLayer(), key(q))].append(t)
    done, used = 0, set()
    for (net, lay, pt), ts in ends.items():
        if len(ts) != 2 or (net, pt) in vias: continue
        a, c = ts
        if a.GetWidth() != c.GetWidth() or id(a) in used or id(c) in used or a.IsLocked() or c.IsLocked(): continue
        v = pcbnew.VECTOR2I(*pt)
        if any(p.IsOnLayer(lay) and p.HitTest(v) for p in padsby[net]): continue
        fa = a.GetEnd() if key(a.GetStart()) == pt else a.GetStart()
        fc = c.GetEnd() if key(c.GetStart()) == pt else c.GetStart()
        ax, ay, cx, cy = fa.x - pt[0], fa.y - pt[1], fc.x - pt[0], fc.y - pt[1]
        cross = ax * cy - ay * cx; dot = ax * cx + ay * cy
        if dot >= 0 or abs(cross) > 1e-3 * math.hypot(ax, ay) * math.hypot(cx, cy): continue   # straight on (< 0.06 deg)
        a.SetStart(fa); a.SetEnd(fc); used |= {id(a), id(c)}
        b.Remove(c); done += 1
    merged += done
    if not done: break
pcbnew.SaveBoard(B, b)
print(f"merge_collinear: {merged} joints merged")
