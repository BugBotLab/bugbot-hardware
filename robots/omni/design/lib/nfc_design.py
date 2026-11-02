# NFC floor coil + WS1850S antenna matching (calculation, no KiCad).
#   coil: round 2-layer spiral on a 22 mm, 0.8 mm board (top + bottom spirals in series, same winding sense).
#     inductance: modified Wheeler / Mohan (circular: c1 1.00, c2 2.46, c3 0, c4 0.20) per layer + mutual between layers
#     (k from the layer gap, ESTIMATE); AC resistance with skin effect.
#   matching: the WS1850S reference circuit (datasheet fig. 3, dual TX) with its implied antenna is the TARGET: we pick
#   series / parallel C (JLC stock values) + damping R so OUR coil shows the TX pins the same impedance at 13.56 MHz.
#   C:/Python312/python.exe design/lib/nfc_design.py
import math, itertools, json, os
F0 = 13.56e6; W = 2 * math.pi * F0; MU0 = 4e-7 * math.pi
RHO = 1.72e-8; T_CU = 35e-6                                  # 1 oz copper
SKIN = math.sqrt(RHO / (math.pi * F0 * MU0))                 # 17.7 um


def spiral_L(n, d_out, d_in):
    d_avg = (d_out + d_in) / 2; rho = (d_out - d_in) / (d_out + d_in)
    return MU0 * n * n * d_avg * 1.0 / 2 * (math.log(2.46 / rho) + 0.20 * rho * rho)


def coil(n_per_layer, d_out=20.6e-3, w=0.30e-3, s=0.20e-3, gap=0.8e-3):
    p = w + s
    d_in = d_out - 2 * n_per_layer * p + 2 * s
    L1 = spiral_L(n_per_layer, d_out, d_in)
    k = 0.62 * math.exp(-gap / (0.25 * (d_out + d_in) / 2))     # layer-to-layer coupling (ESTIMATE: ~0.5 at 0.8 mm)
    L = 2 * L1 * (1 + k)
    length = 2 * n_per_layer * math.pi * (d_out + d_in) / 2
    r_dc = RHO * length / (w * T_CU)
    r_ac = RHO * length / (2 * (w + T_CU) * SKIN) * 1.25        # skin effect + proximity (x1.25, ESTIMATE)
    return {"n_per_layer": n_per_layer, "d_out_mm": d_out * 1e3, "d_in_mm": round(d_in * 1e3, 2), "k": round(k, 3),
            "L_uH": round(L * 1e6, 3), "R_dc": round(r_dc, 2), "R_ac": round(r_ac, 2), "Q": round(W * L / r_ac, 1)}


def z_match(La, Ra, Cs, Cp, Rq, L0=2.2e-6, R0=0.25, C0=56e-12, Lw=25e-9):
    """Differential impedance seen by TX1-TX2: per side L0 -> (C0 to gnd) -> Cs -> (Cp to gnd) -> Rq -> antenna half."""
    jw = 1j * W
    Zant = (Ra + jw * (La + Lw)) / 2                          # half of the antenna (virtual ground at its centre)
    z = Rq + Zant
    z = 1 / (1 / z + jw * Cp)
    z = z + 1 / (jw * Cs)
    z = 1 / (1 / z + jw * C0)
    z = z + R0 + jw * L0
    return 2 * z


# the reference circuit (datasheet): Cs 22 pF, Cp 120 + 15 pF, Rq 0.33, C0 56 pF; its antenna from resonance
Cs_r, Cp_r, Rq_r = 22e-12, 135e-12, 0.33
La_r = 1 / (W * W * (Cp_r + Cs_r) / 2)                        # per-side caps -> differential antenna resonance
Ra_r = 1.0                                                     # a typical module antenna's loss (ESTIMATE)
Zt = z_match(La_r, Ra_r, Cs_r, Cp_r, Rq_r)
print(f"reference antenna (implied by the datasheet values): {La_r*1e6:.2f} uH; TX sees {Zt.real:.1f} {Zt.imag:+.1f}j ohm")

coils = [coil(n) for n in (3, 4, 5, 6)]
for c in coils:
    print("coil", c)
C_OK = {15: "C1548", 18: "C1549", 22: "C1555", 33: "C1562", 47: "C1567", 100: "C1546",              # JLC Basic
        10: "C32949", 27: "C1557", 39: "C1563", 56: "C1572", 68: "C190580", 82: "C45501", 120: "C40059", 150: "C12220", 180: "C78636"}
BASIC = {15, 18, 22, 33, 47, 100}
pairs = sorted(set([v for v in C_OK] + [a + b for a in C_OK for b in C_OK if a >= b]))
best = []
for c in coils:
    La, Ra = c["L_uH"] * 1e-6, c["R_ac"]
    for Cs in sorted(C_OK):
        for Cp in pairs:
            for Rq in (0.0, 0.5, 1.0, 1.5, 2.2):
                z = z_match(La, Ra, Cs * 1e-12, Cp * 1e-12, Rq, C0=47e-12)
                err = abs(z - Zt) / abs(Zt)
                Qtot = W * (La + 25e-9) / (Ra + 2 * Rq)
                best.append((err + 0.01 * abs(Qtot - 30) / 30, c["n_per_layer"], Cs, Cp, Rq, round(z.real, 1), round(z.imag, 1), round(Qtot, 1)))
best.sort()
print("\nbest matches (EMC C0 = 47 pF Basic):  score, turns/layer, Cs pF, Cp pF, Rq ohm, Z real, Z imag, Q")
for b in best[:12]:
    print("  ", b)
json.dump({"target_Z": [Zt.real, Zt.imag], "coils": coils, "best": best[:20]}, open(os.path.join(os.path.dirname(__file__), "nfc_design.json"), "w"), indent=1)
