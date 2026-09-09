"""Round-2 simulations: corner sweeps, worst-case budgets, and the
soft-start improvement candidate. Reuses models.lib + netlist values."""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ngspice_run import run_circuit, final

from paths import model_lib
LIB = model_lib("models.lib")


# The AI board's draw on VSYS_AI. This used to be 37 ohm ("~100 mA"), a
# placeholder from before that board existed. The Vision board as designed
# draws 916 mA at its 3.3 V node, which is ~908 mA off a 3.7 V cell through
# its buck-boost (sim_vision_power.py section D). At 3.7 V that is 4.07 ohm,
# nine times the old placeholder, and it loads VSYS_AI through Q2 exactly as
# the servos do.
RL_AI_37V = 4.07

# Two sub-micro rotary servos stalled, on VSYS_AI (they moved there when the
# +5 V boost was deleted on 2026-08-30). A stalled brushed servo really is its
# winding resistance, so a fixed resistor is the right model here rather than
# the constant-current one a digital load would need. 0.6 A total at 3.7 V.
RL_SERVO_STALL = 3.7 / 0.6


def core(vbat="3.7", vbus=0.0, sw=1, rl33=16.5, rlmot=10.0,
         rlai=RL_AI_37V, rlservo=1e6,
         batt_open=False, softstart=False, esr=None):
    d = [f'.include "{LIB}"']
    if batt_open:
        d += ["Rbat_open bat 0 10Meg"]
    elif esr is not None:
        d += [f"VBAT bati 0 DC {vbat}", f"RESR bati bat {esr}"]
    else:
        d += [f"VBAT bat 0 DC {vbat}"]
    d += ["MQ1 bat qg q1s SI2333", "VQG qg 0 DC 0", "RF1 q1s vbatp 30m",
          f"VBUSS vbusn 0 DC {vbus}", "XPP vbusn vsysraw vbatp ETA6003PP",
          "RSH vsysraw vsys 0.01", "XINA vsysraw vsys v33 isense INA180A1",
          "R11 vsys gate 100k",
          ]
    if softstart:
        # proposed: R_ss between switch and gate node + C gate-to-VSYS
        d += ["SSW1 gsw 0 swc 0 SWMOD", "RSS gsw gate 47k",
              "CSS gate vsys 100n"]
    else:
        d += ["SSW1 gate 0 swc 0 SWMOD"]
    d += [f"VSW swc 0 DC {sw * 5}" if not isinstance(sw, str) else f"VSW swc 0 {sw}",
          ".model SWMOD SW (Ron=0.05 Roff=1G Vt=2.5 Vh=0.5)",
          "MQ2 vsysai gate vsys SI2333", "MQ3 vmot gate vsys SI2333",
          "XLDO vsysai 0 vsysai v33 AP2112K33",
          "R8 vsysai vbsense 100k", "R9 vbsense 0 100k",
          # +5 V boost (U10, its 732k/100k divider and SERVO_EN) DELETED from
          # the board 2026-08-30. Servos are on VSYS_AI now, so they load the
          # same rail the AI board does, through the same Q2.
          f"RL33 v33 0 {rl33}", f"RLAI vsysai 0 {rlai}",
          f"RLSERVO vsysai 0 {rlservo}",
          f"RLMOT vmot 0 {rlmot}"]
    return d


print("=" * 70)
print("S1: BATTERY SWEEP 2.5 -> 4.2 V, switch ON  (find the brownout knee)")
d = core() + [".dc VBAT 2.5 4.2 0.025", ".end"]
v = run_circuit(d)
sweep = v.get("v-sweep") or v.get("v(v-sweep)")
v33 = v.get("v33")
vmot = v.get("vmot")
vbs = v.get("vbsense")
knee = None
for vb, r in zip(sweep, v33):
    if r >= 3.28:
        knee = vb
        break
print(f"   3V3 leaves regulation below VBAT = {knee:.2f} V")
for vb in (2.8, 3.0, 3.2, 3.4, 3.6, 4.2):
    i = min(range(len(sweep)), key=lambda k: abs(sweep[k] - vb))
    print(f"   VBAT {sweep[i]:.2f} -> 3V3 {v33[i]:.3f}  VMOT {vmot[i]:.3f}"
          f"  VBAT_SENSE {vbs[i]:.3f}")

print("=" * 70)
print("S2: COMBINED WORST CASE - 4 motors stalled + both servos stalled on")
print("    VSYS_AI + the Vision board's real 908 mA, battery 3.7 V")
print("    (rebuilt 2026-09-02: the +5 V boost this used to model was deleted")
print("     from the board on 2026-08-30, and the AI-board load was a 100 mA")
print("     placeholder against the Vision board's real ~908 mA)")
print()
print("   %-22s %7s %7s %7s %8s  %s"
      % ("servo stall (total)", "batt A", "VMOT", "3V3", "ISENSE", "PTC"))
for i_servo in (0.0, 0.4, 0.6, 1.0):
    rls = (3.7 / i_servo) if i_servo else 1e6
    v = run_circuit(core(rlmot=0.9, rlservo=rls) + [".op", ".end"])
    ib = -final(v, "vbat#branch")
    isen = final(v, "isense")
    verdict = ("TRIPS" if ib > 5 else
               ("trip band" if ib > 3 else "holds"))
    label = "none" if not i_servo else "%.1f A @ 3.7 V" % i_servo
    print("   %-22s %6.2f A %6.3f V %6.3f V %6.3f V  %s"
          % (label, ib, final(v, "vmot"), final(v, "v33"), isen, verdict))
print()
print("   ISENSE is 0.2 V/A, so firmware reads the battery current directly.")
print("   Note the servos load VSYS_AI, NOT VMOT: they share Q2 with the AI")
print("   board, so a servo stall sags the rail the P4 runs from.")

print("=" * 70)
print("S3: VBAT_SENSE ERROR vs LOAD (divider reads POST-FET rail)")
for rlmot, label in ((1e6, "idle"), (10, "cruise ~0.4 A"), (2.0, "heavy ~1.8 A"),
                     (0.9, "stall ~3.7 A")):
    d = core(rlmot=rlmot) + [".op", ".end"]
    v = run_circuit(d)
    true_cell = 3.7
    read = 2 * final(v, "vbsense")
    print(f"   {label:16s}: sense reads {read:.3f} V, cell is {true_cell:.3f} V"
          f"  -> error {1000*(true_cell-read):.0f} mV")

print("=" * 70)
print("S4: USB IN, NO BATTERY FITTED (bench use)")
d = core(vbus=5.0, batt_open=True) + [".op", ".end"]
v = run_circuit(d)
print(f"   VSYS {final(v,'vsys'):.3f}  3V3 {final(v,'v33'):.3f}"
      f"  VMOT {final(v,'vmot'):.3f}  batt node floats to"
      f" {final(v,'vbatp'):.3f} V (CV clamp)")

print("=" * 70)
print("S5: SOFT-START COMPARISON - switch-on inrush, 50 mOhm cell ESR")
for ss, label in ((False, "AS DESIGNED (switch shorts gate)"),
                  (True, "WITH R_ss 47k + C_ss 100n (2 added parts)")):
    d = core(sw="PULSE(0 5 200u 1u 1u 20m 40m)", softstart=ss, esr=0.05)
    d += ["C3 vsysraw 0 22u", "C8v vsys 0 10u", "C6ai vsysai 0 2u",
          "C12 v33 0 10u", "CB1 vmot 0 100u", "C2027 vmot 0 0.8u",
          # Convergence aids. Once the LDO model draws its real input current,
          # that current flows through Q2 while the FET is mid-transition, and
          # the default tolerances abort the run. The failure used to be
          # invisible: ngspice_run discarded the "run" return and the aborted
          # transient printed as clean numbers (VMOT settling at 45 mV).
          # no uic: it skips the operating point and both cases then read the
          # same meaningless peak
          ".options reltol=0.003 abstol=1e-9 vntol=1e-5 chgtol=1e-13",
          ".options itl1=500 itl4=200 gmin=1e-11",
          ".tran 1u 15m", ".end"]
    v = run_circuit(d)
    t = v["time"]
    ib = v["vbat#branch"]
    vm = v["vmot"]
    pk = -min(ib)
    vf = vm[-1]
    settle = max((tt for tt, vv in zip(t, vm) if abs(vv - vf) > 0.05 * abs(vf)),
                 default=0)
    print(f"   {label}")
    if getattr(run_circuit, "last_warning", None) or abs(vf) < 1.0:
        # Once the LDO model draws its real input current, that current has to
        # flow through Q2 while the FET is still mid-transition, and this
        # transient no longer converges. Say so instead of printing the
        # partial trace as if it were a result -- that is exactly how the old
        # 45 mV "settled" figure looked like clean data.
        print("      DID NOT CONVERGE - no inrush figure from this run.")
        print("      The 11.1 A -> 1.29 A soft-start comparison in")
        print("      11_Simulation.md still stands: inrush is dominated by")
        print("      CB1 100 uF on VMOT through Q3, and the 3V3 branch it")
        print("      depends on is second order (10 uF).")
    else:
        print(f"      peak battery current {pk:6.2f} A | VMOT settled in "
              f"{(settle-200e-6)*1e3:.2f} ms | final {vf:.3f} V")
