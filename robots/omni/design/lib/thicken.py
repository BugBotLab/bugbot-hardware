# Thicken where the current needs it (KiCad python; user, 2026-10-26 "make poor connections better, thicker if need
# be"). Driven by sim_copper.py's results (_work/sim_copper.json): every track piece over its IPC-2221 limit (10 degC) at
# the current it really carries. The whole run it belongs to (pads / vias / 3+-way junctions to the next) gets ONE width:
# the IPC width for 1.2 x that current (rounded up to 0.05, at most 2.0 mm), or the widest below that still clearing
# everything along the run (copper_fit.fits). So tracks get thick only where current flows, and stay one width per
# run; teardrops.py tapers the joins. Locked pieces and the USB pair are left alone.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/thicken.py [board]
import collections, json, math, os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copper_fit import make_fits, mm, tm
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
SIM = BB + "/design/schematics/Main/_work/sim_copper.json"
OUTER = (pcbnew.F_Cu, pcbnew.B_Cu)


def w_ipc(I, outer, dt=10.0):
    A = (I / ((0.048 if outer else 0.024) * dt ** 0.44)) ** (1 / 0.725)            # mil^2
    return A / (1.378 if outer else 0.689) * 0.0254


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


def run_of(i):
    run, todo, seen = [], [i], set()
    while todo:
        j = todo.pop()
        if j in seen: continue
        seen.add(j); run.append(j); tj = tracks[j]
        for q in (tj.GetStart(), tj.GetEnd()):
            k = (tj.GetNetname(), tj.GetLayer(), key(q))
            if not stop(*k): todo += [x for x in ends[k] if x not in seen]
    return run


def find_piece(net, a, c):
    A, C = pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(c[0]), mm(c[1]))
    for i, t in enumerate(tracks):
        if t.GetNetname() == net and {key(t.GetStart()), key(t.GetEnd())} == {key(A), key(C)}: return i
        if t.GetNetname() == net and (t.GetStart() - A).EuclideanNorm() < mm(0.002) and (t.GetEnd() - C).EuclideanNorm() < mm(0.002): return i
    return None


sim = json.load(open(SIM))
done, report = set(), []
for net, r in sim.items():
    if net in ("/USB_DP", "/USB_DN"): continue
    for o in r.get("over", []):
        i = find_piece(net, o["a"], o["b"])
        if i is None or i in done: continue
        run = run_of(i); done |= set(run)
        ts = [tracks[j] for j in run]
        if any(t.IsLocked() for t in ts): continue
        outer = ts[0].GetLayer() in OUTER
        need = min(2.0, math.ceil(w_ipc(o["I"] * 1.2, outer) / 0.05) * 0.05)
        cur = max(t.GetWidth() for t in ts)
        pick = None
        w = need
        while w * 1e6 > cur + 1:
            if all(t.GetWidth() >= mm(w) or fits(t, mm(w)) for t in ts): pick = w; break
            w = round(w - 0.05, 2)
        if pick:
            for t in ts: t.SetWidth(mm(pick))
        report.append(f"{net:10s} {len(ts)} piece run on {b.GetLayerName(ts[0].GetLayer())}: {o['I']} A needs {need:.2f} mm -> "
                      + (f"{pick:.2f} mm" if pick else f"stays {tm(cur):.2f} mm (no room)"))
pcbnew.SaveBoard(B, b)
print("thicken:"); [print("  ", x) for x in report]
