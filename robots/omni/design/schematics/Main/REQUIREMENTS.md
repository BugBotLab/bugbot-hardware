# BugBot main board: requirements (draft for review, 2026-10-23; decisions of 2026-10-23 applied)

One board for every style (Base, Scorpion, Ant, Wasp, Beetle, Spider). It must carry everything any style needs and fit
round every style's add-ons. Sold as a dev board, with the rest of the robot 3D printed by the buyer.
Status: **requirements only**. The KiCad board today has outline + holes, BT1, J4, J6, J11–J13 and the old optical-flow
parts. There is no schematic yet.

Legend: **[have]** already on the board · **[add]** to add · **[remove]** · **[decide]** needs your decision.

## 1. What plugs in, per style

| Function | Base | Scorpion | Ant | Wasp | Beetle | Spider |
|---|---|---|---|---|---|---|
| 3 drive motors + 3 wheel encoders | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Front sensor board (camera + ToF) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| NFC reader + floor PCB (underglow) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| LED beacon ring | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gripper servo (SG90) | – | ✓ | ✓ | – | fitted, unpowered | ✓ (tag arm) |
| Kicker (JF-0520B solenoid) | – | ✓ | – | ✓ | – | – |

So the board needs: 3 motor outputs, 3 encoder inputs, 1 servo output, 1 kicker output, plus the always-fitted sensors.
Parts only some styles use (the kicker charger, the servo feed) are fitted on every board but may stay idle.

## 2. Processor and radio

- **Waveshare ESP32-P4-Module** (P4 + C6 radio, 32 MB PSRAM, 16 MB flash), 88 castellated pads on the underside. **[have, placeholder: no pads yet]**
- **Antenna (decided): an external 2.4 GHz antenna on the module's U.FL (IPEX) socket.** Use an antenna type the module's
  certification lists, and keep it clear of copper, metal and the motors. Its position is not modelled (user: don't worry about it).
- **Pinout checked (2026-10-23)** against Waveshare's module schematic V1.1 (`design/lib/datasheets/Waveshare_ESP32-P4-Module_datasheet.pdf`):
  - 88 pads. GPIO14–19 are the module's internal SDIO link to the C6 and are not on pads.
  - **GPIO6 (to the C6's IO2) and GPIO54 (the C6's reset) are on pads but used by the module.**
  - **GPIO0/1 carry the module's 32.768 kHz crystal.**
  - GPIO24/25 are the USB-Serial/JTAG pins.
  - That leaves **45 usable GPIOs** (0–54 less 14–19, 0, 1, 6, 54), of which GPIO34–38 are strapping pins.
- **The original budget (~50) did not fit.** Fix: a **TCA9535 16-bit I²C GPIO expander** for the slow signals: TI TCA9535PWR
  C130204 (7.3k, $1.33), or the UMW-made equivalent C22396388 (17k, $0.49); address 0x20–0x27, no clash.
- **GPIO map v1** (module pad → P4 GPIO → signal). All 45 are used, so changes need a swap:

| GPIO (pad) | Signal | Note |
|---|---|---|
| 2, 3 (17, 18) | MOT1_IN1, MOT1_IN2 | DRV8833 #1 A |
| 4, 5 (19, 20) | MOT2_IN1, MOT2_IN2 | DRV8833 #1 B |
| 9, 10 (24, 25) | MOT3_IN1, MOT3_IN2 | DRV8833 #2 A (#2 B spare) |
| 7, 8 (22, 23) | I2C_SDA, I2C_SCL | IMU, ToF, camera SCCB, Qwiic, expander; 2.2 k pull-ups |
| 11 (26) | SERVO_PWM | |
| 12 (27) | KICK_FIRE | gate pull-down: the solenoid stays off while the P4 boots |
| 13 (28) | BUZZER | LEDC PWM |
| 20 (29) | VBAT_SENSE | ADC1 |
| 21 (30) | SERVO_ISENSE | ADC1 (INA180A2) |
| 22 (31) | KICK_VSENSE | ADC1 (capacitor divider) |
| 23 (32) | EXP_IO0 | expansion socket (fast / analog: ADC1) |
| 24, 25 (50, 51) | USB_D−, USB_D+ | USB-C (USB-Serial/JTAG) |
| 26–31 (53–58) | ENC1_A/B, ENC2_A/B, ENC3_A/B | PCNT |
| 32, 33 (59, 60) | SPI_SCK, SPI_MOSI | NFC reader + expansion socket |
| 51 (79) | SPI_MISO | |
| 34 (61) | LED_BEACON_DIN | strapping pin: an output into a 74AHCT buffer (no pull) |
| 35 (62) | LED_UNDER_DIN | strapping pin: as above |
| 36 (63) | NFC_NSS | strapping pin: pulled up on the reader board |
| 37 (64) | EXP_SPI_CS | strapping pin: 10 k pull-up |
| 38 (65) | EXPANDER_INT | strapping pin: pulled up (open-drain INT) |
| 39–46 (67–74) | CAM_D2…CAM_D9 | DVP 8-bit, J6 |
| 47, 48, 49, 50 (75–78) | CAM_PCLK, CAM_VSYNC, CAM_HREF, CAM_XCLK | J6 (series resistors on XCLK / PCLK) |
| 52 (80) | NFC_IRQ | |
| 53 (81) | IMU_INT1 | |

  **Check before layout:** the P4's strapping levels on GPIO34–38 (boot mode, JTAG / ROM-print selection) against what each
  signal pulls them to at reset. The mapping above keeps encoders, motor inputs and the kicker off them.
- **On the TCA9535:** DRV_nSLEEP (both drivers), DRV_nFAULT (both, open-drain), NFC_RST, KICK_CHG_EN, STATUS_LED, USB_VBUS_DET,
  IMU_INT2, EXP_IO1…EXP_IO4 (expansion socket), plus 5 spare.
- Module power: ESP_3V3 (pads 85, 86) and VBAT (pad 84, the P4's RTC supply) from 3V3; CHIP_PU (pad 87): RESET button to GND
  (the module has its own RC); GPIO35 also needs the BOOT button to GND (download mode). C6 pads (4–14), LNA_OUT, the CSI/DSI pads and
  VFB_VO4 stay unconnected.

## 3. Power

- **Battery:** 1 × 16340 Li-ion (3.0–4.2 V) in **BT1, Keystone 1051** (through-hole, bought separately, hand-soldered). **[have]**
  - **A protected 16340 does not fit the 1051** (34.67 mm inside, protected cells are 35.5–37.5 mm), so the cell is **unprotected**:
    **the board must protect it [add]**: over-discharge cut-off, over-current / short-circuit cut-off (e.g. DW01A + FS8205A, both JLC
    Basic, or one protection IC), plus a fuse or eFuse.
  - **No charging at all** (decided): an external Li-ion charger. **[remove]** the BQ24074 charger and the "charging port" from PARTS.md.
  - **Chosen protection parts (JLC, 2026-10-23):** DW01A (C351410, 105k in stock) + FS8205A dual N-MOSFET (C2830320, 147k),
    5 A 1206 fuse (C163128, 25k), SI2333 P-MOSFET reverse-polarity guard (C4748717, 11k, 28 mΩ).
- **USB-C (decided): programming + bench power, no charging.** TYPE-C-31-M-12 (C165948, 328k in stock), 2 × 5.1 kΩ CC pull-downs
  (a sink), USBLC6-2SC6 ESD on D+/D− (C2687116, 124k). Power path: VBUS → **LM66100** ideal diode (C2869734, 19k; 1.5 A) → VSYS, and
  the battery → a P-MOSFET (SI2333) → VSYS whose gate VBUS turns off, so USB runs the board and never feeds the cell, and the cell never
  back-feeds USB. On USB the board is limited to ~1.5 A (USB itself gives 0.5–3 A): enough to program, test sensors and turn the wheels
  slowly; full-power driving and kicking are for the battery.
- **Power switch:** C&K L101011ML04Q, 4 A, through the wall slot. Everything after the protection goes through it. **[add]**
- **Reverse polarity:** the 1051 holder is polarised, but add a P-MOSFET reverse-polarity guard anyway (cheap, and a certification plus). **[add]**
- **Rails:**

| Rail | From | Feeds | Peak (estimate) | Part (proposal) |
|---|---|---|---|---|
| VBAT 3.0–4.2 V | cell, after protection + switch | 2 × DRV8833 (3 motors), 5 V boost, 3V3 buck-boost, kicker charger | ≈ 3 A | — |
| 3V3 | buck-boost | P4 module (radio bursts), IMU, encoders, NFC reader, front board (camera + ToF), buzzer | ≈ 1 A | TPS63802 (2 A) **[check JLC]** |
| 5V | boost | servo (stall 0.7 A), 6 beacon + 7 underglow WS2812 (≈ 0.8 A full white; firmware caps it) | ≈ 1.5 A | TPS61023 or similar **[check JLC]** |
| Kicker 24 V (decided) | boost | 330 µF 35 V (69 % of its rating) | charging ≈ 0.3–0.5 A from VBAT | a ≤ 28 V boost (MT3608-class) **[check JLC]** |

- **Battery monitoring:** VBAT divider to an ADC pin (the firmware warns and stops the motors before the cut-off). **[add]**
- **Brown-out:** motor and kicker surges must not reset the P4. Bulk capacitance on VBAT, and keep the 3V3 converter's input separate from the motor current path.

## 4. Actuators

- **Motors:** 2 × TI DRV8833 (HTSSOP-16), 3 channels used (1 spare). Motors run from VBAT. 3 × JST-SH 2 upright, pointing down. **[add]**
- **Servo:** 3-pin 2.54 mm header (5 V, GND, PWM), INA180A2 + 0.1 Ω current sense to an ADC (the gripper's stall protection). **[add]**
- **Kicker:** boost to ~24–30 V, 330 µF 35 V capacitor, low-side MOSFET, SS14 flyback diode, JST-PH 2 upright SMD (pointing down). **[add]**
  - **The MOSFET must be rated ≥ 40–60 V** (an AO3400 is 30 V: too close to a 24–30 V capacitor plus the turn-off spike).
  - **Bleed resistor** across the capacitor, plus firmware that empties it on power-down: a safety and certification point.
  - Capacitor voltage sense to an ADC (kick only when charged; detect a fault).

## 5. Sensors and plug-in boards

| Item | Interface | Connector | Status |
|---|---|---|---|
| IMU LSM6DSV16X (C5267406) | I²C (or SPI) + INT | on board, **near the centre**, away from the kicker | **[add]**; its 0.5 mm pads need a local 0.1 mm clearance rule |
| Front sensor board (camera DVP + ToF) | DVP + I²C, 3V3 | J6, 2 × 10 1.27 mm SMD socket | **[have]**; I²C pull-ups (2.2 k) go on the main board |
| ToF part (front board) | — | — | **decided: VL53L5CX** (C3178303, 3,844 at JLC; 45° × 45°). The VL53L7CX (90° diagonal) shares its footprint, pins and driver: a drop-in later if JLC stocks it. The front board already uses the L5CX, and the sim models its 45° view |
| Wheel encoders × 3 (MT6701 A/B) | 2 GPIO each, 3V3 | J11–J13, 1 × 4 1.27 mm sockets, underside | **[have]** |
| NFC reader (WS1850S board) | SPI + RST + IRQ, 3V3 | JST-SH 8 upright, pointing down (BM08B-SRSS-TB, C160394) | **[add]** |
| Underglow (7 × WS2812B on the floor PCB) | 1 data at 5 V | JST-SH 3 upright, pointing down (C160389) + level shifter | **[add]** |
| LED beacon ring (6 × WS2812B) | 1 data at 5 V | J4, JST-SH 3 upright | **[have]**; **level shifter [add]** |
| Level shifters (decided) | 3.3 V → 5 V, one per LED chain | 2 × SN74AHCT1G125 (C7484, 47k in stock), on 5 V, 33 Ω series out | **[add]** (the dual 74AHCT2G125 has ~97 in stock: not used) |
| Optical-flow sensor PAA5100 (U11, LED1, LED2, R1) | — | — | **[remove]**: dropped from the sensor set |

## 6. User interface and expansion

- BOOT (GPIO35 to GND) and RESET (CHIP_PU to GND) buttons (ZX-QC4545), status LED (on the TCA9535), buzzer (MLT-8530 + AO3400A + 1N4148W). **[add]**
- Qwiic / STEMMA QT I²C port (JST-SH 4). Addresses taken: 0x6A/0x6B (IMU), 0x29 (ToF), 0x30 (OV2640). **[add]**
- 2 × 6 2.54 mm female SMD expansion socket: SPI (SCK, MOSI, MISO, CS on GPIO37), EXP_IO0 (GPIO23, ADC), EXP_IO1…4 (TCA9535), 3V3, GND. **[add]**
- Silkscreen labels for every connector, the polarity and the switch: the board is sold, so it must explain itself.

## 7. Fit: the board must clear every style

- **Keep-outs from the Scorpion: DONE 2026-10-23** (pushed: 10 hard keep-outs + 76 'max height' outlines on the MCAD layer; DRC: no existing part inside one). `mech/freecad/keepouts.py` now adds the Scorpion's modules (servo mount, gripper, kicker) and their bought bodies, and marks every part within 15 mm of a face with its height limit (tightest: kick disc 0.6, solenoid coil 0.9, NFC reader 4.2 below; pivot bushing 2.0, servo horn 2.6 above). Still to check if they reach further: the Beetle's feet, the Spider's arm.
  Earlier notes (kept for reference): The FreeCAD → KiCad push currently sends the base's printed parts (mast,
  deck legs, battery holder) plus the gripper swing. It must also send:
  - the servo block and pivot bracket footprints (Scorpion, Ant, Beetle, Spider);
  - the **kicker bracket and capacitor** (Scorpion, Wasp);
  - the **Beetle shield's feet, which rest on the board top** (no tall parts under them);
  - the Spider tag arm's swing;
  - the TagBar clips and the rear deck posts.
  **[add]** one combined keep-out from every style's modules.
- **Underside:** the P4 module, encoder sockets (fixed by the encoder boards), the NFC reader plug (above the reader's J1), motor plugs
  (clear of the wheels), the kicker plug and capacitor (clear of the solenoid), the switch at the wall slot.
- **Heights:** top-side parts must stay under the top deck, the dome and the servo; underside parts above the gearmotors and the NFC tray.
- Mounting holes and outline stay owned by FreeCAD (pushed to KiCad).

## 8. Certification (UK/EU: UKCA / CE) — design for it from the start

I am not a compliance expert: confirm the route with a test lab or consultant before ordering a batch.

- **Radio (RED):** use the module's existing certification and **only an antenna type its certificate lists**. Keep the antenna area
  clear of copper and metal, as the module's datasheet says.
- **EMC (emissions and immunity):**
  - **a 4-layer board (decided)** with solid ground planes on the inner layers;
  - short return paths for the motor and kicker currents, and RC snubbers / capacitors on the motor leads;
  - TVS / ESD protection on every connector a user touches (USB-C, Qwiic, the expansion socket, the servo header);
  - series resistors on the clock lines (camera XCLK and PCLK), and the boost converters laid out exactly as their datasheets show.
- **Safety (GPSR; LVD does not apply below 75 V DC):**
  - battery protection (section 3), a fuse, reverse-polarity protection, the kicker bleed resistor;
  - thermal checks under load;
  - **no battery shipped with the board** (avoids the Li-ion transport rules).
- **RoHS:** JLC's RoHS parts. **WEEE:** register as a producer.
- **Markings:** UKCA/CE mark, WEEE bin symbol, manufacturer name and address, model and batch on the silkscreen or a label.
- **Market (decided): a 14+ maker kit**, not a toy (so EN 62115 does not apply). Say "14+" on the box, the listing and the
  instructions, and do not market it to young children.
- Keep a technical file: schematics, BOM, test reports, risk assessment.

## 9. Decisions needed before the schematic

Decided 2026-10-23: battery protection on the board; external antenna on U.FL; no charging; level shifters for both LED
chains; keep-outs from the Scorpion; 4 layers; kicker 24 V with 330 µF 35 V (a 2 × 2 m field needs only ~0.9 m/s to cross it:
24 V gives ~2.5–3 m/s, and the firmware can kick softer with shorter pulses).

Also decided: USB-C for programming + bench power (power path, no charging); a 14+ maker kit; the antenna's position is
not modelled (the buyer sticks it inside the shell, away from the motors).

Decided: ToF = VL53L5CX. No open decisions left: next is the schematic.

## Schematic progress

- **2026-10-23, section 1 (power + protection) drawn:** `design/lib/make_main_schematic.py` → `BugBot_Main.kicad_sch` (46 parts, ERC 0 errors).
  - Inductors: 3V3 0.47 µH WPN4020HR47MT (C370628, 6.4 A sat); 5V 1 µH WPN4020H1R0MT (C98359, 5.8 A); kicker 22 µH SWPA4030S220MT (C83472).
  - Dividers changed to parts in stock: 3V3 = 560 k / 100 k (3.30 V; TI: R2 ≤ 100 k), 5V = 750 k / 100 k (5.06 V) + 220 pF feed-forward.
  - TPS63802 DLA footprint (no KiCad stock one): `BugBot:Texas_DLA0010A_VSON-HR-10_2x3mm_P0.5mm` from LCSC's EasyEDA model. **[check against TI's land pattern before layout]**
  - USB_VBUS_DET = VBUS × 2/3 (to the TCA9535). The TPS63802 PG (open drain) drives CHIP_PU: the P4 stays in reset until 3V3 is good.
  - **Open:** SW1 footprint still has no pads; J1 shield straight to GND.
- **2026-10-23, section 2 (P4 module, buttons, expander, USB data) drawn:** 66 parts in all, ERC 0 errors. The 40 warnings are labels for sections not drawn yet.
  - U6 module: 88-pad symbol from Waveshare's V1.1 schematic. GPIO map v1 wired as in the table; 31 pads NC (C6 spares, LNA_OUT, MIPI, USB HS, VFB_VO4, GPIO0/1/6/54).
  - **The usable count is 45, not 43** (GPIO 0–54 less 14–19, 0, 1, 6, 54), and the map uses all 45.
  - Strapping (ESP32-P4 datasheet v0.7 §3, `datasheets/Espressif_ESP32-P4_datasheet.pdf`):
    - GPIO35 10 k up, plus the BOOT button to GND;
    - GPIO36 10 k up (download needs 35 low **and** 36 high);
    - GPIO34 10 k down (ignored with default eFuses, but must not float);
    - GPIO37/38 10 k up (any value).
  - Buttons: SW2 RESET (CHIP_PU) and SW3 BOOT (GPIO35), ZX-QC4545-4.3TP C7470171. I²C pull-ups: 2.2 k.
  - U7 TCA9535 (UMW C22396388) at 0x20:
    - P00 DRV_nSLEEP (100 k down), P01 DRV_nFAULT (10 k up), P02 NFC_RST (10 k up), P03 KICK_CHG_EN (100 k down);
    - P04 STATUS_LED (red KT-0603R C2286, 1 k, on when low), P05 USB_VBUS_DET, P06 IMU_INT2;
    - P10–P13 EXP_IO1–4; P07 and P14–P17 spare.
  - Note: GPIO26/27 (ENC1) come up as the second USB FS port at reset; the firmware reconfigures them before using PCNT.
  - **Open:** footprint pads for the module (`Waveshare_ESP32-P4-Module`, a placeholder outline) and the ZX-QC4545 buttons.
- **2026-10-24, section 3 (actuators) drawn:** 122 parts in all, ERC 0 errors.
  - Warnings: 29 labels waiting for the sensors section, 4 for KiCad typing DRV8833 xISEN as bidirectional to GND, plus the embedded-symbol notices.
  - **Motors:** U8/U9 DRV8833PWPR (C50506) on VSYS.
    - Each: 10 nF VCP, 2.2 µF VINT, 10 µF + 100 µF 1206 on VM.
    - xISEN to GND (no current limit). nSLEEP/nFAULT shared (TCA9535 P00/P01). U9 B spare.
    - J14–J16: JST-SH 2 upright (C160388).
  - **Servo:** J18 1×3 2.54 header (GND, 5V, PWM: SG90 order). 220 Ω on the PWM line.
    - 0.1 Ω 0805 shunt in its 5 V feed, sensed by an **INA180A1** (×20, not A2: A2's ×50 would clip at 0.66 A): 0.7 A gives 1.4 V. 1 k + 100 nF into SERVO_ISENSE.
  - **Kicker:** MT3608 (C84817) from VSYS, EN = KICK_CHG_EN; 22 µH SWPA4030S220MT, SS34; 470 k / 12 k = 24.1 V; 2 × 4.7 µF 50 V.
    - 10 Ω 1206 into C34, 330 µF 35 V (JVJ35V330M10x10, C46550412, 10 × 10.5 mm, **check the fit under the PCB**). The 10 Ω limits the inrush.
    - 47 k 1206 bleed (τ 15.5 s). 1 M / 100 k to KICK_VSENSE (24 V gives 2.2 V).
    - Fire: AO3422 (55 V), gate from 5 V through a SN74AHCT1G125 + 10 Ω; 100 k pull-downs on both KICK_FIRE and the gate. SS14 flyback.
    - J19: JST-PH 2 upright SMD (B2B-PH-SM4-TB, C160352).
  - **Buzzer:** MLT-8530 (C94599, 16 Ω) from 3V3, AO3400A + 1N4148W; 100 Ω gate, 100 k pull-down.
    - Footprint from EasyEDA (`BugBot:Buzzer_MLT-8530_8.5x8.5mm`). Pads 2 and 4 both go to the switch: the datasheet only shows that + and − share one side. **[check the pad order before layout]**
  - **LED level shifters:** 2 × SN74AHCT1G125 (UMW C20617903) on 5 V, 33 Ω series.
    - J4 beacon ring (existing ref, JST-SH 3: 5V, DIN, GND); J17 underglow (JST-SH 3, C160389).
- **2026-10-24, section 4 (sensors + connectors) drawn. The schematic is now complete:** 136 parts, 159 nets.
  - ERC: 0 errors and no unconnected labels. The only warnings are the 4 DRV8833 xISEN typing ones and the embedded-symbol notices.
  - No net has only one pin (NC pins apart).
  - Every part has an LCSC number except BT1 (Keystone 1051), SW1 (L101011ML04Q) and U6 (the Waveshare module): bought separately.
  - **IMU** U15 LSM6DSV16X (C5267406), I²C at 0x6A: CS high, SA0/SDx/SCx to GND, OCS_Aux/SDO_Aux NC; 100 nF each on VDD and VDDIO. INT1 goes to GPIO53, INT2 to TCA9535 P06.
  - **J6** front board: pin-out as add_j6.py, with 33 Ω series on XCLK and PCLK; 10 µF + 100 nF at the socket.
  - **J11–J13** encoders: 3V3, GND, A, B (HX PM1.27-1x4P, C22438070). **[check that socket pin n mates header pin n, as was done for J6]**
  - **J20** NFC: JST-SH 8 (C160394), the reader's order (3V3 GND SCK MOSI MISO NSS RST IRQ). **Needs a 1:1 cable [check the cable type]**
  - **J21** Qwiic: side-entry JST-SH 4 (XY-SM04B, C51940130), GND 3V3 SDA SCL.
  - **J22** expansion: 2×6 2.54 SMD female (C22373947):
    - 1 3V3, 2 GND, 3 SCK, 4 MOSI, 5 MISO, 6 CS (GPIO37);
    - 7 EXP_IO0 (GPIO23, ADC), 8–11 EXP_IO1–4 (expander), 12 GND.
  - **Open before layout:**
    - footprint pads for U6 (module), SW1 and the ZX-QC4545 buttons;
    - the TPS63802 and MLT-8530 footprints (EasyEDA) to check;
    - whether C34 (10 × 10.5 mm) fits under the board;
    - ESD on the external connectors (Qwiic, expansion) is a certification question still to decide.
- **2026-10-24, footprints done** (`design/lib/make_main_footprints.py`, picture `new_footprints.png`). Every symbol pin of all 136 parts has its pad, and every pad its pin (39 footprints checked).
  - **U6 module:** 88 pads from Waveshare's land-pattern DXF (`datasheets/waveshare_p4_land`): 22 a side, 1.0 mm pitch, 1.5 × 0.7 mm on the module edge.
    - Pin 1 is at the dot (top of the left side), numbered anticlockwise.
  - **SW1:** the L101 is **SPST** (pins 1–2; C&K catalog p. I-20), so the schematic now uses SW_SPST. ML/04 pins sit at 4.75 mm with 1.65 mm holes.
    - Both outer pads are pad 1, so it works whichever end is pin 1. Pads and 2 peg holes sit where our 3D model has them (turned 33°, robot frame).
    - **Cost:** $7.12 at LCSC with 0 in stock. Worth swapping for a cheap slide switch (low-cost priority) before ordering.
  - **SW2/SW3 ZX-QC4545:** lands from its drawing (7.2/4.5 × 4.1/1.9; EasyEDA's were 0.7 mm wider). Top pair = pad 1, bottom pair = pad 2, joined inside.
  - **TPS63802 DLA:** redrawn to TI's land pattern (EasyEDA's copy was 0.07 mm off and its pads 0.3 mm wide, not 0.25).
  - **MLT-8530:** EasyEDA pad 1 = +. − is pad 2 or pad 4 (same side as +), and both are tied to BUZ_N, so it is right either way.
- **2026-10-24, power switch and USB-C moved** (approved 2D: `mech/freecad/sketches/switch_usb_move_v1.png`).
  - A sweep of each part's envelope (+0.5 mm) was run against every part of all six styles plus the planned 330 µF capacitor:
    - a 3 A slide switch (SS-12D11 or the C&K) fits **nowhere** round the wall;
    - the old USB-C place (300°) hit wheel 3's encoder board.
  - **Power switch:** SW1 = MSK12C02G25-B (C22435663), SMD under the PCB at 237°, its handle in the existing wall slot.
    - It pulls the gate of **Q6 SI2333** (high-side, after the polarity FET Q1): R47 100 k gate–source, R48 1 k to the switch. Pin 2 = GND, pin 1 = on.
    - Footprint `BugBot:SW_MSK12C02G25_SMD`, from its drawing, with a stepped courtyard so only the handle enters the slot.
  - **USB-C:** J1 moved to **199°** (rear left), underside, mouth flush with the wall's outside; Params `usb_ang` 199, so the 300° slot is closed.
    - Footprint `BugBot:USB_C_Receptacle_HRO_TYPE-C-31-M-12`: KiCad's, with LCSC's 3D model (KiCad has none), turned 180° and shifted −1.05 y to match the pads.
  - Both placed by `design/lib/place_wall_parts.py`; keep-outs re-pushed; FreeCAD 3D check: no collisions.
    - J1's shield legs end inside the PCB, though 2 of its holes sit under the battery holder.
  - The SS-12D11G5R and C&K footprints stay in the library, unused.
- **2026-10-25, placement done** (floor plan v1, approved 2026-10-24, with v1.1/v1.2 fixes; `placement_v1.png`).
  - All 139 parts are on the 4-layer board. Pipeline:
    - `place_map_kicad.py` → `place_free.py` (free area per side: keep-outs, holes, height limits);
    - `place_extract.py` (courtyards per side and turn) → `place_floorplan.py` (greedy, groups in order) → `place_apply.py`;
    - check: `place_check3d.py`, outside FreeCAD.
  - **Fixes on the way:**
    - The board has a **front cut-out** (an arc of r 18.6 at (41.5, 0)), so the kicker charger went behind it on the underside.
    - The 330 µF C34, the solenoid plug J19 and D3 sit on the top rear-left, which has the headroom.
    - With **every style's arms and plates kept out**, the motor drivers U8/U9 and the expander U7 went to the underside (U8/U9 under the NFC tray, 2.1 mm of headroom for 1.2 mm parts).
  - **Keep-outs now cover all six styles** (`mech/freecad/keepouts.py`):
    - style parts (the Beetle's shield, the Spider's arms, magazine and tags, the Wasp's ram) are included;
    - height limits use only the part of each shape over the board;
    - parts 0.05–0.3 mm above the board (the gripper's left arm rides at 0.3) now get a limit too: before, they fell between the touch test and the height test.
  - **DRC:** 0 new errors. What's left was there before: BT1 against posts H2/H3, and the J1/SW1 locating holes under top-side parts.
  - Design rules for JLC 4-layer: 0.1 mm minimum clearance and track, 0.2 mm drill; default netclass 0.15 / 0.2, vias 0.5 / 0.25.
  - **3D check, all six styles:** 0 overlaps. Under 0.5 mm only the contacts that are there by design (sockets at the wall, J4 and its cable, BT1). C34 has 2.7 mm to the arms and 1.9 mm to a screw.
  - **Open:**
    - U8/U9 have no 3D model (KiCad has none for the HTSSOP "Mask" variant);
    - pin 1 of the switch knob is still to check;
    - routing is next.
- **2026-10-25, GPIO map v2** (routing plan v1, approved; `routing_plan_v1.png`, `design/lib/gpio_swap_opt.py`). Each bundle now sits on the module edge facing where it goes:
  - **south edge:** camera GPIO39–50; the ADC2 sense lines KICK_VSENSE 51, SERVO_ISENSE 52, VBAT_SENSE 53.
  - **east edge:** ENC1 26/27, BUZZER 28, IMU_INT1 29, SERVO_PWM 30, KICK_FIRE 31, ENC3 33/32.
  - **west edge:** MOT1 2/3, MOT2 5/4, NFC_IRQ 7.
  - **north edge:** ENC2 9/8, SPI SCK 10, MOSI 11, MISO 12, MOT3 20/13, I²C SDA 21 / SCL 22, EXP_IO0 23 (ADC1).
  - **Fixed:** USB 24/25, straps 34–38 as before.
  - Pad-to-destination length 1.20 m → 1.05 m. **Firmware pin definitions must follow this map** (the table in section 2 above is v1).
