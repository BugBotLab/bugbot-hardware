# The WS1850S NFC reader circuit (WiseSun, MFRC522-compatible 13.56 MHz ISO 14443A, SPI mode; the datasheet's dual-TX
# circuit, fig. 3, matched to the floor PCB loop). One definition for every board that carries it:
#   make_nfc_floor.py   the antenna floor PCB (the reader lives here since 2026-10-31, approved 2D:
#                       mech/freecad/sketches/nfc_reader_on_floor.png)
#   make_nfc_boards.py  the old separate reader board (BugBot_NFC), kept buildable
# add_reader() puts the parts on a Design. Nets: 3V3 GND SCK MOSI MISO NSS RST IRQ (to the main board's J20) and the two
# antenna ends ant = (TX2 side, TX1 side). Every part checked on JLC (design/lib/jlc_find.py); LCSC numbers in the BOM.
QFN = "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm"
C04, C06, R04, R06 = "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric", "Resistor_SMD:R_0402_1005Metric", "Resistor_SMD:R_0603_1608Metric"
L06 = "Inductor_SMD:L_0603_1608Metric"
PJ = {"10pF": ("CL05C100JB5NNNC", "C32949"), "18pF": ("0402CG180J500NT", "C1549"), "15pF": ("0402CG150J500NT", "C1548"), "22pF": ("0402CG220J500NT", "C1555"),
      "47pF": ("0402CG470J500NT", "C1567"), "68pF": ("0402CG680J500NT", "C190580"), "100nF": ("CL05B104KO5NNNC", "C1525"),
      "4.7uF": ("CL05A475MP5NRNC", "C23733"), "1k": ("0402WGF1001TCE", "C11702"), "5.1k": ("0402WGF5101TCE", "C25905"),
      "10k": ("0402WGF1002TCE", "C25744"), "2.2R": ("0603WAF220KT5E", "C22939"), "2.2uH": ("MLZ1608A2R2WT000", "C76797")}
SIGNALS = ("3V3", "GND", "SCK", "MOSI", "MISO", "NSS", "RST", "IRQ")        # the cable to the main board's J20, in its pin order
WSN = {"2": "3V3", "3": "3V3", "15": "3V3", "12": "3V3", "9": "3V3", "6": "RST", "24": "NSS", "29": "SCK", "30": "MOSI", "31": "MISO",
       "23": "IRQ", "1": "GND", "32": "3V3", "21": "OSCIN", "22": "OSCOUT", "13": "TX2", "11": "TX1", "17": "RX", "16": "VMID",
       "4": "GND", "5": "GND", "10": "GND", "14": "GND", "18": "GND", "33": "GND"}
WS_NC = ("19", "20", "7", "8", "25", "26", "27", "28")                       # AUX1/2, MFIN/MFOUT, D1-D4: unused in SPI mode


def ws_symbol(custom_symbol):
    return custom_symbol("BugBot:WS1850S", "U",
        [("2", "PVDD", "power_in"), ("3", "DVDD", "power_in"), ("15", "AVDD", "power_in"), ("12", "TVDD", "power_in"), ("9", "SVDD", "power_in"),
         ("6", "NRSTPD", "input"), ("24", "SDA/NSS", "input"), ("29", "D5/SCK", "input"), ("30", "D6/MOSI", "input"), ("31", "D7/MISO", "output"),
         ("23", "IRQ", "output"), ("1", "I2C", "input"), ("32", "EA", "input"), ("21", "OSCIN", "input"), ("22", "OSCOUT", "output")],
        [("13", "TX2", "output"), ("11", "TX1", "output"), ("17", "RX", "input"), ("16", "VMID", "power_out"), ("19", "AUX1", "output"),
         ("20", "AUX2", "output"), ("7", "MFIN", "input"), ("8", "MFOUT", "output"), ("25", "D1", "bidirectional"), ("26", "D2", "bidirectional"),
         ("27", "D3", "bidirectional"), ("28", "D4", "bidirectional"), ("4", "DVSS", "power_in"), ("5", "PVSS", "power_in"), ("10", "TVSS", "power_in"),
         ("14", "TVSS", "power_in"), ("18", "AVSS", "power_in"), ("33", "EP", "power_in")], 15.24)


def add_reader(D, custom_symbol, ref=lambda r: r, ant=("ANT_A", "ANT_B"), sch=(0, 0)):
    """The reader's parts on Design D. ref renames the designators (a board that has its own C1...); sch shifts them on
    the schematic sheet."""
    D.custom["BugBot:WS1850S"] = ws_symbol(custom_symbol)
    at = lambda x, y: (x + sch[0], y + sch[1])
    def cap(r, val, a, b, xy, fp=C04): D.part(ref(r), "Device:C", val, fp, {"1": a, "2": b}, at(*xy), PJ[val])
    def res(r, val, a, b, xy, fp=R04): D.part(ref(r), "Device:R", val, fp, {"1": a, "2": b}, at(*xy), PJ[val])
    D.part(ref("U1"), "BugBot:WS1850S", "WS1850S", QFN, WSN, at(100, 80), ("WS1850S", "C2686218"))
    D.NC |= {(ref("U1"), p) for p in WS_NC}
    D.part(ref("Y1"), "Device:Crystal_GND24", "27.12MHz 12pF", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
           {"1": "OSCIN", "3": "OSCOUT", "2": "GND", "4": "GND"}, at(60, 40), ("SX32Y027120BC1T001", "C337682"))
    cap("C1", "18pF", "OSCIN", "GND", (50, 30)); cap("C2", "18pF", "OSCOUT", "GND", (70, 30))
    res("R1", "5.1k", "RX", "RXC", (150, 30)); cap("C3", "15pF", "RXC", "M2B", (165, 30))      # RX from the TX2 matching node
    res("R3", "1k", "RX", "VMID", (150, 45)); cap("C4", "100nF", "VMID", "GND", (165, 45))
    for i, r in enumerate(("C5", "C14", "C15", "C16", "C17")):                                # AVDD SVDD DVDD TVDD PVDD
        cap(r, "100nF", "3V3", "GND", (40 + 15 * i, 140))
    cap("C18", "4.7uF", "3V3", "GND", (120, 140))
    res("R6", "10k", "RST", "3V3", (140, 140)); res("R7", "10k", "NSS", "3V3", (155, 140))
    # TX2 side: L1 -> M2A (EMC C7) -> C6 series -> M2B (C8 + C9 parallel) -> R4 -> antenna end A; TX1 side the same into end B.
    # Matching retuned 2026-10-23 for the floor PCB loop (3 turns round the edge, 2.42 uH; design/lib/nfc_floor_calc.py):
    # Cs 10 pF, Cp 47 + 47 = 94 pF per side; ~72 mA in the loop, ~29 mA supply, Q ~33. Calculated, not yet measured.
    D.part(ref("L1"), "Device:L", "2.2uH", L06, {"1": "TX2", "2": "M2A"}, at(170, 70), PJ["2.2uH"])
    cap("C7", "47pF", "M2A", "GND", (180, 60)); cap("C6", "10pF", "M2A", "M2B", (190, 70)); cap("C8", "47pF", "M2B", "GND", (200, 60))
    cap("C9", "47pF", "M2B", "GND", (210, 60)); res("R4", "2.2R", "M2B", ant[0], (220, 70), R06)
    D.part(ref("L2"), "Device:L", "2.2uH", L06, {"1": "TX1", "2": "M1A"}, at(170, 110), PJ["2.2uH"])
    cap("C10", "47pF", "M1A", "GND", (180, 120)); cap("C12", "10pF", "M1A", "M1B", (190, 110)); cap("C13", "47pF", "M1B", "GND", (200, 120))
    cap("C11", "47pF", "M1B", "GND", (210, 120)); res("R5", "2.2R", "M1B", ant[1], (220, 110), R06)
