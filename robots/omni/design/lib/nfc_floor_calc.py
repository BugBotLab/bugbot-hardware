# The NFC floor loop's read range, worked out from the parts instead of assumed (no hardware to test on):
#   WS1850S transmitter (datasheet design/lib/datasheets/WS1850S_C2686218.pdf, 3.3 V column: TX output resistance 25 ohm,
#   ITVDD 60 typ / 110 max mA, RX sensitivity 0.5 mVrms at the 848 kHz subcarrier)
#   -> the reader board's matching network (design/lib/make_nfc_boards.py: per side L0 2.2 uH, C0 47 pF, Cs 47 pF,
#      Cp 68 + 22 pF, Rq 2.2 ohm), and retuned values for the big loop
#   -> the floor PCB loop (kicad/BugBot_NFCfloor: 3 turns round the edge, 779.6 mm of 0.18 mm 1 oz copper, 2.42 uH)
#   -> its field at a tag lying on the floor (Biot-Savart, the sim's own NfcReader maths)
#   -> the on-axis read range the sim takes (range_mm), the read zone, and a check on the tag's reply.
# Every number that is still an estimate is marked ESTIMATE; the spread over them is printed.
#   C:/Python312/python.exe design/lib/nfc_floor_calc.py
import math, json, os, sys, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
F0 = 13.56e6; W = 2 * math.pi * F0; MU0 = 4e-7 * math.pi
TVDD, R_TX = 3.3, 25.0                                # datasheet 3.3 V column
ITVDD_MAX = 0.110                                     # A, datasheet max (continuous carrier, 3.3 V)
H_MIN = 1.5                                           # A/m rms, ISO 14443 minimum operating field
GAP = 6.45e-3                                         # loop (top copper of the floor PCB) to a tag lying on the floor

# ---- the loop
N_LOOP, R_LOOP = 3, 0.0395                            # 3 turns round the edge, ~79 mm across (as the sim's "d79")
L_LOOP = 2.42e-6                                      # computed when the floor PCB was designed
L_CABLE = 0.10e-6                                     # the 2-wire cable reader -> loop (ESTIMATE: ~10 cm of twisted pair)
RHO, T_CU = 1.72e-8, 35e-6
SKIN = math.sqrt(RHO / (math.pi * F0 * MU0))
LEN, TW = 0.7796, 0.18e-3
R_DC = RHO * LEN / (TW * T_CU)
R_AC = max(R_DC, RHO * LEN / (2 * (TW + T_CU) * SKIN) * 1.25)   # skin + proximity x1.25 (ESTIMATE)


def tx_current(Cs, Cp, Rq, La=L_LOOP + L_CABLE, Ra=None, C0=47e-12, L0=2.2e-6, R0=0.25):
    """Half circuit (each TX pin drives one side against the loop's virtual centre): the TX pin a square wave 0..TVDD,
    its fundamental 2/pi x TVDD peak (sqrt 2 / pi x TVDD rms) behind R_TX. Returns (loop current rms, supply current,
    loaded Q, the antenna node voltage rms)."""
    Ra = R_AC if Ra is None else Ra
    jw = 1j * W
    za = Rq + (Ra + jw * La) / 2                      # half the loop (+ the damping R)
    zb = 1 / (1 / za + jw * Cp)
    zc = zb + 1 / (jw * Cs)
    zd = 1 / (1 / zc + jw * C0)
    zin = zd + R0 + jw * L0
    v = math.sqrt(2) / math.pi * TVDD                 # rms of the fundamental, per side
    i_in = v / (R_TX + zin)
    vd = i_in * zd                                    # node after L0
    i_c = vd / zc                                     # through Cs
    vb = i_c * zb
    i_ant = vb / za
    p = 2 * (abs(i_in) ** 2) * (R_TX + zin.real)      # both sides, W (fundamental)
    i_sup = p / TVDD / 0.81                           # a square-wave driver: ~81 % of its power in the fundamental (ESTIMATE)
    q = W * La / (Ra + 2 * Rq)
    return abs(i_ant), i_sup, q, abs(vb)


# ---- the field (the sim's NfcReader geometry: the loop as one circle, the tag's coil sampled)
sys.path.insert(0, os.path.join(HERE, "..", "..", "simlink", "SimLink", "simlink", "sim"))
LOOP = np.array([[R_LOOP * math.cos(2 * math.pi * k / 64), R_LOOP * math.sin(2 * math.pi * k / 64), 0] for k in range(65)])
TAG_D = 21e-3                                         # NTAG213 25 mm coin: its coil ~21 mm across (ESTIMATE)
r_ = TAG_D / 2
DISC = [(0.0, 0.0)] + [(f * r_ * math.cos(2 * math.pi * k / n), f * r_ * math.sin(2 * math.pi * k / n))
                       for f, n in ((0.35, 6), (0.65, 12), (0.9, 18)) for k in range(n)]
DISC = np.array(DISC)


def field(P, I):
    """H (A/m) at points P from current I in the loop polygon (Biot-Savart per segment), per turn."""
    H = np.zeros_like(P, dtype=float)
    for k in range(len(LOOP) - 1):
        A, B = LOOP[k], LOOP[k + 1]
        L = B - A; u = L / np.linalg.norm(L)
        r1, r2 = P - A, P - B
        t = r1 @ u
        perp = r1 - np.outer(t, u); dist = np.linalg.norm(perp, axis=1) + 1e-12
        c1 = t / (np.linalg.norm(r1, axis=1) + 1e-12); c2 = (r2 @ u) / (np.linalg.norm(r2, axis=1) + 1e-12)
        mag = I / (4 * math.pi * dist) * (c1 - c2)
        H += np.cross(np.tile(u, (len(P), 1)), perp / dist[:, None]) * mag[:, None]
    return H


def tag_field(x, z, I_turns):
    """Mean field along the tag's normal over its coil, a flat tag at x off the centre, z below the loop."""
    P = np.c_[DISC[:, 0] + x, DISC[:, 1], np.full(len(DISC), -z)]
    return abs(float(np.mean(field(P, I_turns)[:, 2])))


def on_axis_range(I_turns, detune):
    """How far straight down a flat tag still powers up (what the sim calls range_mm)."""
    lo, hi = 0.0, 0.2
    if tag_field(0, 0.0005, I_turns) * detune < H_MIN:
        return 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if tag_field(0, mid, I_turns) * detune >= H_MIN:
            lo = mid
        else:
            hi = mid
    return lo


def zone(I_turns, detune, z=GAP):
    xs = np.arange(0, 0.0451, 0.0025)
    h = [tag_field(x, z, I_turns) * detune / H_MIN for x in xs]
    ok = [x for x, v in zip(xs, h) if v >= 1.0]
    return (min(ok) * 1000, max(ok) * 1000) if ok else None, h, xs


# ---- the tag's reply (load modulation), order of magnitude
N_TAG, L_TAG = 5, 2.8e-6                              # NTAG213 inlay: ~5 turns, resonant with its ~50 pF (ESTIMATE)
Q_TAG_LOADED, MOD_DEPTH = 6.0, 0.2                    # loaded Q of the tag at threshold, its modulation depth (ESTIMATE)
RX_GAIN = 0.3                                         # antenna node -> RX pin through R1 5.1k / C3 15 pF / R3 (ESTIMATE)
RX_SENS = 0.5e-3                                      # V rms, datasheet


def reply_at_rx(x, z, I_turns):
    """The tag's subcarrier at the RX pin (V rms): its coil current x the modulation depth, coupled back through the
    mutual inductance (the field one amp in the loop makes through the tag) and down the receive divider."""
    h_tag = tag_field(x, z, I_turns)                  # A/m at the tag
    a_tag = math.pi * (TAG_D / 2) ** 2
    emf = W * MU0 * h_tag * a_tag * N_TAG
    i_tag = emf * Q_TAG_LOADED / (W * L_TAG)
    m = MU0 * tag_field(x, z, N_LOOP * 1.0) * a_tag * N_TAG     # H per amp in the loop
    return W * m * i_tag * MOD_DEPTH * RX_GAIN


if __name__ == "__main__":
    out = {}
    print(f"loop: {N_LOOP} turns, R_dc {R_DC:.2f} ohm, R_ac {R_AC:.2f} ohm, L {L_LOOP * 1e6:.2f} + cable {L_CABLE * 1e6:.2f} uH")
    # the board as built (tuned for the old 22 mm coil)
    asb = tx_current(47e-12, 90e-12, 2.2)
    print(f"as built (Cs 47, Cp 90 pF, Rq 2.2): loop {asb[0] * 1000:.1f} mA rms, supply ~{asb[1] * 1000:.0f} mA, Q {asb[2]:.0f}")
    # retuned for the big loop: JLC values, supply within the datasheet's max, Q low enough for 106 kbit/s (<= 35)
    vals = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82, 100, 120, 150, 180]
    cps = sorted(set(vals + [a + b for a in vals for b in vals if a >= b and a + b <= 300]))
    best = None
    for cs, cp, rq in itertools.product(vals, cps, (0.0, 0.5, 1.0, 1.5, 2.2, 3.3)):
        ia, isup, q, vb = tx_current(cs * 1e-12, cp * 1e-12, rq)
        if isup > 0.9 * ITVDD_MAX or q > 35 or q < 12:
            continue
        if best is None or ia > best[0]:
            best = (ia, cs, cp, rq, isup, q)
    ia, cs, cp, rq, isup, q = best
    print(f"retuned (Cs {cs}, Cp {cp} pF, Rq {rq}): loop {ia * 1000:.1f} mA rms, supply ~{isup * 1000:.0f} mA "
          f"(max {ITVDD_MAX * 1000:.0f}), Q {q:.0f}")
    out["as_built"] = {"loop_mA": asb[0] * 1000, "supply_mA": asb[1] * 1000, "Q": asb[2]}
    out["retuned"] = {"Cs_pF": cs, "Cp_pF": cp, "Rq": rq, "loop_mA": ia * 1000, "supply_mA": isup * 1000, "Q": q}
    # the spread: loop resistance, metal detuning, the driver's real strength
    print("\nread range and zone (flat tag on the floor, 6.45 mm below the loop):")
    rows = []
    for label, cfg in (("as built", (47e-12, 90e-12, 2.2)), ("retuned", (cs * 1e-12, cp * 1e-12, rq))):
        for ra_k, det, drv in itertools.product((0.8, 1.0, 1.3), (0.6, 0.8, 1.0), (0.7, 1.0)):
            I = tx_current(*cfg, Ra=R_AC * ra_k)[0] * drv
            rng = on_axis_range(N_LOOP * I, det) * 1000
            zn, h, xs = zone(N_LOOP * I, det)
            rows.append((label, ra_k, det, drv, I * 1000, rng, zn, h[0]))
    for label in ("as built", "retuned"):
        rs = [r for r in rows if r[0] == label]
        mid = next(r for r in rs if r[1] == 1.0 and r[2] == 0.8 and r[3] == 1.0)
        rng_all = sorted(r[5] for r in rs)
        print(f"  {label:8s}: most likely {mid[4]:.0f} mA in the loop -> range {mid[5]:.0f} mm on axis; reads "
              f"{'%.0f-%.0f mm from the centre' % mid[6] if mid[6] else 'NOWHERE'} (centre {mid[7]:.2f} x needed). "
              f"Over the spread: range {rng_all[0]:.0f}-{rng_all[-1]:.0f} mm; zone empty in "
              f"{sum(1 for r in rs if r[6] is None)}/{len(rs)} cases")
        key = label.replace(" ", "_"); out[key]["range_mm_likely"] = mid[5]; out[key]["range_mm_spread"] = [rng_all[0], rng_all[-1]]
        out[key]["zone_mm_likely"] = mid[6]
    # the reply at the edge of the powered zone (the weakest place a tag still powers up)
    I = ia * 1.0
    worst = []
    for x in np.arange(0, 0.0451, 0.0025):
        if tag_field(x, GAP, N_LOOP * I) * 0.8 >= H_MIN:
            worst.append((reply_at_rx(x, GAP, N_LOOP * I * 0.8) / RX_SENS, x * 1000))
    if worst:
        mn = min(worst)
        print(f"\nreply (retuned, likely case): weakest where the tag powers up: {mn[0]:.1f} x the RX sensitivity "
              f"(at {mn[1]:.0f} mm) - {'the power-up limit governs' if mn[0] > 2 else 'the REPLY may limit the range'}")
        out["reply_margin_min"] = mn[0]
    json.dump(out, open(os.path.join(HERE, "nfc_floor_calc.json"), "w"), indent=1, default=float)
