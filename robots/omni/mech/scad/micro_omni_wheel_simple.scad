// Micro omni wheel - FDM printable, metal pin axles
// Two staggered rows of 3 rollers. Frame = 2 identical halves (one per row).
// Print 2x "half" in PLA/PETG (flat face down), 6x "roller" in TPU (upright).
// Assembly: thread roller on pin, press pin into slots from the outer face,
// heat-stake with a soldering iron or a tiny drop of CA. Glue the halves
// together rotated 60 deg so the rollers alternate.

part = "assembly";  // [assembly, half, roller, rollers_plate, fit_test]

/* [Wheel] */
R        = 5.75;   // outer radius (11.5 mm diameter)
W        = 7.5;    // total width
d        = 4.1;    // distance from wheel center to roller axle
L        = 5.4;    // roller length

/* [Pins (metal)] */
pin_d    = 0.6;    // measured pin diameter (sewing pin / music wire)
pin_len  = 7.0;    // cut pin length
slot_fit = 0.0;    // added to slot width (+ looser, - tighter)

/* [Roller] */
roller_hole = 0.8; // TPU hole for pin (prints undersized; ream with hot pin)

/* [Clearances] */
clr_rad  = 0.2;    // radial gap around roller in pocket
clr_end  = 0.25;   // gap at each roller end
rim_gap  = 0.35;   // frame stays this far inside the rolling circle

/* [Hub] */
bore     = 2.0;    // motor shaft diameter (draw 0.05-0.1 under for press fit)
bore_flat= 0;      // D-flat depth (0 = round shaft)

$fn = 64;

zc      = W/4;              // roller row center height within a half
frame_r = R - rim_gap;
rr      = function(t) sqrt(R*R - t*t) - d;   // barrel profile radius

// Barrel solid along local Y, centered at origin. off = radial offset.
module barrel(len, off=0, hole=0) {
    n = 24;
    pts = concat(
        [for (i=[0:n]) let(t = -len/2 + len*i/n) [max(rr(t)+off, 0.05), t]],
        [[hole/2, len/2], [hole/2, -len/2]]);
    rotate([90,0,0]) rotate_extrude($fn=48) polygon(pts);
}

module roller() { barrel(L, 0, roller_hole); }

module bore_cut() {
    difference() {
        cylinder(d=bore, h=W*3, center=true);
        if (bore_flat > 0)
            // flat faces 30 deg so flipped halves index at 60 deg offset
            rotate(30) translate([bore/2 - bore_flat, -bore, -W*2]) cube([bore, bore*2, W*4]);
    }
}

module half() {
    difference() {
        cylinder(r=frame_r, h=W/2);
        bore_cut();
        for (i=[0:2]) rotate(i*120) translate([d,0,0]) {
            // roller pocket: swept through the whole half
            hull() for (z=[-1, W]) translate([0,0,z]) barrel(L + 2*clr_end, clr_rad);
            // pin seat + slot open to the outer face
            translate([0,0,zc]) rotate([90,0,0])
                cylinder(d=pin_d + slot_fit, h=pin_len + 0.4, center=true, $fn=24);
            translate([-(pin_d+slot_fit)/2, -(pin_len+0.4)/2, zc])
                cube([pin_d + slot_fit, pin_len + 0.4, W]);
        }
    }
}

module half_with_rollers() {
    color("silver") half();
    for (i=[0:2]) rotate(i*120) translate([d,0,zc]) {
        color("dimgray") roller();
        color("gold") rotate([90,0,0]) cylinder(d=pin_d, h=pin_len, center=true, $fn=16);
    }
}

module assembly() {
    half_with_rollers();
    rotate(60) mirror([0,0,1]) half_with_rollers();
}

module fit_test() {
    // slot widths and bore sizes to dial in tolerances
    ws = [0.5, 0.6, 0.7, 0.8];
    bs = [bore-0.15, bore-0.1, bore-0.05, bore];
    difference() {
        cube([22, 8, 2.5]);
        for (i=[0:3]) {
            translate([2 + i*5 - ws[i]/2, -1, 1]) cube([ws[i], 5, 3]);
            translate([3 + i*5, 6, -1]) cylinder(d=bs[i], h=5, $fn=48);
        }
    }
}

if (part == "assembly")      assembly();
else if (part == "half")     half();
else if (part == "roller")   translate([0,0,L/2]) rotate([-90,0,0]) roller();
else if (part == "rollers_plate")
    for (i=[0:5]) translate([(i%3)*6, floor(i/3)*6, L/2]) rotate([-90,0,0]) roller();
else if (part == "fit_test") fit_test();
