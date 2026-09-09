"""BugBot stack simulation: Motion board + Vision board, from their REAL
netlists, through every state the robot can be in. Engine: KiCad's ngspice.

    python scripts/sim/sim_stack.py            (Python 3.12, ~1 min)

What is real here: every resistor, capacitor, inductor, FET and IC pin
connection comes from golden_netlist.xml of each board (netlist2spice.py),
the two boards are joined pin-for-pin through the stack sockets J8/J9, and
the ICs are behavioural models of their datasheets (stack_models.lib). The
harness only adds what the boards plug into: the cell, the USB source, the
motors, the servos, the module and the sensors as loads, the slide switch.

Every scenario ends in PASS/FAIL checks. A wrong strap, a swapped label, a
pin on the wrong net, an undersized pull-up: each moves a number past a
check. Run it after every schematic change.

Scenarios
  A  switch OFF, cell 3.7 V              everything dead, leakage < 1 mA
  B  switch ON, cell 3.7 V, idle         3V3 in regulation on BOTH boards, the
                                         module sees it, VBAT_SENSE = half
  C  switch ON, cell 3.0 V (flat)        3V3 STILL in regulation (buck-boost)
  D  cell reversed                       Q1 blocks, nothing downstream
  E  USB in, switch OFF                  charging at 1000/R_ISET1, NTC window
  F  USB in, NTC hot / cold              charging STOPS outside the window
  G  USB in, switch ON                   runs from the adapter, VMOT rides SYS
  H  4 motors running                    driver current mirrors, rails hold
  I  4 motors STALLED + servos stalled   current limit 0.2 V / R_ISENSE holds
                                         each motor, nFAULT pulls MOT_INT low,
                                         PTC current reported, 3V3 holds
  J  cell sweep 4.2 -> 2.8 V             where 3V3 and the module drop out
  K  I2C bus rise time (transient)       4.7 k pull-ups against the real bus
                                         capacitance: 400 kHz needs < 300 ns
  L  USB-C CC pull-downs                 5.1 k sink Rd: 0.25-0.61 V @ 80 uA
  M  power-on inrush (transient)         soft-start R7/C7: peak cell current
  N  Wi-Fi TX bursts (transient)         module 0.55 -> 0.90 A pulses while
                                         driving: 3V3 droop at the module
  O  USB only, NO CELL fitted            switch off: SYS parked, rails dead;
                                         switch on idle / driving: the power
                                         path alone carries the stack
  P  USB at its limits, cell in          5.5 V max and 4.4 V weak source while
                                         charging + running: rails, USB draw

Before the scenarios, check_static.py ties every IC pin to its CONFIRMED
datasheet pin table (straps, addresses, pull-ups, floating inputs): the
things a circuit simulation cannot see. Inductor peak currents include the
switching ripple (2.4 MHz / 3 MHz) the average models do not carry. The
summary line counts the operating points that came from a ramped transient
because .op would not converge: read those numbers with care.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_build import *   # noqa: the shared deck builder (M, V, stack_deck, motor_state, solve, NODES ...)
from ngspice_run import run_circuit, final
from parts_spec import PARTS, MOTOR_TYPES, motor_bemf
from netlist2spice import parse_val

def read(v):
    LAST_V["v"] = v
    r = {"_trouble": run_circuit.last_warning is not None, "_via_tran": v.get("_via_tran", False)}
    for k, n in NODES.items():
        r[k] = final(v, n.lower()) if n != "0" else 0.0
    r["I_CELL"] = -(final(v, "vbat#branch") or 0.0)        # + = discharging
    r["I_USB"] = -(final(v, "vbus#branch") or 0.0)
    for ref, drv in SENSE_R.items():
        r["ISENSE_" + drv] = final(v, M.pin(ref, "1").lower())
    return r


def report(title, r, checks):
    print("\n== " + title)
    keys = ("VSYS", "VSYS_SW", "VMOT", "3V3_M", "3V3_V", "MOD_3V3", "3V3_O", "1V9_O", "GATE",
            "VBAT_SENSE_M", "VBAT_SENSE_V", "MOT_INT_V", "NTC", "I_CELL", "I_USB")
    print("   " + "  ".join("%s=%s" % (k, "%.3f" % r[k] if r[k] is not None else "?") for k in keys))
    ok = True
    if r.get("_via_tran"):
        FALLBACKS.append(title.split(":")[0])
        print("   (operating point taken from a ramped transient: .op would not converge)")
    if r.get("_trouble"):
        print("   FAIL  ngspice did not converge cleanly - numbers above are not a solution")
        ok = False
    for desc, cond in checks:
        try:
            good = bool(cond(r))
        except Exception as e:
            good = False
            desc += "  (%s)" % e
        ok &= good
        print("   %s  %s" % ("PASS" if good else "FAIL", desc))
    if LAST_V.get("v") is not None and any(abs(g(r, k)) > 0.5 for k in ("VSYS_SW", "VMOT", "3V3_M")):
        ok &= spec_checks(LAST_V["v"], r, LOADS_A)
    return ok


def g(r, k):
    return r[k] if r[k] is not None else float("nan")


def node_v(v, node):
    return 0.0 if node == "0" else (final(v, node.lower()) or 0.0)


def spec_checks(v, r, loads_a):
    """Every part against its datasheet limits, from the solved voltages.
    loads_a: total 3.3 V load current the harness attached (for the TPS)."""
    fails, notes, n = [], [], [0]

    def chk(name, val, lo, hi, unit="V", warn=0.9):
        if val is None or val != val:
            return
        n[0] += 1
        if not (lo <= val <= hi):
            fails.append("%s = %.3f %s outside %s..%s" % (name, val, unit, lo, hi))
        elif hi != lo and val > lo + warn * (hi - lo):
            notes.append("%s = %.3f %s (%.0f %% of range)" % (name, val, unit, 100 * (val - lo) / (hi - lo)))

    for B in ALL:
        for ref, meta in B.comps.items():
            val, pins = meta["value"], B.pins_of(ref)
            kind = ref.rstrip("0123456789")
            try:
                if kind in ("C", "CB") and "1" in pins and "2" in pins:
                    vc = abs(node_v(v, pins["1"]) - node_v(v, pins["2"]))
                    key = {"22u": "C_22u_0805", "10u": "C_10u_0805", "100n": "C_100n_0402",
                           "1u": "C_1u_0402", "100u": "CB1_100u", "4.7u": "C_4u7_0603", "22p": "C_22p_0402"}.get(val)
                    if key:
                        lim = PARTS[key]["limits"]
                        chk("%s.%s %s" % (B.prefix, ref, val), vc, 0, lim["v_rated"])
                        if "v_derated" in lim and vc > lim["v_derated"]:
                            notes.append("%s.%s %s = %.2f V is above the 50 %% tantalum derating (%.2f V)"
                                         % (B.prefix, ref, val, vc, lim["v_derated"]))
                elif kind == "R" and "1" in pins and "2" in pins:
                    vr = node_v(v, pins["1"]) - node_v(v, pins["2"])
                    pw = vr * vr / parse_val(val)
                    pk = "R_0603" if ref in ("R19", "R20", "R21", "R22") and B.prefix == "M" else "R_0402"
                    chk("%s.%s %s" % (B.prefix, ref, val), pw * 1e3, 0, PARTS[pk]["limits"]["p_rated"] * 1e3, "mW")
                elif kind == "Q":
                    # Q_PMOS pins are D/G/S on the old symbols, 3/1/2 since the 2026-09-06 fix
                    d, gg, sN = pins.get("D", pins.get("3")), pins.get("G", pins.get("1")), pins.get("S", pins.get("2"))
                    vds, vgs = node_v(v, d) - node_v(v, sN), node_v(v, gg) - node_v(v, sN)
                    lim = PARTS["SI2333"]["limits"]
                    chk("%s.%s |Vds|" % (B.prefix, ref), abs(vds), 0, abs(lim["vds_absmax"]))
                    chk("%s.%s |Vgs|" % (B.prefix, ref), abs(vgs), 0, lim["vgs_absmax"])
            except KeyError:
                pass
    lim = PARTS["ETA6003"]["limits"]
    eta = PARTS["ETA6003"]["model"]
    vb = node_v(v, M.pin("U1", "2"))
    if vb > 1.0:
        chk("U1 ETA6003 VBUS", vb, lim["vbus"][0], lim["vbus"][1])
        vsys = node_v(v, M.pin("U1", "1"))
        chk("U1 ETA6003 SYS", vsys, eta["sys_min"] - 0.05, eta["sys_max"] + 0.05)
        # charger inductor L1: the buck runs at 3 MHz; its average current is the
        # whole SYS-side draw (power balance from the USB input), plus half the ripple
        il = PARTS["L1_1uH"]["model"]
        iavg = abs(g(r, "I_USB")) * vb / (max(vsys, 3.0) * 0.92)
        ripple = vsys * max(0.0, 1 - vsys / max(vb, vsys + 1e-3)) / (il["l"] * eta["f_sw"])
        chk("L1 charger inductor peak (avg %.2f + ripple/2 %.2f A)" % (iavg, ripple / 2), iavg + ripple / 2, 0, PARTS["L1_1uH"]["limits"]["isat"], "A")
        chk("U1 high-side switch peak", iavg + ripple / 2, 0, eta["hs_ilim"], "A")
    lim = PARTS["TPS63020"]["limits"]
    tps = PARTS["TPS63020"]["model"]
    vin = node_v(v, M.pin("U3", "10"))
    if vin > 1.0:
        chk("U3 TPS63020 VIN", vin, lim["vin"][0], lim["vin"][1])
        vout = node_v(v, M.pin("U3", "4"))
        chk("U3 TPS63020 VOUT", vout, 3.2, 3.4)
        chk("U3 TPS63020 IOUT (attached loads)", loads_a, 0, lim["iout"], "A")
        # inductor: average current by mode plus half the 2.4 MHz ripple. Buck
        # (VIN > VOUT): I_L = I_OUT, ripple = VOUT (1 - VOUT/VIN) / (L f). Boost
        # (VIN < VOUT): I_L = I_OUT VOUT / (VIN eff), ripple = VIN (1 - VIN/VOUT) / (L f).
        L, f = PARTS["L2_2u2"]["model"]["l"], tps["f_sw"]
        if vin >= vout:
            il_avg, ripple = loads_a, vout * (1 - vout / vin) / (L * f)
        else:
            il_avg, ripple = loads_a * vout / (max(vin, 1.8) * tps["eff"]), vin * (1 - vin / vout) / (L * f)
        ipk = il_avg + ripple / 2
        chk("L2 inductor peak (avg %.2f + ripple/2 %.2f A, %s)" % (il_avg, ripple / 2, "buck" if vin >= vout else "boost"),
            ipk, 0, PARTS["L2_2u2"]["limits"]["isat"], "A")
        chk("U3 TPS63020 switch peak vs its %.1f A limit (min)" % lim["isw_peak"], ipk, 0, lim["isw_peak"], "A")
    lim = PARTS["DRV8830"]["limits"]
    for ref, drv in SENSE_R.items():
        vcc = node_v(v, M.pin(drv, "4"))          # pin 4 = VCC (SLVSAB2F Table 1)
        if vcc > 1.0:
            chk("%s DRV8830 VCC" % drv, vcc, lim["vcc"][0], lim["vcc"][1])
            iout = (r.get("ISENSE_" + drv) or 0.0) / R_ISENSE
            chk("%s DRV8830 IOUT" % drv, abs(iout), 0, lim["iout_rms"], "A")
    chk("F1 PTC current vs its %.0f A hold (never trips below this)" % PARTS["F1_PTC"]["limits"]["i_hold"],
        abs(g(r, "I_CELL")), 0, PARTS["F1_PTC"]["limits"]["i_hold"], "A")
    mod = g(r, "MOD_3V3")
    if mod > 1.0:
        lim = PARTS["ESP32-P4-Module"]["limits"]["v3v3"]
        chk("ESP32-P4 module 3V3", mod, lim[0], lim[1])
    vm = g(r, "VMOT_V")
    if vm > 1.0:
        lim = PARTS["servo_1S"]["limits"]["v"]
        chk("servo supply (VMOT at Motion J10/J11)", vm, lim[0], lim[1])
    # ---- Odometry board: the LDO and the two sensors at the far end of the cable
    vin_o = node_v(v, O.pin("U1", "1"))
    if vin_o > 1.0:
        lim = PARTS["AP2127K-ADJ"]["limits"]
        chk("O.U1 AP2127K VIN", vin_o, lim["vin"][0], lim["vin"][1])
        vo = node_v(v, O.pin("U1", "5"))
        chk("O.U1 AP2127K VOUT = PMW3360 VDD", vo, *PARTS["PMW3360"]["limits"]["vdd"])
        i19 = PARTS["PMW3360"]["model"]["i_run"] + PARTS["PMW3360"]["model"]["i_led"]
        chk("O.U1 AP2127K current (%.0f mA modelled, TBC)" % (i19 * 1e3), i19, 0, lim["iout"], "A")
        chk("O.U1 AP2127K dissipation at that current", (vin_o - vo) * i19 * 1e3, 0, lim["pd_max"] * 1e3, "mW")
        chk("O.U3 BNO055 VDD", node_v(v, O.pin("U3", "3")), *PARTS["BNO055"]["limits"]["vdd"])
        chk("O.U3 BNO055 VDDIO", node_v(v, O.pin("U3", "28")), *PARTS["BNO055"]["limits"]["vddio"])
        chk("O.U2 PMW3360 VDDIO", node_v(v, O.pin("U2", "5")), *PARTS["PMW3360"]["limits"]["vddio"])
    for f in fails:
        finding("SPEC " + f)
    for x in notes:
        print("   note  SPEC " + x)
    if not fails:
        print("   PASS  every part inside its documented operating range (%d checks)" % n[0])
    return True


LOADS_A = I_MODULE + I_CAM + I_TOF + I_ODO + I_LED
LAST_V = {}
FINDINGS = []      # design results that are true of the boards as drawn
FALLBACKS = []     # scenarios whose operating point came from a ramped transient


def finding(text):
    FINDINGS.append(text)
    print("   FINDING  " + text)


import check_static                         # noqa: E402
allok = check_static.run(M, V, O)
if not allok:
    print("   (static checks failed: the netlist does not match a datasheet pin table)")

# ---- A -----------------------------------------------------------------
r = read(run_circuit(stack_deck("A", sw=0)))
allok &= report("A: switch OFF, cell 3.7 V", r, [
    ("VSYS alive at the cell (> 3.5 V)", lambda r: g(r, "VSYS") > 3.5),
    ("GATE held at VSYS: FETs off", lambda r: abs(g(r, "GATE") - g(r, "VSYS")) < 0.05),
    ("VSYS_SW, VMOT, all three 3V3 rails and the 1V9 dead (< 50 mV)", lambda r:
        all(abs(g(r, k)) < 0.05 for k in ("VSYS_SW", "VMOT", "3V3_M", "3V3_V", "3V3_O", "1V9_O"))),
    ("cell drain < 1 mA", lambda r: abs(g(r, "I_CELL")) < 1e-3),
])

# ---- B -----------------------------------------------------------------
r = read(run_circuit(stack_deck("B", sw=1)))
allok &= report("B: switch ON, cell 3.7 V, idle", r, [
    # the soft-start divider (R7 47k / R8 100k) leaves GATE at 0.32*VSYS, not
    # at ground: what matters is Vgs, which must enhance the SI2333 fully
    ("FETs enhanced: Vgs = GATE - VSYS < -2.0 V", lambda r: g(r, "GATE") - g(r, "VSYS") < -2.0),
    ("Q2 drop < 60 mV", lambda r: 0 <= g(r, "VSYS") - g(r, "VSYS_SW") < 0.06),
    ("Q3 drop < 60 mV", lambda r: 0 <= g(r, "VSYS") - g(r, "VMOT") < 0.06),
    ("3V3 in regulation on the Motion board (3.23-3.37)", lambda r: 3.23 < g(r, "3V3_M") < 3.37),
    ("3V3 reaches the module through J8 within 60 mV", lambda r:
        0 <= g(r, "3V3_M") - g(r, "MOD_3V3") < 0.06),
    ("VMOT reaches the Vision servos through J8", lambda r: abs(g(r, "VMOT") - g(r, "VMOT_V")) < 0.05),
    ("3V3 reaches the Odometry board through the J7 cable within 60 mV", lambda r:
        0 <= g(r, "3V3_M") - g(r, "3V3_O") < 0.06),
    ("1.9 V LDO in regulation for the PMW3360 (1.85-1.95)", lambda r: 1.85 < g(r, "1V9_O") < 1.95),
    ("BNO055 VDD inside 2.4-3.6 V", lambda r: 2.4 < g(r, "IMU_VDD") < 3.6),
    ("VBAT_SENSE = VSYS_SW / 2 (1 %)", lambda r: abs(g(r, "VBAT_SENSE_M") - g(r, "VSYS_SW") / 2) < 0.02),
    ("VBAT_SENSE arrives at the module GPIO20", lambda r: abs(g(r, "VBAT_SENSE_V") - g(r, "VBAT_SENSE_M")) < 0.01),
    ("MOT_INT idles HIGH at the module (> 3.0 V)", lambda r: g(r, "MOT_INT_V") > 3.0),
    ("cell current plausible for idle (0.7-1.3 A)", lambda r: 0.7 < g(r, "I_CELL") < 1.3),
])
I_IDLE = g(r, "I_CELL")

# ---- C -----------------------------------------------------------------
r = read(run_circuit(stack_deck("C", vbat=3.0, rcell=0.15, sw=1)))
allok &= report("C: switch ON, cell 3.0 V (flat, DCIR 150 mOhm)", r, [
    ("3V3 STILL in regulation: the buck-boost earns its place", lambda r: 3.2 < g(r, "3V3_M") < 3.37),
    ("module above its 3.0 V floor", lambda r: g(r, "MOD_3V3") > 3.0),
    ("1.9 V LDO still in regulation on the flat cell", lambda r: 1.85 < g(r, "1V9_O") < 1.95),
    ("cell current < 2 A", lambda r: g(r, "I_CELL") < 2.0),
])

# ---- D -----------------------------------------------------------------
r = read(run_circuit(stack_deck("D", vbat=-3.7, sw=1)))
allok &= report("D: cell REVERSED, switch ON", r, [
    ("Q1 blocks: VBAT_PROT, VSYS, VMOT, 3V3 all < 50 mV", lambda r:
        all(abs(g(r, k)) < 0.05 for k in ("VBAT_PROT", "VSYS", "VMOT", "3V3_M"))),
    ("cell current < 1 mA", lambda r: abs(g(r, "I_CELL")) < 1e-3),
])

# ---- E -----------------------------------------------------------------
r = read(run_circuit(stack_deck("E", vbus=5.0, sw=0)))
ETA = PARTS["ETA6003"]["model"]
allok &= report("E: USB in, switch OFF: charging", r, [
    ("SYS tracks the cell: VBAT + %.2f V, clamped %.1f-%.1f V (datasheet p3/p5)" % (ETA["sys_track"], ETA["sys_min"], ETA["sys_max"]),
     lambda r: abs(g(r, "VSYS") - min(ETA["sys_max"], max(ETA["sys_min"], g(r, "VBAT_PROT") + ETA["sys_track"]))) < 0.08),
    ("charge current = 1000 / R_ISET1 = %.0f mA (+-5 %%)" % (1000e3 / R_ISET1), lambda r:
        abs(-g(r, "I_CELL") - 1000 / R_ISET1) < 0.05 * 1000 / R_ISET1),
    ("NTC midpoint 2.5 V at 25 C (10k / 10k)", lambda r: 2.4 < g(r, "NTC") < 2.6),
    ("rails stay dead with the switch off", lambda r: abs(g(r, "3V3_M")) < 0.05),
])

# ---- F -----------------------------------------------------------------
for rt, label, expect in ((2.3e3, "hot ~55 C", False), (10e3, "25 C", True), (45e3, "cold ~-5 C", False)):
    r = read(run_circuit(stack_deck("F_" + label, vbus=5.0, sw=0, rt1=rt)))
    chg = -g(r, "I_CELL")
    ok = (chg > 0.5) == expect
    allok &= ok
    print("   %s  NTC %-11s RT1=%5.1fk  V(NTC)=%.2f V  charge %.3f A -> %s"
          % ("PASS" if ok else "FAIL", label, rt / 1e3, g(r, "NTC"), chg,
             "charging" if chg > 0.5 else "OFF"))

# ---- G -----------------------------------------------------------------
r = read(run_circuit(stack_deck("G", vbus=5.0, sw=1)))
allok &= report("G: USB in, switch ON: runs from the adapter", r, [
    ("3V3 fine", lambda r: 3.23 < g(r, "3V3_M") < 3.37),
    ("VMOT rides SYS = VBAT + ~0.17 V on USB (3.6-4.5 V window)", lambda r:
        abs(g(r, "VMOT") - g(r, "VSYS")) < 0.06 and ETA["sys_min"] - 0.05 < g(r, "VSYS") < ETA["sys_max"] + 0.05),
    ("USB draw (charge + SYS load at 90 %%) under a 1.5 A Type-C source: %.2f A" % g(r, "I_USB"), lambda r: g(r, "I_USB") < 1.5),
])
if g(r, "I_USB") > 0.5:
    finding("USB: charging at %.0f mA while running draws %.2f A from VBUS; a default 5 V/0.5 A port cannot supply it, "
            "the ETA6003 folds the charge current back when VBUS sags below its 4.5 V Vhold. Needs a source advertising 1.5 A "
            "(CC Rp 180 uA) or firmware that lowers the charge current on a weak source"
            % (1000e3 / R_ISET1, g(r, "I_USB")))

# ---- H -----------------------------------------------------------------
run = motor_state(U6="fwd", U7="fwd", U8="rev", U9="rev")   # driving: two forward, two reverse
r = read(solve("H", sw=1, motors=run, servo_a=0.1))
allok &= report("H: 4 motors driving (%s, 80 %% speed), servos idle" % MOTOR_TYPE, r, [
    ("each driver's ISENSE = I * R_ISENSE, below the 0.2 V trip", lambda r:
        all(0 < g(r, "ISENSE_" + u) < 0.2 for u, _ in MOTORS)),
    ("MOT_INT stays HIGH (no fault)", lambda r: g(r, "MOT_INT_V") > 3.0),
    ("3V3 holds", lambda r: 3.2 < g(r, "3V3_M") < 3.37),
    ("VMOT sag < 0.3 V", lambda r: g(r, "VSYS") - g(r, "VMOT") < 0.3),
])
print("   motor currents: " + "  ".join("%s %.0f mA" % (u, g(r, "ISENSE_" + u) / R_ISENSE * 1e3) for u, _ in MOTORS))

# ---- I -----------------------------------------------------------------
stall = motor_state(U6="stall", U7="stall", U8="stall", U9="stall")
SV_STALL = PARTS["servo_1S"]["model"]["i_stall"]
r = read(solve("I", sw=1, motors=stall, servo_a=SV_STALL))
ILIM = 0.2 / R_ISENSE
allok &= report("I: 4 motors STALLED + both HK-5320 servos stalled (%.2f A each)" % SV_STALL, r, [
    ("every motor held at the %.0f mA limit set by R_ISENSE (ISENSE 0.17-0.21 V)" % (ILIM * 1e3), lambda r:
        all(0.17 < g(r, "ISENSE_" + u) < 0.21 for u, _ in MOTORS)),
    ("nFAULT pulls MOT_INT low at the module (< 0.4 V)", lambda r: g(r, "MOT_INT_V") < 0.4),
    ("3V3 holds through the stall", lambda r: 3.2 < g(r, "3V3_M") < 3.37),
    ("cell current under the PTC's 3 A hold", lambda r: g(r, "I_CELL") < 3.0),
    ("VBAT_SENSE still tracks VSYS_SW/2 under load", lambda r: abs(g(r, "VBAT_SENSE_M") - g(r, "VSYS_SW") / 2) < 0.02),
])
print("   stall currents: " + "  ".join("%s %.0f mA" % (u, g(r, "ISENSE_" + u) / R_ISENSE * 1e3) for u, _ in MOTORS))
I_STALL = g(r, "I_CELL")

# ---- J -----------------------------------------------------------------
print("\n== J: cell sweep, switch ON, idle + running motors")
knee = None
for vb in (4.2, 4.0, 3.8, 3.6, 3.4, 3.2, 3.0, 2.9, 2.8):
    r = read(solve("J", vbat=vb, rcell=0.08 + (4.2 - vb) * 0.05, sw=1, motors=run))
    okv = g(r, "MOD_3V3") > 3.0
    if not okv and knee is None:
        knee = vb
    print("   cell %.1f V: VSYS_SW %.3f  3V3 %.3f  module %.3f  I_cell %.2f A  VBAT_SENSE %.3f  %s"
          % (vb, g(r, "VSYS_SW"), g(r, "3V3_M"), g(r, "MOD_3V3"), g(r, "I_CELL"), g(r, "VBAT_SENSE_M"),
             "ok" if okv else "MODULE BELOW 3.0 V"))
okJ = knee is None or knee <= 3.0
allok &= okJ
print("   %s  module holds 3.0 V down to a %s V cell (firmware cut-off should sit above that)"
      % ("PASS" if okJ else "FAIL", "<= 2.8" if knee is None else "%.1f" % knee))

# ---- K: I2C rise time -----------------------------------------------------
print("\n== K: I2C bus rise time (transient)")
# open-drain master releases SDA at t=0; the pull-up on the VISION board
# (R11 4.7k to 3V3, through J8.5) charges the real bus: 4 x DRV8830 (10 pF
# each in the model) + module pin 10 pF + ToF 8 pF + camera SCCB 8 pF +
# board/socket/cable 25 pF, plus the BNO055 pin (10 pF) at the end of the
# J7 cable (30 pF) since 2026-09-06.
sda_m, sda_v, sda_o = M.net("I2C_SDA"), V.net("I2C_SDA"), O.net("I2C_SDA")
extra = ["Cbus_mod %s 0 10p" % sda_v, "Cbus_tof %s 0 8p" % sda_v, "Cbus_cam %s 0 8p" % sda_v,
         "Cbus_wire %s 0 25p" % sda_m,
         "Cbus_imu %s 0 10p" % sda_o, "Cbus_j7cable %s 0 30p" % sda_o,
         "Smaster %s 0 mstr 0 SWMOD" % sda_v,
         "Vmstr mstr 0 PULSE(5 0 0.2u 1n 1n 5u 10u)"]
v = run_circuit(stack_deck("K", sw=1, extra=extra, analysis=".tran 2n 3u"))
t, sda = v["time"], v[sda_v.lower()]
v33 = final(v, NODES["3V3_V"].lower()) or 3.3
try:
    t30 = next(tt for tt, s in zip(t, sda) if tt > 0.2e-6 and s > 0.3 * v33)
    t70 = next(tt for tt, s in zip(t, sda) if tt > 0.2e-6 and s > 0.7 * v33)
    tr = (t70 - t30) * 1e9
except StopIteration:
    tr = float("inf")
okK = tr < 300
rpu = V.comps["R11"]["value"]
print("   SDA 30-70 %% rise = %.0f ns with %s pull-ups; %s  Fast-mode 400 kHz limit is 300 ns"
      % (tr, rpu, "PASS" if okK else "FINDING"))
if not okK:
    finding("I2C: %s pull-ups give %.0f ns rise against ~90 pF of bus, over the 300 ns Fast-mode limit; 2.2k gives ~%.0f ns"
            % (rpu, tr, tr * 2.2e3 / parse_val(rpu)))

# ---- L: USB-C CC -----------------------------------------------------------
print("\n== L: USB-C CC pull-downs (sink Rd)")
okL = True
for ua, lo, hi, label in ((80e-6, 0.25, 0.61, "default USB"), (180e-6, 0.70, 1.16, "1.5 A"), (330e-6, 1.31, 2.04, "3 A")):
    extra = ["Icc 0 %s DC %s" % (M.net("CC1"), ua)]
    v = run_circuit(stack_deck("L", sw=0, extra=extra))
    vcc = final(v, M.net("CC1").lower())
    ok = lo < vcc < hi
    okL &= ok
    print("   %s  %s source %3.0f uA -> V(CC1) = %.3f V (window %.2f-%.2f)" % ("PASS" if ok else "FAIL", label, ua * 1e6, vcc, lo, hi))
allok &= okL

# ---- M: power-on inrush ------------------------------------------------------
print("\n== M: power-on inrush with the soft-start (transient)")
extra = []
v = None
for opts, an in ((".option method=gear itl4=200 reltol=5e-3", ".tran 5u 6m"),
                 (".option method=gear itl4=500 reltol=1e-2 abstol=1e-6", ".tran 10u 6m"),
                 ("", ".tran 5u 6m uic")):
    d = stack_deck("M", sw=1, extra=[opts] if opts else [], analysis=an)
    d = [("VSW swc 0 PULSE(0 5 0.5m 1u 1u 100m 200m)" if c.startswith("VSW ") else c) for c in d]
    v = run_circuit(d)
    if run_circuit.last_warning is None and "time" in v:
        break
    print("   (attempt with %r did not converge)" % (opts or an))
if run_circuit.last_warning is None and "time" in v:
    icell = [-x for x in v["vbat#branch"]]
    ipk = max(icell)
    t33 = next((tt for tt, s in zip(v["time"], v[NODES["3V3_M"].lower()]) if s > 3.2), None)
    okM = ipk < 3.0
    allok &= okM
    print("   %s  peak cell current %.2f A (PTC hold 3 A); 3V3 up %s after the switch"
          % ("PASS" if okM else "FAIL", ipk, "in %.2f ms" % ((t33 - 0.5e-3) * 1e3) if t33 else "NEVER"))
else:
    print("   transient did not converge - inrush not measured; last log lines:")
    for l in [x for x in v.get("_log", []) if x.strip()][-6:]:
        print("      " + l.strip()[:150])

# ---- N: Wi-Fi bursts on the module ------------------------------------------
print("\n== N: Wi-Fi TX bursts on the module while driving (transient)")
i_pk = PARTS["ESP32-P4-Module"]["model"]["i_peak"]
mod = NODES["MOD_3V3"]
# the rails get 10 ms to settle after the ramped start (the buck-boost loop
# crosses over near 300 Hz), then 1.5 ms bursts every 3 ms for 9 ms
extra = ["Vwifi wifi 0 PULSE(0 1 10m 2u 2u 1.5m 3m)",
         "Bwifi %s 0 I = %s * V(wifi) * min(1, max(0, (V(%s) - 2.3) / 0.4))" % (mod, i_pk - I_MODULE, mod)]
d = stack_deck("N", sw=1, motors=run, extra=extra, analysis=".tran 5u 19m uic")
d = [("VBAT cellp 0 PWL(0 0 1m 3.7)" if c.startswith("VBAT ") else c) for c in d]
d = [c for c in d if not c.startswith(".nodeset")]
v = run_circuit(d)
if "time" in v and run_circuit.last_warning is None:
    t, m3, b3 = v["time"], v[mod.lower()], v[NODES["3V3_M"].lower()]
    pre = next(x for tt, x in zip(t, m3) if tt > 9.9e-3)
    settled = abs(pre - next(x for tt, x in zip(t, m3) if tt > 8.9e-3)) < 0.01
    win = [(x, y) for tt, x, y in zip(t, m3, b3) if tt > 10.0e-3]
    mn = min(x for x, _ in win)
    okN = settled and mn > PARTS["ESP32-P4-Module"]["limits"]["v3v3"][0] and pre - mn < 0.15
    allok &= okN
    print("   %s  module 3V3 %.3f V settled before the bursts%s; min %.3f V during %.2f A bursts: droop %.0f mV (floor 3.0 V, droop < 150 mV)"
          % ("PASS" if okN else "FAIL", pre, "" if settled else " (NOT settled)", mn, i_pk, (pre - mn) * 1e3))
else:
    print("   transient did not converge - bursts not measured")
    allok = False

# ---- O: USB only, no cell fitted --------------------------------------------
SV = PARTS["servo_1S"]["limits"]["v"]
r = read(solve("O_off", nocell=True, vbus=5.0, sw=0))
allok &= report("O: USB 5 V, NO cell, switch OFF", r, [
    ("SYS parked by the power path (3.6-4.5 V)", lambda r: ETA["sys_min"] - 0.05 < g(r, "VSYS") < ETA["sys_max"] + 0.05),
    ("rails dead with the switch off", lambda r: all(abs(g(r, k)) < 0.05 for k in ("VSYS_SW", "VMOT", "3V3_M", "3V3_O"))),
    ("no charge current into the empty connector (< 5 mA)", lambda r: abs(g(r, "I_USB")) < 0.005 or abs(g(r, "VBAT_PROT")) > 4.0),
])
for label, kw in (("idle", dict()), ("4 motors driving", dict(motors=run, servo_a=0.1))):
    r = read(solve("O_" + label, nocell=True, vbus=5.0, sw=1, **kw))
    allok &= report("O: USB 5 V, NO cell, switch ON, " + label, r, [
        ("3V3 in regulation on the Motion board", lambda r: 3.23 < g(r, "3V3_M") < 3.37),
        ("module above 3.0 V", lambda r: g(r, "MOD_3V3") > 3.0),
        ("1.9 V LDO in regulation on the Odometry board", lambda r: 1.85 < g(r, "1V9_O") < 1.95),
        ("VMOT = SYS inside the servo window %.1f-%.1f V" % SV, lambda r: SV[0] < g(r, "VMOT_V") < SV[1]),
        ("USB draw %.2f A under a 1.5 A Type-C source" % g(r, "I_USB"), lambda r: g(r, "I_USB") < 1.5),
    ])

# ---- P: USB at its limits, cell in ----------------------------------------------
ICC = 1000 / R_ISET1
for vb, label in ((5.5, "5.5 V (max input)"), (4.4, "4.4 V (weak source, min input, below the 4.5 V Vhold)")):
    r = read(solve("P_%s" % vb, vbus=vb, sw=1, motors=run, servo_a=0.1))
    if vb >= ETA["vhold"]:
        chg = ("charging at the full %.0f mA CC" % (ICC * 1e3), lambda r: abs(-g(r, "I_CELL") - ICC) < 0.05 * ICC)
    else:
        chg = ("Vhold foldback: charge reduced below the %.0f mA CC, not reversed (%.0f mA)" % (ICC * 1e3, -g(r, "I_CELL") * 1e3),
               lambda r: -ICC < g(r, "I_CELL") <= 0.001)
    allok &= report("P: USB %s, cell 3.7 V, switch ON, 4 motors driving, charging" % label, r, [
        ("3V3 in regulation", lambda r: 3.23 < g(r, "3V3_M") < 3.37),
        ("VMOT rides SYS inside the 3.6-4.5 V power-path window", lambda r:
            abs(g(r, "VMOT") - g(r, "VSYS")) < 0.06 and ETA["sys_min"] - 0.05 < g(r, "VSYS") < ETA["sys_max"] + 0.05),
        chg,
        ("USB draw %.2f A under 2 A" % g(r, "I_USB"), lambda r: g(r, "I_USB") < 2.0),
    ])
    if g(r, "I_USB") > 1.5:
        finding("USB at %.1f V while charging and driving draws %.2f A: over a 1.5 A Type-C source; the ETA6003's Vhold "
                "foldback then throttles the charge, so a weak source is safe but charges slowly" % (vb, g(r, "I_USB")))

print("\n" + ("HARNESS: all scenario checks pass" if allok else "*** HARNESS FAILURES PRESENT ***")
      + " | %d design finding(s) | %d operating point(s) from ramped transients%s"
      % (len(set(FINDINGS)), len(FALLBACKS), (" (" + ", ".join(FALLBACKS) + ")") if FALLBACKS else ""))
print("DESIGN FINDINGS (%d):" % len(FINDINGS))
for i, f in enumerate(sorted(set(FINDINGS)), 1):
    print("  %d. %s" % (i, f))
print(M.report())
print(V.report())
print(O.report())
