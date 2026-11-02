# One width per net (KiCad python), so tracks don't change width for no reason (user, 2026-10-26: no thin-thick-thin,
# "thin as long as possible"). Each net gets ONE width: its class's wide width (W_MAX) only if every run of the net
# clears at it, else the class width. A run (the pieces of one net and layer between pads, vias and 3+-way junctions)
# that can't clear at the net width gets the widest neck that does (0.25 / 0.2 / 0.15), else the narrowest width it
# already has (always legal). Clearance: 0.15 mm rule + 0.01, holes 0.25, board edge 0.3 (copper_fit). USB and camera
# lines keep their exact widths; runs with a locked piece (frozen hand edits) are left alone. pad_necks.py then necks
# runs down to small pads, and the remaining width changes get V tapers (teardrops.py).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/width_runs.py [board]
import collections, os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
from copper_fit import W_MAX, NECKS, cls_of, make_fits, mm
b = pcbnew.LoadBoard(B)
fits = make_fits(b)
key = lambda p: (p.x, p.y)
tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = {(v.GetNetname(), key(v.GetPosition())) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"}
padsby = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): padsby[p.GetNetname()].append(p)
ends = collections.defaultdict(list)
for i, t in enumerate(tracks):
    for q in (t.GetStart(), t.GetEnd()): ends[(t.GetNetname(), t.GetLayer(), key(q))].append(i)


def stop(net, lay, pt):
    if len(ends[(net, lay, pt)]) != 2 or (net, pt) in vias: return True
    v = pcbnew.VECTOR2I(*pt)
    return any(p.IsOnLayer(lay) and p.HitTest(v) for p in padsby[net])


seen, runs = set(), []
for i, t in enumerate(tracks):
    if i in seen: continue
    run, todo = [], [i]
    while todo:                                          # flood through non-stop joints
        j = todo.pop()
        if j in seen: continue
        seen.add(j); run.append(j); tj = tracks[j]
        for q in (tj.GetStart(), tj.GetEnd()):
            k = (tj.GetNetname(), tj.GetLayer(), key(q))
            if not stop(*k): todo += [x for x in ends[k] if x not in seen]
    runs.append(run)
changed = steps_before = 0
bynet = collections.defaultdict(list)
for run in runs:
    ts = [tracks[j] for j in run]
    if len({t.GetWidth() for t in ts}) > 1: steps_before += 1
    bynet[ts[0].GetNetname()].append(ts)
for net, nruns in bynet.items():
    name, w = cls_of(net)
    if name in ("USB", "Camera"): continue
    free = [ts for ts in nruns if not any(t.IsLocked() for t in ts)]
    wide = name in W_MAX and all(all(t.GetWidth() >= mm(W_MAX[name]) or fits(t, mm(W_MAX[name])) for t in ts) for ts in free)
    net_w = mm(W_MAX[name] if wide else w)
    for ts in free:
        cur_min = min(t.GetWidth() for t in ts)
        cand = [net_w] + [mm(n) for n in NECKS if mm(n) < net_w]
        pick = next((c for c in cand if all(t.GetWidth() >= c or fits(t, c) for t in ts)), min(cur_min, net_w))
        for t in ts:
            if t.GetWidth() != pick: t.SetWidth(pick); changed += 1
pcbnew.SaveBoard(B, b)
print(f"width_runs: {len(bynet)} nets, {len(runs)} runs ({steps_before} had mixed widths); {changed} pieces changed")
