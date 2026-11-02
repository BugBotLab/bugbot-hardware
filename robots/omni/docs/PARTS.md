# BugBot v1.1: complete parts list

Every part in `bugbot_chassis.scad`, with the size used in the model. A collision check runs every part
against every other part, including the gripper hoop open and closed. The only overlaps are the intended ones: the
header pins in their socket and the TPU sleeve's stretch fit on the steel bar.

**Changes in v1.1:** the camera sensor is soldered on the front sensor board (no flex cable); the power switch is a
4 A through-hole C&K L101011ML04Q that carries all the robot's current; USB-C moved to the underside; ZX-QC4545
BOOT / RESET buttons (as on the earlier BugBot boards), a status LED and I²C / SPI / GPIO expansion headers on the
free left side of the top face; the gripper arms are stepped (level, right-angle step down, level), so the board and
body have no arm cut-outs; the LED dome is exactly half a sphere.

Where sizes come from:
- **Datasheet**: the maker's drawing or datasheet.
- **Standard**: a standard package or connector size.
- **Sellers**: shop listings that don't fully agree, so **measure** the part before printing.
- **Ours**: a part designed here.

## Overall

| | |
|---|---|
| Body | Ø80 mm, round; wheels stay inside the circle |
| Length with ball | 101.5 mm (ball sticks out 21.5 mm at the front, 2.5 mm more than before to make room for the kicker); 106.4 mm to the front of the closed gripper |
| Height | 29 mm to the wall top · 48 mm at the battery · 77.0 mm to the top of the LED dome |
| Weight (estimate) | ≈ 125 g |

## Printed parts (15 print files)

| File | What it is | Size (mm) | Material | Qty |
|---|---|---|---|---|
| `stl/half_outer.stl` | Omni wheel half, screw-head side | 21.9 × 23.6 × 8.0 | PLA / PETG | 3 |
| `stl/half_motor.stl` | Omni wheel half, motor side (D-shaft hole) | 21.9 × 23.6 × 8.0 | PLA / PETG | 3 |
| `stl/rollers_plate.stl` | 6 wheel rollers per plate | rollers Ø7.3 × 9.9 | TPU 95A | 3 plates |
| `bugbot_stl/chassis.stl` | Base plate, outer wall, motor saddles, board posts, ball pocket | 80.0 × 76.7 × 22.5 | PLA / PETG | 1 |
| `bugbot_stl/motor_caps.stl` | Clamp caps for the motor saddles | 6 caps, each 5 × 12 × 3.6 | PLA / PETG | 1 set |
| `bugbot_stl/batt_cradle.stl` | **Battery holder**: U-cradle for the 16340 cell, strap slot, 4 mm lead exit at the battery-plug end, 0.4 mm end clearance for the minus tab; 2 × M2 up from under the board into pilots in its thick corners (nothing under the cell) | 18.2 × 38.9 × 10.0 | PETG | 1 |
| `bugbot_stl/servo_block.stl` | Rear ear support for the SG90 servo | 4.2 × 4.0 × 12.2 | PLA / PETG | 1 |
| `bugbot_stl/hoop.stl` | The 2 stepped gripper arms (level from the pivot, a right-angle step down outside the body, level again to the front bar), printed flat | each 62.5 × 24.7 × 6.5 | PETG | 1 set |
| `bugbot_stl/hoop_sleeve.stl` | TPU tube on the steel front bar, where the ball touches | Ø5 × 30 | TPU 95A | 1 |
| `bugbot_stl/hoop_bracket.stl` | Pivot post for the −Y arm (an M2 screw is the axle); wide base, 2 × M2 up from under the board | 8.0 × 5.4 × 9.6 | PETG | 1 |
| `bugbot_stl/kick_bracket.stl` | **Kicker bracket**: side plate with 2 slotted M3 holes for the solenoid, front and rear bosses screwed from the top of the board | 32.5 × 13 × 7.7 | PETG | 1 |
| `bugbot_stl/kick_disc.stl` | **Kick disc**: flat Ø12 × 3 face on the solenoid's push end, with a pocket for a thin M3 nut. It is the plunger's return stop (in place of the o-ring and acorn nut) and kicks the ball straight even though the solenoid sits 2.8 mm off-centre | Ø12 × 3 | TPU 95A | 1 |
| `bugbot_stl/mast.stl` | Front mast: windows for the camera and ToF, holds the front sensor board, front servo-ear boss, cut-out over the held ball | 6.5 × 40.0 × 30.0 | PLA / PETG | 1 |
| `bugbot_stl/top_deck.stl` | Top deck over the centre of the robot with 2 legs; carries the LED beacon; 0.6 mm groove locates the dome | 42.5 × 37.0 × 32.0 | PLA / PETG | 1 |
| `bugbot_stl/dome.stl` | Frosted diffuser dome for the LED beacon: exactly half a sphere, 1.2 mm wall | Ø30 × 15 | white / natural PETG, 2 walls | 1 |

The front sensor board is a small custom PCB (see *Small custom boards*), not a printed part. The LED beacon is a bought 7-LED jewel (2026-10-31).

## Motion

| Part | Chosen part | Size (mm) | From | Qty |
|---|---|---|---|---|
| Gearmotor | Pololu 2358, 136:1 sub-micro plastic planetary ($18.35 each at 5+). **Low-cost alternative (2026-10-31, not yet adopted):** generic 6 mm **3 V** 136:1 planetary gearmotor (AliExpress / E-S Motor 6PG-610L-136, sold as "3V 242 rpm", ~$5). The motors run straight off the 3.7 V cell, where the Pololu (6 V, 500 rpm) gives ~308 rpm (the sim's w0 32.3 rad/s) and the 3 V clone ~296 rpm, so speed hardly changes. Stall current is higher (~0.25 A vs ~0.15 A at 3.7 V): check the battery-path budget. Saves ~£38 per robot. **Buy 2 and measure before switching:** can length (listed 18.8 vs 19), bushing, shaft length and terminals vary by seller; if they differ, update `motor_len` / saddles (2D sketch first) | Ø6 × 19, 2 mm D-shaft 2.5 long; 21 incl. terminals | Datasheet | 3 |
| Wheel axle pins | Steel pin or music wire Ø1.0, cut to length | Ø1.0 × 13.8 | Ours | 18 |
| Motor driver | TI DRV8833, HTSSOP-16 (2 channels each) | 6.4 × 5.0 × 1.2 | Standard | 2 |

## Ball handling

| Part | Chosen part | Size (mm) | From | Qty |
|---|---|---|---|---|
| Gripper servo | TowerPro SG90 9 g | body 23 × 12.2 × 22.7, ears 32.2 long, ear holes 27.5 apart | Sellers, **measure** | 1 |
| Servo horn | Single-arm horn supplied with the SG90, screwed straight to a horn-shaped pad on the +Y gripper arm with its own 2 small screws (no hub) | — | Supplied | 1 |
| Gripper front bar | Steel dowel pin DIN 6325 / ISO 8734, 3 × 45 mm, pressed (+ a drop of CA glue) into blind holes in both arm tips | Ø3 × 45 | Standard | 1 |
| Servo current sense | TI INA180A2 (gain 50) + 0.1 Ω 0805 shunt in the servo's 5 V feed, output to a P4 ADC pin | SOT-23-5; 0805 | Datasheet | 1 |
| Kicker | **JF-0520B** push-pull solenoid, **12 V**, 4 N, 10 mm stroke, 2 × M3 threaded holes on one face. Lies on its side in `kick_bracket.stl`, **2.8 mm right of the centre line**; the flat kick disc still pushes the ball straight through its centre | body 13 × 16.5 × 20 (100Y datasheet). Plunger modelled at the **larger** of two sources (3D ContentCentral model; uxcell's photos are 2–3 mm shorter): push end o-ring 2 + acorn nut 6.5; spring end: spring Ø8, washer Ø9 + e-clip at 12–13, clevis 7.5 long to 21.6. **For BugBot: acorn nut and o-ring off, the TPU kick disc (with a thin M3 nut inside) on instead; clevis sawn off 0.5 mm behind the e-clip (spring end 13.5)**. Tightest clearance 1.9 mm (to the front-left wheel) | 100Y datasheet + CAD + photos, **measure** | 1 |
| Flyback diode | SS14 Schottky (SMA) across the solenoid, so the turn-off spike can't kill the MOSFET | 4.3 × 2.6 × 2.1 | Standard | 1 |
| Kicker capacitor | 330 µF 35 V electrolytic | Ø10 × 12.5 | Standard | 1 |
| Ball | Ping-pong ball | Ø40 | Standard | — |

## Sensors and modules

| Part | Chosen part | Size (mm) | From | Qty |
|---|---|---|---|---|
| Camera | SmartSens SC035HGS global-shutter sensor soldered straight onto the front sensor board, under an 8.5 × 8.5 mm M7 lens holder (no flex cable) | holder 8.5 × 8.5 × 3.5, lens Ø7.2 | sensor package **to confirm** | 1 |
| 8×8 ToF | ST VL53L7CX | 6.4 × 3.0 × 1.6 (LGA-16), 60° × 60° view | Datasheet | 1 |
| 6-axis IMU (gyro + accelerometer) | ST **LSM6DSV16X** (JLC C5267406, Extended, 8,020 in stock, $3.36 each on 2026-10-21). No magnetometer: the wheels' encoder magnets swamp it (see Software notes) | 2.5 × 3.0 × 0.83 (LGA-14) | Datasheet | 1 |
| Beacon | Bought 7 × WS2812B-5050 "jewel" board, Ø23 (22–23 by seller), 5 V, ~£1 (AliExpress: "WS2812 7-bit RGB ring"); on a 2 mm double-sided foam pad on the top deck, the 3 cable wires (main J4: 5V / DIN / GND) soldered to its back pads. Check: diameter, back-pad positions, WS2812B / SK6812 (5 V). Replaces our LED ring board (kicad/BugBot_LED, retired 2026-10-31); approved 2D: `mech/freecad/sketches/jewel_beacon.png` | Ø23 × 3.2 (+ 2 foam) | AliExpress | 1 |
| Wheel encoders | Novosense **MT6701QT-ACD** magnetic angle sensor, A/B quadrature out (JLC C49257133, Extended, 1,755 in stock, $2.02 on 2026-10-21), one per drive wheel on its own small board (see *Small custom boards*). Not the SOP-8 MT6701CT (C3003196): that one has only I²C / SSI out | 3 × 3 × 0.75 (QFN-16) | Datasheet | 3 |
| **NFC tag reader** (base: every variant; reads the tags the robot drives over) | **One board since 2026-10-31: the NFC floor PCB** (kicad/BugBot_NFCfloor, generated by design/lib/make_nfc_floor.py; approved 2D: `mech/freecad/sketches/nfc_reader_on_floor.png`). A standard JLC 2-layer FR4 1.6 mm board with the floor's outline (wheel windows and ball notch cut out), screwed flat under the floor plate by the 3 nylon clamp screws (M2 × 5); 1.6 mm below the floor (4.9 mm to the table). It carries: a **3-turn loop** (0.18 / 0.15 mm) 0.35 mm in from the edge (top copper, L 2.42 µH calculated), so tags anywhere under the robot are read; the **reader** (WiseSun WS1850S, MFRC522-compatible 13.56 MHz ISO 14443A, SPI; dual-TX matching EMC 2.2 µH + 47 pF, series 10 pF, parallel 47 + 47 pF, damping 2.2 Ω, Q ~33; circuit in design/lib/nfc_reader_circuit.py) packed into 22 × 13 mm on the **underside** beside the loop's feed, the loop's two ends straight into the matching; the **underglow**: 7 × WS2812B-4020-V6 side-view (C52941387) on the underside on r 9, lens facing out, 100 nF each, 10 µF; and **12 plated solder holes** (1.27 mm) at the centre, in the floor plate's 7.6 × 8.4 opening, for two hand-soldered cables: reader 3V3 / GND / SCK / MOSI / MISO / NSS / RST / IRQ to main J20 (JST-SH 8, cable bought crimped one end) and underglow GND / 5V / DIN to main J17. **Every part is on the underside** (≤ 1.7 mm tall): JLC one-sided (Economic) assembly. The reader board (kicad/BugBot_NFC), its printed tray and the coil cable are gone; the tray's 3 chassis posts stay unused. The reader's ground copper sits inside the loop (~4 % of its area) and the matching is calculated, never measured: do the wire-loop bench test before ordering, and the first boards may need C106/C108/C109 (C112/C113/C111) changed. Reader parts ~$1.5 per robot | floor PCB 78 × 81 × 1.6 | JLC | 1 |
| Encoder magnets | NdFeB diametrically magnetised disc, N42 or better, glued into the printed ring on each wheel's outer hub face (`WheelFrameOne` MagnetRing: Ø8 × 1.2, pocket Ø6.4), 1.4 mm air gap to the MT6701 | Ø6 × 2.5 | Sellers, **measure** | 3 |

## Camera and ToF details

### Camera

**What it does:** gives the ESP32-P4 a live picture for colour-blob tracking and AprilTag detection. Espressif's
ESP-VISION library for the P4 already includes `find_blobs` (colour blobs) and AprilTag detection, and the P4 has a
hardware image processor (ISP) and a 2-lane MIPI-CSI input (up to 1.5 Gbit/s per lane; the ISP takes up to 1920 × 1080).

**Sensor choice:** for fast tracking, a **global-shutter** sensor is much better. It captures the whole picture at
once, so fast-moving balls and robots aren't smeared or bent. Espressif's camera driver supports these on the P4:

| Sensor | Resolution | Shutter | Notes |
|---|---|---|---|
| **SC035HGS** (recommended) | 640 × 480 | Global, colour or mono | Best for high-speed blob + AprilTag tracking at close range |
| SC132GS | 1080 × 1280 | Global | More detail; more data to process |
| SC2336 | 1920 × 1080 | Rolling | Espressif's reference camera; fine for slower scenes |
| OV5647 | 2592 × 1944 | Rolling | Cheap Raspberry Pi v1.3 camera, but discontinued and noisy in low light |

**To check:** the sensor sits on the front sensor board itself, so the board needs SmartSens's package drawing for
the SC035HGS footprint (it's a small chip-scale package, best placed by the board maker). The model uses an 8.5 ×
8.5 mm M7 lens holder screwed to the board over the sensor.

**Where it sits:** on the front sensor board, on the robot's centre line, lens centre 46.1 mm above the floor, looking straight ahead through a
10.5 mm window in the mast. With a typical 53° × 41° lens, the bottom of the picture meets the floor about 12 cm
ahead. Tilting it 10–15° down would show the floor from about 6 cm ahead.

**Wiring:** no flex cable. The sensor's 2 MIPI data lanes + clock, I²C, power-down and reset run in short traces down
the front sensor board to its 2×8 right-angle header, which plugs straight into the socket next to the P4 on the main board.

### 8×8 ToF sensor (VL53L7CX)

**What it does:** fires invisible 940 nm laser pulses (Class 1, eye-safe) and times the echoes. It gives a distance
for each square of a 4 × 4 or 8 × 8 grid covering a 60° × 60° view.

| Spec | Value (ST datasheet) |
|---|---|
| Size | 6.4 × 3.0 × 1.6 mm, LGA-16 |
| Range | 2 cm to 350 cm (4 × 4, dark, white target); about 50–65 cm in bright room light |
| 8 × 8 range | about 200 cm in the dark, 50 cm in 5 klux light (white target) |
| Speed | up to 60 Hz; datasheet tests use 30 Hz for 4 × 4 and 15 Hz for 8 × 8 |
| Accuracy | ±9–12 mm up to 20 cm, ±3–6 % beyond (dark) |
| Supply | AVDD 3.3 V (or 2.8 V); IOVDD 3.3 V / 2.8 V / 1.8 V; AVDD must come up first or together |
| Current | about 45 mA (AVDD) + 50 mA (IOVDD) while ranging, about 0.3 W |
| Interface | I²C up to 1 MHz, address 0x52; the driver loads the sensor's firmware over I²C at start-up |
| Extra pins | LPn (enable; lets several sensors share one bus), INT (data ready), I2C_RST |
| Parts on carrier | 4.7 µF on AVDD, 100 nF on IOVDD, 47 kΩ pull-ups on LPn / INT / RSVD6, 47 kΩ pull-down on I2C_RST, 2.2 kΩ I²C pull-ups (on the main board) |

**Where it sits:** on the front sensor board directly above the camera, on the robot's centre line, centre 55.6 mm above the floor, looking out
through a 6 × 9.4 mm window. The window clears ST's 74° keep-out cone, and the camera lens sits below that cone.
The bottom of its view meets the floor about 9.6 cm ahead.

**Connection:** through the front sensor board's 2×8 header (3.3 V, GND, SDA, SCL, INT, LPn), so there's no cable.

### LED tracking beacon

A frosted Ø30 mm dome sits on a printed top deck **over the centre of the robot**. The deck is level with the top of
the mast, so the dome is the highest point and nothing hides it from the front; other robots' cameras and an
overhead camera can see it from any side, and its centre is the robot's centre. Inside, 7 WS2812B-5050 RGB LEDs (5 V, one data wire) light it in any
colour, so each robot can show its own colour or blink pattern (since 2026-10-31 a bought 7-LED WS2812B-5050 jewel, Ø23, on a foam pad: see *Beacon* above). The dome is exactly half of a Ø30 mm sphere (its rim is the
equator); the rim drops into a 0.6 mm groove in the deck. Print it in white or natural PETG with 2 walls and supports
inside the top, or use an opal acrylic dome of the same size.

## Main board (custom, Ø77 mm round, 1.6 mm)

See the numbered maps `bugbot_renders/board_map_top.png` and `board_map_bottom.png`; the numbers below match them.

### Top side

| # | Part | Chosen part | Size (mm) | 3D model |
|---|---|---|---|---|
| 1 | 6-axis IMU | ST LSM6DSV16X, LGA-14 (JLC C5267406): **chosen, not placed on the board yet**. Keep it near the board centre, away from the motors and the kicker (vibration, kick shocks) | 2.5 × 3.0 × 0.83 | KiCad `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` |
| 2 | Li-ion charger | TI BQ24074 (USB-C input, power-path), QFN-16 | 3 × 3 | drawn |
| 3 | 3.3 V supply | TI TPS63802 buck-boost + 1 µH inductor | 2 × 3 | drawn |
| 4 | 5 V supply (servo, LEDs) | TI TPS61023 boost + inductor | 1.6 × 1.6 | drawn |
| 5 | Battery protection | DW01A + dual MOSFET (SOIC-8 area) | 8 × 4 | drawn |
| 6 | Servo plug | 3-pin 2.54 mm SMD header | 5.0 × 7.6 × 9.3 | KiCad `PinHeader_1x03_P2.54mm_Vertical_SMD_Pin1Left` |
| 7 | BOOT button | **ZX-QC4545-4.3TP** 4.5 mm SMD tactile, top push (LCSC C7470171, same as the earlier BugBot boards); front of the row | 4.5 × 4.5 × 4.3 | drawn from the listing |
| 8 | RESET button | ZX-QC4545-4.3TP, as above | 4.5 × 4.5 × 4.3 | drawn from the listing |
| 9 | Status LED | 0603 green LED + 1 kΩ to a P4 GPIO, between the two buttons | 1.6 × 0.8 × 1.1 | KiCad `LED_0603_1608Metric` |
| 10 | LED beacon cable | JST-SH 3-pin **BM03B-SRSS-TB, upright** (the side-entry one faced the servo, so nothing could plug in); the cable goes straight up to the LED ring | 5.0 × 3.6 × 4.3 | KiCad `JST_SH_BM03B-SRSS-TB` |
| 11 | Battery plug | JST-PH 2-pin B2B-PH-K-S, upright, through-hole | 5.9 × 4.55 × 6.0 | KiCad `JST_PH_B2B-PH-K_1x02` |
| 12 | Front sensor board socket | 2×8 2.0 mm SMD socket; the front sensor board plugs in with a 2×8 2.0 mm right-angle header | 6.1 × 16.0 × 4.55 | KiCad `PinSocket_2x08_P2.00mm_Vertical_SMD` |
| 13 | Servo current sense | INA180A2 + 0.1 Ω 0805 shunt | SOT-23-5 + 0805 | drawn |
| 14 | **I²C expansion** | JST-SH 4-pin BM04B-SRSS-TB, upright (Qwiic / STEMMA QT): GND, 3V3, SDA, SCL | 6.0 × 3.6 × 4.3 | KiCad `JST_SH_BM04B-SRSS-TB` |
| 15 | **SPI + GPIO expansion** | 2×6 2.54 mm **female** SMD socket. Outer row SPI: 3V3, GND, SCK, MOSI, MISO, CS. Inner row GPIO: 3V3, GND, IO1, IO2, IO3, IO4. Female, so there are no bare pins to bend or short, and jumper wires plug straight in; SMD, so nothing pokes through onto the P4 module underneath | 15.2 × 5.1 × 7.5 (6.8 over the legs) | KiCad `PinSocket_2x06_P2.54mm_Vertical_SMD` |
| 16 | **Buzzer** | **MLT-8530** passive electromagnetic buzzer, driven by P4 PWM (LEDC): 80 dB, resonant 2.7 kHz, 2.5–4.5 V (rated 3.6 V), ~95 mA (JLC C94599, Extended, ~38,000 in stock, $0.209 on 2026-10-21). Low-side switch **AO3400A** (C20917, Basic, $0.097) with a gate resistor, **1N4148W** flyback diode across the buzzer (C81598, Basic, $0.012); runs from 3V3. Near the board edge, under a sound hole in the shell; on the main board, not the LED board (its magnet) | 8.5 × 8.5 × 3.3 | drawn (no KiCad model) |

Items 7–9, 14 and 15 sit in one row on the robot's left (+Y), outside the top deck and clear of the gripper arm's path.
Everything you plug into (the 2×6 socket and the Qwiic port) is grouped at the rear. The buttons, with the status LED
between them, are at the front, and nothing taller than the buttons is near them. Checks: a jumper-plug block over
the socket, the Qwiic plug and an 8 mm fingertip over each button touch nothing, with the arm open or closed. The I²C port shares the bus with the IMU and ToF, so add-ons must avoid
addresses 0x6A / 0x6B (LSM6DSV16X, set by its SA0 pin) and 0x29 (VL53L7CX, 8-bit 0x52).

### Underside

| # | Part | Chosen part | Size (mm) | 3D model |
|---|---|---|---|---|
| 1 | Processor module | **Waveshare ESP32-P4-Module-U**: ESP32-P4NRW32 (32 MB PSRAM) + ESP32-C6 Wi-Fi 6/BLE + 16 MB flash under a shield, 88 castellated pads at 1 mm, IPEX antenna socket in one corner | 25 × 25 × 3.3 | **Waveshare STEP** (`ESP32-P4-Module-3D.zip`) |
| 2 | Kicker plug | JST-PH 2-pin **B2B-PH-SM4-TB, upright SMD**, plugs in from below | 6.0 × 4.5 × 6.0 | drawn from JST's drawing (no KiCad model) |
| 3 – 5 | Motor plugs 1, 2, 3 | JST-SH 2-pin **BM02B-SRSS-TB, upright**, plug in from below; motor 1 at (−14, 17) so its wheel isn't underneath, motors 2 and 3 at the back right, (−21, −13) and (−25.5, −12.6), clear of the kicker, its capacitor and the wheels | 4.0 × 3.6 × 4.3 | KiCad `JST_SH_BM02B-SRSS-TB` |
| 6, 7 | Motor drivers | TI DRV8833PWP, HTSSOP-16 | 6.4 × 5.0 × 1.2 | KiCad `HTSSOP-16-1EP_4.4x5mm` |
| 8 | Kicker charger | Boost converter to ~24 V + AO3400 MOSFET + inductor | 6 × 6 area | drawn |
| 10 | Kicker capacitor | 330 µF 35 V SMD electrolytic | 10 × 10.3 × 12.5 | KiCad `CP_Elec_10x12.5` |
| 11 | **Power switch** | **C&K L101011ML04Q**, SPST through-hole right-angle slide switch, **4 A at 28 V DC**. All the robot's current goes through it (peaks ≈ 3 A with 3 motors, the servo and the kicker charger together). Its actuator comes out through a slot in the outer wall at the back right (237°), between two board posts | body ≈ 19.3 × 10.5 × 7.3, actuator 5.08, travel 3.56 | drawn (size from distributor listings: **check the C&K drawing**) |
| 12 | Kicker solenoid | JF-0520B on its side in the printed kicker bracket, M3 face toward −Y (outline shown) | 20 × 16 × 13 | drawn |
| 13 | Charging port | GCT USB4105 USB-C 16-pin, on the underside at 300°; the plug goes in through a slot in the wall | 8.94 × 7.8 × 3.3 | KiCad `USB_C_Receptacle_GCT_USB4105` |
| 14 | Flyback diode | SS14 Schottky across the solenoid coil, next to the kicker MOSFET | 4.3 × 2.6 × 2.1 | drawn |

Every plug was checked for room to go in: a box the size of the mating plug plus a cable bend in front of each
opening must not touch any other part. The side-entry plugs failed (they faced the servo, the solenoid or each other),
so all of them are now upright: the beacon plug points up, and the motor and kicker plugs point down into the body.

The old small slide switch (0.1 A) and the side-push buttons are gone. USB-C moved to the underside because the new
switch's pins now use the board edge where it used to sit.

### Antenna

The module's ESP32-C6 radio uses the IPEX (U.FL) socket in the module's corner. A 2.4 GHz FPC antenna
(about 24 × 8 mm, with a 100 mm IPEX Gen 1 lead) sticks to the underside of the top deck, the highest point
inside the robot and away from the motors.

Board outline: `bugbot_stl/pcb_outline.dxf`. It's a circle with a ball notch at the front, 4 × M2 post holes, M2 holes
for every part screwed to the board (mast, deck legs, cradle, servo block, pivot bracket, kicker bracket) and a 3.2 mm hole
beside the P4 module's corner for the antenna lead.
The stepped gripper arms pass above the board and outside the body, so there are no arm slots any more.

## Battery

| Part | Chosen part | Size (mm) | Qty |
|---|---|---|---|
| Cell | Protected 16340 Li-ion, 700 mAh, 3.7 V, rated ≥ 2 A, with solder tabs + JST-PH lead | Ø16.6 × 36.5 (protected cells vary by 1–2 mm, so **check**) | 1 |
| Holder | Printed cradle `batt_cradle.stl` + 8 mm hook-and-loop strap through the slot; screwed from under the board, so no screw heads sit under the cell; reliefs clear the power switch's frame tab and the 215° board screw | 18.2 × 38.9 × 10.0 | 1 |

## Small custom boards

| Board | Parts on it | Size (mm) | Connects by |
|---|---|---|---|
| Front sensor board | SC035HGS camera sensor + M7 lens holder soldered on the board (no flex), VL53L7CX above it, camera LDOs (2.8 V / 1.8 V / 1.2 V) and 24 MHz crystal, ToF decoupling (4.7 µF + 100 nF), 47 kΩ pull-ups on LPn / INT / RSVD6, 47 kΩ pull-down on I2C_RST | 19.0 × 22.1 × 1.6, 2 × M2 holes; camera and ToF on the robot's centre line, board offset to clear the servo ear | **2×8 2.0 mm right-angle header** (KiCad `PinHeader_2x08_P2.00mm_Horizontal`) straight down into socket #12; no cables |
| Wheel encoder board (× 3, identical; `kicad/BugBot_Enc`, generated by `design/lib/make_enc_board.py`) | MT6701QT-ACD (C49257133) on the wheel's axle line, MODE to GND (A/B mode), 100 nF (C1525) + 1 µF (C52923) on VDD, centre pad unconnected; 1×4 1.27 mm **right-angle header** (C22438190) at the top edge, pins pointing up. **Clip its 4 leads flush (≤ 0.5 mm) on the back**: the back faces the chassis wall | 8 × 16.7 × 0.8 | Plugs straight into a 1×4 1.27 mm socket on the main board's underside (J11–J13, through-hole C22438070, 4.3 mm): 3.3 V, GND, A, B. Its bottom edge sits in a slot in the base plate. No screws, no cable |

The front sensor board stands just behind the mast plate. The camera looks out through a 10.5 mm window and the
ToF through a 6 × 9.4 mm window above it. Two M2 × 4 self-tapping screws go in from behind, through its top corners into blind holes in the mast, so nothing shows on the front; the header holds the bottom.

**Header pinout (2×8, 2.0 mm):** 3.3 V, GND, CSI_CLK+/−, GND, CSI_D0+/−, GND, CSI_D1+/−, SDA, SCL, ToF_INT, ToF_LPn,
CAM_PWDN, CAM_RST. The ground pins between the three high-speed pairs keep the MIPI signals clean over the short
header (about 10 mm).

## Fasteners

| Use | Fastener | Qty |
|---|---|---|
| Wheel halves | M2 × 10 self-tapping | 9 |
| Motor clamp caps | M2 × 6 self-tapping | 12 |
| Main board to posts (from the top) | M2 × 6 self-tapping | 4 |
| Solenoid into the kicker bracket (slotted holes) | M3 × 4 (no longer: they must not reach the coil) | 2 |
| Kick disc onto the solenoid's push end (nut pressed into the disc) | M3 thin nut DIN 439 (1.8 mm) + a drop of threadlocker | 1 |
| Kicker bracket rear and front bosses (from the top of the board) | M2 × 6 self-tapping | 2 |
| Battery cradle (from under the board) | M2 × 6 self-tapping | 2 |
| Mast to board (from under the board, into the mast plate) | M2 × 6 self-tapping | 2 |
| Front sensor board to mast (from behind, blind holes) | M2 × 4 self-tapping | 2 |
| Top deck: 2 down into the mast, 2 up through the board into the legs | M2 × 4 / M2 × 6 self-tapping | 2 + 2 |
| Servo ears to the mast boss and servo block (from the −Y side) | M2 × 6 self-tapping | 2 |
| Servo block (from under the board) | M2 × 6 self-tapping | 1 |
| Servo horn to the +Y gripper arm (into pilots in the arm's horn pad) | M1.4 × 4 self-tapping (the horn's own small screws) | 2 |
| Hoop front bar | Steel dowel pin 3 × 45 mm (DIN 6325), pushed in last from the −Y side | 1 |
| Hoop pivot axle (−Y arm) | M2 × 8 + M2 nyloc nut, snug so the arm still swings | 1 + 1 |
| Hoop pivot bracket (from under the board) | M2 × 6 self-tapping | 2 |
| NFC tray to its 3 chassis posts (heads counterbored under the reader board) | M2 × 6 self-tapping | 3 |
| NFC antenna floor PCB (from below, through the board into the 3 bosses) | M2 × 5 nylon pan | 3 |

Everything screwed from **under** the board has to be done before the board goes into the chassis. The full order, with a
picture for every step, is in `bugbot_renders/assembly.html` (model: `bugbot_assembly_steps.scad`, `step = 1..13`).

## Cables

| Cable | Length (approx) |
|---|---|
| Antenna lead, IPEX Gen 1, 1.13 mm coax (comes with the FPC antenna) | 100 mm |
| LED beacon: JST-SH 3-pin (5 V, GND, data) | 50 mm |
| Motors: JST-SH 2-pin pigtails, soldered to the motor tabs | 3 × 40 mm |
| Kicker: JST-PH 2-pin (PHR-2 plug), 24 AWG | 40 mm |
| Battery lead (on the cell), JST-PH | 60 mm |
| NFC antenna PCB to the reader board: JST-SH 2-pin at the reader end only, the other end's 2 wires soldered into the antenna PCB (route 58 mm: up the centre column, out between the gearmotors at z 14.9, up through the board's notch) | 100 mm |
| NFC reader to the main board: pre-made JST-SH 8-pin, same-side | 100 mm |

## 3D models used

| Source | Parts |
|---|---|
| Waveshare (official STEP) | ESP32-P4-Module-U |
| KiCad 10 library (official STEP) | USB-C, upright JST-SH plugs (2-, 3- and 4-pin) and JST-PH battery plug, 2×8 2.0 mm header and socket, 2×6 2.54 mm SMD socket, 0603 LED, DRV8833, BNO085, kicker capacitor |
| Drawn from datasheets | SG90 servo, JF-0520B solenoid (largest listed size), Pololu gearmotor, camera lens holder, front sensor board, VL53L7CX, 16340 cell, LED ring, power ICs, JST-PH upright SMD kicker plug, ZX-QC4545 buttons, C&K L101 power switch (envelope) |

All STEP files are converted to STL with FreeCAD into `models/`, and `bugbot_parts.scad` holds the drawn models.

## Printing on an FDM printer

Every printed part was checked for overhangs steeper than 45° that aren't on the bed. **Only the dome needs supports**, inside its top, because it's a true hemisphere.
The only unsupported spans are short flat bridges (strap slot, mast window and socket pocket, deck groove). The
stepped gripper arms print flat, as two separate profiles, which also puts the layer lines along the arms where the grip
load bends them.

| File | Orientation (as exported) | Material | Notes |
|---|---|---|---|
| `stl/half_outer.stl`, `half_motor.stl` | flat joining face down | PLA / PETG | 0.12 mm layers |
| `stl/rollers_plate.stl` | rollers standing up | TPU 95A | brim, 15–20 mm/s |
| `chassis.stl` | base plate down | PLA / PETG | all holes are vertical; the switch slot is open at the top |
| `motor_caps.stl` | flat top down, groove up | PLA / PETG | |
| `batt_cradle.stl` | base down | PETG | 0.8 mm walls = 2 perimeters at 0.4 mm |
| `servo_block.stl`, `hoop_bracket.stl` | base down | PETG | |
| `kick_bracket.stl` | solenoid side down, tabs standing up | PETG | 4 perimeters; the slots and holes print vertical |
| `kick_disc.stl` | kick face down, nut pocket up | TPU 95A | 100 % infill; press the thin M3 nut in flush |
| `hoop.stl` | both arms flat, inner face (horn pad, pin bosses) up | PETG | 100 % infill; the pin hole is blind in the +Y arm and goes right through the −Y arm |
| `hoop_sleeve.stl` | standing on end | TPU 95A | 0.2 mm stretch fit on the 3 mm pin |
| `mast.stl` | base down | PLA / PETG | |
| `top_deck.stl` | upside down (deck on the bed, legs up) | PLA / PETG | the 0.6 mm dome groove ends up on the bed side (a short bridge) |
| `dome.stl` | rim down | white / natural PETG | exactly half a sphere, 2 walls; turn on supports (tree supports work well) for the inside of the top only. The outside stays smooth. |

## Software notes

**Wheel encoders:** each MT6701's A/B quadrature goes to one of the P4's hardware pulse counters (PCNT, x4 mode), so
counting costs no CPU. At 1024 pulses per turn that is 4096 counts per wheel turn, about 0.02 mm of wheel travel per
count on the 24 mm wheel (the -ACD variant gives 1024 pulses per turn out of the box: no EEPROM programming).
Read all three counters at 1 kHz for the wheel speed loops and the position filter. Calibrate the wheel diameter on a
measured straight run on your own floor. In the localisation sim, wheels + gyro alone drift 19–43 mm per minute (omni
wheels slip); with the camera's markers the error stays at 4.5–8 mm.

**Kick strength:** a ping-pong ball weighs 2.7 g, so the capacitor's energy sets the kick, not the solenoid's size.
330 µF at 24 V stores about 95 mJ; a small open-frame solenoid turns roughly 10–15 % of that into plunger motion, so
the ball leaves at about 2.5–3 m/s. For a harder kick, raise the capacitor (470 µF at 30 V roughly doubles it; the cap is
rated 35 V). Fire for 10–20 ms, then let the boost recharge it.

**Gripper current limit:** the INA180A2 gives 50 × 0.1 Ω = 5 V per amp, so 1 V on the ADC means 200 mA. An idle
SG90 draws ~10 mA, moving ~150–250 mA, and stalled ~650–700 mA. The gripper arm is screwed straight to the horn, so
this current limit is what protects the servo: when the hoop closes on a ball, the servo stops short of its target and
the current climbs. When it stays above ~350 mA for more than ~150 ms, command the servo back a few degrees to where it
stopped; it then just holds the ball. Read the current faster than the servo's 50 Hz pulse (for example 1 kHz) and average
it. A current limit can't catch a sudden knock to the arm (hitting a wall or another robot); if the SG90's plastic gears
strip, the MG90S (metal gears, same size and mounting) drops straight in.

**Status LED:** one green LED on a P4 GPIO (active high through 1 kΩ). For example: slow blink = booting, steady =
running, fast blink = low battery, double blink = no camera.

## Still to decide

- **Wheel encoders** (approved sketch `mech/freecad/sketches/wheel_encoder_v3.png`; 3D in `mech/freecad/build_encoder.py`): still to do: the main board's schematic (no nets yet) must take J11–J13 to 3V3, GND and 6 P4 pins for the hardware counters (PCNT). Chassis per wheel: plate slot 1.2 × 8.6 (0.2 a side), flat wall seat, header-lead pocket, a wall-top notch under the socket, and a 0.8 mm deep plate relief under the turning magnet ring (0.6 mm clearance); the thinnest wall left is 0.80 mm.
- Place the LSM6DSV16X (U1) on the main board. The old BNO085 spot (−9.4, −14.1) now sits on hole H7, and the servo covers the board centre; clear spots near the centre are drawn in `design/schematics/Main/imu_spot_sketch.png` (best guess: (−12.2, −8.5), furthest from the kicker). Its 0.5 mm pitch pads are 0.15 mm apart, under the board's 0.2 mm clearance, so it will need a local clearance rule (JLC can do 0.1 mm). `placements.json` still lists the BNO085.

- The SC035HGS footprint and lens holder screw holes on the front sensor board (get SmartSens's package drawing).
- The C&K L101011ML04Q's exact body size and pin positions (check the C&K drawing); the slot in the wall has 1 mm to spare each side.
- The exact power ICs (charger, 3.3 V, 5 V servo/LED boost, kicker boost) and the kicker voltage.
- The buzzer's spot on the main board (near the edge, top side) and its sound hole in the shell; the P4 PWM pin it uses.
- **NFC reader connector on the main board (to add):** an upright JST-SH 8-pin (BM08B-SRSS-TB, JLC C160394, pointing down into the body like the motor plugs) for the WS1850S reader board (its J1 sits at the board end near the robot centre, under the main board around (-2, 7)): 3V3, GND, SCK, MOSI, MISO, NSS, RST, IRQ, same pin order. SPI can share the expansion socket's bus with its own CS; RST and IRQ need 2 more P4 GPIOs. The reader draws ~20 mA, up to ~100 mA while the field is on. Plus a 100 mm JST-SH 8-pin cable.
- **Main board, for the underglow (to add):** an upright JST-SH 3 (BM03B-SRSS-TB, C160389) to the antenna floor PCB's J2 (5V, DIN, GND), and a 74AHCT1G125 level shifter (C7484) + 33 Ω series resistor on one P4 GPIO, because the floor board has no shifter. Plus a 100 mm JST-SH 3 cable.
- The NFC matching network for the antenna floor PCB (2.42 µH calculated): design/lib/nfc_design.py suggests series C 47 → 33 pF and parallel 68 + 22 → 68 + 15 pF (damping 2.2 Ω), all JLC stock. The reader board is not changed yet. **Before ordering the antenna PCB, wind a 3-turn wire loop of the same size and test it on the reader:** the big loop's field at the robot centre is the weak spot (model: ~0.8× of the read limit at today's drive), so the TX drive or Q may need raising.
- The JF-0520B's real size. The model uses the larger of the sizes found (3D ContentCentral model), so a real part should be the same or smaller. Measure the M3 hole spacing (the bracket's slots take 1.5–7.5 and 12.5–18.5 mm from the back) and where the e-clip sits. After cutting, the spring end may be **up to 15 mm** from the frame (1 mm clearance left; 13.5 mm gives 1.5 mm more).
