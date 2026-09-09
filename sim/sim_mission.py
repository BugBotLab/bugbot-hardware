"""Mission transients: the stack running in time, with a scripted MCU.

    python scripts/sim/sim_mission.py            (all missions, ~2-3 min)
    MOTOR=N20_geared_3v python scripts/sim/sim_mission.py

The "MCU" is a list of timed register writes to the four DRV8830s (direction
and VSET), exactly what the P4's firmware does over I2C. Motors are
electromechanical (MOTOR_MECH in stack_models.lib): they spin up, draw
inrush, settle, regenerate when reversed and stall against a load torque.
Every rail, current, speed and the fault line are recorded as waveforms.

Output: scripts/sim/out/mission_<name>.json (the waveforms, the MCU script,
the checks) and scripts/sim/out/stack_viewer.html, a Falstad-style animated
view of the stack that plays those waveforms back (built by viewer_html.py).

Missions
  drive   power on, all four forward at 80 %, then two reversed (a turn),
          then all off: spin-up inrush, running current, regen on reverse
  stall   power on, all forward, one motor (U8) blocked by a load torque at
          120 ms: the limit holds it, nFAULT drops MOT_INT, the others keep
          running; the MCU clears the driver at 200 ms
  usb     the same drive with USB plugged in: VMOT rides SYS (~4.5 V)
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_build import *      # noqa
from ngspice_run import run_circuit, final
from parts_spec import MOTOR_TYPES, PARTS
from netlist2spice import parse_val

from paths import OUT
MT = MOTOR_TYPES[MOTOR_TYPE]
KE = MT["kv_v_per_krpm"] / (1000.0 * 2 * math.pi / 60.0)
ILIM = 0.2 / R_ISENSE

MISSIONS = {
    "drive": dict(vbus=0.0, t_end=0.32, stall=None, mcu=[
        (0.020, {"U6": (1, 3.0), "U7": (1, 3.0), "U8": (1, 3.0), "U9": (1, 3.0)}),
        (0.150, {"U8": (-1, 3.0), "U9": (-1, 3.0)}),
        (0.260, {"U6": (0, 3.0), "U7": (0, 3.0), "U8": (0, 3.0), "U9": (0, 3.0)}),
    ]),
    # the DRV8830 only flags a current-limit fault after ~275 ms at the limit
    # (SLVSAB2F p11), so the shaft is blocked for 400 ms and the MCU reacts
    # 75 ms after the flag; writing IN1 = IN2 = 0 is what clears it
    "stall": dict(vbus=0.0, t_end=0.56, stall=("U8", 0.100, 0.500), mcu=[
        (0.020, {"U6": (1, 3.0), "U7": (1, 3.0), "U8": (1, 3.0), "U9": (1, 3.0)}),
        (0.450, {"U8": (0, 3.0)}),                       # MCU sees MOT_INT, stops U8
    ]),
    "usb": dict(vbus=5.0, t_end=0.25, stall=None, mcu=[
        (0.020, {"U6": (1, 3.0), "U7": (1, 3.0), "U8": (1, 3.0), "U9": (1, 3.0)}),
        (0.180, {"U6": (0, 3.0), "U7": (0, 3.0), "U8": (0, 3.0), "U9": (0, 3.0)}),
    ]),
}


def run_mission(name, spec):
    deck, speeds = mission_deck(name, spec["mcu"], MOTOR_TYPE, spec["t_end"], vbus=spec["vbus"], step=25e-6)
    if spec["stall"]:
        ref, t0, t1 = spec["stall"]
        # a blocking load: the motor's TL becomes 100x between t0 and t1
        jref = dict(MOTORS)[ref]
        deck = [c.replace(" 0 MOTOR_MECH ", " blk MOTOR_MECH ") + " TLB=%s" % (MT["t_load"] * 200)
                if c.startswith("XMOT_%s " % jref) else c for c in deck]
        deck.insert(-2, "Vblk blk 0 PULSE(0 1 %s 1m 1m %s 10)" % (t0, t1 - t0))
    v = run_circuit(deck)
    if "time" not in v:
        print("  !! mission %s did not run" % name)
        for l in [x for x in v.get("_log", []) if x.strip()][-6:]:
            print("     " + l.strip()[:140])
        return None
    t = v["time"]
    n = len(t)
    keep = max(1, n // 1500)              # ~1500 points for the viewer

    def vec(node):
        if node == "0":
            return [0.0] * n
        return v.get(node.lower(), [0.0] * n)

    series = {
        "VBAT": [-x for x in v["vbat#branch"]],                       # cell current, + = discharging
        "VSYS": vec(NODES["VSYS"]), "VSYS_SW": vec(NODES["VSYS_SW"]), "VMOT": vec(NODES["VMOT"]),
        "3V3": vec(NODES["3V3_M"]), "MOD_3V3": vec(NODES["MOD_3V3"]), "MOT_INT": vec(NODES["MOT_INT_V"]),
        "GATE": vec(NODES["GATE"]), "VBAT_SENSE": vec(NODES["VBAT_SENSE_M"]),
    }
    for sref, drv in SENSE_R.items():
        series["I_" + drv] = [x / R_ISENSE for x in vec(M.pin(sref, "1"))]
        series["RPM_" + drv] = [x * 60 / (2 * math.pi) for x in vec(speeds[drv])]
        series["DIR_" + drv] = vec("dir_" + drv)
    if spec["vbus"]:
        series["I_USB"] = [-x for x in v["vbus#branch"]]
    ds = {k: [round(s[i], 4) for i in range(0, n, keep)] for k, s in series.items()}
    ts = [round(t[i], 6) for i in range(0, n, keep)]

    # ---- checks
    checks = []
    def chk(desc, ok):
        checks.append((desc, bool(ok)))
        print("   %s  %s" % ("PASS" if ok else "FAIL", desc))
    imax = max(series["VBAT"])
    chk("peak cell current %.2f A under the PTC's 3 A hold" % imax, imax < 3.0)
    v33min = min(x for tt, x in zip(t, series["3V3"]) if tt > 0.005)
    chk("3V3 never below 3.2 V after start-up (min %.3f V)" % v33min, v33min > 3.2)
    for drv in ("U6", "U7", "U8", "U9"):
        rpm = series["RPM_" + drv]
        ipk = max(abs(x) for x in series["I_" + drv])
        chk("%s peak current %.0f mA within the %.0f mA limit (+5 %%)" % (drv, ipk * 1e3, ILIM * 1e3), ipk < ILIM * 1.05)
        nl = MT["rpm_noload_3v"]
        running = max(abs(x) for x in rpm)
        chk("%s reaches %.0f rpm (no-load %.0f rpm at 3 V)" % (drv, running, nl), running > 0.4 * nl)
    if spec["stall"]:
        ref, t0, t1 = spec["stall"]
        t_mcu = next(tm for tm, w in spec["mcu"] if ref in w and w[ref][0] == 0)
        i_st = [abs(x) for tt, x in zip(t, series["I_" + ref]) if t0 + 0.02 < tt < t_mcu] or [0.0]
        chk("%s held at the current limit while blocked (%.0f mA)" % (ref, sum(i_st) / len(i_st) * 1e3), 0.85 * ILIM < sum(i_st) / len(i_st) < 1.05 * ILIM)
        early = [x for tt, x in zip(t, series["MOT_INT"]) if t0 + 0.02 < tt < t0 + 0.25] or [0.0]
        chk("MOT_INT still HIGH in the first 250 ms of the stall (deglitch) (%.2f V)" % min(early), min(early) > 3.0)
        mi = [x for tt, x in zip(t, series["MOT_INT"]) if t0 + 0.30 < tt < t_mcu] or [9.9]
        chk("MOT_INT low at the module after ~275 ms at the limit (%.2f V)" % min(mi), min(mi) < 0.4)
        after = [x for tt, x in zip(t, series["MOT_INT"]) if tt > t_mcu + 0.02] or [0.0]
        chk("MOT_INT released after the MCU wrote IN1=IN2=0 (%.2f V)" % max(after), max(after) > 3.0)
    mission = {"name": name, "motor": MOTOR_TYPE, "t": ts, "series": ds, "mcu": spec["mcu"],
               "stall": spec["stall"], "checks": checks, "ilim": ILIM,
               "rpm_noload": MT["rpm_noload_3v"]}
    with open(os.path.join(OUT, "mission_%s.json" % name), "w") as f:
        json.dump(mission, f)
    return mission


results = {}
for name, spec in MISSIONS.items():
    print("\n== mission %s (%s)" % (name, MOTOR_TYPE))
    r = run_mission(name, spec)
    if r:
        results[name] = r
allok = all(ok for r in results.values() for _, ok in r["checks"])
print("\n" + ("ALL MISSION CHECKS PASS" if allok else "*** MISSION FAILURES ***"))

try:
    import viewer_html
    path = viewer_html.build(results, os.path.join(OUT, "stack_viewer.html"), M, V)
    print("viewer:", path)
except Exception as e:
    print("viewer not built:", e)
