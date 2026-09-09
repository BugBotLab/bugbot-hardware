"""Static checks the simulation cannot make: pins the models do not use,
straps, address uniqueness, pull-ups, connector pairing. Read straight from
the golden netlists against the CONFIRMED datasheet pin tables in
parts_spec.PARTS[...]["pinout"].

    python check_static.py            (also run at the start of sim_stack.py)

Why: the DRV8830 pinout error (2026-09-04) passed every ngspice scenario
because the simulation and the schematic shared the same wrong pin table.
These checks tie each IC pin to what the DATASHEET says must be on it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist2spice import Board, parse_val
from parts_spec import PARTS
from paths import netlist

RESULTS = []


def chk(desc, ok, detail=""):
    RESULTS.append((desc, bool(ok)))
    print("   %s  %s%s" % ("PASS" if ok else "FAIL", desc, ("  [" + detail + "]") if detail else ""))
    return bool(ok)


def leaf(net):
    return (net or "").rsplit("/", 1)[-1]


def netname(B, ref, pin):
    return B.pinnet.get((ref, pin))


def is_gnd(n):
    return n == "GND"


def is_open(n):
    return n is None or n.startswith("unconnected-")


def run(M, V, O=None):
    print("\n== STATIC: netlist against the datasheet pin tables")
    ok = True
    boards = [(M, "motion"), (V, "vision")] + ([(O, "odometry")] if O is not None else [])
    # ---- symbol pin NAMES vs the datasheet pin table (pinfunction carries the symbol's pin name)
    import xml.etree.ElementTree as ET
    for B, bd in boards:
        root = ET.parse(netlist(bd)).getroot()
        fn = {}
        for n in root.iter("net"):
            for nd in n.iter("node"):
                fn[(nd.get("ref"), nd.get("pin"))] = (nd.get("pinfunction") or "").rsplit("_", 1)[0]
        for ref, meta in B.comps.items():
            part = next((k for k in PARTS if "pinout" in PARTS[k] and meta["value"].startswith(k.split("-")[0])), None)
            if not part:
                continue
            table = PARTS[part]["pinout"]
            bad = []
            for pin, name in table.items():
                got = fn.get((ref, pin))
                if got is None:
                    continue
                def canon(x):
                    x = x.split(" ")[0].lower().replace("~{", "").replace("}", "").replace("/", "")
                    return {"nfault": "fault", "faultn": "fault", "stats": "stat", "pssync": "pssync",
                            "shdn": "en", "shutdown": "en", "ncadj": "adj",
                            "nboot_load_pin": "boot_load_pin", "nreset": "reset", "ncs": "cs"}.get(x, x)
                want, g2 = canon(name), canon(got)
                if want != g2 and not (want == "ep" or g2 == "ep" or want.startswith("gnd") and g2.startswith("gnd")):
                    bad.append("%s: datasheet %s, symbol %s" % (pin, name, got))
            ok &= chk("%s.%s %s symbol pin names match the datasheet table" % (B.prefix, ref, part), not bad, "; ".join(bad))

    # ---- DRV8830 (SLVSAB2F): straps, bus, supply
    addr = {("0", "0"): 0x60, ("0", "Z"): 0x61, ("0", "1"): 0x62, ("Z", "0"): 0x63, ("Z", "Z"): 0x64,
            ("Z", "1"): 0x65, ("1", "0"): 0x66, ("1", "Z"): 0x67, ("1", "1"): 0x68}
    seen = {}
    for ref in sorted(r for r, m in M.comps.items() if m["value"].startswith("DRV8830")):
        vcc, gnd, pad = netname(M, ref, "4"), netname(M, ref, "5"), netname(M, ref, "11")
        ok &= chk("%s pin 4 VCC on the motor rail, pin 5 GND and pad on GND" % ref,
                  leaf(vcc) == "VMOT" and is_gnd(gnd) and is_gnd(pad), "4=%s 5=%s 11=%s" % (leaf(vcc), gnd, pad))
        sda, scl = netname(M, ref, "9"), netname(M, ref, "10")
        ok &= chk("%s pin 9 SDA / pin 10 SCL on the I2C bus" % ref, leaf(sda) == "I2C_SDA" and leaf(scl) == "I2C_SCL",
                  "9=%s 10=%s" % (leaf(sda), leaf(scl)))

        def level(n):
            return "0" if is_gnd(n) else "Z" if is_open(n) else "1" if leaf(n) in ("VMOT", "VCC", "3V3", "VSYS") else "?"
        a0, a1 = level(netname(M, ref, "7")), level(netname(M, ref, "8"))
        a = addr.get((a1, a0))
        ok &= chk("%s address straps A1=%s A0=%s -> 0x%02X" % (ref, a1, a0, a or 0), a is not None and a not in seen.values(),
                  "duplicate of %s" % seen.get(a, "") if a in seen.values() else "")
        seen[ref] = a
        isn = netname(M, ref, "2")
        rs = [r for (r, p), n in M.pinnet.items() if n == isn and r.startswith("R")]
        rv = parse_val(M.comps[rs[0]]["value"]) if rs else None
        ok &= chk("%s ISENSE resistor %s = %s ohm -> limit %.0f mA (R <= 1 ohm)" % (ref, rs[0] if rs else "?", rv, 0.2 / rv * 1e3 if rv else 0),
                  rv is not None and rv <= 1.0)
        flt = netname(M, ref, "6")
        ok &= chk("%s FAULTn on MOT_INT" % ref, leaf(flt) == "MOT_INT", leaf(flt))
    pulls = [r for (r, p), n in M.pinnet.items() if leaf(n) == "MOT_INT" and r.startswith("R")]
    ok &= chk("MOT_INT has a pull-up (open-drain wire-OR)", bool(pulls), ",".join(pulls))

    # ---- TPS63020 (SLVS916I)
    u3 = next(r for r, m in M.comps.items() if m["value"].startswith("TPS63020"))
    vin = {netname(M, u3, p) for p in ("10", "11")}
    ok &= chk("U3 VIN pins 10/11 on one net, VINA 1 and EN 12 fed from it", len(vin) == 1 and netname(M, u3, "1") in vin and netname(M, u3, "12") in vin)
    ps = netname(M, u3, "13")
    ok &= chk("U3 PS/SYNC 13 tied (must not float): %s" % ("high = forced PWM" if ps in vin else "GND = power save" if is_gnd(ps) else "FLOATING"), not is_open(ps))
    ok &= chk("U3 VOUT pins 4/5 on 3V3", {leaf(netname(M, u3, "4")), leaf(netname(M, u3, "5"))} == {"3V3"})
    fb = netname(M, u3, "3")
    fbr = [r for (r, p), n in M.pinnet.items() if n == fb and r.startswith("R")]
    if len(fbr) == 2:
        vals = {r: parse_val(M.comps[r]["value"]) for r in fbr}
        top = [r for r in fbr if leaf(M.pinnet[(r, "1")]) == "3V3" or leaf(M.pinnet[(r, "2")]) == "3V3"]
        bot = [r for r in fbr if r not in top]
        vout = 0.5 * (1 + vals[top[0]] / vals[bot[0]]) if top and bot else 0
        ok &= chk("U3 FB divider %s/%s -> VOUT = %.3f V (3.2-3.4)" % (top[0] if top else "?", bot[0] if bot else "?", vout), 3.2 < vout < 3.4)
    else:
        ok &= chk("U3 FB divider present (2 resistors on FB)", False, ",".join(fbr))
    l1 = {netname(M, u3, "8"), netname(M, u3, "9")}
    l2 = {netname(M, u3, "6"), netname(M, u3, "7")}
    lref = [r for r, m in M.comps.items() if r.startswith("L") and {M.pinnet.get((r, "1")), M.pinnet.get((r, "2"))} == (l1 | l2)]
    ok &= chk("U3 L1 (8/9) and L2 (6/7) paired and bridged by the inductor %s" % (lref[0] if lref else "?"), len(l1) == 1 and len(l2) == 1 and bool(lref))
    ok &= chk("U3 GND 2 and PGND pad 15 on GND", is_gnd(netname(M, u3, "2")) and is_gnd(netname(M, u3, "15")))

    # ---- ETA6003 (V2.7 p4)
    u1 = next(r for r, m in M.comps.items() if m["value"].startswith("ETA6003"))
    ok &= chk("U1 IN 2 on VBUS", leaf(netname(M, u1, "2")) == "VBUS", leaf(netname(M, u1, "2")))
    ok &= chk("U1 SYS 1/15 on VSYS, BATT 14/16 on the protected cell net",
              {leaf(netname(M, u1, "1")), leaf(netname(M, u1, "15"))} == {"VSYS"} and len({netname(M, u1, "14"), netname(M, u1, "16")}) == 1)
    ok &= chk("U1 SW 3/4 to the charger inductor", len({netname(M, u1, "3"), netname(M, u1, "4")}) == 1 and any(
        netname(M, u1, "3") in (M.pinnet.get((r, "1")), M.pinnet.get((r, "2"))) for r in M.comps if r.startswith("L")))
    ok &= chk("U1 ENB 6 low (charging enabled)", is_gnd(netname(M, u1, "6")))
    ok &= chk("U1 USB_DET 13 low (fast-charge current from ISET1)", is_gnd(netname(M, u1, "13")))
    enppb = netname(M, u1, "8")
    r4 = [r for (r, p), n in M.pinnet.items() if n == enppb and r.startswith("R")]
    other = [M.pinnet.get((r4[0], "1" if M.pinnet.get((r4[0], "2")) == enppb else "2"))] if r4 else []
    ok &= chk("U1 ENPPB 8 pulled to GND (power path enabled, not shipping mode)", is_gnd(enppb) or (other and is_gnd(other[0])), str(other))
    for pin, nm in (("11", "ISET1"), ("12", "ISET2")):
        n = netname(M, u1, pin)
        rr = [r for (r, p), q in M.pinnet.items() if q == n and r.startswith("R")]
        rv = parse_val(M.comps[rr[0]]["value"]) if rr else None
        ok &= chk("U1 %s resistor %s -> %.0f mA charge" % (nm, rr[0] if rr else "?", 1000e3 / rv if rv else 0), rv is not None and 1000.0 / rv <= 2.5)
    ntc = netname(M, u1, "7")
    ok &= chk("U1 NTC 7 has a divider (resistor + thermistor)", sum(1 for (r, p), q in M.pinnet.items() if q == ntc and r[0] == "R") >= 2)
    ok &= chk("U1 PGND 5, GND 10, EP 17 on GND", all(is_gnd(netname(M, u1, p)) for p in ("5", "10", "17")))

    # ---- USB front end
    u5 = next((r for r, m in M.comps.items() if m["value"].startswith("USBLC6")), None)
    if u5:
        ok &= chk("U5 USBLC6 I/O1 pins 1/6 paired, I/O2 pins 3/4 paired, 5 on VBUS, 2 on GND",
                  netname(M, u5, "1") == netname(M, u5, "6") and netname(M, u5, "3") == netname(M, u5, "4")
                  and leaf(netname(M, u5, "5")) == "VBUS" and is_gnd(netname(M, u5, "2")))
    cc = [r for r, m in M.comps.items() if r.startswith("R") and "5k1" in m["value"]]
    ok &= chk("USB-C CC1/CC2 each have a 5.1k Rd to GND (sink)", len(cc) == 2 and all(
        is_gnd(M.pinnet.get((r, "2"))) or is_gnd(M.pinnet.get((r, "1"))) for r in cc), ",".join(cc))

    # ---- the stack sockets J8/J9: Motion pin k must carry the same signal as Vision pin k (2026-09-07 rework moved
    #      SW_ON to J8.9 and the servo signals to J9.6/J9.7)
    bad = []
    for j in ("J8", "J9"):
        for k in range(1, 11):
            a, b_ = leaf(netname(M, j, str(k))), leaf(netname(V, j, str(k)))
            if a != b_:
                bad.append("%s.%d Motion %s / Vision %s" % (j, k, a, b_))
    ok &= chk("J8/J9 stack: all 20 pins carry the same signal on both boards", not bad, "; ".join(bad))
    ok &= chk("SW_ON on J8.9 both sides, SERVO1/2_SIG on J9.6/J9.7 both sides",
              leaf(netname(M, "J8", "9")) == "SW_ON" == leaf(netname(V, "J8", "9")) and leaf(netname(M, "J9", "6")) == "SERVO1_SIG" and leaf(netname(V, "J9", "7")) == "SERVO2_SIG")
    sw3 = next((r for r, m in V.comps.items() if m["value"].startswith("MSK12C02")), None)
    ok &= chk("V.%s slide switch: pin 1 on SW_ON, pin 2 on GND (grounds the Motion gate divider through the stack)" % sw3,
              sw3 is not None and leaf(netname(V, sw3, "1")) == "SW_ON" and is_gnd(netname(V, sw3, "2")))
    for r in ("J10", "J11"):
        ok &= chk("M.%s servo connector: pin 1 signal from the P4, pin 2 VMOT, pin 3 GND" % r,
                  leaf(netname(M, r, "1")).startswith("SERVO") and leaf(netname(M, r, "2")) == "VMOT" and is_gnd(netname(M, r, "3")))

    # ---- Odometry board (2026-09-06): the J7 cable, the 1.9 V LDO, the flow sensor, the IMU
    if O is not None:
        ok &= odometry_checks(M, V, O)

    # ---- I2C pull-ups: exactly one pair on the whole stack, on 3V3
    pu = []
    for B, _ in boards:
        for (r, p), n in B.pinnet.items():
            if r.startswith("R") and leaf(n) in ("I2C_SDA", "I2C_SCL"):
                o = B.pinnet.get((r, "2" if p == "1" else "1"))
                pu.append((B.prefix, r, leaf(n), leaf(o), parse_val(B.comps[r]["value"])))
    ok &= chk("I2C: one pull-up per line on the stack, to 3V3", len(pu) == 2 and {x[2] for x in pu} == {"I2C_SDA", "I2C_SCL"}
              and all(x[3] == "3V3" for x in pu), "; ".join("%s.%s %s->%s %.0f" % x for x in pu))
    if pu:
        r = pu[0][4]
        ok &= chk("I2C: pull-up %.0f ohm sinks %.1f mA at 3.3 V (<= 3 mA Fast-mode IOL)" % (r, 3.3 / r * 1e3), 3.3 / r <= 3e-3)

    # ---- every power_in pin of every IC sits on a named power net
    for B, bd in boards:
        root = ET.parse(netlist(bd)).getroot()
        bad = []
        for n in root.iter("net"):
            for nd in n.iter("node"):
                if nd.get("ref", "").startswith("U") and (nd.get("pintype") or "").startswith("power_in") and n.get("name", "").startswith("unconnected"):
                    bad.append("%s.%s" % (nd.get("ref"), nd.get("pin")))
        ok &= chk("%s: no IC power_in pin left unconnected" % B.prefix, not bad, ",".join(bad))
        floating = []
        for n in root.iter("net"):
            for nd in n.iter("node"):
                if nd.get("ref", "").startswith("U") and (nd.get("pintype") or "") == "input" and n.get("name", "").startswith("unconnected"):
                    floating.append("%s.%s %s" % (nd.get("ref"), nd.get("pin"), nd.get("pinfunction")))
        # DRV8830 address pins are allowed open (= "Z" level); everything else is a finding
        floating = [f for f in floating if not ("A0" in f or "A1" in f)]
        ok &= chk("%s: no IC input pin floating (DRV8830 A0/A1 may be open by design)" % B.prefix, not floating, ",".join(floating))
    return ok


def odometry_checks(M, V, O):
    """The Odometry board against its datasheets and against the cable it
    hangs on. Since 2026-09-07 Odometry J1 is the mirror image of Motion J7
    (same XY, rotated 180, pins reversed: Motion J7 pin k = Odometry J1 pin 11-k)
    so the two top-entry connectors face each other and a same-side GH cable
    runs straight between them."""
    ok = True
    # ---- the cable: same net leaf on both ends of every pin (reversed order)
    bad = []
    for k in range(1, 11):
        a, b = leaf(netname(M, "J7", str(k))), leaf(netname(O, "J1", str(11 - k)))
        if a != b:
            bad.append("Motion J7.%d %s / Odometry J1.%d %s" % (k, a, 11 - k, b))
    ok &= chk("J7 -> J1 cable (pin k -> pin 11-k): all 10 pins carry the same signal at both ends", not bad, "; ".join(bad))
    ok &= chk("J7: 3V3 on pin 1, GND on pins 2 and 10; J1: 3V3 on pin 10, GND on pins 9 and 1",
              leaf(netname(M, "J7", "1")) == "3V3" and is_gnd(netname(M, "J7", "2")) and is_gnd(netname(M, "J7", "10"))
              and leaf(netname(O, "J1", "10")) == "3V3" and is_gnd(netname(O, "J1", "9")) and is_gnd(netname(O, "J1", "1")))

    # ---- AP2127K-ADJ 1.9 V LDO for the sensor core
    u1 = next((r for r, m in O.comps.items() if m["value"].startswith("AP2127K")), None)
    if u1:
        ok &= chk("O.U1 VIN 1 on 3V3, GND 2 on GND, EN 3 tied to VIN (always on)",
                  leaf(netname(O, u1, "1")) == "3V3" and is_gnd(netname(O, u1, "2")) and netname(O, u1, "3") == netname(O, u1, "1"))
        adj = netname(O, u1, "4")
        rr = [r for (r, p), n in O.pinnet.items() if n == adj and r.startswith("R")]
        vout = None
        if len(rr) == 2:
            vals = {r: parse_val(O.comps[r]["value"]) for r in rr}
            vo = netname(O, u1, "5")
            top = [r for r in rr if vo in (O.pinnet.get((r, "1")), O.pinnet.get((r, "2")))]
            bot = [r for r in rr if r not in top]
            if top and bot:
                vout = PARTS["AP2127K-ADJ"]["model"]["vref"] * (1 + vals[top[0]] / vals[bot[0]])
        lo, hi = PARTS["PMW3360"]["limits"]["vdd"]
        ok &= chk("O.U1 ADJ divider %s -> VOUT = %s V, inside the PMW3360 VDD window %.1f-%.1f V"
                  % ("/".join(rr), "%.3f" % vout if vout else "?", lo, hi), vout is not None and lo < vout < hi)
        ok &= chk("O.U1 VOUT 5 on the 1V9 net that feeds the sensor", leaf(netname(O, u1, "5")) == "1V9")

    # ---- PMW3360 optical flow sensor (PixArt datasheet v1.30 Table 1: 3 VDDPIX, 4 VDD, 5 VDDIO,
    #      7 NRESET, 8 GND, 9 MOTION, 10 SCLK, 11 MOSI, 12 MISO, 13 NCS, 15 LED_P; 1/2/6/14/16 NC)
    u2 = next((r for r, m in O.comps.items() if m["value"].startswith("PMW3360")), None)
    if u2:
        ok &= chk("O.U2 VDD 4 on 1V9, VDDIO 5 on 3V3, GND 8 on GND",
                  leaf(netname(O, u2, "4")) == "1V9" and leaf(netname(O, u2, "5")) == "3V3" and is_gnd(netname(O, u2, "8")))
        for pin, sig in (("9", "FLOW_MOTION"), ("10", "FLOW_SCLK"), ("11", "FLOW_MOSI"), ("12", "FLOW_MISO"), ("13", "FLOW_NCS")):
            ok &= chk("O.U2 pin %s on %s (reaches Motion J7 by the same name)" % (pin, sig),
                      leaf(netname(O, u2, pin)) == sig and sig in {leaf(netname(M, "J7", str(k))) for k in range(1, 11)},
                      leaf(netname(O, u2, pin)))

        def pulled_to(net, rail):
            for (r, p), n in O.pinnet.items():
                if n == net and r.startswith("R"):
                    o = O.pinnet.get((r, "2" if p == "1" else "1"))
                    if leaf(o) == rail:
                        return r
            return None
        ok &= chk("O.U2 nRESET 7 pulled up to VDDIO (3V3)", pulled_to(netname(O, u2, "7"), "3V3") is not None or leaf(netname(O, u2, "7")) == "3V3")
        ok &= chk("O.U2 nCS 13 pulled up (deselected while the P4 boots)", pulled_to(netname(O, u2, "13"), "3V3") is not None)
        ledp = netname(O, u2, "15")
        rl = [r for (r, p), n in O.pinnet.items() if n == ledp and r.startswith("R")]
        ok &= chk("O.U2 LED_P 15 fed through a series resistor from 1V9 (%s)" % ",".join(rl),
                  bool(rl) and pulled_to(ledp, "1V9") is not None)
        ok &= chk("O.U2 VDDPIX 3 decoupled (internal regulator output)",
                  any(r.startswith("C") for (r, p), n in O.pinnet.items() if n == netname(O, u2, "3")))

    # ---- BNO055 IMU (Bosch DS000 Table 4-1)
    u3 = next((r for r, m in O.comps.items() if m["value"].startswith("BNO055")), None)
    if u3:
        ok &= chk("O.U3 VDD 3 and VDDIO 28 on 3V3, GND 2 / GNDIO 25 on GND",
                  leaf(netname(O, u3, "3")) == "3V3" and leaf(netname(O, u3, "28")) == "3V3"
                  and is_gnd(netname(O, u3, "2")) and is_gnd(netname(O, u3, "25")))
        ok &= chk("O.U3 PS1 5 = PS0 6 = GND: I2C interface selected", is_gnd(netname(O, u3, "5")) and is_gnd(netname(O, u3, "6")))
        com3 = netname(O, u3, "17")
        addr = PARTS["BNO055"]["model"]["addr_com3_low"] if is_gnd(com3) else PARTS["BNO055"]["model"]["addr_com3_high"] if leaf(com3) == "3V3" else None
        ok &= chk("O.U3 COM3 17 tied -> I2C address 0x%02X (must not float)" % (addr or 0), addr is not None)
        tof = PARTS["VL53L5CX_addr"]["model"]["addr"]
        drv = set(PARTS["DRV8830"]["addresses"].values())
        ok &= chk("O.U3 address 0x%02X clashes with nothing on the bus (ToF 0x%02X, DRV8830s 0x60-0x68)" % (addr or 0, tof),
                  addr is not None and addr != tof and addr not in drv)
        ok &= chk("O.U3 COM0 20 = SDA, COM1 19 = SCL (I2C pin assignment)",
                  leaf(netname(O, u3, "20")) == "I2C_SDA" and leaf(netname(O, u3, "19")) == "I2C_SCL",
                  "20=%s 19=%s" % (leaf(netname(O, u3, "20")), leaf(netname(O, u3, "19"))))
        ok &= chk("O.U3 COM2 18 tied (unused in I2C mode, must not float)", not is_open(netname(O, u3, "18")))
        for pin, nm in (("4", "nBOOT_LOAD_PIN"), ("11", "nRESET")):
            n = netname(O, u3, pin)
            rr = [r for (r, p), q in O.pinnet.items() if q == n and r.startswith("R")]
            up = any(leaf(O.pinnet.get((r, "2" if O.pinnet.get((r, "1")) == n else "1"))) == "3V3" for r in rr)
            ok &= chk("O.U3 %s %s pulled up to VDDIO (%s)" % (nm, pin, ",".join(rr)), up)
        ok &= chk("O.U3 CAP 9 has its capacitor to GND",
                  any(r.startswith("C") for (r, p), n in O.pinnet.items() if n == netname(O, u3, "9")))
        xin, xout = netname(O, u3, "27"), netname(O, u3, "26")
        y = [r for (r, p), n in O.pinnet.items() if r.startswith("Y") and n in (xin, xout)]
        cx = [r for (r, p), n in O.pinnet.items() if r.startswith("C") and n in (xin, xout)]
        ok &= chk("O.U3 XIN32/XOUT32: 32.768 kHz crystal %s with load caps %s (or both open = internal oscillator)"
                  % (",".join(sorted(set(y))), ",".join(sorted(set(cx)))),
                  (len(set(y)) == 1 and len(set(cx)) == 2) or (is_open(xin) and is_open(xout)))
        for pin, nm in (("10", "BL_IND"), ("14", "INT")):
            ok &= chk("O.U3 %s %s is an output: open or routed, never tied to a rail" % (nm, pin),
                      leaf(netname(O, u3, pin)) not in ("3V3", "1V9") and not is_gnd(netname(O, u3, pin)))
    return ok


if __name__ == "__main__":
    ok = run(Board(netlist("motion"), "M"), Board(netlist("vision"), "V"), Board(netlist("odometry"), "O"))
    print("\nSTATIC: %s (%d checks)" % ("all pass" if ok else "FAILURES", len(RESULTS)))
