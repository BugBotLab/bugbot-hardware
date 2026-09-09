# BugBot stack: firmware notes from the hardware design

Written 2026-09-09 from the schematic review, the ngspice harness and the pre-order audit. These are things the
firmware must do, or must know, because of how the boards are built. Pin names are the ESP32-P4 module GPIOs.

## Rules the firmware must implement

1. **Low-battery cut-off at 3.2 V.** The DRV8830 motor drivers switch off below 2.75 V on the motor rail, which
   the cell reaches at about 3.0 V under load. The 3.3 V converter keeps the P4 alive down to a 2.8 V cell, so the
   robot would keep thinking while the motors stutter and stop. Read VBAT_SENSE (GPIO20, ADC1_CH4; it is
   VSYS_SW / 2 through 100k/100k, so multiply by 2) and stop driving at 3.2 V, warn at 3.4 V. With USB present the
   reading is the charger's SYS output (up to 4.5 V), not the cell.
2. **No hard reversal without a battery.** When running from USB with the cell removed, a fast full-speed reversal
   pushes motor energy back into the motor rail and only the capacitors absorb it; the rail can exceed the drivers'
   7 V limit. Detect "no cell" (VBAT_SENSE tracks the USB-derived SYS, about 4.3 V, and the charger reports no
   battery) and always coast to a stop before reversing in that state. With a cell fitted, reversals are fine.
3. **USB charging while driving needs a 1.5 A or 2 A source.** The charger is set to 0.8 A by a resistor; driving
   adds 0.5 to 1 A, so the USB draw is 1.4 to 1.8 A. On a 0.5 A port the charger folds the charge current back
   (no damage, slow or no charging). Firmware cannot change the charge current on this board; it can only tell the
   user: if VBUS sags below 4.5 V while charging, report "weak USB supply".
4. **Charging only when cool.** The charger's thermistor RT1 sits on the Motion board near the charger and reads
   about 73 C when driving; the charger stops charging above roughly 40 C at that pin and resumes when cool. Expect
   no charging during or just after a drive; don't treat it as a fault.
5. **Motor fault line.** MOT_INT (GPIO on the stack, active low, 10k pull-up) is the wired-OR nFAULT of the four
   DRV8830s. A stalled motor trips the driver's current limit at 400 mA (0R5 sense resistor) and, after about
   275 ms at the limit, the driver latches a fault and pulls MOT_INT low. Clear it by writing IN1=IN2=0 to that
   driver. Read each driver's FAULT register to find which one.
6. **ToF module LPn.** VL53L5CX LPn is GPIO2 with no pull-up; drive it high before any I2C traffic to the module.
   INT is GPIO3.
7. **Camera enable.** CAM_EN is GPIO23 through 100R, wired to both Pi Zero flex pins 17 and 18. Drive it high to
   power the module's regulators before I2C. The OV5647 is at I2C address 0x36 on the camera's own SCL/SDA lines
   (flex pins 20/21), not the main bus.
8. **I2C speed.** One 2.2k pull-up pair on Vision serves the P4, four DRV8830s on Motion, the ToF module, the
   BNO055 over the cable and the camera. Simulated rise 244 ns (limit 300 ns at 400 kHz), so 400 kHz works but
   is marginal; use 100 kHz unless there is a reason not to.

## Addresses and pins

| Device | Bus / pins | Address |
|---|---|---|
| DRV8830 U6 / U7 / U8 / U9 (Motion) | I2C GPIO26 (SDA) / GPIO27 (SCL) | 0x60 / 0x61 / 0x62 / 0x64 |
| BNO055 IMU (Odometry, over the cable) | same I2C | 0x28 |
| VL53L5CX ToF (module on J7) | same I2C, LPn GPIO2, INT GPIO3 | 0x29 |
| OV5647 camera | camera flex SCL/SDA, CAM_EN GPIO23 | 0x36 |
| PMW3360 optical flow (Odometry) | SPI: SCLK GPIO10, MOSI GPIO11, MISO GPIO12, NCS GPIO9, MOTION GPIO8 | |
| Servos | GPIO4 (servo 1), GPIO5 (servo 2), 3.3 V PWM into 1S servos | |
| WS2812 LED ball | data GPIO7, powered from 3.3 V (below the LED's 3.5 V minimum; most units work) | |
| Battery sense | GPIO20 = VSYS_SW / 2 | |
| Motor fault | MOT_INT, active low | |
| Power switch | SW3 on Vision grounds SW_ON; a Motion board alone stays off | |

## Boot and flashing

- P4 boot straps: GPIO35 (BOOT button SW1, 10k up), GPIO36 10k up, GPIO34 10k down. EN has the module's own
  pull-up plus the RESET button SW2 and 1 uF. C6 IO8 10k up (boot strap), IO9 internal pull-up.
- Flashing: the Motion USB-C reaches the P4's USB 2.0 OTG (HS) pins over the stack. The ROM supports DFU and
  USB-CDC download on that port (not if secure boot or flash encryption is enabled). There is no UART console:
  the app must run TinyUSB CDC on the OTG port for a console. GPIO37/38 (UART0) and GPIO24/25 (USB-Serial/JTAG)
  are not brought out.
- The C6 (Wi-Fi) is reachable only through the P4 (ESP-Hosted); its own UART is not brought out.

## Bring-up checks before first power (hardware, not firmware)

- Camera flex: pin 1 = 3V3, pin 22 = GND, contacts facing up in J3.
- GH10 cable Motion J7 to Odometry J1 is the REVERSE type: J7 pad 1 to J1 pad 10 must be a short.
- Battery lead polarity against J2 (JST-PH leads are wired both ways by different sellers).
