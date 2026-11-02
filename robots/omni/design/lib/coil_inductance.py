# Numerical inductance of the NFC floor coil (the real copper pattern, both layers in series): partial-inductance method.
#   the spiral is cut into straight segments; L = sum of every segment's partial self inductance (flat strip, Ruehli /
#   Grover) + every pair's mutual partial inductance (Neumann integral, Gauss points on the centre lines; the sign follows
#   the current direction). Good to a few % for traces wider apart than they are wide.
#   C:/Python312/python.exe design/lib/coil_inductance.py
import math, json, os, sys
import numpy as np
MU0 = 4e-7 * math.pi


def coil_path(r_out, n, w, s, gap, seg_per_turn=72):
    """Pancake 2-layer coil: TOP spirals OUT from r_in to r_out (n turns), via down, BOTTOM spirals back IN (n turns),
    same circulation; both ends at the inner radius. Returns polylines [(N x 3) top, (N x 3) bottom] in metres."""
    p = w + s
    r_in = r_out - (n - 1) * p - w / 2
    r_out_c = r_out - w / 2
    th = np.linspace(0, 2 * math.pi * n, seg_per_turn * n + 1)
    r_top = r_in + (r_out_c - r_in) * th / th[-1]
    top = np.c_[r_top * np.cos(th), r_top * np.sin(th), np.zeros_like(th)]
    r_bot = r_out_c - (r_out_c - r_in) * th / th[-1]
    th_b = th[-1] + th                                         # keeps going the same way round
    bot = np.c_[r_bot * np.cos(th_b), r_bot * np.sin(th_b), -gap * np.ones_like(th)]
    return [top, bot], r_in


def inductance(polys, w, t=35e-6, gauss=4):
    segs = []
    for P in polys:
        for a, b in zip(P[:-1], P[1:]):
            segs.append((a, b))
    A = np.array([s[0] for s in segs]); B = np.array([s[1] for s in segs])
    D = B - A; Lseg = np.linalg.norm(D, axis=1)
    gp, gw = np.polynomial.legendre.leggauss(gauss); gp = (gp + 1) / 2; gw = gw / 2
    pts = A[:, None, :] + D[:, None, :] * gp[None, :, None]      # (N, g, 3)
    N = len(segs)
    L_self = MU0 * Lseg / (2 * math.pi) * (np.log(2 * Lseg / (w + t)) + 0.50049 + (w + t) / (3 * Lseg))
    M = 0.0
    for i in range(N):
        pi = pts[i]                                              # (g, 3)
        d = pi[None, :, None, :] - pts[:, None, :, :]            # (N, g, g, 3)
        r = np.linalg.norm(d, axis=-1)
        r = np.maximum(r, (w + t) * 0.2235 * 2)                  # GMD floor for neighbours
        inv = (gw[None, :, None] * gw[None, None, :] / r).sum(axis=(1, 2))   # (N,)
        dot = D @ D[i]
        m = MU0 / (4 * math.pi) * dot * inv
        m[i] = 0.0
        M += m.sum()
    return float(L_self.sum() + M)


if __name__ == "__main__":
    W_, S_, GAP = 0.30e-3, 0.20e-3, 0.8e-3
    out = {}
    for n in (3, 4, 5):
        polys, r_in = coil_path(10.0e-3, n, W_, S_, GAP)
        L = inductance(polys, W_)
        length = sum(np.linalg.norm(np.diff(P, axis=0), axis=1).sum() for P in polys)
        out[n] = {"L_uH": round(L * 1e6, 3), "r_in_mm": round(r_in * 1e3, 2), "length_mm": round(length * 1e3, 1)}
        print(f"{n} turns per layer: L = {L*1e6:.3f} uH  (inner radius {r_in*1e3:.2f} mm, copper {length*1e3:.0f} mm)", flush=True)
    # sanity: a single circular loop r 10 mm, wire 0.3 mm -> mu0 r (ln(8r/a) - 2), a = equivalent radius
    th = np.linspace(0, 2 * math.pi, 145); loop = np.c_[0.01 * np.cos(th), 0.01 * np.sin(th), np.zeros_like(th)]
    print(f"check: one 20 mm loop of 0.3 mm trace: {inductance([loop], W_)*1e9:.1f} nH (textbook ~{MU0*0.01*(math.log(8*0.01/(0.3e-3*0.2235*2+35e-6))-2)*1e9:.0f} nH)")
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "coil_inductance.json"), "w"), indent=1)
