# Near-miss joints (KiCad python; user, 2026-10-26 "this looks like an error"): two pieces of one net and layer whose
# ends nearly meet (closer than the wider track's width) but are not the same point - they only connect by overlapping
# copper and leave a lump. Both ends are moved to where the two lines cross (a clean corner) when that is within
# 0.6 mm of each end; collinear pieces are joined end to end. Every moved piece must still clear everything
# (copper_fit.fits), else it is put back. Pads / vias at the ends, locked pieces and the USB pair are left alone.
# Only moves ends (no Remove(): KiCad python loses its types after one).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/joint_snap.py [board]
import collections, math, os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copper_fit import make_fits, mm, tm
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
SKIP = {"/USB_DP", "/USB_DN"}
b = pcbnew.LoadBoard(B)
fits = make_fits(b)
key = lambda p: (p.x, p.y)
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() not in SKIP]
vias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)
endcount = collections.Counter()
for t in tracks:
    for q in (t.GetStart(), t.GetEnd()): endcount[(t.GetNetname(), t.GetLayer(), key(q))] += 1


def lone(t, q):
    """an end that meets nothing at a point: no other end there, not in a pad, not on a via"""
    net, lay = t.GetNetname(), t.GetLayer()
    if endcount[(net, lay, key(q))] > 1: return False
    if any(p.IsOnLayer(lay) and p.HitTest(q) for p in padsby[net]): return False
    return not any(v.GetNetname() == net and (v.GetPosition() - q).EuclideanNorm() <= v.GetWidth(pcbnew.F_Cu) // 2 for v in vias)


def ends(t):
    return [(0, t.GetStart(), t.GetEnd()), (1, t.GetEnd(), t.GetStart())]


def setend(t, which, X):
    (t.SetStart if which == 0 else t.SetEnd)(X)


snapped = refused = 0
used = set()
byl = collections.defaultdict(list)
for t in tracks: byl[(t.GetNetname(), t.GetLayer())].append(t)
for grp in byl.values():
    for i, t in enumerate(grp):
        if t.IsLocked(): continue
        for wt, q, qo in ends(t):
            if (id(t), wt) in used or not lone(t, q): continue
            for u in grp[i + 1:]:
                if u.IsLocked(): continue
                for wu, p, po in ends(u):
                    if (id(u), wu) in used or not lone(u, p): continue
                    d = (q - p).EuclideanNorm()
                    if d == 0 or d > max(t.GetWidth(), u.GetWidth()): continue
                    ax, ay, bx, by = q.x - qo.x, q.y - qo.y, p.x - po.x, p.y - po.y
                    den = ax * by - ay * bx
                    if abs(den) < 1e-6 * math.hypot(ax, ay) * math.hypot(bx, by):     # collinear: meet end to end
                        X = p
                    else:                                                          # where the two lines cross
                        s = ((po.x - qo.x) * by - (po.y - qo.y) * bx) / den
                        X = pcbnew.VECTOR2I(int(qo.x + ax * s), int(qo.y + ay * s))
                    if (X - q).EuclideanNorm() > mm(0.6) or (X - p).EuclideanNorm() > mm(0.6): continue
                    old_q, old_p = pcbnew.VECTOR2I(q.x, q.y), pcbnew.VECTOR2I(p.x, p.y)
                    setend(t, wt, X); setend(u, wu, X)
                    if fits(t, t.GetWidth()) and fits(u, u.GetWidth()):
                        snapped += 1; used |= {(id(t), wt), (id(u), wu)}
                    else:
                        setend(t, wt, old_q); setend(u, wu, old_p); refused += 1
                    break
                if (id(t), wt) in used: break
pcbnew.SaveBoard(B, b)
print(f"joint_snap: {snapped} near-miss joints made clean corners, {refused} left (a moved piece would not clear)")
