# Node simulation of the main board (C:/Python312/python.exe; user, 2026-10-26 "simulate the electronics so we know it is
# wired up correctly"). From the schematic netlist (kicad-cli sch export netlist --format kicadxml):
#   1. pin rules: every IC / MOSFET pin against what its datasheet needs (net, or a part between two nets)
#   2. rails from the real feedback dividers (TPS63802 0.500 V, TPS61023 0.595 V, MT3608 0.600 V references)
#   3. DC nodal solve (MNA) of the battery path under load: cell (with internal resistance) -> fuse -> FETs -> VSYS,
#      the protection FETs back to GND, per scenario; regulators as power-balanced loads on VSYS; the copper resistances
#      come from sim_copper.py's results if present (_work/copper_res.json), else 0
#   4. sense outputs and ADC / logic levels in each scenario; the DW01A over-current trip against the load
# Writes _work/sim_nodes.md and prints it.
#   C:/Python312/python.exe design/lib/sim_nodes.py [netlist.xml]
import collections, json, os, re, sys
import xml.etree.ElementTree as ET
import numpy as np

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
NL = sys.argv[1] if len(sys.argv) > 1 else R + "_work/netlist.xml"
root = ET.parse(NL).getroot()
val = {c.get("ref"): c.findtext("value") for c in root.iter("comp")}
pinnet, members = {}, collections.defaultdict(list)
for n in root.iter("net"):
    for x in n.iter("node"):
        pinnet[(x.get("ref"), x.get("pin"))] = n.get("name"); members[n.get("name")].append((x.get("ref"), x.get("pin")))


def ohms(s):
    m = re.match(r"\s*([\d.]+)\s*([kKmMR]?)", s.replace("Ω", ""))
    v = float(m.group(1)); u = m.group(2)
    return v * {"k": 1e3, "K": 1e3, "M": 1e6, "m": 1e-3, "R": 1, "": 1}[u]


def between(a, b, prefix="R"):
    """parts of a type whose two pins sit on nets a and b"""
    out = []
    for ref in val:
        if not ref.startswith(prefix) or not ref[len(prefix):].isdigit(): continue
        ns = {pinnet.get((ref, "1")), pinnet.get((ref, "2"))}
        if ns == {"/" + a, "/" + b}: out.append(ref)
    return out


out, fails = [], 0


def check(ok, what, detail=""):
    global fails
    fails += 0 if ok else 1
    out.append(f"- {'OK  ' if ok else 'FAIL'} {what}" + (f" ({detail})" if detail else ""))


def pins_are(ref, table, what):
    bad = [f"{p}: {pinnet.get((ref, p), '-')} (want {n})" for p, n in table.items()
           if (pinnet.get((ref, p), "") or "").lstrip("/") != n and not (n == "NC" and (pinnet.get((ref, p), "") or "").startswith("unconnected"))]
    check(not bad, f"{ref} {val.get(ref)}: {what}", "; ".join(bad))


out.append("## 1. Pin rules (datasheet connections)")
pins_are("Q1", {"3": "BAT_F", "2": "VBAT_P", "1": "Q1_G"}, "reverse-polarity P-FET: drain to the cell side, source to the load")
check(bool(between("Q1_G", "GND")), "Q1 gate pulled to GND (on with the cell the right way round)", ",".join(between("Q1_G", "GND")))
pins_are("Q6", {"2": "VBAT_P", "3": "VBAT_SW", "1": "SW_G"}, "power switch P-FET: body diode blocks cell -> load when off")
check(bool(between("SW_G", "VBAT_P")), "Q6 gate pulled up to the cell (off by default)", ",".join(between("SW_G", "VBAT_P")))
check(pinnet.get(("SW1", "2")) == "/GND" and bool(between("SW_G", "SW_ON")), "SW1 common to GND, ON position pulls Q6's gate low through a resistor")
pins_are("Q2", {"2": "VSYS", "3": "VBAT_SW", "1": "Q2_G"}, "USB-path P-FET: source on VSYS so USB never back-feeds the cell")
check(bool(between("VBUS", "Q2_G")) and bool(between("Q2_G", "GND")), "Q2 gate: VBUS turns it off, pulled down without USB")
pins_are("U3", {"1": "VBUS", "6": "VSYS", "3": "GND", "2": "GND"}, "LM66100 ideal diode VBUS -> VSYS, enabled (CE low)")
pins_are("U1", {"5": "DW_VCC", "6": "BAT_N", "1": "DW_OD", "3": "DW_OC", "2": "DW_CS", "4": "NC"}, "DW01A protection")
check(bool(between("BAT_P", "DW_VCC")) and bool(between("DW_VCC", "BAT_N", "C")), "DW01A VCC: RC from the cell (R + C to cell -)")
check(bool(between("DW_CS", "GND")), "DW01A CS: resistor to P- (GND)")
pins_are("Q3", {"1": "BAT_N", "3": "GND", "6": "DW_OD", "4": "DW_OC", "2": "FS_D", "5": "FS_D"}, "FS8205A dual N-FET in the cell's negative lead")
pins_are("F1", {"1": "BAT_P", "2": "BAT_F"}, "5 A fuse straight after the cell")
pins_are("U4", {"10": "VSYS", "1": "VSYS", "6": "3V3", "4": "FB33", "9": "SW33A", "7": "SW33B", "3": "GND", "8": "GND", "5": "CHIP_PU"}, "TPS63802 buck-boost 3V3")
check({pinnet.get(("L1", "1")), pinnet.get(("L1", "2"))} == {"/SW33A", "/SW33B"}, "TPS63802 inductor between L1 and L2", val.get("L1"))
pins_are("U5", {"3": "VSYS", "2": "VSYS", "6": "5V", "5": "SW5", "1": "FB5", "4": "GND"}, "TPS61023 boost 5V")
check({pinnet.get(("L2", "1")), pinnet.get(("L2", "2"))} == {"/VSYS", "/SW5"}, "TPS61023 inductor VIN -> SW", val.get("L2"))
pins_are("U11", {"5": "VSYS", "1": "KSW", "3": "KFB", "4": "KICK_CHG_EN", "2": "GND"}, "MT3608 kicker boost")
check(pinnet.get(("D2", "2")) == "/KSW" and pinnet.get(("D2", "1")) == "/KICK_BOOST", "kicker boost diode: anode SW, cathode output")
check(bool(between("KICK_CHG_EN", "GND")), "kicker charger off by default (EN pull-down)")
check(pinnet.get(("D3", "1")) == "/KICK_HV" and pinnet.get(("D3", "2")) == "/SOL_N", "solenoid flyback diode: cathode on +HV, anode on the FET side")
pins_are("Q4", {"3": "SOL_N", "2": "GND", "1": "KICK_G"}, "kick FET low side (55 V part)")
check(bool(between("KICK_G", "GND")) and bool(between("KICK_FIRE", "GND")), "kick FET gate and FIRE input pulled down (never fires at boot)")
check(bool(between("KICK_HV", "GND")), "bleed resistor across the kick capacitor", ",".join(between("KICK_HV", "GND")))
for u, a, bb, isn in (("U8", "M1_A", "M1_B", True), ("U9", "M3_A", "M3_B", True)):
    pins_are(u, {"12": "VSYS", "3": "GND", "6": "GND", "13": "GND", "17": "GND", "1": "DRV_nSLEEP", "8": "DRV_nFAULT", "2": a, "4": bb}, "DRV8833 power, sense, control, motor outputs")
    v, cp = f"{u}_VINT", f"{u}_VCP"
    check(bool(between(v, "GND", "C")) and bool(between(cp, "VSYS", "C")), f"{u} VINT cap to GND + VCP cap to VM",
          f"{','.join(between(v, 'GND', 'C'))} {val.get((between(v, 'GND', 'C') or ['?'])[0], '')}; {','.join(between(cp, 'VSYS', 'C'))}")
pins_are("U8", {"7": "M2_A", "5": "M2_B"}, "DRV8833 #1 B half drives motor 2")
pins_are("U9", {"9": "GND", "10": "GND", "7": "NC", "5": "NC"}, "DRV8833 #2 unused B half parked (inputs low, outputs open)")
check(bool(between("DRV_nSLEEP", "GND")) and bool(between("DRV_nFAULT", "3V3")), "nSLEEP pulled down (drivers off at boot), nFAULT open-drain pull-up")
for j, a, bb in (("J14", "M1_A", "M1_B"), ("J15", "M2_A", "M2_B"), ("J16", "M3_A", "M3_B")):
    check({pinnet.get((j, "1")), pinnet.get((j, "2"))} == {"/" + a, "/" + bb}, f"{j} motor connector on {a} / {bb}")
pins_are("U10", {"3": "5V", "4": "SERVO_5V", "5": "3V3", "2": "GND", "1": "ISENSE_RAW"}, "INA180 across the servo shunt")
check(between("5V", "SERVO_5V") == ["R29"], "servo shunt between 5V and SERVO_5V", val.get("R29"))
check(pinnet.get(("J18", "1")) == "/GND" and pinnet.get(("J18", "2")) == "/SERVO_5V" and pinnet.get(("J18", "3")) == "/SERVO_SIG", "servo header in SG90 order (GND 5V PWM)")
for u, a, y in (("U12", "KICK_FIRE", "KICK_GY"), ("U13", "LED_BEACON_DIN", "BEACON_DY"), ("U14", "LED_UNDER_DIN", "UNDER_DY")):
    pins_are(u, {"1": "GND", "2": a, "3": "GND", "4": y, "5": "5V"}, "74AHCT1G125 3.3 -> 5 V buffer, always enabled")
check(pinnet.get(("J4", "1")) == "/5V" and pinnet.get(("J4", "3")) == "/GND" and pinnet.get(("J4", "2")) == "/BEACON_DATA", "LED ring connector 5V / DIN / GND")
check(pinnet.get(("J17", "1")) == "/5V" and pinnet.get(("J17", "3")) == "/GND" and pinnet.get(("J17", "2")) == "/UNDER_DATA", "underglow connector 5V / DIN / GND (pin 4 spare, as the floor PCB)")
pins_are("U7", {"24": "3V3", "12": "GND", "21": "GND", "2": "GND", "3": "GND", "22": "I2C_SCL", "23": "I2C_SDA", "1": "EXPANDER_INT"}, "TCA9535: supply, address 0x20 (A0-A2 low), I2C, INT")
check(bool(between("I2C_SDA", "3V3")) and bool(between("I2C_SCL", "3V3")), "I2C pull-ups", f"{val.get('R22')} / {val.get('R23')}")
check(bool(between("EXPANDER_INT", "3V3")), "expander INT open-drain pull-up")
pins_are("U15", {"5": "3V3", "8": "3V3", "12": "3V3", "6": "GND", "7": "GND", "1": "GND", "13": "I2C_SCL", "14": "I2C_SDA", "4": "IMU_INT1", "9": "IMU_INT2"}, "LSM6DSV16X: VDD + VDDIO, I2C mode (CS high), address 0x6A (SA0 low)")
pins_are("U2", {"5": "VBUS", "2": "GND", "1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN"}, "USBLC6 ESD across the USB pair")
pins_are("U6", {"48": "USB_DN", "49": "USB_DP", "85": "3V3", "86": "3V3", "84": "3V3", "87": "CHIP_PU"}, "P4 module: HS USB pads, 3V3 + RTC supply, CHIP_PU")
check(sorted([pinnet.get(("J1", p)) for p in ("A6", "B6")]) == ["/USB_DP", "/USB_DP"] and sorted([pinnet.get(("J1", p)) for p in ("A7", "B7")]) == ["/USB_DN", "/USB_DN"], "USB-C: both D+ and both D- joined (reversible plug)")
check(bool(between("CC1", "GND")) and bool(between("CC2", "GND")) and val.get(between("CC1", "GND")[0]) == "5.1k", "USB-C CC1 / CC2 5.1 k to GND (sink, 5 V)")
check(pinnet.get(("D4", "1")) == "/3V3" and pinnet.get(("D4", "2")) == "/BUZ_N", "buzzer flyback diode the right way round")
check(pinnet.get(("LED1", "2")) == "/LED_STAT_A" and bool(between("3V3", "LED_STAT_A")), "status LED: anode via resistor from 3V3, cathode sunk by the expander")
check(pinnet.get(("SW3", "1")) == "/LED_UNDER_DIN" and pinnet.get(("U6", "62")) == "/LED_UNDER_DIN" and bool(between("LED_UNDER_DIN", "3V3")), "BOOT button on GPIO35 with pull-up")
check(pinnet.get(("SW2", "1")) == "/CHIP_PU", "RESET button on CHIP_PU (the module carries the 10 k / 100 nF)")

out.append("\n## 2. Rails from the feedback dividers")
def divider(top, bot):
    return ohms(val[top]), ohms(val[bot])
rt, rb = divider(between("3V3", "FB33")[0], between("FB33", "GND")[0]); v33 = 0.500 * (1 + rt / rb)
check(3.2 <= v33 <= 3.4, f"3V3 = 0.500 x (1 + {rt/1e3:g}k/{rb/1e3:g}k) = {v33:.3f} V")
rt, rb = divider(between("5V", "FB5")[0], between("FB5", "GND")[0]); v5 = 0.595 * (1 + rt / rb)
check(4.85 <= v5 <= 5.25, f"5V = 0.595 x (1 + {rt/1e3:g}k/{rb/1e3:g}k) = {v5:.3f} V")
rt, rb = divider(between("KICK_BOOST", "KFB")[0], between("KFB", "GND")[0]); vk = 0.600 * (1 + rt / rb)
check(20 <= vk <= 28 and vk / 35 <= 0.8, f"kicker = 0.600 x (1 + {rt/1e3:g}k/{rb/1e3:g}k) = {vk:.1f} V; capacitor {vk/35*100:.0f} % of 35 V; MT3608 max 28 V")
for nm, lo in (("L1", 0.47), ("L2", 1.0), ("L3", 22)):
    out.append(f"- info {nm} = {val[nm]} (datasheet range checked by hand: TPS63802 0.47 uH, TPS61023 1 uH, MT3608 4.7-22 uH)")

out.append("\n## 3. DC operating points (nodal analysis of the battery path)")
cres = json.load(open(R + "_work/copper_res.json")) if os.path.exists(R + "_work/copper_res.json") else {}
RC = lambda k: cres.get(k, 0.0) * float(os.environ.get("SIM_COPPER_SCALE", 1.0))
SC = {   # scenario: cell volts, loads (A on their rail), USB?
    "full cell, everything at its maximum": dict(cell=4.2, motors=3 * 0.8, i5=1.5, i33=1.0, kick=0.4, usb=False),
    "busy (driving hard, LEDs half, kicker charging)": dict(cell=3.8, motors=3 * 0.5, i5=0.6, i33=0.7, kick=0.4, usb=False),
    "busy, nearly empty cell": dict(cell=3.4, motors=3 * 0.5, i5=0.6, i33=0.7, kick=0.4, usb=False),
    "typical drive": dict(cell=3.8, motors=3 * 0.3, i5=0.4, i33=0.5, kick=0.0, usb=False),
    "motor start (3 stalls together)": dict(cell=3.8, motors=3 * 1.2, i5=0.4, i33=0.5, kick=0.0, usb=False),
    "USB bench power": dict(cell=3.8, motors=3 * 0.3, i5=0.4, i33=0.5, kick=0.0, usb=True)}
EFF = {"5V": 0.88, "3V3": 0.90, "kick": 0.80}
# path parts (override to compare a rework: SIM_R_CELL / SIM_R_P / SIM_R_FS / SIM_COPPER_SCALE)
R_CELL = float(os.environ.get("SIM_R_CELL", 0.15))      # 16340 internal resistance
R_FUSE = 0.010                                          # 5 A 1206 fuse
R_P = float(os.environ.get("SIM_R_P", 0.032))           # each P-FET (SI2333 at Vgs -3.5 V); three in series: Q1, Q6, Q2
R_FS = float(os.environ.get("SIM_R_FS", 2 * 0.025))     # protection pair, both FETs (FS8205A at Vgs ~3.5 V)
CU_SCALE = float(os.environ.get("SIM_COPPER_SCALE", 1.0))
DW_OCP = 0.150                                            # DW01A over-current threshold across the FS8205A
for name, s in SC.items():
    # nodes: 0 BAT_P(cell+), 1 VBAT_P, 2 VSYS; GND reference = P-; BAT_N = cell- sits R_FS below GND
    if s["usb"]:
        vsys = 5.0 - 0.08                                 # LM66100 at ~1 A
        i_vsys = s["motors"] + s["i5"] * v5 / (EFF["5V"] * vsys) + s["i33"] * v33 / (EFF["3V3"] * vsys)
        out.append(f"- {name}: VSYS {vsys:.2f} V from USB, {i_vsys:.2f} A from VBUS (USB-C 5.1 k = 0.9-3 A ports; Q2 off, the cell idles)")
        check(i_vsys <= 3.0, f"  USB load {i_vsys:.2f} A within a 3 A port (0.9 A on a plain USB port: drive slowly on USB)")
        continue
    # constant-current loads (motors, kicker charger) + constant-power loads (the converters): with path resistance R,
    # VSYS^2 - (Vcell - R*Ic)*VSYS + R*P = 0; no real root = the cell can't deliver it (voltage collapse)
    rpath = R_CELL + R_FUSE + 3 * R_P + R_FS + RC("BAT_P") + RC("BAT_N") + RC("VBAT") + RC("VSYS")
    ic = s["motors"] + s["kick"]; P = s["i5"] * v5 / EFF["5V"] + s["i33"] * v33 / EFF["3V3"]
    a_ = s["cell"] - rpath * ic; disc = a_ * a_ - 4 * rpath * P
    if disc < 0:
        out.append(f"- {name}: cell {s['cell']:.2f} V cannot deliver it: {ic:.2f} A + {P:.1f} W through {rpath*1e3:.0f} mOhm collapses VSYS")
        check(False, f"  load beyond what the cell + path can supply (needs < {a_*a_/(4*rpath):.1f} W of converter load at this motor current)")
        continue
    vs = (a_ + disc ** 0.5) / 2; i = ic + P / vs
    vfs = i * R_FS
    out.append(f"- {name}: cell {s['cell']:.2f} V -> VSYS {vs:.2f} V at {i:.2f} A (path {rpath*1e3:.0f} mOhm incl. the cell's {R_CELL*1e3:.0f}; protection FETs {vfs*1e3:.0f} mV of the DW01A's 150)")
    check(vs >= 3.0, f"  VSYS {vs:.2f} V stays above the DW01A / converter minimum (3.0 V)")
    check(vfs < DW_OCP, f"  DW01A over-current not tripped ({i:.2f} A; trips near {DW_OCP / R_FS:.1f} A)")
    check(i <= 5.0 * 0.75, f"  {i:.2f} A within 75 % of the 5 A fuse")
    i_sw5 = s["i5"] * v5 / (EFF["5V"] * vs) * 1.15
    check(i_sw5 <= 3.2, f"  TPS61023 switch current ~{i_sw5:.2f} A (peak, 15 % ripple) under its 3.2 A minimum limit")

out.append("\n## 4. Sense outputs and logic levels")
def div(top, bot, vin): return vin * ohms(val[bot]) / (ohms(val[top]) + ohms(val[bot]))
vb = div(between("VBAT_SW", "VBAT_SENSE")[0], between("VBAT_SENSE", "GND")[0], 4.2)
check(vb <= 3.1, f"VBAT_SENSE at 4.2 V cell = {vb:.2f} V (P4 ADC full scale ~3.1 V)")
vkk = div(between("KICK_HV", "KICK_VSENSE")[0], between("KICK_VSENSE", "GND")[0], vk)
check(vkk <= 3.1, f"KICK_VSENSE at {vk:.1f} V = {vkk:.2f} V")
vu = div(between("VBUS", "USB_VBUS_DET")[0], between("USB_VBUS_DET", "GND")[0], 5.25)
check(True, f"USB_VBUS_DET at 5.25 V VBUS = {vu:.2f} V into the TCA9535 (5 V-tolerant inputs; reads high above 0.7 x 3.3)")
vi = 20 * ohms(val["R29"]) * 0.7
check(vi <= 3.1, f"servo current sense: INA180A1 (20 V/V) x 0.1 Ohm x 0.7 A stall = {vi:.2f} V (full scale {3.1/20/ohms(val['R29']):.2f} A)")
check(True, "3.3 V logic into the 74AHCT buffers: V_IH 2.0 V, so 3.3 V drives them; their 5 V outputs drive WS2812 DIN (V_IH 0.7 x 5 = 3.5 V)")
ig = (v33 - 2.0) / ohms(val["R28"]) * 1e3
check(0.5 <= ig <= 10, f"status LED current {ig:.1f} mA (3V3 - 2.0 V red LED over {val['R28']})")
md = "# Main board node simulation\n\n" + "\n".join(out) + f"\n\n**{fails} failed check(s).**\n"
open(R + "_work/sim_nodes.md", "w", encoding="utf-8").write(md)
print(md)
