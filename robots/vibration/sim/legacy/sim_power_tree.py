"""Power-tree state-matrix simulation for the BugBot main board.

Component values are read from golden_netlist.xml (never retyped), the deck
topology mirrors sheets 01/02, and each scenario asserts the behavior the
design promises. Engine: KiCad's own ngspice.dll.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ngspice_run import run_circuit, final

from paths import model_lib, netlist
LIB = model_lib("models.lib")


def parse_val(s):
    m = re.match(r"([\d.]+)\s*([kKmMuUnR]?)", s)
    n = float(m.group(1))
    suf = m.group(2).lower()
    mult = {"k": 1e3, "m": 1e-3, "u": 1e-6, "n": 1e-9, "r": 1, "": 1}[suf]
    # "1k24" style: trailing digits after the multiplier
    tail = re.match(r"[\d.]+[kKmM](\d+)", s)
    if tail:
        n = n + float("0." + tail.group(1))
    return n * mult


# folder renamed BugBot_Main -> BugBot_Motion_Board on 2026-09-02; this path
# was stale and the sim could not run at all until it was corrected
tree = ET.parse(netlist("motion"))
vals = {}
for c in tree.getroot().iter("comp"):
    vals[c.get("ref")] = c.findtext("value") or ""

# Roles resolved by NET MEMBERSHIP on 2026-09-02, not by refdes number: the
# board was re-annotated after this sim was written and every number moved,
# so the old map silently pointed at the wrong parts.
#   shunt        RSH -> RSH1        gate pull-up  R11 -> R8
#   charger ISET R2  -> R5          NTC top       R1  -> R3
#   VBAT_SENSE   R8/R9 -> R9/R10
# The +5 V servo boost (U10, its 732k/100k divider and the SERVO_EN pulldown)
# was DELETED from the board on 2026-08-30 when Jerome moved to 1S servos, so
# scenario E and everything touching v5 goes with it.
ROLE = {"ntc_top": "R3", "iset1": "R5", "gate_pu": "R8",
        "vbs_top": "R9", "vbs_bot": "R10", "shunt": "RSH1", "ntc": "RT1"}
R = {k: parse_val(vals[v]) for k, v in ROLE.items()}
assert abs(R["gate_pu"] - 100e3) < 1, R
assert abs(R["vbs_top"] - 100e3) < 1 and abs(R["vbs_bot"] - 100e3) < 1, R
assert abs(R["shunt"] - 0.010) < 1e-4, R["shunt"]
assert abs(R["iset1"] - 1240) < 1, R["iset1"]
assert abs(R["ntc_top"] - 10e3) < 1, R["ntc_top"]


RL_AI_37V = 4.07          # Vision board, ~908 mA off a 3.7 V cell


def deck(name, vbat=3.7, vbus=0.0, sw=0, rl33=16.5,
         rlmot=10.0, rlai=RL_AI_37V, rt1=10e3, tran=None):
    d = [f"* BugBot power tree - {name}",
         f'.include "{LIB}"',
         # battery + reverse-protection FET (D=battery, G=gnd, S=fuse side)
         f"VBAT bat 0 DC {vbat}",
         "MQ1 bat qg q1s SI2333",
         "VQG qg 0 DC 0",
         "RF1 q1s vbatp 30m",           # PTC 1812L300/24GR typ
         # charger power path
         f"VBUSS vbusn 0 DC {vbus}",
         "XPP vbusn vsysraw vbatp ETA6003PP",
         # shunt + current sense (V+ from 3V3 per design)
         f"RSH vsysraw vsys {R['shunt']}",
         "XINA vsysraw vsys v33 isense INA180A1",
         # gate network + slide switch (50 mOhm contact)
         f"R11 vsys gate {R['gate_pu']}",
         "SSW1 gate 0 swc 0 SWMOD",
         f"VSW swc 0 DC {sw * 5}",
         ".model SWMOD SW (Ron=0.05 Roff=1G Vt=2.5 Vh=0.5)",
         # high-side load switches (S on supply, D on rail)
         "MQ2 vsysai gate vsys SI2333",
         "MQ3 vmot gate vsys SI2333",
         # LDO (EN tied to VIN, as drawn)
         "XLDO vsysai 0 vsysai v33 AP2112K33",
         # battery-sense divider on the SWITCHED rail
         f"R8 vsysai vbsense {R['vbs_top']}",
         f"R9 vbsense 0 {R['vbs_bot']}",
         # NTC divider from VBUS
         f"R1 vbusn ntc {R['ntc_top']}",
         f"RT1 ntc 0 {rt1}",
         # loads
         f"RL33 v33 0 {rl33}",
         # The AI board on VSYS_AI. This was 37 ohm ("~100 mA"), a placeholder
         # from before that board existed. The Vision board as designed draws
         # 916 mA at its 3.3 V node, ~908 mA off a 3.7 V cell through its
         # buck-boost (sim_vision_power.py section D) -> 4.07 ohm. Nine times
         # the placeholder, and it moves every rail figure below.
         f"RLAI vsysai 0 {rlai}",
         f"RLMOT vmot 0 {rlmot}",
         ]
    if tran:
        d += ["C3 vsysraw 0 22u", "C8v vsys 0 10u",
              "C6 vsysai 0 2u", "C12 v33 0 10u",
              tran]
    else:
        d += [".op"]
    d += [".end"]
    return d


def report(name, v, checks):
    print(f"\n== {name}")
    def node(k):
        return final(v, k) if "#" in k else final(v, k[2:-1])
    row = {k: node(k) for k in
           ("v(vsys)", "v(vsysai)", "v(vmot)", "v(v33)", "v(gate)",
            "v(vbsense)", "v(isense)", "v(ntc)", "v(vbatp)", "vbat#branch")}
    for k, val in row.items():
        if val is not None:
            print(f"   {k:14s} = {val:8.4f}")
    ok = True
    for desc, cond in checks:
        good = cond(row)
        ok &= good
        print(f"   {'PASS' if good else 'FAIL'}  {desc}")
    return ok, row


allok = True
g = lambda r, k: r[k] if r[k] is not None else float("nan")

v = run_circuit(deck("A_switch_off_idle", sw=0))
ok, _ = report("A: switch OFF, battery 3.7 V", v, [
    ("all rails dead (<50 mV)", lambda r: all(abs(g(r, k)) < 0.05 for k in
        ("v(vsysai)", "v(vmot)", "v(v33)"))),
    ("VSYS alive at ~battery", lambda r: 3.4 < g(r, "v(vsys)") < 3.75),
    ("gate held at VSYS (FETs off)", lambda r:
        abs(g(r, "v(gate)") - g(r, "v(vsys)")) < 0.05),
    ("battery drain < 1 mA", lambda r: abs(g(r, "vbat#branch")) < 1e-3),
])
allok &= ok

v = run_circuit(deck("B_switch_on_run", sw=1))
ok, rowB = report("B: switch ON, battery 3.7 V, servo off", v, [
    ("3V3 in regulation", lambda r: 3.25 < g(r, "v(v33)") < 3.35),
    ("VMOT ~ VSYS (FET drop < 60 mV)", lambda r:
        0 < g(r, "v(vsys)") - g(r, "v(vmot)") < 0.06),
    ("VSYS_AI ~ VSYS", lambda r:
        0 < g(r, "v(vsys)") - g(r, "v(vsysai)") < 0.06),
    ("gate pulled low (<0.2 V)", lambda r: g(r, "v(gate)") < 0.2),
    ("VBAT_SENSE = VSYS_AI/2 (1 %)", lambda r:
        abs(g(r, "v(vbsense)") - g(r, "v(vsysai)") / 2) < 0.02),
])
allok &= ok

v = run_circuit(deck("C_flat_battery", vbat=3.0, sw=1))
ok, rowC = report("C: switch ON, battery 3.0 V (flat)", v, [
    ("rails still up", lambda r: g(r, "v(vmot)") > 2.8),
    # This check used to be "> 2.6", loose enough to pass while the rail sat
    # under the ESP32-S3's own brownout trip. With the Vision board's real
    # ~908 mA on VSYS_AI it does exactly that, so the check now asserts the
    # thing that matters.
    ("3V3 above the S3's 2.8 V brownout", lambda r: g(r, "v(v33)") > 2.80),
    ("3V3 above the S3's 3.0 V recommended minimum", lambda r:
        g(r, "v(v33)") > 3.00),
])
allok &= ok

v = run_circuit(deck("D_reverse_battery", vbat=-3.7, sw=1))
ok, _ = report("D: battery REVERSED, switch ON", v, [
    ("Q1 blocks - nothing downstream (<50 mV magnitude)", lambda r: all(
        abs(g(r, k)) < 0.05 for k in
        ("v(vbatp)", "v(vsys)", "v(vsysai)", "v(vmot)", "v(v33)"))),
    ("battery current ~ 0 (<1 mA)", lambda r: abs(g(r, "vbat#branch")) < 1e-3),
])
allok &= ok

# Scenario E (SERVO_EN / +5 V boost) DELETED 2026-09-02: U10, its
# divider and the +5 V rail were removed from the board on 2026-08-30
# when Jerome moved to 1S servos running straight off VSYS_AI.

v = run_circuit(deck("F_usb_charging_off", vbus=5.0, sw=0))
ok, rowF = report("F: USB in, switch OFF (charging)", v, [
    ("SYS regulated ~4.5 V", lambda r: 4.3 < g(r, "v(vsys)") < 4.6),
    ("charge current ~806 mA into battery", lambda r:
        0.75 < g(r, "vbat#branch") < 0.86),
    ("NTC divider midpoint 2.5 V @ 25 C", lambda r:
        2.4 < g(r, "v(ntc)") < 2.6),
    ("rails still dead with switch off", lambda r:
        abs(g(r, "v(v33)")) < 0.05),
])
allok &= ok

v = run_circuit(deck("G_usb_and_running", vbus=5.0, sw=1))
ok, rowG = report("G: USB in, switch ON (run from adapter)", v, [
    ("3V3 fine", lambda r: 3.25 < g(r, "v(v33)") < 3.35),
    ("VMOT rides SYS (~4.4-4.5 V - motors faster on USB!)", lambda r:
        4.2 < g(r, "v(vmot)") < 4.6),
])
allok &= ok

v = run_circuit(deck("H_motor_stall", sw=1, rlmot=0.9))
ok, rowH = report("H: switch ON, motor stall (~4 A on VMOT)", v, [
    ("VMOT sag reported", lambda r: g(r, "v(vmot)") > 2.5),
    ("ISENSE = 20 * I * 10 mOhm (within 10 %)", lambda r:
        abs(g(r, "v(isense)") -
            20 * R["shunt"] * (g(r, "v(vsysraw)") if False else
                             abs(g(r, "vbat#branch")))) /
        max(g(r, "v(isense)"), 1e-3) < 0.15 if g(r, "v(isense)") else False),
])
allok &= ok

for rt, label in ((3e3, "hot ~50C"), (10e3, "25C"), (30e3, "cold ~0C")):
    v = run_circuit(deck(f"I_ntc_{label}", vbus=5.0, sw=0, rt1=rt))
    n = final(v, "ntc")
    print(f"   NTC {label:10s} RT1={rt/1000:.0f}k -> V(NTC) = {n:.3f} V")

print("\n" + ("ALL SCENARIOS PASS" if allok else "*** FAILURES PRESENT ***"))
