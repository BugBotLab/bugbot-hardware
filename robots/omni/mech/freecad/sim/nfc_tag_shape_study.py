# Which NFC tag shape triggers with the least of it under another robot's rim (edge loop kicad/BugBot_NFCfloor)?
#   C:/Python312/python.exe mech/freecad/sim/nfc_tag_shape_study.py
# Field: nfc_stinger_study.py (Biot-Savart of the real loop, the estimated drive). A tag reads when its flux reaches the
# 25 mm coin's at the ISO minimum: threshold = h_min x (coin coil area / this tag's antenna area) (ESTIMATE: equal EMF).
# Tags lie flat, z 2.6 mm, long side along the rim ("along") or pointing in ("across"); pushed in straight from outside.
import math, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "nfc_stinger_study.py"), encoding="utf-8").read()
g = {"__file__": os.path.join(HERE, "nfc_stinger_study.py")}
exec(src[:src.index("# ---- B's read zone")], g)
SA, SB, I, H, field_z, outer = g["SA"], g["SB"], g["I_TURN"], g["H_MIN"], g["field_z"], g["outer"]
from shapely.geometry import Point
A_REF = math.pi * 10.5 ** 2                          # the coin's coil (21 mm)
TAGS = [("round 25 mm coin (coil 21)", "disc", 21.0, 21.0), ("21 x 13.5 inlay (ant. 19 x 11.5)", "rect", 19.0, 11.5),
        ("30 x 15 token (ant. 18 x 10)", "rect", 18.0, 10.0), ("40 x 12 strip (ant. 38 x 10, custom)", "rect", 38.0, 10.0)]
Z = 2.6e-3
ANGLES = (100, 140, 200, 240, 320)                   # rim points between the wheels and away from the front notch


def samples(kind, L, W, n=13):
    if kind == "disc":
        pts = [(0, 0)] + [(ring * L / 2 * math.cos(2 * math.pi * k / int(24 * ring)), ring * L / 2 * math.sin(2 * math.pi * k / int(24 * ring)))
                          for ring in (0.25, 0.5, 0.75, 1.0) for k in range(int(24 * ring))]
        return np.array(pts) * 1e-3
    u = np.linspace(-L / 2, L / 2, n); v = np.linspace(-W / 2, W / 2, max(5, int(n * W / L) | 1))
    U, Vv = np.meshgrid(u, v); return np.c_[U.ravel(), Vv.ravel()] * 1e-3   # (along, radial-in)


out = {}
for name, kind, L, W in TAGS:
    area = math.pi * (L / 2) ** 2 if kind == "disc" else L * W
    thr = H * A_REF / area
    res = {}
    for orient in (("along",) if kind == "disc" else ("along", "across")):
        Lt, Wt = (L, W) if orient == "along" else (W, L)          # Lt along the rim, Wt pointing in
        S = samples(kind, Lt, Wt) if kind == "disc" else samples(kind, Lt, Wt)
        need = {1.5: [], 2.0: [], 3.0: []}
        for a in ANGLES:
            ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a)); tx, ty = -uy, ux
            rim = max(t for t in np.arange(0, 45, 0.25) if outer.contains(Point(t * ux, t * uy)))
            best = {}
            for e in np.arange(0.5, Wt + 12.0, 0.5):           # e: how far the tag's leading edge is past the rim
                rc = (rim - e + Wt / 2) * 1e-3                 # tag centre radius
                X = np.c_[rc * ux + S[:, 0] * tx - S[:, 1] * ux, rc * uy + S[:, 0] * ty - S[:, 1] * uy, np.full(len(S), Z)]
                k = abs(field_z(SA, SB, X, I).mean()) / thr
                for m in need:
                    if m not in best and k * m >= 1.0: best[m] = e
            for m in need: need[m].append(best.get(m))
        res[orient] = {f"x{m:g}": ([None if v is None else round(float(v), 1) for v in vals]) for m, vals in need.items()}
        res[orient]["tag_depth_mm"] = Wt
    out[name] = res
    print(name, json.dumps(res))
json.dump(out, open(os.path.join(HERE, "nfc_tag_shape_study.json"), "w"), indent=1)
