// Preview scenes for micro_omni_wheel.scad (not for printing)
// Uses the exported STLs in stl/ for the frame halves (export them first).
include <micro_omni_wheel.scad>

view = "with_motor";  // [wheel, with_motor, exploded]
upright = true;       // true: axle horizontal, wheel on a floor plate

/* Pololu sub-micro plastic planetary gearmotor, approximate:
   6 mm body, 19 mm long (136:1 version), 2 mm D-shaft 2.5 mm long, 0.5 mm flat */
motor_d   = 6;
motor_len = 19;
shaft_len = 2.5;
screw_L   = 10;       // M2 x 10

module pololu_motor() {
    color("gainsboro") difference() {
        cylinder(d=2, h=shaft_len, $fn=32);
        rotate(30) translate([0.5, -1, -1]) cube([2, 2, shaft_len+2]);
    }
    color("dimgray") translate([0,0,-0.6]) cylinder(d=3, h=0.6, $fn=32);
    color([0.15,0.15,0.15]) translate([0,0,-0.6-motor_len*0.55]) cylinder(d=motor_d, h=motor_len*0.55, $fn=48);
    color("silver") translate([0,0,-0.6-motor_len]) cylinder(d=motor_d, h=motor_len*0.45, $fn=48);
    color("goldenrod") for (x=[-1.4, 1.4]) translate([x-0.4, -0.15, -0.6-motor_len-1.2]) cube([0.8, 0.3, 1.2]);
}

module m2_screw() {   // head top at z=0, shank pointing down
    color([0.3,0.3,0.32]) {
        translate([0,0,-1.6]) cylinder(d=3.8, h=1.6, $fn=32);
        translate([0,0,-1.6-screw_L]) cylinder(d=2, h=screw_L, $fn=16);
    }
}

module half_vis(kind) {
    color([0.95,0.55,0.15]) import(str("stl/half_", kind, ".stl"));
    for (i=[0:2]) rotate(i*120) translate([d,0,zc]) {
        color([0.2,0.2,0.22]) roller();
        color("gold") rotate([90,0,0]) cylinder(d=pin_d, h=pin_len, center=true, $fn=16);
    }
}

module screws(lift=0) {
    for (i=[0:2]) rotate(30 + i*120) translate([screw_circle, 0, W/2 - head_h + 1.6 + lift]) m2_screw();
}

module scene() {
    if (view == "wheel") {
        half_vis("outer"); rotate(60) mirror([0,0,1]) half_vis("motor"); screws();
    }
    else if (view == "with_motor") {
        half_vis("outer"); rotate(60) mirror([0,0,1]) half_vis("motor"); screws();
        translate([0,0,-W/2]) pololu_motor();
    }
    else if (view == "exploded") {
        screws(lift=22);
        translate([0,0,9]) half_vis("outer");
        rotate(60) mirror([0,0,1]) half_vis("motor");
        translate([0,0,-W/2-9]) pololu_motor();
    }
}

if (upright) {
    rotate([90,0,0]) scene();
    color([0.85,0.85,0.8]) translate([-35,-50,-R-0.5]) cube([70,70,0.5]);
} else scene();
