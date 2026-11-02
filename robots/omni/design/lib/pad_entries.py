# Straight pad entries (KiCad python): the last piece into a pad centre that runs at an odd angle (not a multiple of
# 45 deg; often a stub from a corner just inside the pad) is replaced by
#   1. the incoming line carried on to the point level with the pad centre (inside the pad), then a short square step to
#      the centre: the step hides under the pad's copper, so the track visibly runs straight into the pad; or
#   2. a 45-deg dogleg (diagonal then straight, or straight then diagonal) when the corner is outside the pad.
# Each new leg must clear everything (copper_fit.fits); if nothing fits, the piece stays. Pads turned off the 45-deg grid
# and the USB pair are left alone, and so are locked pieces (frozen hand edits).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/pad_entries.py [board]
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
ends = collections.defaultdict(list)
for t in tracks:
    for q in (t.GetStart(), t.GetEnd()): ends[(t.GetNetname(), t.GetLayer(), key(q))].append(t)
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)


def octilinear(a, c):
    ang = math.degrees(math.atan2(c.y - a.y, c.x - a.x)) % 45
    return min(ang, 45 - ang) < 0.5


def seg(a, c, like):
    n = pcbnew.PCB_TRACK(b); n.SetLayer(like.GetLayer()); n.SetNet(like.GetNet()); n.SetWidth(like.GetWidth())
    n.SetStart(a); n.SetEnd(c); return n


fixed = kept = 0
for t in tracks:
    if t.IsLocked(): continue
    net, lay = t.GetNetname(), t.GetLayer()
    for c_end, o_end in ((t.GetEnd(), t.GetStart()), (t.GetStart(), t.GetEnd())):
        pad = next((p for p in padsby[net] if p.IsOnLayer(lay) and p.HitTest(c_end)), None)
        if not pad: continue
        C = pad.GetPosition()
        if (C - c_end).EuclideanNorm() > mm(0.02): continue          # only pieces that end on the pad centre
        if pad.GetOrientationDegrees() % 45 > 0.5 and 45 - pad.GetOrientationDegrees() % 45 > 0.5: continue
        if octilinear(o_end, C): continue
        P = o_end; dx, dy = C.x - P.x, C.y - P.y; m = min(abs(dx), abs(dy))
        sx, sy = (1 if dx > 0 else -1), (1 if dy > 0 else -1)
        cand = []
        inc = [u for u in ends[(net, lay, key(P))] if u is not t and not (key(u.GetStart()) == key(t.GetStart()) and key(u.GetEnd()) == key(t.GetEnd()))]
        if len(inc) == 1:                                              # carry the incoming line on, square step in the pad
            u = inc[0]; Q = u.GetStart() if key(u.GetEnd()) == key(P) else u.GetEnd()
            ux, uy = P.x - Q.x, P.y - Q.y; L = math.hypot(ux, uy)
            if L > 0:
                k = ((C.x - P.x) * ux + (C.y - P.y) * uy) / L / L
                K0 = pcbnew.VECTOR2I(int(P.x + k * ux), int(P.y + k * uy))
                if k > 0 and pad.HitTest(K0): cand.append(K0)
        if not pad.HitTest(P):
            cand += [pcbnew.VECTOR2I(P.x + sx * m, P.y + sy * m),        # diagonal first, then straight into the pad
                     pcbnew.VECTOR2I(C.x - sx * m, C.y - sy * m)]        # straight first, then diagonal into the pad
        done = False
        for K in cand:
            if (K - P).EuclideanNorm() < mm(0.02): continue
            if (K - C).EuclideanNorm() < mm(0.005):                     # already level: one straight piece
                a = seg(P, C, t)
                if fits(a, t.GetWidth()): b.Add(a); b.Remove(t); fixed += 1; done = True; break
                continue
            a, c = seg(P, K, t), seg(K, C, t)
            if fits(a, t.GetWidth()) and fits(c, t.GetWidth()):
                b.Add(a); b.Add(c); b.Remove(t); fixed += 1; done = True
                break
        if not done: kept += 1
        break
pcbnew.SaveBoard(B, b)
print(f"pad_entries: {fixed} slanted pad entries straightened, {kept} kept (no room)")
