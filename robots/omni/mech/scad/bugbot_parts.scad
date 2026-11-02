// BugBot detailed bought-part models (visual detail for renders and fit checks).
// Each module is drawn in the part's own frame, as noted. Sizes from datasheets / drawings listed in PARTS.md.

$fn = 32;
C_BLK  = [0.12,0.12,0.13];
C_GRY  = [0.45,0.45,0.48];
C_STEEL= [0.72,0.72,0.75];
C_GOLD = [0.85,0.68,0.25];
C_WHT  = [0.93,0.92,0.88];
C_NYL  = [0.95,0.93,0.82];   // JST nylon housings
C_PCB  = [0.08,0.42,0.22];
C_PCBB = [0.06,0.22,0.55];   // Waveshare blue
C_COPPER=[0.80,0.45,0.20];

module rbox(size, r=0.5) {   // rounded-corner box (rounded in X/Y)
    hull() for (x=[r, size[0]-r], y=[r, size[1]-r]) translate([x, y, 0]) cylinder(r=r, h=size[2], $fn=16);
}

// ---------------- Waveshare ESP32-P4-Module-U (25 x 25 mm, 88 castellated pads at 1 mm, IPEX corner) --------
// Frame: module PCB from z=0 (pad side, faces the main board) to z=0.8; parts on top up to z=3.1.
// x,y from 0..25; the IPEX (U.FL) socket J5 is at the (0, 25) corner.
module p4_module() {
    color(C_PCBB) difference() {
        cube([25, 25, 0.8]);
        // castellated half-holes, 22 per side at 1.0 mm pitch
        for (i=[0:21]) {
            p = 2 + i;
            for (q=[[p, 0], [p, 25], [0, p], [25, p]]) translate([q[0], q[1], -1]) cylinder(d=0.6, h=3, $fn=12);
        }
    }
    color(C_GOLD) for (i=[0:21]) { p = 2 + i;
        for (q=[[p, 0], [p, 25], [0, p], [25, p]]) translate([q[0], q[1], -0.01]) cylinder(d=0.9, h=0.82, $fn=12); }
    // shield cans: ESP32-P4 (big) and ESP32-C6 (small)
    color(C_STEEL) translate([8.5, 1.5, 0.8]) rbox([15, 17.5, 2.2], 0.6);
    color(C_STEEL) translate([1.8, 9.5, 0.8]) rbox([6.2, 6.5, 2.0], 0.5);
    // flash (WSON-8) and crystals near the bottom-left, like the board drawing
    color(C_BLK) translate([3.2, 2.5, 0.8]) cube([5, 6, 0.8]);
    color(C_STEEL) translate([9.0, 20.2, 0.8]) cube([3.2, 2.5, 0.8]);
    // IPEX / U.FL socket (J5) in the top-left corner
    translate([3.8, 21.4, 0.8]) {
        color(C_GOLD) translate([-1.3, -1.3, 0]) cube([2.6, 2.6, 0.3]);
        color(C_STEEL) difference() { cylinder(d=2.0, h=1.25, $fn=24); translate([0, 0, 0.3]) cylinder(d=1.4, h=2, $fn=24); }
        color(C_GOLD) cylinder(d=0.5, h=1.0, $fn=12);
    }
    // a scatter of passives
    color([0.55,0.45,0.30]) for (p=[[3,18],[5,18],[3,16],[5,16],[1.6,7],[3,7],[20,20.5],[22,20.5],[18,20.5],[14.5,20.5],[14.5,22.5],[20,22.5]]) translate([p[0], p[1], 0.8]) cube([1.0, 0.5, 0.5]);
}

// ---------------- TowerPro SG90 servo, lying on its side ------------------------------------------------
// Frame: output shaft axis along +Y through the origin; body length along -X from x = +5.9.
module sg90(horn=true) {
    L = 23.0; H = 22.7; T = 12.2;   // length, height (shaft axis), thickness
    x0 = 5.9 - L;
    color([0.15,0.25,0.65]) {
        translate([x0, -H/2, -T/2]) rbox([L, H - 3.2, T], 0.4);                 // main case
        translate([x0, H/2 - 3.2, -T/2]) rbox([L, 3.2, T], 0.4);                 // top cap
        difference() {                                                           // mounting ears with holes + slots
            translate([x0 - 4.6, -H/2 + 15.9, -T/2]) cube([32.2, 2.5, T]);
            for (x=[x0 - 4.6 + 2.35, x0 - 4.6 + 32.2 - 2.35]) {
                translate([x, -H/2 + 15, 0]) rotate([-90,0,0]) cylinder(d=2.0, h=5, $fn=16);
                translate([(x < 0 ? x - 3 : x), -H/2 + 15, -0.5]) cube([3, 5, 1]);
            }
        }
        translate([0, H/2, 0]) rotate([-90,0,0]) cylinder(d=11.8, h=4, $fn=48);           // gear housing
        translate([-5.5, H/2, 0]) rotate([-90,0,0]) cylinder(d=5.5, h=4, $fn=32);         // second gear boss
    }
    color(C_WHT) translate([0, H/2 + 4, 0]) rotate([-90,0,0]) cylinder(d=4.8, h=2.5, $fn=24);  // output spline
    if (horn) color(C_WHT) translate([0, H/2 + 6.5, 0]) rotate([-90,0,0]) hull() {             // single-arm horn
        cylinder(d=7, h=1.3, $fn=32); translate([0, -14, 0]) cylinder(d=4, h=1.3, $fn=24);
    }
    // cable: brown / red / orange leaving the rear end
    for (i=[0:2]) color([[0.35,0.2,0.1],[0.8,0.1,0.1],[0.95,0.55,0.1]][i])
        translate([x0, -H/2 + 3 + i*1.1, -T/2 + 2]) rotate([0,-90,0]) cylinder(d=1.0, h=0.5, $fn=12);   // cable stub (routed down to the header)
}

// ---------------- JF-0530B push-pull solenoid (CMU / JF-0530B datasheet drawing) ---------------------
// Frame: 30 long (X), 15 deep (Y), 13 across the mounting face (Z). The mounting face (base of the steel U, 2 x M3 at
// 7 and 22 mm from the back) is the y = 0 face. Plunger exits at x = 30 on the axis (y 7.5, z 6.5): 6 mm, 7 mm out + clevis.
module jf0530b(stroke_out=0) {
    color(C_STEEL) difference() {
        union() {
            cube([30, 1.0, 13]);                                                  // base plate = mounting face
            for (x=[0, 29]) translate([x, 0, 0]) cube([1.0, 15, 13]);            // end plates
        }
        for (x=[7, 22]) translate([x, -1, 6.5]) rotate([-90,0,0]) cylinder(d=2.5, h=3, $fn=16);   // M3 threads
        translate([28, 7.5, 6.5]) rotate([0,90,0]) cylinder(d=6.4, h=4, $fn=24);
    }
    color([0.80,0.45,0.15]) translate([1, 7.5, 6.5]) rotate([0,90,0]) cylinder(d=11.5, h=28, $fn=48);   // coil
    color(C_BLK) for (x=[1, 28]) translate([x, 7.5, 6.5]) rotate([0,90,0]) cylinder(d=12.4, h=1, $fn=48);
    translate([30 + stroke_out, 7.5, 6.5]) {                                      // plunger with clevis slot + 2 mm pin hole
        color(C_STEEL) difference() {
            translate([-12, 0, 0]) rotate([0,90,0]) cylinder(d=6, h=12 + 7 + 2.5, $fn=24);
            translate([7 - 0.1, -0.8, -4]) cube([3, 1.6, 8]);
            translate([7 + 1.2, 0, -4]) cylinder(d=2, h=8, $fn=12);
        }
        color([0.6,0.6,0.62]) translate([0.2, 0, 0]) rotate([0,90,0]) cylinder(d=7, h=0.6, $fn=24);
    }
    for (i=[0:1]) color([[0.8,0.1,0.1],[0.1,0.1,0.1]][i]) translate([0, 10 + i*1.6, 9]) rotate([0,-90,0]) cylinder(d=1.0, h=5, $fn=12);   // leads at the back
}
// ---------------- JF-0520B push-pull solenoid (12 V, 4 N, 10 mm stroke) ----------------------------------
// Body 20 x 13 x 16.5 (100Y datasheet: 13*16.5*20). Plunger hardware at the LARGER of the two sources found (3D ContentCentral
// JF-0520B model, measured from its true-scale views; uxcell's photos give 2-3 mm less): push end o-ring 2 + acorn nut 6.5,
// spring end: return spring to the washer + e-clip at 12-13 mm, slotted clevis (7.5 long, 1.5 slot) to 21.6 mm.
// The acorn nut is the return stop (the spring pulls the plunger back until nut + o-ring hit the frame).
// BugBot version (nut="thin", cut=true): acorn nut swapped for a thin M3 nut (DIN 439, 1.8 mm) with the stud trimmed flush,
// clevis sawn off 0.5 mm behind the e-clip (spring end 13.5 mm).
// Frame: x 0..L (push end at x = L), depth D in Y, width H (the M3 face, y = 0) in Z; plunger axis at (y D/2, z H/2).
// nut = "acorn" (as bought), "thin" (thin M3 nut + o-ring) or "disc" (BugBot: 3 mm TPU kick disc with the thin nut inside,
// replacing the o-ring and nut: it is the return stop and a flat kick face, so the kick is straight even off-centre).
module kick_disc_shape(with_nut=true) {   // d12 x 3, hex pocket for a DIN 439 M3 thin nut (5.5 AF, 1.8) open toward the frame; z = 0 on the frame face
    color([0.2,0.2,0.22]) difference() {
        cylinder(d=12, h=3, $fn=48);
        translate([0, 0, -0.01]) cylinder(d=5.65/cos(30), h=1.9, $fn=6);
        translate([0, 0, -1]) cylinder(d=2.0, h=5, $fn=16);
    }
    if (with_nut) color(C_STEEL) translate([0, 0, 0.05]) difference() { cylinder(d=5.5/cos(30), h=1.8, $fn=6); translate([0,0,-1]) cylinder(d=2.4, h=4, $fn=12); }
}
module jf0520b(size=[20, 16.5, 13], nut="acorn", cut=false, show_cut=false) {
    L = size[0]; D = size[1]; H = size[2];
    tail = cut ? 13.5 : 21.6;
    color(C_STEEL) difference() {
        union() { cube([L, 1.0, H]); for (x=[0, L - 1]) translate([x, 0, 0]) cube([1.0, D, H]); }
        for (x=[L/2 - 5.5, L/2 + 5.5]) translate([x, -1, H/2]) rotate([-90,0,0]) cylinder(d=2.5, h=3, $fn=16);   // 2 x M3 (spacing ~11, check)
        for (x=[-1, L - 2]) translate([x, D/2, H/2]) rotate([0,90,0]) cylinder(d=6.4, h=4, $fn=24);
    }
    color([0.15,0.3,0.75]) translate([1.5, D/2, H/2]) rotate([0,90,0]) cylinder(d=11.5, h=L - 3, $fn=48);   // blue taped coil
    translate([0, D/2, H/2]) {
        color(C_STEEL) rotate([0,90,0]) cylinder(d=6, h=L, $fn=24);                                   // plunger inside the coil
        // push end (+X): o-ring bumper, then the nut that stops the return stroke (BugBot: a TPU kick disc does both)
        if (nut != "disc") color(C_BLK) translate([L, 0, 0]) rotate([0,90,0]) cylinder(d=6.5, h=2.0, $fn=24);
        if (nut == "disc") translate([L, 0, 0]) rotate([0,90,0]) kick_disc_shape();
        if (nut == "acorn") color(C_STEEL) translate([L + 2, 0, 0]) rotate([0,90,0]) { cylinder(d=5.5/cos(30), h=3.8, $fn=6); translate([0,0,3.8]) sphere(d=5.2, $fn=20); }
        if (nut == "thin") color(C_STEEL) translate([L + 2, 0, 0]) rotate([0,90,0]) difference() { cylinder(d=5.5/cos(30), h=1.8, $fn=6); translate([0,0,-1]) cylinder(d=2.4, h=4, $fn=12); }
        color(C_STEEL) translate([L, 0, 0]) rotate([0,90,0]) cylinder(d=3, h=nut == "acorn" ? 6 : nut == "disc" ? 1.8 : 3.8, $fn=16);   // M3 stud (trimmed to the nut)
        // spring end (-X)
        color(C_STEEL) translate([-tail, 0, 0]) rotate([0,90,0]) cylinder(d=6, h=tail, $fn=24);
        color([0.8,0.8,0.82]) for (i=[0:9]) translate([-1.15*i - 0.7, 0, 0]) rotate([0,90,0]) difference() { cylinder(d=8, h=0.6, $fn=24); translate([0,0,-1]) cylinder(d=6.8, h=3, $fn=24); }   // return spring
        color(C_STEEL) translate([-12.4, 0, 0]) rotate([0,90,0]) cylinder(d=9, h=0.5, $fn=24);          // washer
        color(C_BLK) translate([-13.0, 0, 0]) rotate([0,90,0]) cylinder(d=8, h=0.6, $fn=24);           // e-clip
        if (!cut) color(C_STEEL) translate([-21.6, 0, 0]) rotate([0,90,0]) difference() { cylinder(d=6, h=8.1, $fn=24); translate([-0.75, -4, -1]) cube([1.5, 8, 8.5]); }
        if (show_cut) color([0.9,0.15,0.1], 0.45) translate([-21.6, 0, 0]) rotate([0,90,0]) difference() {   // the clevis you saw off
            cylinder(d=6, h=8.1, $fn=24); translate([-0.75, -4, -1]) cube([1.5, 8, 8.5]);
        }
    }
    for (i=[0:1]) color(C_BLK) translate([L/2 - 2 + i*2, D, 1.5]) rotate([-90,0,0]) cylinder(d=1.2, h=4, $fn=12);   // leads out of the open side
}

// ---------------- Pololu 2358 136:1 sub-micro planetary gearmotor ----------------------------------------
// Frame: 2 mm D-shaft along +Z from z=0, body along -Z (total 21 incl. terminals).
module pololu_2358() {
    color(C_STEEL) difference() { cylinder(d=2, h=2.5, $fn=24); translate([0.5, -1, -0.1]) cube([2, 2, 3]); }   // D-shaft
    color(C_GRY) translate([0, 0, -0.6]) cylinder(d=3, h=0.6, $fn=24);              // bushing
    color(C_BLK) translate([0, 0, -11]) cylinder(d=6, h=10.4, $fn=40);             // plastic gearbox
    color([0.2,0.2,0.21]) for (z=[-3.5, -7.2]) translate([0, 0, z]) cylinder(d=6.15, h=0.5, $fn=40);   // stage seams
    color(C_STEEL) translate([0, 0, -19.4]) cylinder(d=6, h=8.4, $fn=40);          // motor can
    color(C_WHT) translate([0, 0, -19.9]) cylinder(d=5.6, h=0.5, $fn=40);          // end cap
    color(C_GOLD) for (x=[-1.6, 1.0]) translate([x, -0.25, -21]) cube([0.6, 0.5, 1.2]);   // terminals
}

// ---------------- Raspberry Pi size MIPI camera board (official RPi drawing) -----------------------------
// Frame: board back face at x = 0, front (lens side) toward +X. Board spans y 0..25, z 0..23.862,
// FPC socket edge at z = 0. Lens centre at (y 13.8, z 23.862 - 9.462).
module rpi_camera() {
    W = 23.862; Hh = 25;
    lens = [13.8, W - 9.462];
    color(C_PCB) difference() {
        translate([0, 0, 0]) rotate([90,0,90]) rbox([Hh, W, 1.0], 2.0);
        for (a=[2, 14.5], b=[2, 23]) translate([-1, b, W - a]) rotate([0,90,0]) cylinder(d=2.2, h=3, $fn=16);
    }
    translate([1, lens[0], lens[1]]) {
        color(C_BLK) translate([0, -4.25, -4.25]) cube([3.0, 8.5, 8.5]);                // sensor holder
        color(C_BLK) rotate([0,90,0]) cylinder(d=7.2, h=4.6, $fn=40);                   // lens barrel
        color([0.15,0.2,0.35]) translate([4.6, 0, 0]) rotate([0,90,0]) cylinder(d=4.5, h=0.2, $fn=32);   // glass
    }
    color([0.80,0.45,0.15]) translate([1, lens[0] - 2.5, 3]) cube([0.4, 5, 3]);         // flex from sensor
    // 15-pin FPC socket on the back, along the bottom edge
    translate([-1.2, (Hh - 20.8)/2, 0]) { color(C_WHT) cube([1.2, 20.8, 5.5]); color([0.35,0.2,0.1]) translate([-0.3, 0.4, 3.5]) cube([0.3, 20, 2]); }
    color([0.55,0.45,0.30]) for (p=[[4,4],[6,4],[19,5],[21,5],[4,18],[21,18]]) translate([1, p[0], p[1]]) cube([0.5, 1.0, 0.5]);
}

// ---------------- VL53L7CX on its 10 x 12 mm carrier ---------------------------------------------------
// Frame: carrier back face at x = 0, sensor facing +X; carrier spans y 0..10, z 0..12.
module vl53l7cx_carrier() {
    color([0.35,0.08,0.40]) difference() {
        cube([1.0, 10, 12]);
        for (z=[2, 10]) translate([-1, 8.5, z]) rotate([0,90,0]) cylinder(d=2.2, h=3, $fn=16);
    }
    translate([1, 5 - 1.5, 6 - 3.2]) {                        // LGA-16 module standing on end: 3.0 wide, 6.4 tall
        color(C_BLK) cube([1.6, 3.0, 6.4]);
        color([0.25,0.25,0.35]) translate([1.6, 0.9, 0.7]) cube([0.05, 1.2, 1.2]);   // Tx aperture
        color([0.25,0.25,0.35]) translate([1.6, 0.9, 4.0]) cube([0.05, 1.2, 1.6]);   // Rx aperture
    }
    color([0.55,0.45,0.30]) for (p=[[1.2,1.2],[1.2,9.6],[7,1.2],[7,9.6]]) translate([1, p[0], p[1]]) cube([0.5, 1.0, 0.5]);
}

// ---------------- connectors, switch, buttons --------------------------------------------------------
// Each sits on the board surface at z = 0 and grows +Z (callers flip it for the underside).
module jst_sh_body(n, vertical=false) {   // JST-SH 1.0 mm, side entry: width 2 + n, depth 4.25, height 2.95
    w = n + 2;
    color(C_NYL) difference() {
        cube([w, 4.25, 2.95]);
        translate([1, -0.1, 0.6]) cube([w - 2, 3.2, 1.8]);
    }
    color(C_GOLD) for (i=[0:n-1]) translate([1.5 + i, 3.6, -0.05]) cube([0.3, 1.2, 0.2]);
    color(C_GOLD) for (x=[-0.6, w]) translate([x, 1, 0]) cube([0.6, 2.2, 0.2]);   // mounting tabs
}
module jst_ph_side(n) {                  // JST-PH 2.0 mm SMD side entry (S..B-PH-SM4-TB): 8.0 x 7.9 x 4.8 for 2-pin
    w = 2*n + 4;
    color(C_NYL) difference() { cube([w, 7.9, 4.8]); translate([1.2, -0.1, 0.8]) cube([w - 2.4, 5.5, 3.4]); }
    color(C_GOLD) for (i=[0:n-1]) translate([2.6 + i*2, 6.8, 0]) cube([0.6, 2, 0.2]);
}
module jst_ph_top(n) {                   // JST-PH 2.0 mm through-hole top entry (B2B-PH-K-S): 6.0 x 4.5 x 6.0
    w = 2*n + 2;
    color(C_NYL) difference() { cube([w, 4.5, 6.0]); translate([0.8, 0.8, 1.2]) cube([w - 1.6, 2.9, 6]); }
    color(C_GOLD) for (i=[0:n-1]) translate([2 + i*2 - 0.25, 2.0, 1.2]) cube([0.5, 0.5, 4]);
}
module jst_ph_top_smd(n) {               // JST-PH 2.0 mm SMD top entry (B2B-PH-SM4-TB): 6.0 x 4.5 x 6.0 for 2-pin, 2 solder tabs
    w = 2*n + 2;
    color(C_NYL) difference() { cube([w, 4.5, 6.0]); translate([0.8, 0.8, 1.2]) cube([w - 1.6, 2.9, 6]); }
    color(C_GOLD) for (i=[0:n-1]) translate([2 + i*2 - 0.25, 2.0, 1.2]) cube([0.5, 0.5, 4]);
    color(C_GOLD) for (i=[0:n-1]) translate([2 + i*2 - 0.4, -1.2, 0]) cube([0.8, 1.3, 0.2]);      // SMD leads
    color(C_STEEL) for (x=[-1.2, w]) translate([x, 1.2, 0]) cube([1.2, 2.2, 0.2]);                // solder tabs
}
module fpc15_conn() {                    // 15-pin 1.0 mm FPC connector, 20.6 x 5.3 x 2.3, latch on the back
    color(C_WHT) cube([20.6, 3.8, 2.3]);
    color(C_BLK) translate([0.6, 3.8, 0.4]) cube([19.4, 1.5, 1.9]);
    color(C_GOLD) for (i=[0:14]) translate([3.3 + i, -0.6, 0]) cube([0.4, 0.8, 0.15]);
}
module usb_c() {                         // USB-C 16-pin mid-mount receptacle, 8.94 x 7.35 x 3.2
    color(C_STEEL) difference() {
        translate([0, 0, 0]) hull() for (y=[1.6, 8.94 - 1.6]) translate([0, y, 1.6]) rotate([0,90,0]) cylinder(d=3.2, h=7.35, $fn=24);
        hull() for (y=[2.0, 8.94 - 2.0]) translate([-0.1, y, 1.6]) rotate([0,90,0]) cylinder(d=2.5, h=7, $fn=24);
    }
    color(C_BLK) translate([0.5, 2.3, 1.25]) cube([5, 4.34, 0.7]);
}
module header3() {                       // 3-pin 2.54 mm male header
    color(C_BLK) cube([7.6, 2.5, 2.5]);
    color(C_GOLD) for (i=[0:2]) translate([1.27 + i*2.54 - 0.32, 0.93, 0]) cube([0.64, 0.64, 8.5]);
}
module slide_switch() {                  // MSK-12C02, 7 x 3 x 1.5 body, lever 1.5 mm
    color(C_STEEL) cube([7, 3, 1.5]);
    color(C_BLK) translate([2.75, -1.5, 0.3]) cube([1.5, 1.5, 0.9]);
}
module tact_side() {                     // 3 x 4 mm side-push tactile switch
    color(C_STEEL) cube([3, 4, 2]);
    color(C_BLK) translate([-0.6, 1.3, 0.5]) cube([0.6, 1.4, 1.0]);
}
module ic_pkg(size, pins=0, pitch=0.65) {   // generic IC with gull-wing leads on two long sides
    color(C_BLK) translate([0.4, 0, 0]) cube([size[0] - 0.8, size[1], size[2]]);
    if (pins > 0) color(C_STEEL) for (i=[0:pins/2 - 1]) for (x=[0, size[0] - 0.4])
        translate([x, size[1]/2 - (pins/2 - 1)*pitch/2 + i*pitch - 0.12, 0]) cube([0.4, 0.24, 0.2]);
}
module lga(size) { color(C_BLK) cube(size); color(C_GOLD) translate([0.3, 0.3, -0.01]) cube([size[0] - 0.6, size[1] - 0.6, 0.02]); }
module inductor(s=2.5) { color([0.25,0.25,0.26]) cube([s, s, 1.2]); }

// ---------------- PAA5100JE-Q with lens and two LEDs (looking down) -------------------------------------
module paa5100() {
    color(C_BLK) cube([6, 6, 2.0]);
    color(C_BLK) translate([3, 3, 2.0]) cylinder(d=4.2, h=1.08, $fn=32);
    color([0.4,0.45,0.6]) translate([3, 3, 3.08]) cylinder(d=2.2, h=0.01, $fn=24);
}
module led_1206() { color(C_WHT) cube([1.6, 1.6, 0.6]); color([1,1,0.6]) translate([0.3, 0.3, 0.6]) cube([1.0, 1.0, 0.2]); }

// ---------------- Li-ion 16340 protected cell with tabs and lead -----------------------------------------
// Frame: cell axis along +Y from the origin.
module cell_16340(d=16.6, l=36.5) {
    color([0.15,0.45,0.85]) rotate([-90,0,0]) cylinder(d=d, h=l - 2, $fn=64);                // wrap
    color(C_WHT) translate([0, l - 2, 0]) rotate([-90,0,0]) cylinder(d=d - 1, h=0.4, $fn=64);  // insulating ring
    color([0.1,0.35,0.15]) translate([0, l - 1.6, 0]) rotate([-90,0,0]) cylinder(d=d - 2, h=1.0, $fn=48);   // protection board
    color(C_STEEL) translate([0, l - 0.6, 0]) rotate([-90,0,0]) cylinder(d=6, h=0.6, $fn=24);  // + cap
    color(C_STEEL) translate([-3, -0.3, -d/2 + 1]) cube([6, 0.3, d - 4]);                        // - tab
    for (i=[0:1]) color([[0.8,0.1,0.1],[0.1,0.1,0.1]][i]) translate([-1 + i*2, l, 0]) rotate([-90,0,0]) cylinder(d=1.1, h=4, $fn=12);
}

// ---------------- 330 uF 35 V electrolytic, 10 x 12.5 ----------------------------------------------------
module ecap(d=10, h=12.5) {   // h = overall height incl. the top rim
    h = h - 0.35;
    color([0.1,0.1,0.12]) cylinder(d=d, h=h, $fn=48);
    color([0.7,0.7,0.75]) translate([0, 0, h]) cylinder(d=d - 0.8, h=0.2, $fn=48);
    color([0.85,0.85,0.88]) rotate(30) translate([d/2 - 1.6, -1.2, 0.01]) cube([1.6, 2.4, h]);   // polarity stripe
    color([0.4,0.4,0.42]) for (a=[0, 90]) rotate(a) translate([-d/2 + 1.5, -0.15, h + 0.1]) cube([d - 3, 0.3, 0.15]);  // vent cross
}

// ---------------- WS2812B-2020 LED ring (24 mm) ------------------------------------------------------
module led_ring24() {
    color(C_PCB) cylinder(d=24, h=1, $fn=48);
    for (a=[0:60:300]) rotate(a) translate([7, -1, 1]) { color(C_WHT) cube([2, 2, 0.9]); color([1,1,0.85]) translate([0.4, 0.4, 0.9]) cube([1.2, 1.2, 0.05]); }
    color([0.55,0.45,0.30]) for (a=[30:60:330]) rotate(a) translate([7, -0.25, 1]) cube([1.0, 0.5, 0.5]);
}

// ---------------- 2.4 GHz FPC antenna with U.FL lead -------------------------------------------------
module fpc_antenna(l=30, w=8) {
    color([0.85,0.6,0.15]) cube([l, w, 0.15]);
    color(C_COPPER) for (i=[0:5]) translate([3 + i*4, 1, 0.15]) cube([1, w - 2, 0.02]);
    color(C_BLK) translate([l - 1, w/2, 0.1]) rotate([0,90,0]) cylinder(d=1.13, h=10, $fn=12);
}

// ---------------- ZX-QC4545-4.3TP tactile switch (as on the earlier BugBot boards) -----------------------
// 4.5 x 4.5 mm SMD top-push, 4.3 mm tall, 4 gull-wing legs at 3.0 mm pitch, 6.9 mm lead span. Centred, z = 0 on the board.
module tact_4545() {
    color(C_BLK) translate([-2.25, -2.25, 0]) cube([4.5, 4.5, 2.6]);
    color(C_STEEL) translate([-2.25, -2.25, 2.6]) cube([4.5, 4.5, 0.3]);
    color([0.35,0.25,0.2]) translate([0, 0, 2.9]) cylinder(d=2.6, h=1.4, $fn=24);
    color(C_STEEL) for (sx=[-1, 1], sy=[-1, 1]) translate([sx > 0 ? 2.25 : -3.45, sy*1.5 - 0.35, 0]) cube([1.2, 0.7, 0.2]);
}

// ---------------- C&K L101011ML04Q slide switch, right angle, through-hole, 4 A @ 28 V DC --------------------
// Envelope from the distributor listings (19.3 x 10.5 x 7.3 mm, 5.08 mm actuator, 3.56 mm travel): check against the C&K drawing.
// Frame: board underside at z = 0, body hangs to -Z; actuator face at x = 0, actuator points +X; slide along Y.
module ck_l101_ra(on=true) {
    color(C_STEEL) translate([-7.3, -9.65, -11.5]) cube([7.3, 19.3, 10.5]);                       // steel cover + housing
    color(C_BLK) translate([-0.01, -6.5, -9.5]) cube([0.4, 13, 6.5]);                              // actuator slot face
    color(C_BLK) translate([0, (on ? 1.78 : -1.78) - 1.5, -6.25 - 1.5]) cube([5.08, 3.0, 3.0]);   // actuator
    color(C_GOLD) for (y=[-4.7, 0, 4.7]) translate([-5.6, y - 0.4, -1]) cube([0.8, 0.8, 1 + 1.6 + 1.5]);   // PC pins up through the board
    color(C_STEEL) for (y=[-8.4, 8.4]) translate([-6.4, y - 0.6, -1]) cube([1.2, 1.2, 1 + 1.6 + 1.0]);    // frame tabs
}
