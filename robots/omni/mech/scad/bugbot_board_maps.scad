// Labelled maps of the BugBot main board. side = "top" (seen from above) or "bottom" (seen from below).
include <bugbot_chassis.scad>
side = "top";

top_items = [   // [number, x, y]
    [1, -9.4, -14.1], [2, -6.0, -27.5], [3, -2.5, -27.5], [4, 1.0, -28.2], [5, 9.0, -32.0],
    [6, 6.8, -15.3], [7, 8.5, 29.6], [8, 16.0, 29.6], [9, 12.25, 25.0], [10, -6.5, 14.0],
    [11, 0.0, -33.6], [12, 17.4, -3.6], [13, -1.5, -18.5], [14, 0.5, 26.5], [15, -11.44, 26.5],
];
bottom_items = [
    [1, 4.5, 20.5], [2, -15.0, 12.0], [3, -14.0, 17.0], [4, -21.0, -13.0], [5, -25.5, -12.6],
    [6, 20.3, 12.8], [7, -25.8, 4.5], [8, -22.0, -6.0], [9, -17.0, 25.0], [10, -9.0, -17.5],
    [11, -17.0, -26.2], [12, 6.0, -0.8], [13, 15.6, -27.0], [14, -24.85, -1.3],
];

module marker(n, flip=false) {
    color([1,1,1]) cylinder(d=4.4, h=0.2, $fn=32);
    color([0.85,0.2,0.15]) difference() { cylinder(d=4.8, h=0.25, $fn=32); translate([0,0,-1]) cylinder(d=4.2, h=2, $fn=32); }
    color([0.1,0.1,0.1]) translate([0, 0, 0.21]) linear_extrude(0.1)
        mirror([0, flip ? 1 : 0, 0]) text(str(n), size=2.2, halign="center", valign="center", font="Liberation Sans:style=Bold");
}

pcb();
if (side == "top") {
    for (it=top_items) translate([it[1], it[2], 42]) marker(it[0]);
    color([0.7,0.7,0.75], 0.35) { translate([0,0,0]) servo9g(); battery(); }   // footprints of what sits on top
} else {
    for (it=bottom_items) translate([it[1], it[2], 14]) mirror([0,0,1]) marker(it[0], flip=true);
    color([0.7,0.7,0.75], 0.5) solenoid();
    kick_cap();
}
