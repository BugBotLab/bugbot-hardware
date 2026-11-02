# Real 3D models for the main board's parts that had none or a placeholder box (KiCad python). The LCSC / EasyEDA model
# of each part (fetched with easyeda2kicad into lib/3dmodels/lcsc/<LCSC>.pretty / .3dshapes) comes with EasyEDA's footprint; its pads are
# matched to ours (best of 4 turns and the 2 mirrorings, least squares on the pad centres) and the model's offset and turn
# carried over, so the model sits on our pads. U8 / U9 get KiCad's own HTSSOP-16 model with the exposed pad.
# Writes the board; model_to_library.py then copies the models into our library footprints (BugBot.pretty).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/model_fit.py [board]
import glob, math, os, re, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
LIB = BB + "/design/lib"
LC = LIB + "/3dmodels/lcsc"
PARTS = {"BZ1": "C94599", "U4": "C2845237", "J19": "C160352", "SW1": "C22435663", "SW2": "C7470171", "SW3": "C7470171",
         "BT1": "C238066"}
STOCK = {"U8": "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm.step",
         "U9": "${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm.step"}
mm, tm = pcbnew.FromMM, pcbnew.ToMM


def local_pads(fp):
    """pad number -> centre in the footprint's own frame (unturned, top side), mm, y down (KiCad)"""
    out = {}
    o = fp.GetPosition(); a = -math.radians(fp.GetOrientationDegrees()); flip = fp.IsFlipped()
    for p in fp.Pads():
        if not p.GetNumber(): continue
        x, y = tm(p.GetPosition().x - o.x), tm(p.GetPosition().y - o.y)
        x, y = x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)   # KiCad turns are CCW on screen
        if flip: x = -x                                                                  # flipped left-right
        out.setdefault(p.GetNumber(), []).append((x, y))
    return out


def fit(src, dst):
    """best (turn deg, mirror, dx, dy, rms) mapping src pad centres onto dst"""
    best = None
    nums = [n for n in src if n in dst]
    for mir in (1, -1):
        for rot in (0, 90, 180, 270):
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            A = []; Bp = []
            cen = lambda pts: (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
            for n in nums:                                # each pin number by the centre of its pads (4-pad buttons ...)
                x, y = cen(src[n]); x *= mir; A.append((x * c + y * s, -x * s + y * c))
                Bp.append(cen(dst[n]))
            dx = sum(b[0] - a[0] for a, b in zip(A, Bp)) / len(A); dy = sum(b[1] - a[1] for a, b in zip(A, Bp)) / len(A)
            rms = math.sqrt(sum((a[0] + dx - b[0]) ** 2 + (a[1] + dy - b[1]) ** 2 for a, b in zip(A, Bp)) / len(A))
            if best is None or rms < best[4] - 0.02: best = (rot, mir, dx, dy, rms)   # ties: keep the unmirrored, first turn
    return best, len(nums)


def fit_shape(src, dst):
    """when the two footprints number their pads differently: match the pad layouts as point sets (centroids aligned,
    best turn / mirror by mean nearest-pad distance)"""
    S = [q for v in src.values() for q in v]; D = [q for v in dst.values() for q in v]
    cs = (sum(q[0] for q in S) / len(S), sum(q[1] for q in S) / len(S)); cd = (sum(q[0] for q in D) / len(D), sum(q[1] for q in D) / len(D))
    best = None
    for mir in (1, -1):
        for rot in (0, 90, 180, 270):
            c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            T = []
            for x, y in S:
                x = (x - cs[0]) * mir; y = y - cs[1]
                T.append((x * c + y * s_ + cd[0], -x * s_ + y * c + cd[1]))
            err = sum(min(math.dist(t, d) for d in D) for t in T) / len(T)
            if best is None or err < best[4] - 0.02:
                # the shift that carries src's origin: rotate the centroid offset, as fit() reports dx, dy
                x0, y0 = -cs[0] * mir, -cs[1]
                best = (rot, mir, x0 * c + y0 * s_ + cd[0], -x0 * s_ + y0 * c + cd[1], err)
    return best, len(S)


b = pcbnew.LoadBoard(B)
report = []
for ref, code in PARTS.items():
    f = b.FindFootprintByReference(ref)
    kmod = glob.glob(f"{LC}/{code}.pretty/*.kicad_mod")[0]
    step = glob.glob(f"{LC}/{code}.3dshapes/*.step")[0]
    e = pcbnew.FootprintLoad(os.path.dirname(kmod), os.path.basename(kmod)[:-10])
    src = {}
    for p in e.Pads():
        if p.GetNumber(): src.setdefault(p.GetNumber(), []).append((tm(p.GetPosition().x), tm(p.GetPosition().y)))
    (rot, mir, dx, dy, rms), n = fit(src, local_pads(f))
    if rms > 0.1: (rot, mir, dx, dy, rms), n = fit_shape(src, local_pads(f))     # pads numbered differently
    em = list(e.Models())[0]
    ox, oy, oz = em.m_Offset.x, em.m_Offset.y, em.m_Offset.z            # model offset: mm, y up (KiCad's 3D convention)
    # carry the EasyEDA model offset through the same turn, then add the pad-fit shift (dy flips: 3D y is up)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    mx, my = ox * mir * c - oy * s, ox * mir * s + oy * c
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/../lib/3dmodels/lcsc/" + os.path.relpath(step, LC).replace("\\", "/")
    m.m_Offset = pcbnew.VECTOR3D(mx + dx, my - dy, oz)
    m.m_Rotation = pcbnew.VECTOR3D(em.m_Rotation.x, em.m_Rotation.y, em.m_Rotation.z + rot)
    m.m_Scale = pcbnew.VECTOR3D(1, 1, 1)
    keep_cell = [x for x in f.Models() if "Cell_16340" in x.m_Filename]          # BT1: the 16340 cell model stays too
    f.Models().clear()
    f.Models().push_back(m)
    for x in keep_cell: f.Models().push_back(x)
    report.append(f"{ref:4s} {code:10s} pads matched {n:2d}  turn {rot:3d} {'mirrored' if mir < 0 else '':8s} shift ({dx:+.2f}, {dy:+.2f}) mm  fit error {rms:.3f} mm  {os.path.basename(step)}")
for ref, path in STOCK.items():
    f = b.FindFootprintByReference(ref)
    m = pcbnew.FP_3DMODEL(); m.m_Filename = path
    f.Models().clear(); f.Models().push_back(m)
    report.append(f"{ref:4s} KiCad stock model {os.path.basename(path)}")
pcbnew.SaveBoard(B, b)
print("\n".join(report))

