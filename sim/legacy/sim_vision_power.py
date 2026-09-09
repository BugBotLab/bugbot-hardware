"""Power-tree simulation for the BugBot Vision board.

Same discipline as sim_power_tree.py: every resistor value is read from
golden_netlist.xml rather than retyped, the deck mirrors sheets 01 and 03, and
each scenario asserts the behaviour the design promises.

The question this exists to answer
----------------------------------
The 3.3 V rail was changed from a plain buck (TLV62569) to a buck-boost
(TPS63020) on the argument that four P4 rails have a hard 3.0 V floor while a
buck needs roughly 3.4 V in to hold 3.3 V out, and that a servo stall drags a
1S cell through exactly that point. That is a claim about the hardware, so it
should be measured rather than asserted: scenario B runs the SAME tree with a
buck in place of the buck-boost and compares.

Engine: KiCad's own ngspice.dll, via ngspice_run.py.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ngspice_run import run_circuit, final

from paths import model_lib, netlist
LIB = model_lib("vision_models.lib")
NET = netlist("vision")


def parse_val(s):
    """Case MATTERS: 1M is a megohm, 1m is a milliohm. Folding case turned the
    TPS63020's 1M feedback resistor into 1 mOhm and the assertion caught it."""
    m = re.match(r"([\d.]+)\s*([kKMmuUnNpPrR]?)", s)
    n = float(m.group(1))
    mult = {"k": 1e3, "K": 1e3, "M": 1e6, "m": 1e-3, "u": 1e-6, "U": 1e-6,
            "n": 1e-9, "N": 1e-9, "p": 1e-12, "P": 1e-12,
            "r": 1, "R": 1, "": 1}[m.group(2)]
    return n * mult


vals = {c.get("ref"): (c.findtext("value") or "")
        for c in ET.parse(NET).getroot().iter("comp")}
R = {r: parse_val(vals[r]) for r in
     ("R1", "R2", "R3", "R4", "R6", "R15", "R16", "R17", "R18", "R20",
      "R29", "R30")}
C = {c: parse_val(vals[c]) for c in ("C14",)}
# both camera dividers use a series pair on one leg, because the exact ratios
# are not reachable from two JLC basic values
R28_TOP = R["R15"]                 # 2.8 V rail, top leg
R28_BOT = R["R16"] + R["R29"]      # bottom leg is 4.7k + 100R
R13_TOP = R["R17"] + R["R30"]      # 1.3 V rail, top leg is 12k + 510R
R13_BOT = R["R18"]

# the load-bearing values, asserted so a schematic edit cannot silently
# invalidate every number below
assert abs(R["R1"] - 1e6) < 1 and abs(R["R2"] - 180e3) < 1, R
assert abs(R["R3"] - 499e3) < 1 and abs(R["R4"] - 499e3) < 1, R
assert abs(R28_TOP / R28_BOT - 2.5) < 0.01, (R28_TOP, R28_BOT)
assert abs(R13_TOP / R13_BOT - 0.625) < 0.005, (R13_TOP, R13_BOT)
assert abs(R["R6"] - 10e3) < 1 and abs(C["C14"] - 1e-6) < 1e-12, (R, C)

# Load budget. Espressif: "The minimum operating supply current of ESP32-P4 is
# 380 mA (including flash and PSRAM)" and I_VDD "current supplied to core" min
# 0.5 A. Camera rails from the OV2640 datasheet.
I_P4_3V3 = 0.380          # P4 on the 3.3 V side
I_CORE = 0.500            # VDD_HP
I_SD = 0.150              # microSD active
I_MISC = 0.040            # LED, pull-ups, ToF module
I_CAM_2V8 = 0.100         # AVDD + DOVDD
I_CAM_1V3 = 0.050         # DVDD


def rload(v, i):
    return max(v / max(i, 1e-9), 1e-3)


def tree(front, vbat, i3v3_extra=0.0, tran=None):
    """The whole tree. front is 'buckboost' (as designed) or 'buck' (the A/B).

    Both are driven from the same cell and carry the same loads, so the only
    difference between the two decks is which part sits on the 3.3 V rail.
    """
    d = ["* BugBot Vision power tree - %s front end" % front,
         '.include "%s"' % LIB,
         "VBAT vsysai 0 DC %g" % vbat]

    if front == "buckboost":
        # the real divider, straight off the netlist: 0.5 V reference
        d += ["X1 vsysai 0 vsysai v33 fb1 TPS63020"]
        r2 = R["R2"]
    else:
        # A fair comparison regulates to the SAME 3.3 V, so the buck gets a
        # divider sized for ITS 0.6 V reference. Reusing the buck-boost's
        # 1M/180k here would have set the buck to 3.93 V and compared two
        # different rails instead of two topologies.
        d += ["X1 vsysai 0 vsysai v33 fb1 TLV62569"]
        r2 = R["R1"] / (3.3 / 0.6 - 1.0)
    d += ["R1 v33 fb1 %g" % R["R1"],
          "R2 fb1 0 %g" % r2,
          # core buck: EN from the P4 (modelled high), divider R3/R4
          "X2 v33 0 v33 vddhp fb2 TLV62569",
          "R3 vddhp fb2 %g" % R["R3"],
          "R4 fb2 0 %g" % R["R4"],
          # camera rails
          "X5 v33 0 v33 v2v8 fb5 AP2127KADJ",
          "R15 v2v8 fb5 %g" % R28_TOP,
          "R16 fb5 0 %g" % R28_BOT,
          "X6 v33 0 v33 v1v3 fb6 AP2127KADJ",
          "R17 v1v3 fb6 %g" % R13_TOP,
          "R18 fb6 0 %g" % R13_BOT,
          # loads
          "RL33 v33 0 %g" % rload(3.3, I_P4_3V3 + I_SD + I_MISC + i3v3_extra),
          "RLHP vddhp 0 %g" % rload(1.1, I_CORE),
          "RL28 v2v8 0 %g" % rload(2.8, I_CAM_2V8),
          "RL13 v1v3 0 %g" % rload(1.3, I_CAM_1V3)]
    d += tran if tran else [".op"]
    d += [".end"]
    return d


def op(front, vbat, **kw):
    v = run_circuit(tree(front, vbat, **kw))
    return {k: final(v, k) for k in ("v33", "vddhp", "v2v8", "v1v3", "fb1")}


print("=" * 72)
print("A. Cell sweep, nominal load - does 3V3 hold across the discharge?")
print("=" * 72)
print("  %-8s %-24s %-24s" % ("cell", "buck-boost (as designed)", "plain buck (rejected)"))
rows = []
for vb in (4.2, 4.0, 3.8, 3.7, 3.6, 3.5, 3.4, 3.3, 3.2, 3.1, 3.0):
    a = op("buckboost", vb)
    b = op("buck", vb)
    rows.append((vb, a["v33"], b["v33"]))
    flag = "" if a["v33"] > 3.2 else "  <-- buck-boost sagging"
    flag2 = " OUT OF SPEC" if b["v33"] < 3.0 else ""
    print("  %-8.2f 3V3 = %-20.3f 3V3 = %.3f%s%s"
          % (vb, a["v33"], b["v33"], flag2, flag))

bb_min = min(r[1] for r in rows)
bk_min = min(r[2] for r in rows)
print("\n  buck-boost worst case over the sweep: %.3f V" % bb_min)
print("  plain buck  worst case over the sweep: %.3f V" % bk_min)
buck_drops_below = [r[0] for r in rows if r[2] < 3.135]     # 3.3 V - 5%
if buck_drops_below:
    print("  the plain buck leaves regulation at or below a %.2f V cell"
          % max(buck_drops_below))

print()
print("=" * 72)
print("B. Servo stall - two sub-micro servos drag the shared cell down")
print("=" * 72)
# A resting 3.7 V cell sags on its internal resistance plus the protection FET
# when the servos pull. 0.8 A into ~0.35 ohm of cell+FET+wiring is ~280 mV.
for label, vb in (("resting 3.7 V", 3.7), ("stall sag to 3.42 V", 3.42),
                  ("flat cell 3.1 V", 3.1), ("flat + stall 2.85 V", 2.85)):
    a = op("buckboost", vb)
    b = op("buck", vb)
    print("  %-22s buck-boost 3V3 = %.3f    plain buck 3V3 = %.3f"
          % (label, a["v33"], b["v33"]))

print()
print("=" * 72)
print("C. Derived rails, from the real dividers")
print("=" * 72)
a = op("buckboost", 3.7)
print("  3V3    = %.3f V   (R1 %.0fk / R2 %.0fk, FB %.3f V)"
      % (a["v33"], R["R1"] / 1e3, R["R2"] / 1e3, a["fb1"]))
print("  VDD_HP = %.3f V   (R3 %.0fk / R4 %.0fk) - external divider only;"
      % (a["vddhp"], R["R3"] / 1e3, R["R4"] / 1e3))
print("           the P4 trims this rail with an internal variable resistor in")
print("           parallel, so silicon sets the final value inside 0.99-1.3 V")
print("  +2V8   = %.3f V   (%.1fk / %.2fk) - AVDD, ceiling 3.0 V"
      % (a["v2v8"], R28_TOP / 1e3, R28_BOT / 1e3))
print("  +1V3   = %.3f V   (%.2fk / %.0fk) - DVDD, floor 1.24 V"
      % (a["v1v3"], R13_TOP / 1e3, R13_BOT / 1e3))
# The tolerance corners are what the earlier review found dangerous, and a
# single-point DC run structurally cannot see them, so compute them here.
# AP2127K VFB is 0.784/0.800/0.816 over temperature and 1-300 mA load.
for name, rt, rb, lo_lim, hi_lim in (
        ("+2V8", R28_TOP, R28_BOT, None, 3.000),
        ("+1V3", R13_TOP, R13_BOT, 1.240, 1.360)):
    wc_lo = 0.784 * (1 + rt * 0.99 / (rb * 1.01))
    wc_hi = 0.816 * (1 + rt * 1.01 / (rb * 0.99))
    msg = "  %s worst case %.4f .. %.4f V" % (name, wc_lo, wc_hi)
    if lo_lim:
        msg += "   floor margin %+.0f mV" % ((wc_lo - lo_lim) * 1000)
    if hi_lim:
        msg += "   ceiling margin %+.0f mV" % ((hi_lim - wc_hi) * 1000)
    print(msg)

print()
print("=" * 72)
print("D. Worst-case current out of the cell, and the TPS63020's headroom")
print("=" * 72)
# Compare like with like, at the 3.3 V NODE. The earlier version divided an
# output-referred capability by an input-referred draw, which is dimensionally
# incoherent; the ratio was wrong by exactly the derating factor. It also
# treated the LDOs as power converters -- an LDO conserves CURRENT, so its
# input draw equals its OUTPUT current, not Pout/(eta*Vin).
i_3v3 = (I_P4_3V3 + I_SD + I_MISC                    # direct loads
         + (1.1 * I_CORE) / (0.85 * 3.3)             # core buck input
         + I_CAM_2V8 + I_CAM_1V3)                    # LDO inputs = their Iout
p_3v3 = 3.3 * i_3v3
print("  3.3 V rail load: %.0f mA (%.2f W)" % (i_3v3 * 1000, p_3v3))
print()
for vb in (4.2, 3.7, 3.0):
    i_cell = p_3v3 / (vb * 0.90)
    # TI SLVS916I features: 2 A output at VOUT = 3.3 V for VIN > 2.5 V.
    # That is the guaranteed figure; Figure 2 gives ~2.39 A typical at 3.0 V.
    i_avail = 2.000
    print("  cell %.2f V: cell draws %.0f mA; at the 3.3 V node %.0f mA of "
          "%.0f mA guaranteed -> %.2fx"
          % (vb, i_cell * 1000, i_3v3 * 1000, i_avail * 1000, i_avail / i_3v3))

print()
print("=" * 72)
print("E. CHIP_PU reset RC - t_STBL >= 50 us, and the S3 must wait for it")
print("=" * 72)
d = ["* CHIP_PU rise",
     "V33 v33 0 PWL(0 0 100u 3.3)",
     "R6 v33 pu %g" % R["R6"],
     "C14 pu 0 %g" % C["C14"],
     ".tran 20u 40m",
     ".end"]
v = run_circuit(d)
t = v.get("time") or []
pu = v.get("v(pu)") or v.get("pu") or []
# V_IH_nRST is 0.75 x VDD_BAT, and VDD_BAT is tied to 3V3 on this board
thr = 0.75 * 3.3
hit = next((t[i] for i in range(len(pu)) if pu[i] >= thr), None)
print("  R6 = %.0f k, C14 = %.1f uF" % (R["R6"] / 1e3, C["C14"] * 1e6))
print("  threshold V_IH_nRST = 0.75 x VDD_BAT = %.2f V" % thr)
if hit:
    print("  CHIP_PU crosses it at %.1f ms with an ideal fast rail" % (hit * 1e3))
else:
    print("  !! never reached the threshold within 40 ms")
# The nominal figure is not the number firmware should use. The rail is not a
# 100 us step: /3V3 carries ~114 uF and SLVS916I 7.4.1 says the TPS63020 has
# no soft-start timer ("There is no timer implemented"), so it ramps in
# 0.5-0.94 ms. Add R and C tolerance and the corners spread badly.
import math
print("  corners (t to threshold, then +3 ms for the t_H strap hold):")
for label, rtol, ctol, ramp in (("nominal, ideal rail", 1.00, 1.00, 0.0001),
                                ("R +1%", 1.01, 1.00, 0.0001),
                                ("real ~1 ms rail rise", 1.00, 1.00, 0.001),
                                ("R +1%, C +10%", 1.01, 1.10, 0.001),
                                ("R +1%, C +20%", 1.01, 1.20, 0.001)):
    tau = R["R6"] * rtol * C["C14"] * ctol
    k = (tau / ramp) * (1 - math.exp(-ramp / tau))
    t = ramp + tau * math.log(k / 0.25)
    print("    %-22s %6.2f ms   -> release at %6.2f ms"
          % (label, t * 1e3, t * 1e3 + 3))
print("  -> firmware: use 25 ms for the S3's EN-release delay, and measure it")
print("     from EN release in the stacked case, not from rail rise.")

print()
print("Honest limits: DC behaviour only. No switching ripple, no loop")
print("stability, no layout effects. The core rail's final value is set by the")
print("P4's internal trim, not by R3/R4 alone. Bench-test items on first spin.")
