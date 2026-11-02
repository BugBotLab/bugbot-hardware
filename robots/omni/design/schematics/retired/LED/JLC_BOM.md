# BugBot LED ring: JLCPCB assembly BOM

Checked against the JLCPCB parts library (jlcpcb.com/parts search API) on 2026-10-20. Prices are JLC's USD unit price at qty 1
(the next price break is in brackets). Stock is JLC's count on that date. Re-check stock before ordering.

| Ref | Value | Footprint (KiCad) | MPN (manufacturer) | LCSC | Type | Stock | Unit price |
|---|---|---|---|---|---|---|---|
| D1–D8 | WS2812B-2020 | LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm | WS2812B-2020-V6 (Worldsemi) | **C52917434** | Extended | 849,832 | $0.0914 ($0.0736 @50) |
| U1 | 74AHCT1G125 | Package_TO_SOT_SMD:SOT-23-5 | SN74AHCT1G125DBVR (TI) | **C7484** | Extended | 49,376 | $0.1002 ($0.0798 @50) |
| R1 | 33R | Resistor_SMD:R_0402_1005Metric | 0402WGF330JTCE (Uniroyal), 1 %, 62.5 mW | **C25105** | Basic | 2,407,260 | $0.0011 |
| C1–C8 | 100nF | Capacitor_SMD:C_0402_1005Metric | CL05B104KO5NNNC (Samsung), 16 V X7R | **C1525** | Basic | 38,973,642 | $0.0055 |
| C9 | 10uF | Capacitor_SMD:C_0603_1608Metric | CL10A106KP8NNNC (Samsung), 10 V X5R | **C19702** | Basic | 10,098,792 | $0.0272 |
| J1 | LED lead | BugBot:SolderWire_1x03_P2.60mm_D0.7mm | (hand-soldered JST-SH lead) | none | not in BOM | | |
| H1, H2 | M2 | MountingHole:MountingHole_2.2mm_M2 | none | none | not in BOM | | |

Parts cost per board is about $1.00 (8 × LED $0.73, U1 $0.10, passives $0.08). JLC adds a setup fee for each **Extended** part type (2 here: the LED and U1).

## Swaps and why

- **LED: WS2812B-2020 → WS2812B-2020-V6 (C52917434).** The original Worldsemi WS2812B-2020 (C965555) is marked discontinued
  (停产) at JLC with 1 left in stock. The V6 is Worldsemi's current version of the same part. It has a large stock and is cheaper.
  I checked the V6 datasheet (JLC copy of C52917434.pdf):
  - Pinout is unchanged: 1 DO, 2 GND, 3 DI, 4 VDD, in the same corners and the same rotational order as the KiCad footprint.
  - The recommended land pattern is four 0.7 × 0.7 mm pads, 1.13 mm apart across the rows and 0.40 mm apart along them. Those
    are the same pad centres as KiCad's footprint (±0.915, ±0.55). **The footprint is unchanged.**
  - The body is 2.2 × 2.0 × 0.84 mm (2.2 along the pad rows). KiCad's fab outline and courtyard already allow for 2.2 × 2.0.
  - Supply is 3.3–5.3 V. The input threshold is V_IH = 0.55·VDD (2.75 V at 5 V). The 74AHCT1G125 at 5 V drives that easily.
  - Alternatives that are in stock if the V6 runs out: XINGLIGHT XL-2020RGBC-2812B **C5349955** (97,794 pcs, $0.1015) and
    OPSCO SK6805-EC20 **C2890036** (11,954 pcs, $0.1099). Both are 2 × 2 mm, single-wire WS2812 protocol, 5 V. Check their
    pin order before swapping.
- **U1: no swap.** TI SN74AHCT1G125DBVR (C7484) is in stock. JLC has no Basic 74AHCT1G125. The TI DBV pinout
  (1 OE, 2 A, 3 GND, 4 Y, 5 VCC) matches the 74xGxx:74LVC1G125 symbol and KiCad's SOT-23-5 footprint.
- **Passives: no swap.** All three are JLC Basic parts.

## Footprints vs JLC's library footprints

I compared JLC's EasyEDA footprints for these LCSC numbers with the KiCad footprints:

| Package | JLC/EasyEDA footprint | Pads | Pin 1 at 0° | CPL rotation offset |
|---|---|---|---|---|
| WS2812B-2020-V6 | LED-SMD_4P-L2.2-W2.0-P1.00 | 0.8 mm pads at ±0.865, ±0.55 (KiCad: 0.7 at ±0.915, per datasheet) | top-left, same as KiCad | **0°** |
| SOT-23-5 | SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR | 1.1 × 0.6 at ±1.30 (KiCad 1.325 × 0.6 at ±1.1375) | **bottom-right** (KiCad: top-left) | **+180°** |
| 0402 / 0603 | R0402 / C0402 / C0603 | pad 1 at −X, same as KiCad | | 0° |

The pads match within normal IPC variation, so I kept the KiCad library footprints. No new footprints were made.

`jlc/BugBot_LED_CPL_JLC.csv` already includes the **+180° for U1**. All other rotations are KiCad's own. Check JLC's placement
preview anyway:
- U1: the pin-1 dot must sit on KiCad's pad 1 (OE, tied to GND).
- LEDs: pin 1 is DO, toward the board centre.

JLC has made per-part rotation corrections on their own side before, so if the preview already shows U1 right, take the 180 back out.

## Files

- `jlc/BugBot_LED_BOM_JLC.csv`: Comment, Designator, Footprint, LCSC (J1/H1/H2 left out).
- `jlc/BugBot_LED_CPL_JLC.csv`: Designator, Mid X, Mid Y, Layer, Rotation. All parts are on the top side. The origin is the board
  centre (aux/drill origin = robot axis) and Y is up. Export the Gerbers with "use drill/place file origin" so they match, or
  line them up in JLC's viewer.
- Both files are written by `design/lib/make_led_board.py`. The schematic symbols and the PCB footprints carry `MPN` and `LCSC`
  fields (hidden), and `Datasheet` points at the JLC part page (TI datasheet for U1).
