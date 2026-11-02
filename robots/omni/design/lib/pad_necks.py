# Neck down to small pads (KiCad python): a track no wider than the pad it lands on (no fat blobs over small pads; user,
# 2026-10-26). For each track end on a pad whose narrow side n (rounded down to 0.05, min 0.15) is less than the track:
#   run <= 3 mm (a stub, e.g. pad -> plane via): the whole run gets width n
#   longer run: the piece into the pad is split; the part from the pad centre to 0.8 mm outside the pad gets width n,
#               the rest keeps its width (a deliberate neck at the pad, which teardrops.py then tapers)
# Locked pieces (frozen hand edits) and the USB pair are left alone.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/pad_necks.py [board]
import collections, math, os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copper_fit import mm, tm
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
SKIP = {"/USB_DP", "/USB_DN"}
b = pcbnew.LoadBoard(B)
key = lambda p: (p.x, p.y)
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() not in SKIP]
vias = {(v.GetNetname(), key(v.GetPosition())) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"}
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)
ends = collections.defaultdict(list)
for i, t in enumerate(tracks):
    for q in (t.GetStart(), t.GetEnd()): ends[(t.GetNetname(), t.GetLayer(), key(q))].append(i)


def pad_at(net, lay, pt):
    return next((p for p in padsby[net] if p.IsOnLayer(lay) and p.HitTest(pt)), None)


def run_from(i, start):
    out, L, cur, at = [], 0.0, i, start
    while True:
        t = tracks[cur]; out.append(cur); L += tm(t.GetLength())
        far = t.GetEnd() if key(t.GetStart()) == at else t.GetStart()
        k = (t.GetNetname(), t.GetLayer(), key(far))
        nxt = [x for x in ends[k] if x != cur]
        if len(nxt) != 1 or (t.GetNetname(), key(far)) in vias or pad_at(t.GetNetname(), t.GetLayer(), far): return out, L
        cur, at = nxt[0], key(far)


stubs = necks = 0
done = set()
for i, t in enumerate(tracks):
    if i in done or t.IsLocked(): continue
    net, lay = t.GetNetname(), t.GetLayer()
    for q, far in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        p = pad_at(net, lay, q)
        if not p or p.HitTest(far): continue
        sz = p.GetSize(); n = max(0.15, math.floor(tm(min(sz.x, sz.y)) / 0.05 + 1e-6) * 0.05)
        if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE or t.GetWidth() <= mm(n) + mm(0.001): continue
        run, L = run_from(i, key(q))
        if any(tracks[j].IsLocked() for j in run): continue
        if L <= 3.0:
            for j in run: tracks[j].SetWidth(mm(n)); done.add(j)
            stubs += 1
        else:
            dx, dy = far.x - q.x, far.y - q.y; Lseg = math.hypot(dx, dy)
            s = 0.0
            while s < Lseg and p.HitTest(pcbnew.VECTOR2I(int(q.x + dx * s / Lseg), int(q.y + dy * s / Lseg))): s += mm(0.02)
            neck = s + mm(0.8)
            if Lseg > neck + mm(0.3):
                X = pcbnew.VECTOR2I(int(q.x + dx * neck / Lseg), int(q.y + dy * neck / Lseg))
                nt = pcbnew.PCB_TRACK(b); nt.SetLayer(lay); nt.SetNet(t.GetNet()); nt.SetWidth(mm(n)); nt.SetStart(q); nt.SetEnd(X); b.Add(nt)
                if key(t.GetStart()) == key(q): t.SetStart(X)
                else: t.SetEnd(X)
            else:
                t.SetWidth(mm(n))
            done.add(i); necks += 1
        break
pcbnew.SaveBoard(B, b)
print(f"pad_necks: {stubs} short stubs set to their pad's width, {necks} longer tracks necked down at the pad")
