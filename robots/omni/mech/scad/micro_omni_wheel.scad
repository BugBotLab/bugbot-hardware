// Micro omni wheel - FDM printable, metal pin axles, M2 screws
// Two staggered rows of 3 rollers. Frame = 2 halves (one per roller row).
// Print "half_outer" + "half_motor" in PLA/PETG (flat mating face down),
// 6x "roller" in TPU (upright).
// Assembly: drop roller into its pocket, push the pin in from outside along the
// tangent hole: through the frame, through the roller, into the frame on the
// far side. Pin is held in fully enclosed holes at both ends. Heat the pin
// tip with a soldering iron while pushing so it melts its own snug hole.
// Join the halves with 3x M2 x 10 self-tapping screws from the outer side;
// the screw holes only line up with the halves 60 deg apart.

part = "assembly";  // [assembly, half_outer, half_motor, roller, rollers_plate, fit_test]

/* [Wheel] */
wheel_d  = 24;     // outer diameter. Everything below scales from the 11.5 mm design
s        = wheel_d / 11.5;
R        = wheel_d/2;
d        = 4.0 * s;    // distance from wheel center to roller axle
L        = 2*d*tan(30) + 0.25;  // roller length: just over the 60 deg needed for continuous contact
row_gap  = 0.35;       // gap between a roller and each face of its half
W        = 2 * (2*(R - d) + 2*row_gap);  // total width (two rows)

/* [Pins (metal)] */
pin_d    = 1.0;    // measured pin diameter (1.0 mm music wire or steel dowel pin)
pin_wall = 0.8;     // minimum wall round the pin, even at its outer end
pin_fit  = -0.05;  // added to frame hole (pilot slightly under, hot pin opens it)

/* [Roller] */
roller_hole = pin_d + 0.2; // TPU hole for pin (prints undersized; ream with hot pin)

/* [Clearances] */
clr_rad  = 0.2;    // radial gap around roller in pocket
clr_end  = 0.25;   // gap at each roller end
rim_gap  = 0.15;   // frame stays this far inside the rolling circle
                   // (frame lobes only exist where the other row's roller is down)

/* [Frame shape] */
boss_t    = 1.5;      // wall round the pin in each support block
fillet    = 0.8;      // convex corner radius
fillet_in = 0.3;      // concave corner radius (pocket corners; keep small)
edge_r    = 0.6;      // rounded edge on each half's outer face (and all vertical edges)

/* [Hub] */
// Defaults: Pololu sub-micro plastic planetary gearmotor (6 mm), 2 mm D-shaft,
// 0.5 mm flat, 2.5 mm long -> only the motor-side half has the shaft hole.
bore     = 1.95;   // motor shaft diameter (drawn 0.05 under for press fit)
bore_flat= 0.5;    // D-flat depth (0 = round shaft)

/* [Screws: M2 self-tapping] */
screw_circle = 3.0 * s / (24/11.5);  // radius of the 3 screws (3.0 mm at 24 mm wheel)
screw_clear  = 2.3;  // clearance hole in the outer half
screw_pilot  = 1.6;  // pilot hole in the motor half (self-tapping into plastic)
head_d       = 3.9;  // counterbore for the screw head (M2 socket head is 3.8)
head_h       = 1.8;  // counterbore depth
pilot_floor  = 1.2;  // solid floor left under the blind pilot holes (motor face)

$fn = 64;

zc      = W/4;              // roller row center height within a half
frame_r = R - rim_gap;
// pin ends where the wall to the rim would drop below pin_wall
pin_end = sqrt(frame_r*frame_r - (d + pin_d/2 + pin_wall)^2);
pin_len = 2 * pin_end;      // cut pin length (ends sit inside the frame)
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

module bore_cut_d(b) {
    difference() {
        cylinder(d=b, h=W*3, center=true);
        if (bore_flat > 0)
            rotate(30) translate([b/2 - bore_flat, -b, -W*2]) cube([b, b*2, W*4]);
    }
}
module bore_cut() { bore_cut_d(bore); }

// 2D outline of a roller pocket (local frame, roller axle along Y at x=0)
module pocket2d() {
    y0 = L/2 + clr_end;
    n  = 24;
    polygon(concat(
        [for (i=[0:n]) let(y = -y0 + 2*y0*i/n) [rr(y) + clr_rad + R, y]],   // outboard: open through rim
        [for (i=[n:-1:0]) let(y = -y0 + 2*y0*i/n) [-(rr(y) + clr_rad), y]]));
}

// Support block round one pin end (local frame of its roller): even wall boss_t
module pin_boss(sign) {
    y0 = L/2 + clr_end;
    hull() for (y=[y0, pin_end]) translate([d, sign*y]) circle(r=pin_d/2 + boss_t, $fn=48);
}

// Frame outline: hub + 3 simple lobes, each a hull of two pin supports and the hub,
// trimmed to the rim, minus the roller pockets; corners rounded
module frame2d() {
    offset(r=fillet) offset(delta=-fillet)          // round convex corners
    offset(r=-fillet_in) offset(delta=fillet_in)    // round concave corners
    difference() {
        intersection() {
            circle(r=frame_r, $fn=128);
            for (i=[0:2]) hull() {
                circle(r=d - (R - d) + 0.5, $fn=64);                  // hub
                rotate(i*120) pin_boss(+1);                           // end of roller i
                rotate((i+1)*120) pin_boss(-1);                       // start of roller i+1
            }
        }
        for (i=[0:2]) rotate(i*120) translate([d,0]) pocket2d();
    }
}

// kind = "outer": screw clearance holes + head counterbores, no shaft hole
// kind = "motor": shaft hole + blind pilot holes from the mating face
// Screws sit between pockets: 30+120k in the outer half, -30+120k in the motor
// half (it is mounted rotated 60 deg), so both land on the same spots.
module half(kind="outer") {
    h  = W/2;
    sa = kind == "outer" ? 30 : -30;
    difference() {
        // flat mating face (z=0), outer face edges rounded with radius edge_r
        minkowski() {
            linear_extrude(h - edge_r) offset(delta=-edge_r) frame2d();
            intersection() {
                sphere(r=edge_r, $fn=16);
                translate([-edge_r, -edge_r, 0]) cube(2*edge_r);
            }
        }
        if (kind == "motor") bore_cut();
        for (i=[0:2]) rotate(sa + i*120) translate([screw_circle, 0, 0]) {
            if (kind == "outer") {
                translate([0,0,-1]) cylinder(d=screw_clear, h=h+2, $fn=32);
                translate([0,0,h-head_h]) cylinder(d=head_d, h=head_h+1, $fn=48);
            } else
                translate([0,0,-1]) cylinder(d=screw_pilot, h=h-pilot_floor+1, $fn=24);
        }
        // enclosed tangent hole for each pin, through both support bosses
        for (i=[0:2]) rotate(i*120) translate([d,0,zc]) rotate([90,0,0])
            cylinder(d=pin_d + pin_fit, h=4*R, center=true, $fn=24);
    }
}

module half_with_rollers(kind="outer") {
    color([0.95,0.55,0.15]) half(kind);
    for (i=[0:2]) rotate(i*120) translate([d,0,zc]) {
        color([0.2,0.2,0.22]) roller();
        color("gold") rotate([90,0,0]) cylinder(d=pin_d, h=pin_len, center=true, $fn=16);
    }
}

module assembly() {
    half_with_rollers("outer");
    rotate(60) mirror([0,0,1]) half_with_rollers("motor");
}

module fit_test() {
    // top row: D-bores bore-0.1 .. bore+0.05 (try them on the motor shaft)
    // middle row: M2 pilot holes (pick the one the screw bites into firmly)
    // side: horizontal pin pilots, same z height as in the wheel
    bs = [bore-0.1, bore-0.05, bore, bore+0.05];
    ps = [pin_d-0.15, pin_d-0.1, pin_d-0.05, pin_d];
    ts = [screw_pilot-0.2, screw_pilot-0.1, screw_pilot, screw_pilot+0.1];
    difference() {
        cube([22, 12, W/2]);
        for (i=[0:3]) {
            translate([3 + i*5, 9, 0]) bore_cut_d(bs[i]);
            translate([3 + i*5, 5.5, 1]) cylinder(d=ts[i], h=W, $fn=24);
            translate([3 + i*5, -1, zc]) rotate([-90,0,0]) cylinder(d=ps[i], h=4, $fn=24);
        }
    }
}

if (part == "assembly")      assembly();
else if (part == "half_outer") half("outer");
else if (part == "half_motor") half("motor");
else if (part == "roller")   translate([0,0,L/2]) rotate([-90,0,0]) roller();
else if (part == "rollers_plate")
    for (i=[0:5]) translate([(i%3)*(R+1), floor(i/3)*(R+1), L/2]) rotate([-90,0,0]) roller();
else if (part == "fit_test") fit_test();
