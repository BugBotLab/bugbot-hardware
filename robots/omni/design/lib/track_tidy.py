# Track tidy-up (KiCad python), after routing (user, 2026-10-25):
#  1. every track end that stops inside a pad of its net, off the pad's centre, gets a straight piece to the centre
#     (on the pad's layer, no wider than the pad's narrow side), so each connection lands on the pad centre;
#  2. widths from a small set per net class, measured against the real copper: power as wide as its class allows
#     (W_MAX) wherever it clears by the 0.15 mm rule, else the class width, else a neck (0.25 / 0.2 / 0.15); signals at
#     their class width; USB and camera keep theirs. So a thin bit is left only where something really is in the way.
# Usage: "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/track_tidy.py [board]
import math, re, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
mm, tm = pcbnew.FromMM, pcbnew.ToMM
CLASSES = [("Battery", r"/BAT_.*|/VBAT_P|/VBAT_SW|/BAT_F|/FS_D", 0.6), ("Local", r"/SW33[AB]|/SW5", 0.3),
           ("Rail3V3", r"/3V3", 0.4),
           ("Power", r"/VBUS|/5V|/SERVO_5V|/M\d_[AB]|/KICK_HV|/KICK_BOOST|/KSW|/SOL_N|/BUZ_N|/VSYS|/GND", 0.4),
           ("USB", r"/USB_D[PN]", 0.2), ("Camera", r"/CAM_.*", 0.15)]
W_MAX = {"Battery": 1.0, "Power": 0.8, "Rail3V3": 0.6, "Local": 0.5}          # as route_engine.py
NECKS = (0.15, 0.2, 0.25)


def cls_of(net):
    for name, pat, w in CLASSES:
        if re.fullmatch(pat, net): return name, w
    return "Default", 0.2


b = pcbnew.LoadBoard(B)
tracks = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA"]
# ---- 2. widths: as wide as the class allows wherever it really clears (0.15 mm rule + 0.01), else narrower
CL = mm(0.16)
LAYERS_CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
items = {l: [] for l in LAYERS_CU}                     # other copper per layer: (bbox, net, shape)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        for l in LAYERS_CU: items[l].append((t, t.GetNetname()))
    elif t.GetLayer() in items: items[t.GetLayer()].append((t, t.GetNetname()))
for f in b.GetFootprints():
    for p in f.Pads():
        for l in LAYERS_CU:
            if p.IsOnLayer(l): items[l].append((p, p.GetNetname()))
holes = [(p.GetPosition(), p.GetDrillSize().x) for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSize().x > 0]


def fits(t, w):
    seg = pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), w)
    bb = t.GetBoundingBox(); bb.Inflate(int(w) + mm(1))
    for it, net in items[t.GetLayer()]:
        if net == t.GetNetname() or it is t: continue
        if not bb.Intersects(it.GetBoundingBox()): continue
        if it.GetClass() == "PCB_VIA":
            if seg.Collide(pcbnew.SHAPE_CIRCLE(it.GetPosition(), it.GetWidth(t.GetLayer()) // 2), CL): return False
        elif it.GetClass() == "PCB_TRACK":
            if seg.Collide(pcbnew.SHAPE_SEGMENT(it.GetStart(), it.GetEnd(), it.GetWidth()), CL): return False
        else:
            if it.GetEffectivePolygon(pcbnew.ERROR_INSIDE).Collide(seg, CL): return False
    for c, d in holes:
        if seg.Collide(pcbnew.SHAPE_CIRCLE(c, d // 2), mm(0.25)): return False
    for pt in (t.GetStart(), t.GetEnd()):                # board edge: the 40.6 circle less the ball cut-out (r 18.6 at 141.5, 100)
        x, y = tm(pt.x), tm(pt.y)
        d = min(40.6 - math.hypot(x - 100, y - 100), math.hypot(x - 141.5, y - 100) - 18.6)
        if d < tm(w) / 2 + 0.3: return False
    return True


changed = 0
for t in tracks:
    name, w = cls_of(t.GetNetname())
    cur = t.GetWidth()
    if name in ("USB", "Camera"): cand = [w]                       # these keep their exact width
    elif name in W_MAX: cand = [W_MAX[name], w] + [n for n in NECKS if n < w]
    else: cand = [w] + [n for n in NECKS if n < w]
    # widths only go up (to the class's wide or standard width) where that clears; otherwise the track keeps its
    # width, which is already legal (narrowing could pull a track end off the pad it reaches)
    for c in [c for c in cand if mm(c) > cur + mm(0.001)]:
        if fits(t, mm(c)):
            t.SetWidth(mm(c)); changed += 1
            break
print(f"widths: {changed} of {len(tracks)} track pieces changed (power as wide as it clears, signals at their class width)")
# ---- 1. ends onto pad centres
pads = {}
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname(): pads.setdefault(p.GetNetname(), []).append(p)
ends = {}                                              # (net, layer, x, y) of every track end, to skip ends already central
for t in tracks:
    for q in (t.GetStart(), t.GetEnd()): ends.setdefault((t.GetNetname(), t.GetLayer()), set()).add((q.x, q.y))
added = 0
for t in tracks:
    net, lay = t.GetNetname(), t.GetLayer()
    for q in (t.GetStart(), t.GetEnd()):
        for p in pads.get(net, []):
            if not p.IsOnLayer(lay) or not p.HitTest(q): continue
            c = p.GetPosition()
            if math.hypot(c.x - q.x, c.y - q.y) < mm(0.02): break
            if (c.x, c.y) in ends.get((net, lay), set()): break      # another piece already reaches the centre
            sz = p.GetSize()
            w = min(t.GetWidth(), min(sz.x, sz.y)) if p.GetShape() != pcbnew.PAD_SHAPE_CIRCLE else t.GetWidth()
            n = pcbnew.PCB_TRACK(b); n.SetLayer(lay); n.SetNet(t.GetNet()); n.SetWidth(w)
            n.SetStart(q); n.SetEnd(c); b.Add(n); added += 1
            ends.setdefault((net, lay), set()).add((c.x, c.y))
            break
print(f"pad centres: {added} short pieces added so track ends land on their pad centre")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
