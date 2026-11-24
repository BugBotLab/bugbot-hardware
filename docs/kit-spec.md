# BugBot Kit: design spec

Written 2026-11-24 from the design discussion, the Seeed XIAO ESP32-S3 Sense wiki (read 2026-11-24) and the
verified circuits already in this repo. **The schematic is drawn** (see *The schematic*); there is no layout and
no priced BOM yet. The kit's product name is still open.

The kit is a sellable version of the vibration BugBot: **one daughter board** that a XIAO ESP32-S3 Sense plugs
into. The XIAO is the whole brain — MCU, Wi-Fi, BLE, PSRAM, camera, microphone, SD card and battery charging all
come with it. Our board carries the motors, the drivers, the IMU, the distance-sensor header, the lamp and the
power switch, and nothing else.

It is significantly smaller than the three-board stack, with smaller motors and a smaller cell.

## What this replaces

| Three-board stack (today) | Kit |
|---|---|
| Three 40 x 40 mm boards on 2 x 5 sockets, 7.1 mm apart | One board, roughly 28 x 28 mm (see *Open items*) |
| ESP32-P4 + ESP32-C6 for Wi-Fi, on the Vision board | XIAO ESP32-S3 Sense, bought |
| OV5647 on a 22-pin flex, our connector | The Sense's own camera module on a short flex |
| PMW3360 optical flow on a cabled Odometry board | Deleted; the IMU is the only motion sense |
| BNO055 IMU on the Odometry board | BNO055 on the main board (see *The IMU stays 9-axis*) |
| USB-C charger, 0.8 A, with its own thermistor and 3.3 V converter | The XIAO's charger and its 3.3 V regulator |
| Two servo outputs | None |
| Four DRV8830 drivers, 6 x 15 mm coreless motors | One DRV8833 for all four, smaller motors |

Only the motor drive and the IMU survive, and both are deliberate: see the two sections below.

## The board

| Block | Part | Notes |
|---|---|---|
| Brain socket | XIAO ESP32-S3 Sense, 21.14 x 17.78 mm, 14 pads | 2 x 7 socket, 2.54 mm pitch, rows 15.24 mm apart. **Confirmed**, see below |
| Motor driver | 1 x TI DRV8833, HTSSOP-16, LCSC C50506 | All four motors from one chip; replaced four DRV8830s on 2026-11-24 |
| Motors | 4 x vibration motor, in an X at the board corners, eccentrics on the axles | Size **to confirm by measurement** |
| IMU | 9-axis, Bosch BNO055 as the default | Same part and address as today, so firmware carries over |
| Distance sensor | 6-pin 2.54 mm **right-angle** header at the front edge | A bought VL53L1X breakout plugs straight in, facing forward, no cable |
| Lamp | WS2812B under a printed semicircular diffuser dome | Behind or beside the XIAO; the XIAO covers most of the top face |
| Power | LiPo connector, master switch, reverse-polarity P-FET | Cell **to confirm**; the FET guards against a reversed cell |
| Camera | No connector on our board: a slot for the Sense's flex to pass through, and a mount for the bracket | The module folds 90 degrees to face forward |

## The XIAO's footprint, and why it cannot sit flat

Measured 2026-11-24 from Seeed's own CAD, not from the wiki: `XIAO_ESP32S3_v1.1_Dimensioning.dxf`,
`XIAO_ESP32S3_ExpBoard_v1.0_top.dxf` and `_bot.dxf`, and the two schematic PDFs (main board v1.3,
ExpBoard v1.2). All of these are linked from the wiki's resources section.

**The socket footprint.** The XIAO is **21.14 x 17.78 mm**. Seven castellated pads per side at **2.54 mm
pitch**. The pads straddle the board edges, which are 17.78 mm apart, but the on-board half of each pad is
centred **15.24 mm** from its opposite number — exactly 0.600 inch. So the footprint is an ordinary
**2 x 7 header, 2.54 mm pitch, rows 15.24 mm apart**, and any 0.1 inch socket fits. The two rows are centred
along the board's length, 2.95 mm in from each end.

**The expansion board does not pass the pads through.** It is 17.78 x 15.42 mm — the same width as the XIAO
but 5.7 mm shorter — and carries only **two** castellated pads, one per side, and those sit midway between two
of the XIAO's pad positions rather than lining up with them. The XIAO's own castellations are the only
interface. The expansion board simply hangs underneath.

**So the stack cannot be soldered flat to our board.** The two are joined by a Hirose **DF40C-30DP-0.4V** on the
XIAO mating a **DF40HC(3.0)-30DS-0.4V** on the expansion board: 30 pins, 0.4 mm pitch, 0.3 A per pin, and a
**3.0 mm** mated height. Add the expansion board's own thickness and the microSD socket on it and roughly
**6 mm** has to clear below the XIAO's pad plane. A standard 2.54 mm female header gives about 8.5 mm, which
clears it with room to spare; a low-profile socket at 5 mm does not. **Use the full-height socket.**

Two things fall out of that gap, both good. The camera flex can leave sideways through it, so the slot through
our PCB may not be needed at all — check it at layout before cutting board away. And because the expansion
board covers only the lower 15.42 mm, the XIAO overhangs it by about 6.3 mm at the far end, which is exactly
where the **BAT pads** are: they stay reachable with the expansion board fitted, and the cell's wires can run up
to them in that strip.

## One DRV8833, and what it costs

This spec originally used four I2C DRV8830s, carried over from the Motion board, because they cost no GPIOs at
all. Costing killed that on 2026-11-24: four of them are $5.90 a board against $1.08 for one DRV8833, and JLC
had **948 DRV8830s in stock, a 237-board ceiling**, against 36,630 DRV8833s.

**Four motors out of two H-bridges.** Each motor sits between one output and **VMOT**, not GND, so it runs when
its output is pulled low. The DRV8833's truth table (00 = both Z, 01 = L H, 10 = H L, 11 = L L) means xOUT1 is
low exactly when xIN2 is high, and xOUT2 is low exactly when xIN1 is high. The half-bridges are therefore
independent, but **the control is crossed**, and firmware has to know it:

| pad | drives |
|---|---|
| AIN1 (D0) | motor B |
| AIN2 (D1) | motor A |
| BIN1 (D6) | motor D |
| BIN2 (D7) | motor C |

**The catch, and it is a real one.** The two motors on a bridge share a decay mode. While motor A is PWMed off,
the bridge sits at 00 (coast, fast decay) if motor B is off, but at 10 (both motor ends at VMOT, slow decay) if
motor B is on. So motor A's average current for a given duty depends on whether motor B is running. The four
DRV8830s did not do this — they regulated each motor's voltage on their own, against battery sag too. Firmware
must now calibrate that coupling out, or always drive each pair in a fixed pattern. **If repeatable gaits turn
out to need the DRV8830s' independence, this is the thing that will send us back.**

Also gone: the per-motor 400 mA current limit (AISEN and BISEN are tied to GND, so there is no limit at all) and
the wired-OR fault line, since no pad was left for it — nFAULT has a pull-up and is a test point only.

## The IMU stays 9-axis

A 6-axis part drifts in yaw, and on a vibration robot with no wheel odometry there is nothing else to correct it:
the optical flow sensor is gone and the camera faces forward, not down. So the kit needs a magnetometer.

Note that this is the opposite of the omni robot's choice, and for a good reason: that robot rejects the
magnetometer because its wheel encoder magnets swamp it. The kit has no encoder magnets and no steel near the
board, so a magnetometer works here.

It is the **BNO055**: the part this robot already uses, at the same I2C address, doing the sensor fusion on-chip
and outputting absolute orientation, so a kit buyer gets a drift-free heading with no filter to write.

**Settled by costing on 2026-11-24, and not the way this section used to predict.** The plan was to fall back to
LSM6DSV16X + LIS2MDL if $10 did not survive pricing. It does not survive — the BNO055 is $6.88 at 100 off — but
the fallback is worse: **LIS2MDL has zero stock at JLC** in either listing, so the pair cannot be built at all,
and even if it could, LSM6DSV16X at $2.29 plus a magnetometer at about $3.17 saves roughly a dollar and buys a
filter to write. The BNO055 has 7,836 in stock. It stays, on availability rather than on price.

## Pin budget

| Pad | GPIO | Use |
|---|---|---|
| D0 | GPIO1 | AIN1 (PWM, drives motor B) |
| D1 | GPIO2 | AIN2 (PWM, drives motor A) |
| D2 | GPIO3 | WS2812 lamp data |
| D3 | GPIO4 | VBAT sense (ADC1_CH3) |
| D4 | GPIO5 | I2C SDA |
| D5 | GPIO6 | I2C SCL |
| D6 | GPIO43 | BIN1 (PWM, drives motor D) |
| D7 | GPIO44 | BIN2 (PWM, drives motor C) |
| D8, D9, D10 | GPIO7, 8, 9 | Not used by us: left to the SD card's SPI |

Every pad is now spoken for, and two of the placements are forced rather than chosen.

**Why the motor PWMs are split across D0/D1 and D6/D7** instead of sitting together on D0 to D3: the battery
sense needs an ADC, and on the S3 only GPIO1 to GPIO6 have one — D6 and D7 are GPIO43 and GPIO44, which have no
ADC at all. So two PWMs had to take the pads that cannot measure anything, leaving D3 free for the divider.

**Why the lamp is on the strapping pin.** D2 is GPIO3, sampled at reset. A WS2812's DIN is an input only, so
that pad floats at reset exactly as it would bare, which is safe. The battery divider must *not* go there: it
would hold the strap high at reset.

The distance sensor lost its XSHUT and INT pads in the swap. XSHUT is active low, so it now has a 10k pull-up to
3V3 on the header — without it the module would never leave reset. INT is simply unconnected; a VL53L1X works on
I2C alone.

D6 and D7 are UART0 TX and RX. The S3 consoles over native USB, so using them as GPIO is fine, but it means no
UART debug on the pads. The BNO055's own INT and RST are left unconnected, as they are today.

## I2C map

One bus, the XIAO's default pins. Addresses as on the Motion board, so firmware carries over.

| Device | Address |
|---|---|
| BNO055 IMU | 0x28 |
| VL53L1X module | 0x29 |

Only two devices, now that the motors are on PWM rather than I2C. One thing to get right: the BNO055's
**alternate** address is 0x29, which is the distance sensor's, so tie its ADR pin (COM3) low and keep it at
0x28.

Pull-ups live on our board, because the XIAO has none on D4/D5. Size them for the four drivers, the IMU and the
module; on the old stack 2.2k gave a 244 ns rise against a 300 ns limit, so 400 kHz was marginal and 100 kHz was
the recommendation. This bus is shorter and lighter, so 400 kHz should be comfortable — **simulate it before
trusting it**.

## Power

1. **One master switch.** The cell plugs into our board. Cell positive goes through the switch, and the switch
   feeds both the motor rail and the XIAO's BAT+ pads. Switch off is fully dead. You charge with the switch on.
2. **Charging is the XIAO's, at 110 mA.** Through its own USB-C. The charger is an **SGM40567-4.2XG**, and its
   schematic states the current outright: `ICharge = 24000 / 220K = 110 mA`. Ignore the wiki's 50 mA and 100 mA
   figures, which belong to other boards. It is resistor-set, but the resistor is on Seeed's board, so for us it
   is fixed. A 300 mAh cell is therefore about a three-hour charge. If that is too slow the only fix is our own
   charger, which puts USB-C and a charge IC back on our board.
3. **With the switch off and USB plugged in, the XIAO runs but does not charge**, because VBUS powers it directly
   while the switch holds the cell off BAT+. Harmless, but say so in the instructions.
4. **No cell means no motors**, since the motor rail comes from the cell through the switch and never from VBUS.
   This deletes the old stack's rule about never reversing hard without a battery fitted: on this board it cannot
   happen.
5. **We must add our own battery sense.** The standard XIAO brings no battery voltage to a GPIO. Put a divider
   from the switched cell rail to **D3** (D1 is a motor PWM now) and keep the old thresholds: stop driving at
   3.2 V, warn at 3.4 V. Those thresholds protect the cell, not the driver: the DRV8833's own minimum supply is
   lower than the DRV8830s' 2.75 V, so firmware is what stops the robot, not the chip. **Confirm the DRV8833's
   UVLO against its datasheet** before relying on either number.
6. **3.3 V comes from the XIAO, and there is less of it than the wiki says.** The rail is an **SGM6029** DC-DC
   marked **Imax = 600 mA** on Seeed's own block diagram, not the 700 mA the wiki quotes, and the ESP32-S3 itself
   feeds from it — Wi-Fi peaks are the bulk of that. Budget roughly **300 mA** for the IMU, the distance sensor
   and the lamp together, and cap the WS2812's brightness in firmware rather than assuming headroom: one of them
   at full white is 60 mA on its own. Motors never touch this rail; they run from the cell.
7. **The board runs with no cell fitted.** VBAT reaches the DC-DC through a P-FET (LP040AN3TBG) and VBUS through
   a Schottky (LMBR4010BST5G), so USB alone powers the XIAO. The motors still will not turn, per rule 4.

## Mechanical

- Four motors at the corners, splayed at 45 degrees so the bodies form an X and the cables leave outward.
- **The XIAO's shadow is usable, and that is what makes a small board possible.** Standing 8.5 mm up on its
  socket, it does not cover the top face so much as roof it. Under the expansion board there is roughly 2.6 mm
  of headroom, which takes the DRV8833 in HTSSOP-16 and every passive on the board; under the 6.3 mm
  overhang there is the full 8.5 mm. So the electronics can live beneath the XIAO on the top face instead of
  being pushed to the underside. Confirm the 2.6 mm against a real Sense board before trusting it — it depends
  on the expansion board's thickness and what sits on its underside, neither of which Seeed document.
- What the XIAO's shadow cannot hold is anything that has to be seen or reached: the lamp and its dome need
  their own strip of board behind or beside it. That, not the electronics, is what sets the board's length.
- The distance sensor's right-angle header puts the module out past the front edge, cantilevered on its own pins.
  The breakout weighs almost nothing, so pins alone should hold it, but check it against the robot's own vibration
  before calling it done — this board shakes itself for a living.
- The XIAO rides about 8.5 mm up on its socket, with the expansion board and the camera flex in the gap. That is
  the robot's tallest feature and it sets the centre of mass. It is still less than the 15 mm of stacked boards
  on the robot it replaces.
- The camera is a **24-pin 0.5 mm flex** on an AFC01-S24FCC-00 connector on the expansion board. A printed
  bracket holds the module turned 90 degrees to face forward; respect the flex's bend radius. Route it out
  through the socket gap if it will go, and only cut a slot in the PCB if it will not.
- The BAT pads sit in the 6.3 mm of XIAO that overhangs the expansion board, so they stay reachable. Keep that
  strip clear of our own tall parts: Seeed warn against obstructing those pads, and we are soldering to them.

## Open items

The footprint question that used to head this list is closed: see *The XIAO's footprint*. So is the charge
current, at 110 mA. What is left, in roughly the order it blocks drawing:

1. **Which distance-sensor breakout.** Vendors order their pins differently — Pololu's VL53L1X carrier is VDD,
   GND, SDA, SCL, XSHUT, GPIO1, Adafruit's is not the same. Name one module in the kit and match the header to
   it, or the kit ships a board nobody's sensor fits.
2. **Motor size.** Buy two or three candidates and measure: can diameter and length, terminal type, eccentric
   mass, winding resistance and no-load current. Then put the measured numbers into `sim/parts_spec.py` as a new
   `MOTOR_TYPES` entry and re-run the bench. There is no current limit on this board at all now — AISEN and
   BISEN go to GND — so the motors' stall current has to be safe on its own, or sense resistors go back in.
3. **Board size.** Less pressing than it looked. Because the drivers and passives can sit under the raised XIAO,
   about 28 x 28 mm now looks achievable with **one-sided** assembly, which is the cheap option at JLC and the
   one a kit wants. Settle it by laying the parts out, not by picking a number — and if the 2.6 mm of headroom
   turns out to be less, fall back to roughly 32 x 32 mm rather than to two-sided assembly.
4. **Cell.** Capacity, dimensions and connector, against a 110 mA charge and the four motors' draw.
5. **Camera module.** The flex is 24-pin 0.5 mm, but Seeed say the module itself varies between OV5640, OV3660
   and OV2640 during the transition, and the shipped flex may be too short to reach a forward bracket once it has
   taken a 90 degree fold. Buy one and try it.
6. **Whether the DRV8833's shared decay mode hurts the gait.** The swap is done and drawn, but the two motors
   on each bridge now interact (see *One DRV8833*). This can only be answered on real hardware with real
   motors; if it bites, the way back is four DRV8830s and a much tighter board.
7. **The parts that are still unpriced**: the distance-sensor module, the cell, the motors, the PCB and
   assembly quote, and the through-hole connectors. The board's own SMT parts are priced.
8. **The product name.**

The IMU question is closed: the BNO055 stays, because its cheaper alternative cannot be sourced.

## The schematic

Drawn 2026-11-24, in `design/schematics/Kit/`: the sheet, `BugBot.kicad_sym`, the project file,
`golden_netlist.xml` and the PDF, the same set each of the other three boards carries. It is generated by
`make_kit_schematic.py` in that folder, which reuses the shared `Design` writer out of `cad-tools`. One A3 sheet,
**39 parts, 46 nets** — flat, not hierarchical, because at this size hierarchy would hide the circuit rather
than reveal it. It was 49 parts before the DRV8833 swap on 2026-11-24 took out three drivers, four sense
resistors and six capacitors.

**Treat the generator as scaffolding from here on.** It has done its job; once the board is electrically
verified the schematic is frozen and edited in the GUI, like the other three. Do not re-run the script over
hand edits.

ERC: **0 errors**, 2 warnings, both of them `kicad-cli` not finding the global `jlc` footprint library. The
Odometry board throws four of exactly the same warning, so it is the environment, not the circuit. The netlist
has no floating nets.

The DRV8833 symbol is ours rather than KiCad's, for one reason: `Driver_Motor:DRV8833PWP` leaves the thermal
pad off the symbol entirely, so the pad would never reach the netlist and could be forgotten at layout. Ours
carries it as pin 17, tied to GND.

**Q1, a reverse-polarity P-FET**, between the switch and VMOT, with R1 holding its gate down. It was not in the
original spec; proposed and kept on 2026-11-24. The reason is in `docs/bring-up.md`, which already warns that
JST-PH battery leads are wired both ways round by different sellers. On the stack that is a note for whoever
assembles it; on a kit it is a customer reversing a cell and killing the board. The FET sits after the switch,
so it draws nothing when the robot is off, and it conducts both ways when on, which the charge path needs.

Two placeholders are deliberately visible in the drawing:

- **J5 to J8**, the motor terminations, are 1x02 2.54 mm headers until the motors are bought and measured.
- **AISEN and BISEN are tied straight to GND**, so there is no current limit at all. If the chosen motors need
  one, sense resistors go there — but the limit is then shared by the two motors on that bridge.

Every part now carries an LCSC number checked on JLC, including the ones that did not before: the P-FET is
C5343298 and the switch C431540.

Cosmetics only: the generator puts each part's value text at a fixed offset, so a few labels sit over their
symbols. The other generated boards do the same. Nudge them in the GUI.

## What it costs

Priced 2026-11-24 against JLC's own component search (`cad-tools/kicad/lib/jlc_find.py`) from the schematic's
netlist, then re-priced the same day after the DRV8833 swap. The JLC BOM is
`design/bom/BugBot_Kit_Board-JLC-BOM.csv`: 17 SMT lines. The eight through-hole connectors are not in it,
because JLC's economic assembly will not fit them — they ship loose, which for a kit is arguably the point.

**The board's SMT parts: $12.25 at one off, $8.67 at a hundred.** Before the driver swap those were $20.32 and
$13.59, so one chip in place of four saved **$4.92 a board** at volume. What is left is dominated by a single
part:

| | each at 100 | qty | line |
|---|---|---|---|
| BNO055 | $6.8804 | 1 | **$6.88** |
| DRV8833 | $1.0777 | 1 | $1.08 |
| everything else (15 lines) | | 28 | $0.71 |

**The IMU is now 79 per cent of the board.** Cost work here means the BNO055 or nothing, and *The IMU stays
9-axis* explains why its cheaper alternative cannot be sourced at all.

The supply ceiling moved as well. It used to be 948 DRV8830s, or 237 boards. The tightest line is now the
JST-PH battery connector at 2,280 in stock — and unlike the DRV8830 that is a commodity with a dozen drop-in
substitutes, so it is not really a ceiling.

**The whole kit, parts only, around 100 units.** Only the first two rows are verified; the rest are marked.

| | | |
|---|---|---|
| XIAO ESP32-S3 Sense | $18.90 | Seeed list price, read 2026-11-24. No bulk break published; there is a bulk-quote form |
| Board SMT parts | $8.67 | verified on JLC |
| PCB and assembly | ~$1 | **estimate**, not quoted |
| The eight through-hole connectors | ~$0.50 | **estimate**; JLC's search does not surface them |
| Distance-sensor module | $3 to $6 | **not priced**, and not yet chosen |
| 1S LiPo cell | $2 to $4 | **not chosen** |
| Four vibration motors | $2 to $6 | **not chosen** |

Roughly **$36 to $45 of parts**, before the printed chassis, the mat, a box, shipping, a failure allowance and
any margin. **The XIAO is now about half of that** — it is the one line with no second source and no published
volume discount. If the kit has to get cheaper from here, that is where to look, not at the board.

## Still public, still private

The same rule as the rest of the robot: the kit's **schematics are public**, the **PCB layout is not**. A kit that
people buy makes this sharper, not looser — publish the sheets, the symbols, the netlist and the BOM, and keep the
`.kicad_pcb`, the gerbers and the pick-and-place out of the repo.
