"""Shared deck builder for the BugBot stack simulations (extracted from
sim_stack.py 2026-09-04 so the mission/transient runs and the Falstad-style
viewer use exactly the same circuit)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist2spice import Board, parse_val
from ngspice_run import run_circuit, final
from parts_spec import PARTS, MOTOR_TYPES, motor_bemf

from paths import netlist, model_lib

LIB = model_lib("stack_models.lib")
M = Board(netlist("motion"), "M")
V = Board(netlist("vision"), "V")
O = Board(netlist("odometry"), "O")        # optical flow + IMU, on the J7 cable (2026-09-06)
ALL = (M, V, O)

# ------------------------------------------------------------ what plugs in
# loads at 3.3 V (A): the module (P4 + C6 Wi-Fi + camera-side regulators),
# the camera head, the ToF, the LED string idle. The flow board is no longer
# a constant load: the Odometry board's own netlist hangs on J7 (its LDO,
# the PMW3360 and the BNO055 are modelled). I_ODO is what those draw from
# 3V3 in total (for the TPS63020 load check): PMW3360 37 mA (run4, LED
# included, datasheet Table 5) through the 1.9 V LDO, BNO055 12.3 mA, VDDIO ~1 mA.
I_MODULE, I_CAM, I_TOF, I_LED = 0.55, 0.15, 0.05, 0.02
I_ODO = 0.051
# Motion J7 <-> Odometry J1: a 10-way GH1.25 cable, ~100 mm of AWG30 plus
# two crimps: ~120 mOhm per conductor
R_CABLE = 0.12
R_ISENSE = parse_val(M.comps["R19"]["value"])            # 0.5 ohm
R_ISET1 = parse_val(M.comps["R5"]["value"])              # 1k24
SENSE_R = {"R19": "U6", "R20": "U7", "R21": "U8", "R22": "U9"}
# the camera connector's 3V3 pin, looked up by net: the 2026-09-07 rework mirrored J3 (top-contact
# connector, pin k = Pi Zero pin 23-k), so 3V3 moved from pin 22 to pin 1
CAM_3V3_PIN = next(k for k in range(1, 23) if V.pin("J3", str(k)) == V.net("3V3"))
CAM_3V3 = V.pin("J3", str(CAM_3V3_PIN))
MOTORS = [("U6", "J3"), ("U7", "J4"), ("U8", "J5"), ("U9", "J6")]


MOTOR_TYPE = os.environ.get("MOTOR", "0615_coreless")     # MOTOR=N20_geared_3v python sim_stack.py


def motor_state(**per_motor):
    """Per-driver state, e.g. motor_state(U6="fwd", U7="rev", U8="off", U9="stall").
    fwd/rev run at 80 % of no-load speed (load 0.2); "stall" is fwd at 0 rpm;
    a tuple (dir, load_frac, vset) sets anything else."""
    out = {}
    for ref, _ in MOTORS:
        st = per_motor.get(ref, "off")
        if isinstance(st, tuple):
            dirv, load, vset = st
        else:
            dirv, load, vset = {"off": (0, 0.0, 3.0), "fwd": (1, 0.2, 3.0), "rev": (-1, 0.2, 3.0),
                                "stall": (1, 1.0, 3.0), "free": (1, 0.0, 3.0)}[st]
        out[ref] = (dirv, vset, dirv * motor_bemf(MOTOR_TYPE, load))   # EMF sign = direction
    return out


def stack_deck(name, vbat=3.7, rcell=0.08, vbus=0.0, sw=0, motors=None,
               servo_a=0.0, rt1=10e3, extra=(), analysis=".op", nocell=False):
    """motors: {ref: (DIR, VSET, VBEMF)} for the four drivers (see motor_state).
    nocell=True: J2 is empty (no battery), only USB can power the stack; the
    battery node gets a 10 k leak so it is defined (the charger's taper
    then parks it at 4.2 V, as the real chip does into an open battery)."""
    motors = motors or {}
    d = ["* BugBot stack - " + name, '.include "%s"' % LIB,
         ".option rshunt=1e12 gmin=1e-10 abstol=1e-9 reltol=1e-3"]
    # ---- Motion board, as netlisted; the switch and the thermistor are
    # replaced by harness elements (state, temperature)
    # the slide switch moved to the Vision board (SW3, 2026-09-07): it grounds SW_ON, which reaches
    # the Motion gate divider through stack pin J8.9
    sw_node = V.pin("SW3", "1")
    over = {"RT1": "R_RT1 %s 0 %s" % (M.pin("RT1", "1"), rt1)}
    for ref, drv in SENSE_R.items():
        pass
    els = M.elements(over)
    # give each driver its register state
    for i, e in enumerate(els):
        if e.startswith("XM_U") and e.endswith(" DRV8830"):
            ref = e.split()[0][3:]
            dirv, vset, _ = motors.get(ref, (0, 3.0, 0.0))
            els[i] = e + " DIR=%s VSET=%s ILIM=%s" % (dirv, vset, round(0.2 / R_ISENSE, 4))
    d += els
    d += ["VSW swc 0 DC %s" % (sw * 5),
          ".model SWMOD SW (Ron=0.05 Roff=1G Vt=2.5 Vh=0.5)"]
    if nocell:
        d += ["Rnocell %s 0 10k" % M.pin("J2", "1")]
    else:
        # the cell, with its DCIR, into J2
        d += ["VBAT cellp 0 DC %s" % vbat,
              "Rcell cellp %s %s" % (M.pin("J2", "1"), rcell)]
    # USB into J1's VBUS pins
    d += ["VBUS %s 0 DC %s" % (M.pin("J1", "A4"), vbus)]
    # motors across J3..J6
    for ref, jref in MOTORS:
        _, _, bemf = motors.get(ref, (0, 3.0, 0.0))
        # 0615 coreless: ~4 ohm winding (stall ~0.75 A at 3 V), so a stall
        # really does reach the 400 mA limit and the limiter is exercised
        mt = MOTOR_TYPES[MOTOR_TYPE]
        # motor p = the OUT1 side. Since the 2026-09-04 pinout fix OUT1 drives
        # connector pin 1 (label swap on sheet 04), so "fwd" = OUT1 high = pin 1 high.
        d.append("XMOT_%s %s %s MOTOR RWIND=%s LWIND=%s VBEMF=%s" % (jref, M.pin(jref, "1"), M.pin(jref, "2"), mt["r"], mt["l"], bemf))
    # ---- Vision board, as netlisted, joined through the sockets pin for pin
    d += V.elements({"SW3": "S_SW3 %s 0 swc 0 SWMOD" % sw_node})
    for j in ("J8", "J9"):
        for k in range(1, 11):
            a, b = M.pin(j, str(k)), V.pin(j, str(k))
            if a and b and a != b and not (a == "0" and b == "0"):
                if a == "0" or b == "0":
                    d.append("R_%s_%d %s %s 20m" % (j, k, a if a != "0" else b, "0"))
                else:
                    d.append("R_%s_%d %s %s 20m" % (j, k, a, b))
    # ---- Odometry board, as netlisted, on the J7 -> J1 cable pin for pin
    d += O.elements()
    for k in range(1, 11):
        a, b = M.pin("J7", str(k)), O.pin("J1", str(11 - k))    # J1 is J7's mirror image since 2026-09-07 (pin k -> 11-k)
        if a and b and not (a == "0" and b == "0"):
            d.append("R_J7_%d %s %s %s" % (k, a, b, R_CABLE))
    # the module: its supply pads, the camera, the ToF, the LED
    d += ["XLD_MOD %s 0 CCLOAD I0=%s" % (V.pin("U3", "85"), I_MODULE),
          "XLD_CAM %s 0 CCLOAD I0=%s" % (CAM_3V3, I_CAM),
          "XLD_TOF %s 0 CCLOAD I0=%s" % (V.pin("J7", "1"), I_TOF),
          "XLD_LED %s 0 CCLOAD I0=%s" % (V.pin("J10", "1"), I_LED)]
    # servos on VMOT through the Motion board's J10/J11 (pin 2 = VMOT on the side-entry GH3, 2026-09-07)
    if servo_a:
        d += ["XLD_SV1 %s 0 CCLOAD I0=%s" % (M.pin("J10", "2"), servo_a),
              "XLD_SV2 %s 0 CCLOAD I0=%s" % (M.pin("J11", "2"), servo_a)]
    d += list(extra)
    # starting guesses: with the motors running Newton otherwise wanders off
    # to a non-converged point that LOOKS like a collapsed tree (2026-09-04)
    if sw and "uic" not in analysis and not nocell:   # also the initial op of a .tran
        vb = max(vbus - 0.1, vbat) if vbus > 3.9 else vbat
        # the LDO guess follows the real divider: with 47k/33k (1.939 V) a
        # fixed 1.9 V guess left Newton on a non-converged branch (2026-09-07)
        v19 = 0.8 * (1 + parse_val(O.comps["R1"]["value"]) / parse_val(O.comps["R2"]["value"]))
        # v(SW_ON)=0: the closed switch (now on the Vision board, through J8.9) holds the divider foot at ground
        d += [".nodeset v(%s)=%.2f v(%s)=%.2f v(%s)=%.2f v(%s)=3.3 v(%s)=3.3 v(%s)=3.3 v(%s)=%.3f v(%s)=%.2f v(%s)=0 v(%s)=0 v(xm_u3.regc)=3.3"
              % (M.net("VSYS"), vb - 0.1, M.net("VSYS_SW"), vb - 0.15, M.net("VMOT"), vb - 0.15,
                 M.net("3V3"), V.net("3V3"), O.net("3V3"), O.net("1V9"), v19, M.net("GATE"), 0.32 * vb, sw_node, M.net("SW_ON"))]
    d += [analysis, ".end"]
    return d


NODES = {
    "VSYS": M.net("VSYS"), "VSYS_SW": M.net("VSYS_SW"), "VMOT": M.net("VMOT"),
    "3V3_M": M.net("3V3"), "GATE": M.net("GATE"), "VBAT_SENSE_M": M.net("VBAT_SENSE"),
    "NTC": M.net("NTC"), "VBAT_PROT": M.net("VBAT_PROT"), "MOT_INT": M.net("MOT_INT"),
    "3V3_V": V.net("3V3"), "MOD_3V3": V.pin("U3", "85"), "VMOT_V": V.net("VMOT"),
    "VBAT_SENSE_V": V.pin("U3", "29"),        # GPIO20 = VBAT_SENSE on the module
    "SDA_V": V.net("I2C_SDA"), "MOT_INT_V": V.pin("U3", "55"),   # pads 53-65 = GPIO26-38: GPIO28 = pad 55
    # Odometry board, at the far end of the J7 cable
    "3V3_O": O.net("3V3"), "1V9_O": O.net("1V9"), "SDA_O": O.net("I2C_SDA"),
    "IMU_VDD": O.pin("U3", "3"), "FLOW_VDD": O.pin("U2", "4"), "FLOW_LEDP": O.pin("U2", "15"),
}


def solve(name, **kw):
    """Operating point: .op first; if ngspice cannot converge it, a ramped
    transient (cell 0 -> V over 1 ms, settle to 6 ms) and its final values.
    The transient itself is tried with a ladder of integrator/step settings:
    since the 2026-09-07 rework (10 uF less on the Vision 3V3 rail) the first
    setting aborts for the 4.2 V cell and the no-cell driving cases, and a
    finer step converges to the same answer as before."""
    v = run_circuit(stack_deck(name, **kw))
    if run_circuit.last_warning is None:
        return v
    if kw.get("nocell"):
        # no battery: Newton never finds the charger's open-battery point
        # (the taper parks BATT at 4.2 V with a huge loop gain), a gear
        # transient with VBUS ramped over 1 ms and 20 ms of settling does
        ladder = [(".tran 10u 20m", ".option method=gear itl4=200 reltol=5e-3"),
                  (".tran 5u 20m", ".option method=gear itl4=200 reltol=5e-3"),
                  (".tran 10u 20m", ".option method=gear itl4=500 reltol=1e-2 abstol=1e-6"),
                  (".tran 2u 20m", ".option method=gear itl4=500 reltol=1e-2 abstol=1e-6")]
    else:
        ladder = [(".tran 5u 6m uic", None),
                  (".tran 2u 6m uic", None),
                  (".tran 5u 6m uic", ".option method=gear itl4=200 reltol=5e-3"),
                  (".tran 2u 6m", ".option method=gear itl4=500 reltol=1e-2 abstol=1e-6")]
    vb = kw.get("vbat", 3.7)
    for analysis, opt in ladder:
        extra = list(kw.get("extra", ())) + ([opt] if opt else [])
        d = stack_deck(name, analysis=analysis, **dict(kw, extra=extra))
        if kw.get("nocell"):
            d = [("VBUS %s 0 PWL(0 0 1m %s)" % (M.pin("J1", "A4"), kw.get("vbus", 0.0)) if c.startswith("VBUS ") else c) for c in d]
        else:
            d = [("VBAT cellp 0 PWL(0 0 1m %s)" % vb if c.startswith("VBAT ") else c) for c in d]
        d = [c for c in d if not c.startswith(".nodeset")]
        v = run_circuit(d)
        v["_via_tran"] = True
        if run_circuit.last_warning is None:
            break
    return v




def mission_deck(name, mcu, mtype, t_end, vbat=3.7, rcell=0.08, vbus=0.0, servo_a=0.05, step=20e-6):
    """Transient deck: the DRV8830s take their DIR/VSET from PWL sources that
    the scripted MCU writes (mcu = list of (t_seconds, {ref: (dir, vset)})),
    and every motor is an electromechanical MOTOR_MECH with its own speed
    node. Returns (deck, speed_nodes)."""
    from parts_spec import MOTOR_TYPES
    d = stack_deck(name, vbat=vbat, rcell=rcell, vbus=vbus, sw=1, motors={}, servo_a=servo_a,
                   analysis=".tran %s %s uic" % (step, t_end))
    d = [c for c in d if not c.startswith((".nodeset", "XMOT_"))]
    d = [("VBAT cellp 0 PWL(0 0 1m %s)" % vbat if c.startswith("VBAT ") else c) for c in d]
    mt = MOTOR_TYPES[mtype]
    ke = mt["kv_v_per_krpm"] / (1000.0 * 2 * math.pi / 60.0)      # V per rad/s
    speeds = {}
    out = []
    for c in d:
        if c.startswith("XM_U") and " DRV8830 " in c:
            ref = c.split()[0][3:]
            ports = c.split()[1:8]
            out.append("XM_%s %s dir_%s vset_%s DRV8830T ILIM=%s" % (ref, " ".join(ports), ref, ref, round(0.2 / R_ISENSE, 4)))
            # PWL register writes: hold the previous value until the next write
            for sig, idx, dflt in (("dir", 0, 0), ("vset", 1, 3.0)):
                pts, cur = [(0.0, dflt)], dflt
                for t, regs in mcu:
                    if ref in regs:
                        nv = regs[ref][idx]
                        pts += [(t, cur), (t + 20e-6, nv)]     # a 20 us I2C write
                        cur = nv
                out.append("V%s_%s %s_%s 0 PWL(%s)" % (sig, ref, sig, ref, " ".join("%g %g" % p for p in pts)))
        else:
            out.append(c)
    # the motors go BEFORE the analysis card - anything after .end is ignored
    # by ngspice, silently (the first mission run had no motors at all)
    ia = next(i for i, c in enumerate(out) if c.startswith(".tran"))
    for ref, jref in MOTORS:
        out.insert(ia, "XMOT_%s %s %s w_%s 0 MOTOR_MECH R=%s L=%s KE=%s J=%s B=%s TL=%s"
                   % (jref, M.pin(jref, "1"), M.pin(jref, "2"), ref, mt["r"], mt["l"], ke,
                      mt.get("j", 2e-9), mt.get("b", 2e-8), mt.get("t_load", 1e-5)))
        ia += 1
        speeds[ref] = "w_" + ref
    return out, speeds
