# Remove dead-end track stubs safely (KiCad python): every track piece with a free end (no pad, via, zone fill or other
# piece there) is taken out and the board's connectivity re-checked; it goes back only if that left something
# unconnected (some stubs carry a connection by overlapping another track's side). Repeats as removing one can leave the
# next one free. A kept one is joined properly: its free end is carried on along its own line to the centre line of the
# track it overlaps (<= 0.5 mm), so it meets it as a real T joint (same angle). Also reports vias whose copper lies partly on an SMD pad (via-on-pad, not centred on it).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/dead_ends.py [board]
import collections, math, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
SKIP = {"/USB_DP", "/USB_DN"}
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
ALL_Z = [z for z in b.Zones() if not z.GetIsRuleArea()]          # cached: KiCad python's board lists break after a Remove()
pads = collections.defaultdict(list)
for f in b.GetFootprints():
    for p in f.Pads(): pads[p.GetNetname()].append((f.GetReference(), p))


CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]


def _sd(p, a, c):                                      # point-segment distance (nm)
    ax, ay, cx, cy = a.x, a.y, c.x, c.y; dx, dy = cx - ax, cy - ay; L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0.0, min(1.0, ((p.x - ax) * dx + (p.y - ay) * dy) / L2))
    return math.hypot(p.x - ax - k * dx, p.y - ay - k * dy)


def _ss(a, c, d, e):                                   # segment-segment distance (nm; crossing segments -> 0)
    def cr(o, p, q): return (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x)
    if (cr(a, c, d) > 0) != (cr(a, c, e) > 0) and (cr(d, e, a) > 0) != (cr(d, e, c) > 0): return 0.0
    return min(_sd(a, d, e), _sd(c, d, e), _sd(d, a, c), _sd(e, a, c))


def _samples(t, step=mm(0.1)):
    a, c = t.GetStart(), t.GetEnd(); n = max(1, int(math.hypot(c.x - a.x, c.y - a.y) / step))
    return [pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * i / n), int(a.y + (c.y - a.y) * i / n)) for i in range(n + 1)]


def groups(net):
    """number of separate pieces of a net that hold pads (1 = fully connected), from what really touches
    (KiCad python can't give its own connectivity counts)"""
    T = [t for t in ALL_T if t.GetNetname() == net]
    V = [t for t in ALL_V if t.GetNetname() == net]
    Pd = [p for _, p in pads[net]]
    Z = [(z, l) for z in ALL_Z if z.GetNetname() == net for l in CU if z.IsOnLayer(l)]
    items = [("t", x) for x in T] + [("v", x) for x in V] + [("p", x) for x in Pd] + [("z", x) for x in Z]
    par = list(range(len(items)))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    def touch(A, Bb):
        (ka, a), (kb, c) = A, Bb
        if ka > kb: (ka, a), (kb, c) = (kb, c), (ka, a)          # order: p < t < v < z
        if (ka, kb) == ("t", "t"):
            return a.GetLayer() == c.GetLayer() and _ss(a.GetStart(), a.GetEnd(), c.GetStart(), c.GetEnd()) <= (a.GetWidth() + c.GetWidth()) / 2
        if (ka, kb) == ("t", "v"): return _sd(c.GetPosition(), a.GetStart(), a.GetEnd()) <= a.GetWidth() / 2 + c.GetWidth(pcbnew.F_Cu) / 2
        if (ka, kb) == ("p", "t"): return a.IsOnLayer(c.GetLayer()) and any(a.HitTest(q, c.GetWidth() // 2) for q in _samples(c))
        if (ka, kb) == ("p", "v"): return a.HitTest(c.GetPosition(), c.GetWidth(pcbnew.F_Cu) // 2)
        if (ka, kb) == ("t", "z"): return c[1] == a.GetLayer() and any(c[0].HitTestFilledArea(c[1], q, a.GetWidth() // 2) for q in _samples(a))
        if (ka, kb) == ("v", "z"): return c[0].HitTestFilledArea(c[1], a.GetPosition(), a.GetWidth(pcbnew.F_Cu) // 2)
        if (ka, kb) == ("p", "z"): return a.IsOnLayer(c[1]) and c[0].HitTestFilledArea(c[1], a.GetPosition(), 0)
        if (ka, kb) == ("v", "v"): return (a.GetPosition() - c.GetPosition()).EuclideanNorm() <= a.GetWidth(pcbnew.F_Cu)
        return False                                              # pad-pad, zone-zone: only through other items
    boxes = []
    for k, o in items:
        bb = o[0].GetBoundingBox() if k == "z" else o.GetBoundingBox(); bb.Inflate(mm(0.5)); boxes.append(bb)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if find(i) == find(j) or not boxes[i].Intersects(boxes[j]): continue
            if touch(items[i], items[j]): par[find(i)] = find(j)
    return len({find(i) for i, it in enumerate(items) if it[0] == "p"})


def unconnected(net):
    return groups(net)


def free_end(t, q, tracks, vias):
    net, lay = t.GetNetname(), t.GetLayer()
    if any(p.IsOnLayer(lay) and p.HitTest(q) for _, p in pads[net]): return False
    if any((v.GetPosition() - q).EuclideanNorm() <= v.GetWidth(pcbnew.F_Cu) // 2 for v in vias if v.GetNetname() == net): return False
    for u in tracks:
        if u is t or u.GetNetname() != net or u.GetLayer() != lay: continue
        if u.HitTest(q, u.GetWidth() // 2): return False
    for z in ALL_Z:
        if z.GetNetname() == net and z.IsOnLayer(lay) and z.HitTestFilledArea(lay, q): return False
    return True


# own lists of tracks / vias (as ALL_Z): after a Remove() KiCad python's board.GetTracks() stops working
ALL_T = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
ALL_V = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
removed = kept = 0; gone = []; keep = []                          # removed from the board only at the end: after any Remove()
for rnd in range(6):                                     # KiCad python loses its object types board-wide
    tracks = [t for t in ALL_T if t.GetNetname() not in SKIP and not t.IsLocked()]
    vias = ALL_V
    cands = [t for t in tracks if free_end(t, t.GetStart(), tracks, vias) or free_end(t, t.GetEnd(), tracks, vias)]
    n0 = removed
    for t in cands:
        net = t.GetNetname(); before = unconnected(net)
        ALL_T.remove(t)
        if unconnected(net) > before:
            ALL_T.append(t); kept += 1; keep.append(t)
        else:
            gone.append(t); removed += 1
    if removed == n0: break
def tee(t):
    """carry t's free end on along its line to the centre line of an overlapped same-net track (<= 0.5 mm)"""
    for which in (0, 1):
        q = t.GetStart() if which == 0 else t.GetEnd(); o = t.GetEnd() if which == 0 else t.GetStart()
        if not free_end(t, q, ALL_T, ALL_V): continue
        dx, dy = q.x - o.x, q.y - o.y; L = math.hypot(dx, dy)
        if L == 0: continue
        for u in ALL_T:
            if u is t or u.GetNetname() != t.GetNetname() or u.GetLayer() != t.GetLayer(): continue
            a, c = u.GetStart(), u.GetEnd(); ex, ey = c.x - a.x, c.y - a.y
            den = dx * ey - dy * ex
            if abs(den) < 1e-9: continue                 # parallel
            s_ = ((a.x - q.x) * ey - (a.y - q.y) * ex) / den            # along t from q (in units of L)
            k = ((a.x - q.x) * dy - (a.y - q.y) * dx) / den             # along u from a
            if 0 <= k <= 1 and -0.01 <= s_ * L <= mm(0.5):            # carry on only (trimming back can lose a pad overlap)
                X = pcbnew.VECTOR2I(int(q.x + dx * s_), int(q.y + dy * s_))
                (t.SetStart if which == 0 else t.SetEnd)(X)
                return True
    return False


teed = sum(tee(t) for t in keep)
if "--why" in sys.argv:                                  # what each kept stub's free end overlaps
    why = collections.Counter()
    for t in keep:
        for q in (t.GetStart(), t.GetEnd()):
            if not free_end(t, q, ALL_T, ALL_V): continue
            r = mm(0.01) + t.GetWidth() // 2
            hit = [f"pad {ref}.{p.GetNumber()}" for ref, p in pads[t.GetNetname()] if p.IsOnLayer(t.GetLayer()) and p.HitTest(q, r)]
            if not hit and any(u is not t and u.GetNetname() == t.GetNetname() and u.GetLayer() == t.GetLayer() and u.HitTest(q, r + u.GetWidth() // 2) for u in ALL_T): hit = ["track side"]
            why[(hit or ["?"])[0].split(".")[0] if hit and hit[0].startswith("pad") else (hit or ["?"])[0]] += 1
            if hit and hit[0].startswith("pad"): print("   pad-edge end:", t.GetNetname(), hit[0], f"({pcbnew.ToMM(q.x):.2f}, {pcbnew.ToMM(q.y):.2f})")
    print("kept stubs' free ends overlap:", dict(why))
vp = []
for v in ALL_V:
    c, r = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) // 2
    for ref, p in pads[v.GetNetname()]:
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD: continue
        lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        if p.GetEffectivePolygon(pcbnew.ERROR_INSIDE).Collide(pcbnew.VECTOR2I(c.x, c.y), r) and (p.GetPosition() - c).EuclideanNorm() > mm(0.05):
            vp.append(f"{ref}.{p.GetNumber()} {v.GetNetname()} ({tm(c.x):.2f}, {tm(c.y):.2f})")
for t in gone: b.Remove(t)
pcbnew.SaveBoard(B, b)
print(f"dead_ends: {removed} dead-end stubs removed, {kept} kept (they carry a connection), {teed} of those made proper T joints")
print(f"vias partly on an SMD pad: {len(vp)}"); [print("  ", x) for x in vp]
