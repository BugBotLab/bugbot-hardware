# Tracks that stop short of their pad's centre (KiCad python; user, 2026-10-26 "not connected to the pad"): a track end
# just outside a pad that only touches it through its width, or inside it but off its centre, is carried on:
#   1. along its own line to the point level with the pad centre (inside the pad), then a short square step to the
#      centre (hidden under the pad's copper), or
#   2. straight to the centre if that is a 0 / 45 / 90-deg line, or
#   3. a 45-deg dogleg (diagonal then straight, or straight then diagonal).
# New pieces must clear everything (copper_fit.fits) and are no wider than the pad's narrow side. Locked pieces and the
# USB pair are left alone. Only adds / moves pieces (no Remove(): KiCad python loses its types after one).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/pad_reach.py [board]
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
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)


def octi(a, c):
    ang = math.degrees(math.atan2(c.y - a.y, c.x - a.x)) % 45
    return min(ang, 45 - ang) < 0.5


def joined(t, q):
    """does q meet anything at a point (a pad's centre, via, other piece's end or body)?"""
    net, lay = t.GetNetname(), t.GetLayer()
    if any(p.IsOnLayer(lay) and (p.GetPosition() - q).EuclideanNorm() <= mm(0.02) for p in padsby[net]): return True
    if any(v.GetNetname() == net and (v.GetPosition() - q).EuclideanNorm() <= v.GetWidth(pcbnew.F_Cu) // 2 for v in vias): return True
    return any(u is not t and u.GetNetname() == net and u.GetLayer() == lay and u.HitTest(q, u.GetWidth() // 2) for u in tracks)


def piece(a, c, like, w):
    n = pcbnew.PCB_TRACK(b); n.SetLayer(like.GetLayer()); n.SetNet(like.GetNet()); n.SetWidth(w); n.SetStart(a); n.SetEnd(c); return n


reached = left = 0
for t in list(tracks):
    if t.GetNetname() in SKIP or t.IsLocked(): continue
    for q, o in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        if joined(t, q): continue
        lay = t.GetLayer()
        pad = next((p for p in padsby[t.GetNetname()] if p.IsOnLayer(lay) and p.HitTest(q, t.GetWidth() // 2 + mm(0.01))), None)
        if not pad: continue
        C = pad.GetPosition(); sz = pad.GetSize()
        w = min(t.GetWidth(), mm(max(0.15, math.floor(tm(min(sz.x, sz.y)) / 0.05 + 1e-6) * 0.05)))
        if pad.HitTest(q) and any(u is not t and u.GetNetname() == t.GetNetname() and u.GetLayer() == lay and
                                  {(u.GetStart().x, u.GetStart().y), (u.GetEnd().x, u.GetEnd().y)} == {(q.x, q.y), (C.x, C.y)} for u in tracks):
            continue                                       # a piece from here to the centre is already there
        dx, dy = q.x - o.x, q.y - o.y; L = math.hypot(dx, dy)
        plans = []
        if L > 0:                                          # 1. carry on along the track's line, square step in the pad
            k = ((C.x - q.x) * dx + (C.y - q.y) * dy) / L / L
            K0 = pcbnew.VECTOR2I(int(q.x + k * dx), int(q.y + k * dy))
            if k > -1e-6 and pad.HitTest(K0) and (K0 - q).EuclideanNorm() > mm(0.005) or (K0 - q).EuclideanNorm() <= mm(0.005) and pad.HitTest(q):
                plans.append([q, K0, C] if (K0 - C).EuclideanNorm() > mm(0.005) else [q, C])
        if octi(q, C): plans.append([q, C])                # 2. straight in
        mx, my = C.x - q.x, C.y - q.y; m = min(abs(mx), abs(my)); sx, sy = (1 if mx > 0 else -1), (1 if my > 0 else -1)
        plans += [[q, pcbnew.VECTOR2I(q.x + sx * m, q.y + sy * m), C], [q, pcbnew.VECTOR2I(C.x - sx * m, C.y - sy * m), C]]
        done = False
        for pl in plans:
            segs = [piece(a, c, t, t.GetWidth() if i == 0 and not pad.HitTest(c) else w) for i, (a, c) in enumerate(zip(pl, pl[1:]))
                    if (c - a).EuclideanNorm() > mm(0.005)]
            if segs and all(fits(s, s.GetWidth()) for s in segs):
                for s in segs: b.Add(s); tracks.append(s)
                reached += 1; done = True
                break
        if not done: left += 1
pcbnew.SaveBoard(B, b)
print(f"pad_reach: {reached} track ends carried on into their pad's centre, {left} left (no clear way in)")
