// Bought-part shapes for the FreeCAD model, each in its own frame. Exported as CSG (true solids in FreeCAD)
// or STL by mech/freecad/export_bought.sh. Uses the BugBot master and part models.
include <../scad/bugbot_chassis.scad>
part = "none";
what = "";
module sol_body_only(size=[20, 16.5, 13]) {   // jf0520b as fitted (nut="disc", spring end cut), without the printed disc and its nut
    L = size[0]; D = size[1]; H = size[2]; tail = 13.5;
    color(C_STEEL) difference() {
        union() { cube([L, 1.0, H]); for (x=[0, L - 1]) translate([x, 0, 0]) cube([1.0, D, H]); }
        for (x=[L/2 - 5.5, L/2 + 5.5]) translate([x, -1, H/2]) rotate([-90,0,0]) cylinder(d=2.5, h=3, $fn=16);
        for (x=[-1, L - 2]) translate([x, D/2, H/2]) rotate([0,90,0]) cylinder(d=6.4, h=4, $fn=24);
    }
    color([0.15,0.3,0.75]) translate([1.5, D/2, H/2]) rotate([0,90,0]) cylinder(d=11.5, h=L - 3, $fn=48);   // blue taped coil
    translate([0, D/2, H/2]) {
        color(C_STEEL) rotate([0,90,0]) cylinder(d=6, h=L, $fn=24);
        color(C_STEEL) translate([L, 0, 0]) rotate([0,90,0]) cylinder(d=3, h=1.8, $fn=16);
        color(C_STEEL) translate([-tail, 0, 0]) rotate([0,90,0]) cylinder(d=6, h=tail, $fn=24);
        color([0.8,0.8,0.82]) for (i=[0:9]) translate([-1.15*i - 0.7, 0, 0]) rotate([0,90,0]) difference() { cylinder(d=8, h=0.6, $fn=24); translate([0,0,-1]) cylinder(d=6.8, h=3, $fn=24); }
        color(C_STEEL) translate([-12.4, 0, 0]) rotate([0,90,0]) cylinder(d=9, h=0.5, $fn=24);
        color(C_BLK) translate([-13.0, 0, 0]) rotate([0,90,0]) cylinder(d=8, h=0.6, $fn=24);
    }
    color(C_BLK) for (i=[0:1]) translate([L/2 - 2 + i*2, D, 1.5]) rotate([-90,0,0]) cylinder(d=1.2, h=4, $fn=12);
}
module pcb_parts_only() {   // everything pcb() puts on the main board (not the board itself)
    // ---- top side ----
    on_top(-9.4, -14.1) stl_part("lga28_bno085.stl", [0.15,0.15,0.16]);   // BNO085 9-axis IMU (LGA-28 5.2 x 3.8)
    on_top(-7.5, -29) lga([3, 3, 0.8]);                       // USB-C Li-ion charger (BQ24074, QFN-16 3 x 3)
    on_top(-3.5, -29) lga([2.0, 3.0, 0.9]);                   // 3.3 V buck-boost (TPS63802, 2 x 3)
    on_top(-3.75, -25) inductor(2.5);                         //   ... its inductor
    on_top(0.2, -29) lga([1.6, 1.6, 0.6]);                    // 5 V boost for servo + LEDs (TPS61023)
    on_top(-0.25, -25.5) inductor(2.5);                       //   ... its inductor
    on_top(5, -34) ic_pkg([8, 4, 1.2], 8, 1.27);              // battery protection / power-path (SOIC-8 area)
    on_top(6.8, -15.3, 90) stl_part("hdr_1x03_254_smd.stl");                 // servo plug, 3-pin 2.54 mm SMD header
    on_top(-3.95, -19.9) ic_pkg([2.9, 2.8, 1.1], 6, 0.95);   // INA180A2 servo current-sense amplifier (SOT-23-5), output to a P4 ADC pin
    on_top(-0.5, -19.1) color([0.12,0.12,0.13]) cube([2.0, 1.25, 0.5]);   // 0.1 ohm 0805 shunt in the servo supply
    // robot's left (+Y), outside the deck and the arm path, in one row: plug-ins at the rear, buttons at the front
    on_top(-11.44, 26.5, 90) stl_part("sock_2x06_254_smd.stl", [0.15,0.15,0.16]);   // expansion: 2x6 2.54 mm FEMALE SMD socket. Outer row SPI (3V3 GND SCK MOSI MISO CS), inner row GPIO (3V3 GND IO1..IO4)
    on_top(0.5, 26.5, 180) stl_part("jst_sh_4_vert.stl", [0.93,0.91,0.82]);   // I2C expansion: JST-SH 4 (Qwiic / STEMMA QT: GND 3V3 SDA SCL), next to the socket
    on_top(8.5, 29.6) tact_4545();                                            // BOOT button (ZX-QC4545-4.3TP, as on the earlier BugBot)
    on_top(16.0, 29.6) tact_4545();                                           // RESET button
    on_top(12.25, 27.0) color([0.3,0.85,0.3]) import("models/led_0603.stl");  // status LED (0603 green, 1 k to a P4 GPIO), between the buttons
    on_top(-6.5, 14.0) stl_part("jst_sh_3_vert.stl", [0.93,0.91,0.82]);      // LED beacon cable (JST-SH 3 BM03B-SRSS-TB, upright: the cable goes straight up to the LED ring)
    on_top(-0.5, -34.55, 90) stl_part("jst_ph_2_vert.stl", [0.93,0.91,0.82]);   // battery plug (JST-PH B2B-PH-K, upright)
    on_top(fsb_sock[0], fsb_sock[1]) stl_part("sock_2x08_200_smd.stl", [0.15,0.15,0.16]);   // front sensor board socket (2x8 2.0 mm SMD)
    // ---- underside ----
    on_bottom(p4_pos[0], p4_pos[1]) translate([0, 0, 0.8]) stl_part("esp32_p4_module.stl", [0.55,0.6,0.7]);   // Waveshare ESP32-P4-Module-U (Waveshare 3D model)
    on_bottom(-18.0, 9.75) jst_ph_top_smd(2);                 // kicker solenoid (JST-PH B2B-PH-SM4-TB, upright SMD: plugs in from below)
    on_bottom(-14.0, 17.0) stl_part("jst_sh_2_vert.stl", [0.93,0.91,0.82]);  // motor 1 (JST-SH 2 BM02B-SRSS-TB, upright; moved off the 160 deg wheel)
    on_bottom(-21.0, -13.0) stl_part("jst_sh_2_vert.stl", [0.93,0.91,0.82]);      // motor 2 (upright, back right: clear of the kicker, its capacitor and the wheels)
    on_bottom(-25.5, -12.6) stl_part("jst_sh_2_vert.stl", [0.93,0.91,0.82]);      // motor 3 (upright, beside motor 2)
    on_bottom(-27.0, -2.6) { color([0.12,0.12,0.13]) cube([4.3, 2.6, 2.1]); color([0.75,0.75,0.78]) for (x=[-0.4, 4.3]) translate([x, 0.6, 0]) cube([0.4, 1.4, 0.3]); }   // SS14 flyback diode (SMA) across the solenoid
    on_bottom(20.3, 12.8) stl_part("htssop16.stl", [0.15,0.15,0.16]);        // DRV8833 motor driver #1 (HTSSOP-16), clear of the ball
    on_bottom(-25.8, 4.5) stl_part("htssop16.stl", [0.15,0.15,0.16]);        // DRV8833 motor driver #2
    on_bottom(-24, -8) ic_pkg([3, 3, 1.0], 6, 0.95);          // kicker boost converter
    on_bottom(-20.5, -8) inductor(2.5);                       //   ... its inductor
    on_bottom(-24, -4.6) ic_pkg([3, 1.6, 1.0], 4, 0.95);      //   ... switching MOSFET (AO3400, SOT-23)
    on_bottom(flow_pos[0] - 3, flow_pos[1] - 3) paa5100();    // PAA5100JE-Q floor sensor + lens
    for (dx=[-4.8, 3.2]) on_bottom(flow_pos[0] + dx, flow_pos[1] - 0.8) led_1206();   // floor LEDs, inside the base-plate window
    power_switch();
}
if (what == "PCBParts") pcb_parts_only();
if (what == "Gearmotor") pololu_2358();
if (what == "Solenoid") sol_body_only();
if (what == "M3ThinNut") color(C_STEEL) translate([0,0,0.05]) difference() { cylinder(d=5.5/cos(30), h=1.8, $fn=6); translate([0,0,-1]) cylinder(d=2.4, h=4, $fn=12); }
if (what == "Servo") sg90(horn=false);
if (what == "Cell") cell_16340(16.6, 36.5);
if (what == "KickCap") ecap(10, 12.5);
if (what == "LEDRing") led_ring24();
if (what == "Antenna") mirror([1,0,0]) fpc_antenna(24, 8);
if (what == "FrontBoard") front_board();
// the front board's 2x8 right-angle header, in place (FreeCAD's CSG importer drops the transforms on mirrored STL imports)
if (what == "FrontHeader") translate([fsb_x, fsb_sock[1] + 7, hdr_zm]) mirror([1,0,0]) rotate([0,90,0]) import("../models/hdr_2x08_200_ra.stl");
