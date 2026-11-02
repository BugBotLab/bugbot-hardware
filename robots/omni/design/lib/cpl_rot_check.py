# JLC placement check (KiCad python): for every part in a JLC CPL, JLC's own footprint (EasyEDA, fetched with easyeda2kicad
# into lib/3dmodels/lcsc/<LCSC>.pretty) is fitted onto our footprint's pads by pin number (model_fit.py's fit: best of 4 turns
# and 2 mirrorings; any angle). That gives the turn JLC needs and where JLC's footprint origin sits on ours. Compared with the CPL:
#   rotation   JLC's footprint turn that lands on our pads, seen from the part's side (bottom: board flipped left-right)
#   position   JLC's origin vs the CPL point (our footprint origin): an offset > 0.05 mm means the CPL point must move
# Writes <out>.csv (ref, LCSC, side, cpl rot, needed rot, offset, fit error, note); -> fix_cpl with --fix (CPL rewritten).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/cpl_rot_check.py board.kicad_pcb BOM.csv CPL.csv [--fix] [--symmetric=J6,J22,...] [--origin=aux]
# Bottom parts: JLC looks at them from below with the board flipped left-right, i.e. JLC = 180 - KiCad angle + offset (KiBot's
# 'correct' form for JLC); checked 2026-10-26 on C20617903, which is on both sides (U13 / U14 top give offset 270, U12 bottom fits 270).
import csv, glob, math, os, re, sys, pcbnew
B, BOM, CPL = sys.argv[1:4]
FIX = "--fix" in sys.argv
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
LC = BB + "/design/lib/3dmodels/lcsc"
# parts with no polarity whose JLC footprint numbers the pads differently: matched by pad shape
SYMMETRIC = {r for a in sys.argv if a.startswith("--symmetric=") for r in a.split("=", 1)[1].split(",")}
tm = pcbnew.ToMM


def view_pads(fp):
    """pad number -> centres round the footprint origin as JLC sees the part: top parts from above, bottom parts from below
    (the board flipped left-right, x -> -x); mm, y down. Absolute pad positions only: no KiCad flip / angle conventions."""
    out = {}
    o = fp.GetPosition(); bot = fp.IsFlipped()
    for p in fp.Pads():
        if not p.GetNumber(): continue
        x, y = tm(p.GetPosition().x - o.x), tm(p.GetPosition().y - o.y)
        out.setdefault(p.GetNumber(), []).append((-x if bot else x, y))
    return out


def _rot(x, y, rot):                                  # turn CCW as seen (y down), degrees
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return x * c + y * s_, -x * s_ + y * c


def fit(src, dst):
    """best (turn, mirror, dx, dy, rms) by pin number; the turn is free (parts at 109 deg etc.), solved per mirroring (2D Kabsch)"""
    best = None
    nums = [n for n in src if n in dst]
    cen = lambda pts: (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
    if not nums: return None, 0
    for mir in (1, -1):
        A = [(cen(src[n])[0] * mir, cen(src[n])[1]) for n in nums]; Bp = [cen(dst[n]) for n in nums]
        ca, cb = cen(A), cen(Bp)
        sxy = sum((a[0] - ca[0]) * (b[1] - cb[1]) - (a[1] - ca[1]) * (b[0] - cb[0]) for a, b in zip(A, Bp))
        sxx = sum((a[0] - ca[0]) * (b[0] - cb[0]) + (a[1] - ca[1]) * (b[1] - cb[1]) for a, b in zip(A, Bp))
        rot = (-math.degrees(math.atan2(sxy, sxx))) % 360
        if abs(rot - round(rot / 90) * 90) < 0.6: rot = (round(rot / 90) * 90) % 360   # snap tiny numeric noise
        R = [_rot(x, y, rot) for x, y in A]
        cr = cen(R); dx, dy = cb[0] - cr[0], cb[1] - cr[1]
        rms = math.sqrt(sum((r[0] + dx - b[0]) ** 2 + (r[1] + dy - b[1]) ** 2 for r, b in zip(R, Bp)) / len(R))
        if best is None or rms < best[4] - 0.02: best = (rot, mir, dx, dy, rms)
    return best, len(nums)


def fit_shape(src, dst, kicad_rot):
    """unpolarised parts (pins numbered differently): match the pad sets as points; turns tried round our part's own angle
    in 90 deg steps (and 1 deg steps near them), centroids aligned"""
    S = [q for v in src.values() for q in v]; D = [q for v in dst.values() for q in v]
    cs = (sum(q[0] for q in S) / len(S), sum(q[1] for q in S) / len(S)); cd = (sum(q[0] for q in D) / len(D), sum(q[1] for q in D) / len(D))
    best = None
    for k in range(4):
        for d in range(-3, 4):
            rot = (kicad_rot + 90 * k + d) % 360
            T = [_rot(x - cs[0], y - cs[1], rot) for x, y in S]
            err = sum(min(math.dist((t[0] + cd[0], t[1] + cd[1]), q) for q in D) for t in T) / len(T)
            if best is None or err < best[4] - 1e-6:
                r0 = _rot(-cs[0], -cs[1], rot); best = (rot, 1, r0[0] + cd[0], r0[1] + cd[1], err)
    return best, len(S)


lcsc = {}
for r in csv.DictReader(open(BOM, encoding="utf-8")):
    for d in r["Designator"].split(","): lcsc[d.strip()] = r["LCSC"]
rows = list(csv.DictReader(open(CPL, encoding="utf-8")))
b = pcbnew.LoadBoard(B)
ao = b.GetDesignSettings().GetAuxOrigin()
O = (tm(ao.x), tm(ao.y)) if "--origin=aux" in sys.argv else (0.0, 0.0)   # CPL origin: same as the gerbers (abs, or the aux origin)
report, fixed = [], 0
for r in rows:
    ref = r["Designator"]; code = lcsc.get(ref); f = b.FindFootprintByReference(ref)
    mods = glob.glob(f"{LC}/{code}.pretty/*.kicad_mod")
    cpl_rot = float(r["Rotation"]) % 360
    if not mods:
        report.append([ref, code, r["Layer"], cpl_rot, "", "", "", "no JLC footprint"]); continue
    e = pcbnew.FootprintLoad(os.path.dirname(mods[0]), os.path.basename(mods[0])[:-10])
    src = {}
    for p in e.Pads():
        if p.GetNumber(): src.setdefault(p.GetNumber(), []).append((tm(p.GetPosition().x), tm(p.GetPosition().y)))
    dst = view_pads(f)
    a = f.GetOrientationDegrees(); bot = f.IsFlipped()
    res, n = fit(src, dst)
    shape = res is None or n < 2 or res[1] < 0 or res[4] > 0.4 or ref in SYMMETRIC   # (mount tabs named differently: fine)
    if shape:                                          # unpolarised (sockets, buttons) or numbered differently: by pad shape
        view_a = (180 - a) % 360 if bot else a % 360
        res, n = fit_shape(src, dst, view_a)
    rot, mir, dx, dy, rms = res
    need = round(rot, 1) % 360                         # JLC's footprint turned CCW as seen from the part's own side
    ox, oy = (-dx if bot else dx), dy                  # JLC's origin on the board (top view, y down)
    off = math.hypot(ox, oy)
    note = []
    if shape: note.append("by pad shape (unpolarised / numbered differently)")
    if rms > 0.15: note.append(f"pads differ ({n} pins, rms {rms:.2f})")
    if abs(((need - cpl_rot + 180) % 360) - 180) > 0.5: note.append("ROTATION")
    if off > 0.05: note.append("OFFSET")
    report.append([ref, code, r["Layer"], f"{cpl_rot:g}", f"{need:g}", f"{off:.2f}", f"{rms:.3f}", "; ".join(note)])
    if FIX and (rms <= 0.4 or ref in SYMMETRIC):
        r["Rotation"] = f"{need:g}"
        p0 = f.GetPosition()                           # from the board, not the old CPL point: re-runs give the same file
        r["Mid X"] = f"{tm(p0.x) - O[0] + ox:.4f}mm"; r["Mid Y"] = f"{-(tm(p0.y) - O[1] + oy):.4f}mm"   # CPL y is up, KiCad's down
        fixed += 1
out = os.path.splitext(CPL)[0] + "_rotcheck.csv"
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["ref", "LCSC", "side", "cpl_rot", "jlc_rot", "origin_offset_mm", "fit_rms_mm", "note"]); w.writerows(report)
if FIX:
    with open(CPL, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
bad = [x for x in report if x[7]]
print(f"{len(report)} parts: {sum('ROTATION' in x[7] for x in report)} rotation, {sum('OFFSET' in x[7] for x in report)} offset, "
      f"{sum('shape' in x[7] or 'differ' in x[7] or 'no JLC' in x[7] for x in report)} to look at; fixed {fixed}; -> {out}")
for x in bad: print("  ", x)
