# Routing quality report (KiCad python): the things that make a board look unplanned.
#   width steps    a track meets another of its net with a different width, away from any pad / via
#   jogs           short pieces (< 0.4 mm) between two others, away from pads / vias (zig-zags, little doglegs)
#   collinear      two pieces of one net, same layer and width, in a straight line: should be one
#   odd angles     corners that are not 45 / 90 / 135 deg (any-angle wiggles)
#   pad entries    the last piece into a pad not along one of the pad's axes or diagonals
# Prints totals and the worst nets; with --json writes every finding for plotting.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_quality.py [board] [--json out.json]
import collections, json, math, sys, pcbnew
args = [a for a in sys.argv[1:] if not a.startswith("--")]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = args[0] if args else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
JS = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
SKIP = {"/USB_DP", "/USB_DN"}                     # the impedance-controlled pair keeps its own geometry
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
key = lambda p: (round(tm(p.x), 3), round(tm(p.y), 3))
tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() not in SKIP]
vias = {(v.GetNetname(), key(v.GetPosition())) for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T}
vlist = [(v.GetNetname(), v.GetPosition(), v.GetWidth(pcbnew.F_Cu) / 2) for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]


def in_via(net, pt):                                  # joints under a via's copper don't show
    p = pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1]))
    return any(n == net and (c - p).EuclideanNorm() <= r for n, c, r in vlist)


pads = [p for f in b.GetFootprints() for p in f.Pads()]
padsby = collections.defaultdict(list)
for p in pads: padsby[p.GetNetname()].append(p)
ends = collections.defaultdict(list)                   # (net, layer, point) -> [(track, which end)]
for t in tracks:
    for w, p in ((0, t.GetStart()), (1, t.GetEnd())):
        ends[(t.GetNetname(), t.GetLayer(), key(p))].append(t)


def in_pad(net, layer, pt):
    v = pcbnew.VECTOR2I(pcbnew.FromMM(pt[0]), pcbnew.FromMM(pt[1]))
    return next((p for p in padsby[net] if p.IsOnLayer(layer) and p.HitTest(v)), None)


def direction(t, at):
    s, e = key(t.GetStart()), key(t.GetEnd())
    o = e if s == at else s
    return math.degrees(math.atan2(o[1] - at[1], o[0] - at[0]))


F = collections.defaultdict(list)
for (net, lay, pt), ts in ends.items():
    pad = in_pad(net, lay, pt); via = (net, pt) in vias or in_via(net, pt)
    if len(ts) == 2 and not pad and not via:
        a, c = ts
        if a.GetWidth() != c.GetWidth(): F["width steps"].append((net, pt))
        d = (direction(a, pt) - direction(c, pt)) % 360
        turn = abs(180 - d)                            # 0 = straight on
        if turn < 0.5 and a.GetWidth() == c.GetWidth(): F["collinear"].append((net, pt))
        elif min(abs(turn - k) for k in (45, 90, 135)) > 2 and turn > 0.5: F["odd angles"].append((net, pt))
    if pad and len(ts) == 1:
        t = ts[0]; d = direction(t, pt) - pad.GetOrientationDegrees()
        if min(abs(((d - k) + 180) % 360 - 180) for k in range(0, 360, 45)) > 2: F["pad entries"].append((net, pt))
for t in tracks:
    L = tm(t.GetLength())
    if L < 0.4:
        s, e = key(t.GetStart()), key(t.GetEnd())
        n, l = t.GetNetname(), t.GetLayer()
        if all(len(ends[(n, l, p)]) >= 2 and not in_pad(n, l, p) and not in_via(n, p) for p in (s, e)):
            F["jogs"].append((n, s))
print(f"{len(tracks)} track pieces (USB pair skipped)")
for k in ("width steps", "jogs", "collinear", "odd angles", "pad entries"):
    c = collections.Counter(n for n, _ in F[k])
    print(f"  {k:12s} {len(F[k]):4d}   worst: {', '.join(f'{n} {m}' for n, m in c.most_common(6))}")
if JS: json.dump({k: v for k, v in F.items()}, open(JS, "w"))
