"""Turn a KiCad golden_netlist.xml into SPICE elements - the REAL connectivity.

Why not hand-write the deck (as sim_power_tree.py did): a hand-written deck
mirrors what the author believes the schematic says. Building the deck from
the netlist means a swapped label, a pin on the wrong net or a strap left
floating shows up in the simulation, which is the whole point of a
"realistic" testbench (the alpha_3 board shipped with two crossed labels
that a netlist-driven sim would have caught).

Every component becomes a SPICE element by RULE (see RULES): passives from
their value field, FETs by pin number, ICs as behavioural subcircuits with
their pins mapped by NUMBER from the datasheet pin table, connectors as
nothing (their pin nets are exported so the harness can attach sources,
loads and the other board). Pins the models do not use are left floating;
`.option rshunt` in the harness keeps the matrix non-singular.

    from netlist2spice import Board
    m = Board(xml_path, prefix="M")
    lines = m.elements()          # list of SPICE cards
    m.net("VMOT")                 # SPICE node name of the net whose leaf is VMOT
    m.pin("J8", "5")              # node the connector pin sits on
"""
import os
import re
import xml.etree.ElementTree as ET


def parse_val(s):
    """'5k1 Rd' -> 5100, '1k24' -> 1240, '0R5' -> 0.5, '10m 3W' -> 0.01,
    '100n' -> 1e-7, '1uH 4.5A' -> 1e-6, '22u' -> 2.2e-5."""
    s = s.strip()
    m = re.match(r"(\d+)([kKmMuUnNpPrR])(\d+)", s)          # 5k1, 1k24, 0R5
    if m:
        whole, suf, frac = m.groups()
        n = float(whole + "." + frac)
    else:
        m = re.match(r"([\d.]+)\s*([kKmMuUnNpPrR]?)", s)
        if not m:
            raise ValueError("cannot parse value %r" % s)
        n, suf = float(m.group(1)), m.group(2)
    # KiCad values are case-sensitive where it matters: "1M" is a megohm,
    # "10m" is ten milliohms. Folding case turned R16's 1 M into 1 mOhm and
    # shorted the 3V3 rail into its feedback divider (2026-09-04).
    if suf == "M":
        mult = 1e6
    else:
        mult = {"k": 1e3, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "r": 1, "": 1}[suf.lower()]
    return n * mult


def sanitize(net):
    if net == "GND":
        return "0"
    s = re.sub(r"[^A-Za-z0-9_]", "_", net.strip("/"))
    return s.strip("_")


# pin maps: symbol pin NUMBER -> subckt port, per part VALUE prefix
RULES = {
    # value prefix : (subckt, [(port, [pin numbers])])
    "ETA6003": ("ETA6003PP", [("vbus", ["2"]), ("sys", ["1", "15"]), ("batt", ["14", "16"]),
                              ("enb", ["6"]), ("iset1", ["11"]), ("ntc", ["7"]), ("stats", ["9"])]),
    "TPS63020": ("TPS63020", [("in", ["10", "11"]), ("en", ["12"]), ("out", ["4", "5"]),
                              ("fb", ["3"]), ("l1", ["8", "9"]), ("l2", ["6", "7"])]),
    # TI SLVSAB2F Table 1 (DGQ): 1 OUT2, 2 ISENSE, 3 OUT1, 4 VCC, 5 GND, 6 FAULTn,
    # 7 A0, 8 A1, 9 SDA, 10 SCL. (The first table here was wrong, 2026-09-04.)
    "DRV8830": ("DRV8830", [("vcc", ["4"]), ("out1", ["3"]), ("out2", ["1"]), ("isense", ["2"]),
                            ("fault", ["6"]), ("scl", ["10"]), ("sda", ["9"])]),
    "USBLC6": ("USBLC6", [("io1", ["1"]), ("io2", ["3"]), ("vbus", ["5"])]),
    "SI2333": ("SI2333_FET", None),      # MOSFET: handled specially (M element)
    "WS2812": (None, None),
    # ---- Odometry board (2026-09-06)
    # Diodes AP2127K-ADJ DS36478, SOT-23-5: 1 VIN, 2 GND, 3 EN, 4 ADJ, 5 VOUT
    "AP2127K": ("AP2127KADJ", [("in", ["1"]), ("gnd", ["2"]), ("en", ["3"]), ("out", ["5"]), ("fb", ["4"])]),
    # Bosch BNO055 LGA-28: 3 VDD, 28 VDDIO, 2 GND / 25 GNDIO (a load: its bus
    # pins are open-drain I2C and carry no DC)
    "BNO055": ("BNO055_LD", [("vdd", ["3"]), ("vddio", ["28"]), ("gnd", ["2", "25"])]),
    # PixArt PMW3360DM-T2QU, alpha-board symbol (datasheet not obtainable):
    # 4 VDD (1.9 V), 5 VDDIO, 3 VDDPIX (internal regulator out), 15 LED_P, 8 GND
    "PMW3360": ("PMW3360_LD", [("vdd", ["4"]), ("vddio", ["5"]), ("vddpix", ["3"]), ("ledp", ["15"]), ("gnd", ["8"])]),
}


class Board:
    def __init__(self, xml_path, prefix):
        self.prefix = prefix
        root = ET.parse(xml_path).getroot()
        self.comps = {c.get("ref"): {"value": c.findtext("value") or "",
                                     "footprint": c.findtext("footprint") or ""}
                      for c in root.iter("comp")}
        self.pinnet = {}          # (ref, pin) -> raw net name
        self.nets = {}            # raw net name -> [(ref, pin)]
        for n in root.iter("net"):
            name = n.get("name")
            for node in n.iter("node"):
                self.pinnet[(node.get("ref"), node.get("pin"))] = name
                self.nets.setdefault(name, []).append((node.get("ref"), node.get("pin")))
        self.unused = []

    # ------------------------------------------------------------- naming
    def node(self, rawnet):
        if rawnet == "GND":
            return "0"
        return self.prefix + "_" + sanitize(rawnet)

    def net(self, leaf):
        """SPICE node for the net whose last path element is `leaf`."""
        hits = [n for n in self.nets if n.rsplit("/", 1)[-1] == leaf]
        if len(hits) != 1:
            raise KeyError("net leaf %r: %s" % (leaf, hits or "not found"))
        return self.node(hits[0])

    def pin(self, ref, num):
        raw = self.pinnet.get((ref, num))
        if raw is None:
            return None
        return self.node(raw)

    def pins_of(self, ref):
        return {p: self.node(n) for (r, p), n in self.pinnet.items() if r == ref}

    # ------------------------------------------------------------ elements
    def elements(self, overrides=None):
        """SPICE cards for every component. overrides: {ref: card or None}
        lets the harness replace/skip a part (e.g. a switch, a thermistor)."""
        overrides = overrides or {}
        out = []
        self.unused = []
        for ref, meta in sorted(self.comps.items()):
            if ref in overrides:
                if overrides[ref]:
                    out.append(overrides[ref])
                continue
            val = meta["value"]
            pins = self.pins_of(ref)
            kind = ref.rstrip("0123456789")
            tag = self.prefix + "_" + ref
            if kind in ("R", "RSH", "RT"):
                out.append("R%s %s %s %s" % (tag, pins["1"], pins["2"], parse_val(val)))
            elif kind in ("C", "CB"):
                out.append("C%s %s %s %s" % (tag, pins["1"], pins["2"], parse_val(val)))
            elif kind == "L":
                out.append("L%s %s %s %s" % (tag, pins["1"], pins["2"], parse_val(val)))
            elif kind == "F":                                  # PTC: 30 mOhm cold
                out.append("R%s %s %s 30m" % (tag, pins["1"], pins["2"]))
            elif kind == "Q" and val.startswith("SI2333"):
                # KiCad Q_PMOS carries its pins as G/D/S in the netlist
                # (numbered 1/2/3 on older symbols); ngspice M: d g s
                d = pins.get("D", pins.get("3"))
                g = pins.get("G", pins.get("1"))
                s = pins.get("S", pins.get("2"))
                # VDMOS takes THREE nodes (d g s); a fourth is silently taken
                # as the model name and the FET stops being a FET
                out.append("M%s %s %s %s SI2333" % (tag, d, g, s))
            elif kind == "U":
                rule = next((RULES[k] for k in RULES if val.startswith(k)), None)
                if rule is None or rule[0] is None:
                    self.unused.append(ref)
                    continue
                sub, ports = rule
                nodes = []
                for port, nums in ports:
                    nets = {pins.get(n) for n in nums} - {None}
                    if len(nets) > 1:
                        raise ValueError("%s: pins %s of port %s sit on different nets %s"
                                         % (ref, nums, port, nets))
                    nodes.append(nets.pop() if nets else "%s_%s_%s_nc" % (self.prefix, ref, port))
                out.append("X%s %s %s" % (tag, " ".join(nodes), sub))
            else:
                self.unused.append(ref)      # connectors, switches, holes, LEDs
        return out

    def report(self):
        return "%s: %d parts, %d nets, not modelled: %s" % (
            self.prefix, len(self.comps), len(self.nets), ", ".join(self.unused) or "none")
