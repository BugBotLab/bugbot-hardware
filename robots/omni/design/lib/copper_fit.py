# Shared by width_runs.py and pad_joins.py (KiCad python): net classes and a clearance test for a track at a new width.
import math, re, pcbnew
mm, tm = pcbnew.FromMM, pcbnew.ToMM
CLASSES = [("Battery", r"/BAT_.*|/VBAT_P|/VBAT_SW|/BAT_F|/FS_D", 0.6), ("Local", r"/SW33[AB]|/SW5", 0.3),
           ("Rail3V3", r"/3V3", 0.4),
           ("Power", r"/VBUS|/5V|/SERVO_5V|/M\d_[AB]|/KICK_HV|/KICK_BOOST|/KSW|/SOL_N|/BUZ_N|/VSYS|/GND", 0.4),
           ("USB", r"/USB_D[PN]", 0.2), ("Camera", r"/CAM_.*", 0.15)]      # as track_tidy.py / route_engine.py
W_MAX = {"Battery": 1.0, "Power": 0.8, "Rail3V3": 0.6, "Local": 0.5}
NECKS = (0.25, 0.2, 0.15)


def cls_of(net):
    for name, pat, w in CLASSES:
        if re.fullmatch(pat, net): return name, w
    return "Default", 0.2


CL = mm(0.16)
LAYERS_CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)


def make_fits(b):
    """fits(track, width_nm): would the track clear everything else at that width (0.15 rule + 0.01, holes 0.25, edge 0.3)"""
    items = {l: [] for l in LAYERS_CU}
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            for l in LAYERS_CU: items[l].append((t, t.GetNetname()))
        elif t.GetLayer() in items: items[t.GetLayer()].append((t, t.GetNetname()))
    for f in b.GetFootprints():
        for p in f.Pads():
            for l in LAYERS_CU:
                if p.IsOnLayer(l): items[l].append((p, p.GetNetname()))
    holes = [(p.GetPosition(), p.GetDrillSize().x) for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSize().x > 0]
    holes += [(v.GetPosition(), v.GetDrillValue()) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]

    def fits(t, w):
        seg = pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), w)
        bb = t.GetBoundingBox(); bb.Inflate(int(w) + mm(1))
        for it, net in items[t.GetLayer()]:
            if net == t.GetNetname(): continue
            if not bb.Intersects(it.GetBoundingBox()): continue
            if it.GetClass() == "PCB_VIA":
                if seg.Collide(pcbnew.SHAPE_CIRCLE(it.GetPosition(), it.GetWidth(t.GetLayer()) // 2), CL): return False
            elif it.GetClass() == "PCB_TRACK":
                if seg.Collide(pcbnew.SHAPE_SEGMENT(it.GetStart(), it.GetEnd(), it.GetWidth()), CL): return False
            else:
                if it.GetEffectivePolygon(pcbnew.ERROR_INSIDE).Collide(seg, CL): return False
        for c, d in holes:
            if (c - t.GetStart()).EuclideanNorm() > t.GetLength() + mm(3) and (c - t.GetEnd()).EuclideanNorm() > t.GetLength() + mm(3): continue
            if seg.Collide(pcbnew.SHAPE_CIRCLE(c, d // 2), mm(0.25)):
                # a via of this net at the track's own end is fine
                if any((c - q).EuclideanNorm() < mm(0.01) for q in (t.GetStart(), t.GetEnd())): continue
                return False
        for pt in (t.GetStart(), t.GetEnd()):                # board edge: the 40.6 circle less the ball cut-out (r 18.6 at 141.5, 100)
            x, y = tm(pt.x), tm(pt.y)
            d = min(40.6 - math.hypot(x - 100, y - 100), math.hypot(x - 141.5, y - 100) - 18.6)
            if d < tm(w) / 2 + 0.3: return False
        return True
    return fits
