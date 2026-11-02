// BugBot (new) - 80 mm round chassis, first-pass layout
// 3x 24 mm omni wheels (micro_omni_wheel.scad) on Pololu 136:1 sub-micro gearmotors,
// all wheels inside the 80 mm circle. Motors are offset sideways (pinwheel) so their
// backs pass each other in the middle.
// Front: ping-pong ball pocket, solenoid kicker behind it, one 9g servo swinging a stepped hoop
// down over the ball (gripper). Top: round main PCB (ESP32-P4), 1S LiPo, camera + 8x8 ToF
// mast. Floor tracking: PAA5100JE optical-flow sensor on the PCB underside, looking down
// through a window in the base plate. Chosen parts and their sizes: PARTS.md
//
// Parts: "assembly" (everything), "chassis" (print, plate down), "motor_caps" (print),
// "hoop" (print), "mast" (print), "pcb_outline" (2D DXF outline for the board).
// Bought parts are drawn at their listed outer sizes (see PARTS.md), not detailed models.

use <bugbot_parts.scad>   // detailed bought-part models

part = "assembly";   // [assembly, exploded, chassis, motor_caps, hoop, hoop_sleeve, hoop_bracket, servo_block, mast, top_deck, dome, batt_cradle, pcb_outline, wheel, motor, solenoid, servo, battery, pcb, camera, cap, ball]
hoop_open = false;   // assembly: show the gripper hoop raised
ghost = false;       // assembly: draw the chassis see-through to show the parts inside

/* [Body] */
body_r   = 40;       // 80 mm round body
wall_t   = 1.2;      // outer wall
r_in     = body_r - wall_t;
plate_z  = 6.5;      // underside of base plate (floor clearance)
plate_t  = 1.6;
pcb_z    = 29.0;     // underside of main PCB (wall top); kicker hangs below it
pcb_t    = 1.6;
pcb_top  = pcb_z + pcb_t;

/* [Wheels + motors] */
wheel_r  = 12;       // 24 mm omni wheel
wheel_w  = 16.01;
wheel_gap= 0.6;      // wheel corner to inside of wall
e        = 8;        // sideways motor offset (pinwheel)
wheel_ang= [40, 160, 280];   // 120 deg apart, turned 20 deg so the ball clears the front wheels
axle_z   = wheel_r;
// outer face of each wheel: as far out as the corner allows inside the wall
wf       = sqrt((r_in - wheel_gap)^2 - (e + wheel_r)^2);
motor_d  = 6;
motor_len= 21;       // shaft bushing + gearbox + motor + terminals (Pololu 2358 approx)
m_front  = wf - wheel_w - 0.3;   // motor output face (radial)

/* [Ball + kicker] */
ball_d   = 40;       // ping-pong ball
ball_x   = 41.5;     // ball centre when held (sticks out 21.5 mm at the front: 2.5 mm more, to make room for the kicker)
pocket_r = ball_d/2 + 1.5;
pcb_notch_r = 18.6;            // main-board notch round the ball (ball is <= 17.9 mm across at board height)
sol_body = [20, 16.5, 13];   // JF-0520B 12 V frame, largest size sellers list: 20 long, 13 across the M3 face, 16 deep. Lies on its side: 16 in Y, 13 in Z
sol_plunger = 6;           // plunger diameter
sol_out  = 3.0;            // push end: 3 mm TPU kick disc with the thin M3 nut inside (replaces the o-ring and acorn nut)
sol_tail = 13.5;           // spring end after sawing the clevis off 0.5 mm behind the e-clip (as bought ~21.6: hits wheel 160)
sol_dy   = 2.8;            // shifted 2.8 mm to -Y (right): clears the front-left wheel and the top of the back wheel; the flat kick disc still kicks straight
sol_z    = pcb_z - sol_body[2]/2 - 0.2;   // hangs under the PCB, plunger just above ball centre
sol_tip_x= ball_x - ball_d/2;   // retracted plunger tip touches the ball
sol_x0   = sol_tip_x - sol_out - sol_body[0];   // frame rear end (X)
kb_rear  = [-1.0, -14.2];       // kicker bracket rear boss: M2 x 6 down from the top of the board (outside the servo)
kb_front = [10.5, -14.0];       // kicker bracket front boss: M2 x 6 down from the top of the board (outside the servo)
cradle_screws = [[-30.6, 13.0], [-16.6, -10.1]];   // battery cradle: M2 up from below into pilots in its thick corners (nothing under the cell)
antenna_hole = [-9.5, 31.5];    // 3.2 mm hole for the antenna lead, beside the P4 module's corner

/* [Gripper: one 9g servo + hoop] */
servo    = [23.0, 22.7, 12.2];  // TowerPro SG90 body 23 x 12.2 x 22.7 mm (X length, Y height along shaft, Z thickness)
pivot    = [8, pcb_top + 6.1];  // hoop pivot (X, Z); axis along Y = servo shaft
hoop_y   = 22.5;                // arm centre-lines either side of the ball
hoop_arm = [4, 2.5];            // arm section: width, thickness
grip_pt  = [ball_x + (ball_d/2 + 2.5)*cos(5), ball_d/2 - (ball_d/2 + 2.5)*sin(5)];  // front bar just below ball centre; 1 mm TPU sleeve touches the ball
// compliant drive: rigid hub on the servo horn -> 2 lugs -> 4 TPU pads -> pockets in the hoop's +Y boss
boss_d   = 11.2;            // +Y pivot boss diameter (bottom stays 0.5 mm above the board at every angle)
horn_y   = servo[1]/2 + 7.8;   // outer face of the SG90's single-arm horn: the +Y arm's horn pad sits on it
// stepped arms: level from the pivot, a right-angle step down outside the body, level again to the front bar.
// Two flat-printed arms joined by a 3 x 45 mm steel dowel pin (the front bar) with a TPU sleeve on it.
step_x   = 37;              // riser centre-line X (closed); inner face 1.1 mm clear of the body wall
bar      = grip_pt - pivot; // front bar centre relative to the pivot (closed)
rod_d    = 3;  rod_l = 45;  // DIN 6325 3 x 45 dowel pin
tip_boss = [7, 4];          // inward boss round the pin at each arm tip: diameter, length
hoop_len = norm(bar);
hoop_closed_ang = 0;        // closed: the top segment is level with the ground
hoop_open_ang   = 105;      // raised, clear of the camera

servo_x0 = pivot[0] + 5.9 - servo[0];          // body rear end (X)
ear_x    = [servo_x0 - 4.6 + 2.35, servo_x0 - 4.6 + 32.2 - 2.35];   // ear hole X positions
ear_y    = -servo[1]/2 + 15.9 + 2.5;             // back face of the ears (+Y side)

/* [Electronics placement] */
cell_d   = 16.6;                // protected 16340 Li-ion (700 mAh): 16.6 mm across
cell_l   = 36.5;                //   ... 36.5 mm long incl. protection board, with solder tabs + JST lead
cradle_t = 0.8;                 // printed cradle wall (2 perimeters; keeps the corners on the board)
cradle_gap = 0.4;               // end clearance each side: the cell's minus tab (0.3) fits with 0.1 to spare
batt_x   = -14.5 - cell_d/2 - cradle_t;   // rear, lying across the robot, just behind the servo ears
cap_pos  = [-9, -17.5, 16.5];   // kicker storage cap 330 uF 35 V, 10 x 12.5 mm, hanging under the PCB (rear right)
p4_pos   = [-8, 8];             // Waveshare ESP32-P4-Module-U, 25 x 25 mm, on the PCB underside (IPEX corner at the rear left)
flow_pos = [-17, 25];           // PAA5100JE on the PCB underside: lens ~25.6 mm above the floor (works 15-35)
mast_x   = 21;                  // back face of the mast plate (plate is 3 mm thick)
boss_ang = [90, 140, 215, 260];  // PCB screw posts (clear of wheels and pocket)
boss_r   = 36;
mast_screws = [[mast_x + 1.5, -17.5], [mast_x + 1.5, 17.5]];   // M2 x 6 up from below into the mast plate

$fn = 48;

// ---------- helpers ----------
module at_wheel(i) { rotate(wheel_ang[i]) translate([wf - wheel_w/2, e, axle_z]) rotate([0,90,0]) children(); }
module radial(i, r) { rotate(wheel_ang[i]) translate([r, e, 0]) children(); }

// ---------- bought parts (envelopes) ----------
module wheel() { color([0.95,0.55,0.15]) import("stl/wheel_assembly.stl"); }

module gearmotor() { pololu_2358(); }   // shaft along +Z from z=0, body along -Z

module solenoid(show_cut=false) {   // JF-0520B push solenoid on its side under the PCB, M3 face toward -Y, plunger forward (nut off, spring end cut)
    translate([sol_x0, -sol_body[1]/2 - sol_dy, sol_z - sol_body[2]/2]) jf0520b(sol_body, nut="disc", cut=true, show_cut=show_cut);
}
module kick_bracket() {   // printed PETG bracket: side plate on the solenoid's M3 face + 2 tabs to the board
    y0 = -sol_body[1]/2 - sol_dy;        // solenoid's M3 face
    zb = sol_z - sol_body[2]/2;          // solenoid bottom
    t  = 2.0;
    difference() {
        intersection() { union() {
            translate([sol_x0 - 0.5, y0 - t, zb + 0.5]) cube([max(sol_body[0] + 1, kb_front[0] + 3 - (sol_x0 - 0.5)), t - 0.05, pcb_z - zb - 0.5]);   // side plate, runs on under the front boss so it prints without support
            hull() {   // rear tab + boss
                translate([sol_x0 - 0.5, y0 - t, pcb_z - 4]) cube([3, t - 0.05, 4]);
                translate([kb_rear[0], kb_rear[1], pcb_z - 4]) cylinder(r=2.5, h=4, $fn=32);
            }
            hull() {   // front tab + boss
                translate([sol_x0 + sol_body[0] - 1.5, y0 - t, pcb_z - 4]) cube([2, t - 0.05, 4]);
                translate([kb_front[0], kb_front[1], pcb_z - 4]) cylinder(r=2.5, h=4, $fn=32);
            }
        }
        translate([-60, y0 - 0.05 - 60, 0]) cube([120, 60, 60]); }   // nothing past the plate's inner face, so it prints flat
        for (x=[sol_body[0]/2 - 5.5, sol_body[0]/2 + 5.5]) hull() for (dx=[-3, 3]) translate([sol_x0 + x + dx, y0 + 1, zb + sol_body[2]/2]) rotate([90,0,0]) cylinder(d=3.3, h=t + 2, $fn=24);   // M3 slots, 6 mm long: fit whatever hole spacing the solenoid has
        translate([kb_rear[0], kb_rear[1], pcb_z - 4.6]) cylinder(d=1.6, h=5, $fn=16);    // M2 pilot, screw from the top
        translate([kb_front[0], kb_front[1], pcb_z - 4.6]) cylinder(d=1.6, h=5, $fn=16);  // M2 pilot, screw from the top
    }
}

module servo9g() {   // TowerPro SG90 lying on its side, shaft along +Y at the hoop pivot
    translate([pivot[0], 0, pivot[1]]) sg90(horn=false);   // the horn is drawn with the arm it is screwed to (servo_horn)
}

module batt_cradle() {   // printed U-cradle, 2 x M2 to the PCB, cell held by a hook-and-loop strap
    difference() {
        translate([batt_x - cell_d/2 - cradle_t, -cell_l/2 - cradle_gap - cradle_t, pcb_top]) cube([cell_d + 2*cradle_t, cell_l + 2*cradle_gap + 2*cradle_t, cell_d*0.6]);
        translate([batt_x, -cell_l/2 - cradle_gap, pcb_top + cradle_t + cell_d/2]) rotate([-90,0,0]) cylinder(d=cell_d + 0.4, h=cell_l + 2*cradle_gap, $fn=64);
        translate([batt_x - cell_d/2 - 5, -4, pcb_top + cradle_t + 2]) cube([cell_d + 10, 8, 1.6]);      // strap slot
        translate([batt_x - 2, -cell_l/2 - 5, pcb_top + cradle_t + cell_d/2 - 2]) cube([4, 6, 4]);         // lead exit (4 wide: both leads pass)
        for (c=cradle_screws) translate([c[0], c[1], pcb_top - 1]) cylinder(d=1.6, h=1 + 4, $fn=16);   // M2 pilots, screws come up from under the board
        rotate(215) translate([boss_r, 0, pcb_top - 1]) cylinder(d=4.4, h=1 + 2, $fn=24);        // relief: the 215 deg board screw head can be driven with the cradle fitted
        rotate(sw_ang) translate([sw_r - 7.3 + 0.3, -10.2, pcb_top - 1]) cube([2.8, 20.4, 1 + 1.4]);   // relief for the power switch's pins and frame tabs
    }
}
module battery() {
    color([0.8,0.8,0.85]) batt_cradle();
    translate([batt_x, cell_l/2, pcb_top + cradle_t + cell_d/2]) rotate(180) cell_16340(cell_d, cell_l);   // + end and leads toward -Y: out through the lead exit to the battery plug
}
module kick_cap() { on_bottom(cap_pos[0], cap_pos[1]) stl_part("cp_elec_10x12_5.stl", [0.12,0.12,0.13]); }   // 330 uF 35 V, SMD can 10 x 12.5

module chip(pos, size, bottom=false, c=[0.15,0.15,0.15]) {   // component block on the PCB
    color(c) translate([pos[0], pos[1], bottom ? pcb_z - size[2] : pcb_top]) cube(size);
}

module on_top(x, y, r=0)    { translate([x, y, pcb_top]) rotate(r) children(); }
module on_bottom(x, y, r=0) { translate([x, y, pcb_z]) mirror([0,0,1]) rotate(r) children(); }

module stl_part(f, c=[0.62,0.62,0.66]) { color(c) import(str("models/", f)); }

module power_switch() {   // C&K L101011ML04Q right-angle slide switch (4 A), underside, actuator points out radially
    rotate(sw_ang) translate([sw_r, 0, pcb_z]) ck_l101_ra();
}
module usb_port() {       // GCT USB4105 USB-C, underside, opening at the board edge behind the wall slot
    rotate(usb_ang) translate([34.9, 0, pcb_z]) mirror([0,0,1]) rotate(90) stl_part("usb_c_usb4105.stl");
}

module pcb() {
    color([0.1,0.45,0.25]) translate([0,0,pcb_z]) linear_extrude(pcb_t) pcb2d();
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
    usb_port();
}

// --- Front sensor board (custom PCB): camera module low, VL53L7CX 8x8 ToF above it ---
// Stands just behind the mast plate and looks out through two windows. It plugs straight down into the
// main board with a 2x8 2.0 mm right-angle header -> 2x8 2.0 mm SMD socket (no cables).
fsb_x    = mast_x - 1.8;          // back face of the 1.6 mm board (0.2 mm behind the plate)
fsb_t    = 1.6;
fsb_y0   = -12.2;  fsb_w = 19.0;  // spans Y -12.2 .. 6.8 (clear of the servo-ear boss at Y 7.2); sensors on the centre line
fsb_z0   = pcb_top + 7.5;         // bottom edge (header rows at pcb_top + 9.25 and + 11.25)
cam_c    = [0, pcb_top + 15.5];      // camera lens centre (Y, Z): on the robot's centre line, 46.1 mm above the floor
tof_c    = [0, pcb_top + 25.0];      // ToF centre (Y, Z): on the centre line, 55.6 mm above the floor
hdr_zm   = pcb_top + 11.25;       // upper header row; pin tips reach pcb_top + 1.55, inside the socket
fsb_sock = [fsb_x - 2, -3.6];     // 2x8 2.0 mm SMD socket centre on the main board (pins Y -10.6 .. 3.4, clear of the servo ear)

// --- LED beacon over the centre of the robot ---
// A printed top deck sits level with the mast top (so nothing hides the dome from the front),
// held by the mast at the front and two legs behind the servo. Dome centred over the robot.
dome_d   = 30;                   // diffuser dome
mast_top = pcb_top + 30;         // top of the mast plate = underside of the deck
fsb_h    = mast_top - 0.5 - fsb_z0;
cap_t    = 2;                    // deck thickness
deck_r   = 18.5;                 // round part of the deck (hoop arms run at +-21.25 mm)
deck_legs= [[-11.8, -3], [-11.8, 13.6]]; // clear of servo body/ears, servo block and battery cradle
sw_ang   = 237;                  // power switch (C&K L101011ML04Q, 4 A, through-hole) on the underside, between the 215 and 260 deg posts
sw_r     = 34.9;                 //   ... actuator face radius: the 5.08 mm actuator ends at r 39.98, inside the 80 mm circle
usb_ang  = 300;                  // USB-C on the underside, plug goes in through a slot in the wall (above the 280 deg wheel)

module front_board() {   // camera + ToF on one board, header pins turned down into the main board
    translate([fsb_x, 0, 0]) {
        color([0.08,0.30,0.55]) difference() {             // the board
            translate([0, fsb_y0, fsb_z0]) cube([fsb_t, fsb_w, fsb_h]);
            for (y=[fsb_y0 + 2, fsb_y0 + fsb_w - 2]) translate([-1, y, fsb_z0 + fsb_h - 2]) rotate([0,90,0]) cylinder(d=2.2, h=4, $fn=16);   // M2 to the mast
        }
        // camera: SC035HGS sensor soldered on the board's front face under an 8.5 mm M7 lens holder (no flex, no FPC socket);
        // MIPI CSI runs down the board to the 2x8 header and on to the P4
        translate([fsb_t, cam_c[0], cam_c[1]]) {
            color([0.3,0.3,0.32]) translate([0, -2.6, -2.2]) cube([0.6, 5.2, 4.4]);   // sensor package (hidden by the holder)
            color([0.12,0.12,0.13]) translate([0, -4.25, -4.25]) cube([3.5, 8.5, 8.5]);
            color([0.12,0.12,0.13]) rotate([0,90,0]) cylinder(d=7.2, h=6.0, $fn=40);
            color([0.15,0.2,0.35]) translate([6.0, 0, 0]) rotate([0,90,0]) cylinder(d=4.5, h=0.1, $fn=32);
        }
        // VL53L7CX on the front, standing on end
        translate([fsb_t, tof_c[0] - 1.5, tof_c[1] - 3.2]) {
            color([0.12,0.12,0.13]) cube([1.6, 3.0, 6.4]);
            color([0.3,0.3,0.4]) translate([1.6, 0.9, 0.7]) cube([0.05, 1.2, 1.2]);
            color([0.3,0.3,0.4]) translate([1.6, 0.9, 4.0]) cube([0.05, 1.2, 1.6]);
        }
        // passives on the back (camera LDOs + crystal, ToF decoupling, pull-ups)
        color([0.55,0.45,0.30]) for (p=[[-10,52],[-8,52],[2,52],[4,52],[-10,56],[-8,56],[2,56],[4,56],[-9,48],[0,48]]) translate([-0.5, p[0], p[1] - 30.6 + pcb_top]) cube([0.5, 1.0, 0.5]);
    }
    // 2x8 2.0 mm right-angle header on the back, pins turned down into the socket
    translate([fsb_x, fsb_sock[1] + 7, hdr_zm]) mirror([1,0,0]) rotate([0,90,0]) stl_part("hdr_2x08_200_ra.stl", [0.15,0.15,0.16]);
}
module led_ring() { translate([0, 0, mast_top + cap_t]) led_ring24(); }   // 6 x WS2812B-2020 on a 24 mm board
module antenna()  { translate([13.5, 2, mast_top - 0.75]) mirror([1,0,0]) fpc_antenna(24, 8); }   // 2.4 GHz FPC antenna under the top deck; IPEX lead to the module's corner socket

module dome_solid(d) {   // true hemisphere
    intersection() { sphere(d=d, $fn=96); translate([0, 0, d]) cube(2*d, center=true); }
}
dome_wall = 1.2;
module dome() {      // printed diffuser: white/natural PETG, exactly half a sphere (rim = equator) with a 1.2 mm wall;
                     // the rim drops into a 0.6 mm groove in the deck; prints rim down (support inside the top only)
    translate([0, 0, mast_top + cap_t - 0.6]) difference() {   // rim sits in the deck's 0.6 mm groove
        dome_solid(dome_d);
        translate([0, 0, -0.01]) dome_solid(dome_d - 2*dome_wall);
    }
}

module mast() {     // printed bracket: front sensor board behind the plate, deck on top
    difference() {
        union() {
            translate([mast_x - 3.5, -20, pcb_top]) cube([6.5, 40, 2]);           // base
            translate([mast_x, -20, pcb_top]) cube([3, 40, mast_top - pcb_top]);  // upright plate
            translate([mast_x - 3.5, -19, pcb_top]) cube([3.5, 2, mast_top - pcb_top]);       // rear brace, -Y side
            translate([mast_x - 3.5, 19.7, pcb_top]) cube([3.5, 1.2, mast_top - pcb_top]);    // rear brace, +Y side (clear of the hoop arm)
            translate([servo_x0 + servo[0] + 0.3, ear_y + 0.15, pcb_top]) cube([mast_x - (servo_x0 + servo[0] + 0.3), 4, servo[2]]);  // front servo-ear boss
        }
        translate([mast_x - 1, cam_c[0] - 5.25, cam_c[1] - 5.25]) cube([5, 10.5, 10.5]); // camera window
        translate([mast_x - 1, tof_c[0] - 3.0, tof_c[1] - 4.7]) cube([5, 6.0, 9.4]);     // ToF window (74 deg keep-out cone)
        translate([mast_x - 0.1, fsb_sock[1] - 8.4, hdr_zm - 3.0]) cube([1.3, 16.8, 3.8]);  // pocket for the header's pin ends
        for (y=[fsb_y0 + 2, fsb_y0 + fsb_w - 2]) translate([mast_x - 1, y, fsb_z0 + fsb_h - 2]) rotate([0,90,0]) cylinder(d=1.6, h=1 + 2.2, $fn=16);   // blind M2 pilots for the sensor board (2.2 deep, 0.8 mm skin left on the front)
        translate([fsb_sock[0] - 3.4, fsb_sock[1] - 8.6, pcb_top - 1]) cube([mast_x + 0.2 - (fsb_sock[0] - 3.4), 17.0, 3 + 1]);   // base cut for the socket and header
        translate([mast_x - 1, -13.5, pcb_top - 1]) cube([5, 27, 34.5 - pcb_top + 1]);   // clears the held ball under the plate
        translate([ear_x[1], ear_y - 1, pivot[1]]) rotate([-90,0,0]) cylinder(d=1.6, h=6, $fn=16);   // M2 into the front ear
        translate([servo_x0 + servo[0] + 0.2, ear_y - 2.8, pcb_top - 1]) cube([mast_x + 0.8 - (servo_x0 + servo[0] + 0.2), 3.1, servo[2] + 2]);   // notch for the servo ear
        for (m=mast_screws) translate([m[0], m[1], pcb_top - 1]) cylinder(d=1.6, h=1 + 6, $fn=16);  // M2 x 6 up from under the board
        for (y=[-8, 8]) translate([mast_x + 1.5, y, mast_top - 6]) cylinder(d=1.6, h=7, $fn=16);  // deck screws (M2 pilot)
    }
}

module top_deck() {  // printed deck: centre disc + bridge to the mast + 2 legs down to the PCB
    difference() {
        union() {
            translate([0, 0, mast_top]) linear_extrude(cap_t) hull() {
                circle(r=deck_r, $fn=96);
                translate([mast_x - 3, -12]) square([6, 24]);
            }
            for (l=deck_legs) translate([l[0], l[1], pcb_top]) cylinder(d=4, h=mast_top - pcb_top + 1, $fn=32);
        }
        for (y=[-8, 8]) translate([mast_x + 1.5, y, mast_top - 1]) cylinder(d=2.3, h=cap_t + 2, $fn=16);   // M2 into mast
        for (l=deck_legs) translate([l[0], l[1], pcb_top - 1]) cylinder(d=1.6, h=6, $fn=16);              // M2 from under the PCB
        translate([0, 0, mast_top - 1]) cylinder(d=6.5, h=cap_t + 2, $fn=24);                               // LED wires: the JST-SH 3 plug passes through
        // shallow groove that locates the dome's rim (0.15 mm clearance each side); the deck prints top-face down, so no raised ring
        translate([0, 0, mast_top + cap_t - 0.6]) difference() { cylinder(d=dome_d + 0.3, h=1, $fn=96); translate([0,0,-1]) cylinder(d=dome_d - 2*dome_wall - 0.3, h=3, $fn=96); }
    }
}

module servo_block() {   // rear ear support for the SG90, 1 x M2 up through the PCB
    difference() {
        translate([servo_x0 - 4.6 + 0.2, ear_y + 0.15, pcb_top]) cube([servo_x0 - (servo_x0 - 4.6 + 0.2) - 0.2, 4, servo[2]]);
        translate([ear_x[0], ear_y - 1, pivot[1]]) rotate([-90,0,0]) cylinder(d=1.6, h=6, $fn=16);
        translate([servo_x0 - 2.3, ear_y + 2.15, pcb_top - 1]) cylinder(d=1.6, h=6, $fn=16);
    }
}

module servo_horn(ang = hoop_closed_ang) {   // SG90 single-arm horn, screwed to the +Y arm's pad, turns with the arm
    color([0.93,0.92,0.88]) translate([pivot[0], 0, pivot[1]]) rotate([0, -ang, 0]) translate([0, horn_y - 1.3, 0]) rotate([-90,0,0]) hull() {
        cylinder(d=7, h=1.3, $fn=32); translate([0, -14, 0]) cylinder(d=4, h=1.3, $fn=24);
    }
}

module hoop_bracket() {  // -Y pivot: printed post on the PCB, M2 screw as the axle (nyloc nut inside)
    y1 = -hoop_y - hoop_arm[1]/2 - 0.4;   // inner face, 0.4 mm from the arm
    yb = -29.5;                           // base runs out to here (clear of the SOIC at Y -30)
    difference() {
        hull() {
            translate([pivot[0] - 4, yb, pcb_top]) cube([8, y1 - yb, 2]);
            translate([pivot[0], y1, pivot[1]]) rotate([90,0,0]) cylinder(d=7, h=3.2, $fn=32);
        }
        translate([pivot[0], y1 + 1, pivot[1]]) rotate([90,0,0]) cylinder(d=2.2, h=10, $fn=16);
        for (dx=[-2.5, 2.5]) translate([pivot[0] + dx, -27.3, pcb_top - 1]) cylinder(d=1.6, h=1 + 5, $fn=16);   // M2 x 6 up from under the board
    }
}

module camera_mast() {
    color([0.85,0.85,0.85]) { mast(); top_deck(); servo_block(); hoop_bracket(); }
    front_board(); led_ring(); antenna(); color([1,1,1], 0.55) dome();
}

module ball() { color([1,1,0.95]) translate([ball_x, 0, ball_d/2]) sphere(d=ball_d, $fn=64); }

// ---------- printed parts ----------
module front_cut2d() {   // ball pocket only: the stepped hoop arms pass outside the body
    translate([ball_x, 0]) circle(r=pocket_r, $fn=96);
}

module pcb2d() {
    difference() {
        circle(r=r_in - 0.3, $fn=128);
        translate([ball_x, 0]) circle(r=pcb_notch_r, $fn=96);
        for (a=boss_ang) rotate(a) translate([boss_r, 0]) circle(d=2.3);
        for (h=concat(mast_screws, deck_legs, cradle_screws, [[servo_x0 - 2.3, ear_y + 2.15], [pivot[0] - 2.5, -27.3], [pivot[0] + 2.5, -27.3], kb_front, kb_rear]))
            translate(h) circle(d=2.3, $fn=16);                                        // M2 holes for the parts screwed to the board
        translate(antenna_hole) circle(d=3.2, $fn=24);                                 // antenna lead
    }
}

module wheel_window(i) { radial(i, wf - wheel_w - 1) translate([0, -wheel_r - 1, -1]) cube([wheel_w + 2, 2*wheel_r + 2, 40]); }

module cradle(i, s, top=false) {   // motor saddle at distance s behind the motor face
    len = 5;
    radial(i, m_front - s - len) difference() {
        translate([0, -6, top ? axle_z : plate_z + plate_t - 0.01]) cube([len, 12, top ? 3.6 : axle_z - plate_z - plate_t + 0.01]);
        translate([-1, 0, axle_z]) rotate([0,90,0]) cylinder(d=motor_d + 0.2, h=len + 2);
        for (y=[-4.55, 4.55]) translate([len/2, y, 0]) cylinder(d=top ? 2.3 : 1.6, h=30);
    }
}

module chassis() {
    difference() {
        union() {
            // base plate
            translate([0,0,plate_z]) cylinder(r=body_r, h=plate_t, $fn=160);
            // outer wall up to the PCB
            translate([0,0,plate_z]) difference() {
                cylinder(r=body_r, h=pcb_z - plate_z, $fn=160);
                translate([0,0,-1]) cylinder(r=r_in, h=pcb_z, $fn=160);
            }
            // PCB posts
            for (a=boss_ang) rotate(a) translate([boss_r, 0, plate_z]) cylinder(d=5, h=pcb_z - plate_z);
            // motor saddles
            for (i=[0:2]) for (s=[1.5, 9]) cradle(i, s);
        }
        for (i=[0:2]) wheel_window(i);
        // front: ball-shaped pocket (1 mm clearance) open to the front; hoop-arm gap through the wall
        hull() for (dx=[0, 30]) translate([ball_x + dx, 0, ball_d/2]) sphere(r=ball_d/2 + 1, $fn=96);
        translate([0,0,plate_z + plate_t]) linear_extrude(50) front_cut2d();
        // slot in the wall for the power switch actuator: 3 mm actuator + 3.56 mm travel (open at the top, prints without support)
        rotate(sw_ang) translate([r_in - 1, -3.9, pcb_z - 8.6]) cube([wall_t + 2, 7.8, 9]);
        // slot in the wall for the USB-C plug (overmould up to 12.4 x 6.5), open at the top
        rotate(usb_ang) translate([r_in - 1, -6.6, pcb_z - 1.6 - 3.6]) cube([wall_t + 2, 13.2, 6]);
        // floor-sensor window under the PAA5100JE (42 deg view cone)
        translate([flow_pos[0], flow_pos[1], plate_z - 1]) cylinder(d=14, h=plate_t + 2);
        // PCB post pilot holes (M2 self-tapping)
        for (a=boss_ang) rotate(a) translate([boss_r, 0, pcb_z - 6]) cylinder(d=1.6, h=7);
    }
}

module motor_caps() { for (i=[0:2]) for (s=[1.5, 9]) cradle(i, s, top=true); }

// arm profile in the hoop's own X-Z plane (pivot at the origin, closed position)
module arm2d(drive) {
    sx = step_x - pivot[0];  w = hoop_arm[0];
    offset(r=1) offset(delta=-1) offset(r=-2) offset(delta=2) union() {   // fillet the inside corners r 2, round the outside r 1
        translate([0, -w/2]) square([sx + w/2, w]);                    // 1: level with the ground
        translate([sx - w/2, bar[1] - w/2]) square([w, -bar[1] + w]);   // 2: right-angle step down
        translate([sx - w/2, bar[1] - w/2]) square([bar[0] - sx + w/2, w]);   // 3: level again to the front bar
        translate(bar) circle(d=tip_boss[0], $fn=40);
        circle(d=drive ? boss_d : 6, $fn=64);
        if (drive) hull() { circle(d=10, $fn=48); translate([0, 9]) circle(d=5, $fn=32); }   // under the horn pad, so it prints on solid arm
    }
}
module hoop_arm(side, ang = hoop_closed_ang) {   // side +1: +Y arm (screwed straight to the servo horn), -1: -Y arm (runs on the bracket's M2 axle)
    t = hoop_arm[1];
    yi = side*(hoop_y - t/2);   // inner face
    translate([pivot[0], 0, pivot[1]]) rotate([0, -ang, 0]) difference() {
        union() {
            translate([0, side > 0 ? hoop_y + t/2 : -hoop_y + t/2, 0]) rotate([90, 0, 0]) linear_extrude(t) arm2d(side > 0);
            translate([bar[0], yi + 0.01*side, bar[1]]) rotate([side*90, 0, 0]) cylinder(d=tip_boss[0], h=tip_boss[1], $fn=40);   // inward pin boss
            if (side > 0) hull() {   // horn pad on the inner face: the horn's shape (it points up when the gripper is closed)
                translate([0, horn_y, 0]) rotate([-90,0,0]) cylinder(d=10, h=yi - horn_y + 0.01, $fn=48);
                translate([0, horn_y, 9]) rotate([-90,0,0]) cylinder(d=5, h=yi - horn_y + 0.01, $fn=32);
            }
        }
        rotate([90,0,0]) cylinder(d=side > 0 ? 4.5 : 2.2, h=60, center=true, $fn=24);    // +Y: access hole for the horn's centre screw; -Y: M2 axle
        if (side > 0) for (z=[4.5, 8.5]) translate([0, horn_y - 0.01, z]) rotate([-90,0,0]) cylinder(d=1.0, h=4, $fn=12);   // pilots for the horn's 2 small screws
        translate([bar[0], 0, bar[1]]) rotate([90,0,0]) translate([0, 0, side > 0 ? -rod_l/2 : 0]) cylinder(d=rod_d - 0.05, h=30, $fn=24);   // pin hole: blind in the +Y arm, right through the -Y arm (pin goes in last, from outside)
    }
}
module hoop(ang = hoop_closed_ang) {   // both arms + the steel front bar
    hoop_arm(1, ang); hoop_arm(-1, ang);
    color([0.72,0.72,0.75]) translate([pivot[0], 0, pivot[1]]) rotate([0, -ang, 0]) translate([bar[0], 0, bar[1]]) rotate([90,0,0]) cylinder(d=rod_d, h=rod_l, center=true, $fn=24);
}

module hoop_sleeve(ang = hoop_closed_ang) {   // TPU tube on the steel bar, between the arm-tip bosses; slid on before the second arm is pressed on
    translate([pivot[0], 0, pivot[1]]) rotate([0, -ang, 0]) translate([bar[0], 0, bar[1]]) rotate([90,0,0]) difference() {
        cylinder(d=5, h=30, center=true, $fn=40);
        cylinder(d=rod_d - 0.2, h=32, center=true, $fn=24);   // 0.2 mm stretch fit
    }
}

module assembly() {
    if (ghost) %chassis(); else color([0.9,0.9,0.92]) chassis();
    color([0.8,0.8,0.82]) motor_caps();
    for (i=[0:2]) at_wheel(i) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); }
    solenoid(); color([0.95,0.55,0.2]) kick_bracket(); kick_cap(); pcb(); battery(); servo9g(); camera_mast();
    color([0.95,0.3,0.25]) hoop(hoop_open ? hoop_open_ang : hoop_closed_ang);
    servo_horn(hoop_open ? hoop_open_ang : hoop_closed_ang);
    color([0.15,0.15,0.17]) hoop_sleeve(hoop_open ? hoop_open_ang : hoop_closed_ang);
    ball();
}

// exploded view: each layer lifted, wheels slid outward, ball pulled forward
module exploded(gap=26) {
    color([0.9,0.9,0.92]) chassis();
    translate([0,0,gap*0.45]) color([0.8,0.8,0.82]) motor_caps();
    for (i=[0:2]) at_wheel(i) translate([0,0,22]) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); }
    translate([0,0,gap]) { solenoid(); color([0.95,0.55,0.2]) kick_bracket(); kick_cap(); }
    translate([0,0,gap*2]) pcb();
    translate([0,0,gap*3]) { battery(); servo9g(); camera_mast(); }
    translate([0,0,gap*3.6]) color([0.95,0.3,0.25]) hoop(hoop_closed_ang);
    translate([45,0,0]) ball();
}

if (part == "assembly") assembly();
else if (part == "exploded") exploded();
else if (part == "wheel") wheel();
else if (part == "motor") gearmotor();
else if (part == "solenoid") solenoid();
else if (part == "kick_disc") translate([0, 0, 3]) rotate([180,0,0]) kick_disc_shape(with_nut=false);   // TPU 95A, kick face down, nut pocket up; press the thin M3 nut in
else if (part == "kick_bracket") translate([0, 0, -sol_body[1]/2 - sol_dy - 0.05]) rotate([-90,0,0]) kick_bracket();   // prints with the solenoid side down, tabs standing up
else if (part == "servo") servo9g();
else if (part == "battery") battery();
else if (part == "pcb") pcb();
else if (part == "camera") camera_mast();
else if (part == "front_board") front_board();
else if (part == "mast") translate([0,0,-pcb_top]) mast();
else if (part == "dome") translate([0, 0, -(mast_top + cap_t - 0.6)]) dome();
else if (part == "servo_block") translate([0,0,-pcb_top]) servo_block();
else if (part == "hoop_sleeve") difference() { cylinder(d=5, h=30, $fn=40); translate([0,0,-1]) cylinder(d=rod_d - 0.2, h=32, $fn=24); }   // TPU, stands on its end
else if (part == "hoop_bracket") translate([0,0,-pcb_top]) hoop_bracket();
else if (part == "top_deck") translate([0, 0, mast_top + cap_t]) rotate([180,0,0]) top_deck();   // prints upside down: deck on the bed, legs up
else if (part == "batt_cradle") translate([0,0,-pcb_top]) batt_cradle();
else if (part == "cap") kick_cap();
else if (part == "ball") ball();
else if (part == "chassis") chassis();
else if (part == "motor_caps") translate([0, 0, axle_z + 3.6]) rotate([180,0,0]) motor_caps();   // flat top on the bed, motor groove facing up
else if (part == "hoop") {   // the two arms, printed flat with the inner face (pockets, pin bosses) up
    rotate([-90,0,0]) translate([-pivot[0], -(hoop_y + hoop_arm[1]/2), -pivot[1]]) hoop_arm(1, 0);
    translate([0, -45, 0]) rotate([90,0,0]) translate([-pivot[0], hoop_y + hoop_arm[1]/2, -pivot[1]]) hoop_arm(-1, 0);
}
else if (part == "pcb_outline") pcb2d();
