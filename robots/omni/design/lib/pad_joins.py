# Clean pad joins (KiCad python): a track should run into its pad's centre at one width, not stop at the pad's edge and
# go on as a thin stub (user, 2026-10-26; the stubs came from track_tidy.py's "ends onto pad centres", capped at the pad's
# narrow side). For each piece lying wholly inside a pad that a wider piece of its net joins:
#   1. widen the stub to the joining track's width when that clears its neighbours (fine for passives and connectors),
#   2. else give the whole run into the pad (back to its previous via / junction / pad, if <= 3 mm) the stub's width,
#   3. else leave it (reported). Locked pieces (frozen hand edits) are never changed.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/pad_joins.py [board]
import collections, os, sys, pcbnew
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
    """pieces from track i outward from its end `start` until a pad / via / junction: (indices, length mm)"""
    out, L, cur, at = [], 0.0, i, start
    while True:
        t = tracks[cur]; out.append(cur); L += tm(t.GetLength())
        far = t.GetEnd() if key(t.GetStart()) == at else t.GetStart()
        k = (t.GetNetname(), t.GetLayer(), key(far))
        nxt = [x for x in ends[k] if x != cur]
        if len(nxt) != 1 or (t.GetNetname(), key(far)) in vias or pad_at(t.GetNetname(), t.GetLayer(), far): return out, L
        cur, at = nxt[0], key(far)


widened = narrowed = left = 0
for i, t in enumerate(tracks):
    net, lay = t.GetNetname(), t.GetLayer()
    p = pad_at(net, lay, t.GetStart())
    if not p or not p.HitTest(t.GetEnd()) or t.IsLocked(): continue
    for q in (t.GetStart(), t.GetEnd()):
        js = [j for j in ends[(net, lay, key(q))] if j != i and tracks[j].GetWidth() > t.GetWidth()]
        if not js: continue
        u = tracks[js[0]]
        if u.IsLocked(): continue
        if fits(t, u.GetWidth()):
            t.SetWidth(u.GetWidth()); widened += 1; break
        run, L = run_from(js[0], key(q))
        if L <= 3.0 and not any(tracks[j].IsLocked() for j in run):
            for j in run: tracks[j].SetWidth(t.GetWidth())
            narrowed += 1; break
        left += 1
pcbnew.SaveBoard(B, b)
print(f"pad_joins: {widened} stubs widened to their track, {narrowed} short runs narrowed to the pad's width, {left} left as they are")
