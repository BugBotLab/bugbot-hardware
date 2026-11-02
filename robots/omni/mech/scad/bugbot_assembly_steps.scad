// BugBot v1.1 assembly steps. step = 1..12; each step shows what is already built plus the new parts,
// pulled back along the way they go in (red arrow), with their screws in blue.
include <bugbot_chassis.scad>
step = 1;
part = "none";

C_SCREW = [0.2, 0.45, 0.95];
module screw(p, dir=[0,0,1], len=6, d=2, head=3.8) {   // dir: the way the screw travels as it goes in
    a = dir[2] != 0 ? (dir[2] > 0 ? [0,0,0] : [180,0,0]) : (dir[0] != 0 ? [0, dir[0] > 0 ? 90 : -90, 0] : [dir[1] > 0 ? -90 : 90, 0, 0]);
    color(C_SCREW) translate(p) rotate(a) translate([0, 0, -len - 4]) {
        translate([0, 0, -1.4]) cylinder(d=head, h=1.4, $fn=20);
        cylinder(d=d, h=len, $fn=12);
    }
}
module arrow(from, to) {   // red arrow showing the direction a part moves
    v = to - from; L = norm(v);
    color([0.9, 0.15, 0.1]) translate(from) rotate([0, acos(v[2]/L), atan2(v[1], v[0])]) {
        cylinder(d=0.8, h=L - 2.5, $fn=10); translate([0, 0, L - 2.5]) cylinder(d1=2.2, d2=0, h=2.5, $fn=16);
    }
}
module moving(off, at) { translate(off) children(); arrow(at + off, at + off*0.25); }

module kicker_sub() { solenoid(); color([0.95,0.55,0.2]) kick_bracket(); }
module board_top() { front_board(); color([0.85,0.85,0.85]) mast(); servo9g(); color([0.85,0.85,0.85]) servo_block(); }

// what is already done before each step
module done(n) {
    if (n >= 2 && n <= 10) pcb();
    if (n >= 3) front_board();
    if (n >= 4) color([0.85,0.85,0.85]) mast();
    if (n >= 5) { servo9g(); color([0.85,0.85,0.85]) servo_block(); }
    if (n >= 6) { color([0.85,0.85,0.85]) hoop_bracket(); }
    if (n >= 7) { kicker_sub(); kick_cap(); color([0.8,0.8,0.85]) batt_cradle(); }
    if (n >= 8) { color([0.85,0.85,0.85]) top_deck(); led_ring(); antenna(); color([1,1,1], 0.55) dome(); }
}
module chassis_done(n) {
    if (n >= 9) { color([0.9,0.9,0.92]) chassis(); }
    if (n >= 10) { color([0.8,0.8,0.82]) motor_caps(); for (i=[0:2]) at_wheel(i) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); } }
}

if (step == 1) {          // prepare the JF-0520B (acorn nut off, clevis cut off behind the e-clip, shown red), then into the bracket, 2 x M3 x 4
    solenoid(show_cut=true);
    moving([0, -8, 0], [sol_x0 + 10, -sol_body[1]/2 - sol_dy - 1, sol_z]) color([0.95,0.55,0.2]) kick_bracket();
    for (x=[sol_body[0]/2 - 5.5, sol_body[0]/2 + 5.5]) screw([sol_x0 + x, -sol_body[1]/2 - sol_dy - 2 - 8, sol_z], [0,1,0], 4, 3, 5.5);
}
if (step == 2) {          // the main board, parts soldered
    pcb();
}
if (step == 3) {          // front sensor board straight down into its socket (before the mast!)
    done(3 - 1);
    moving([0, 0, 12], [fsb_x, 0, fsb_z0]) front_board();
}
if (step == 4) {          // mast slides on from the front, 2 x M2 x 6 up from below; then the sensor board's 2 x M2 x 4 from behind
    done(3);
    moving([14, 0, 0], [mast_x + 3, 0, pcb_top + 20]) color([0.85,0.85,0.85]) mast();
    for (m=mast_screws) screw([m[0], m[1], pcb_z], [0,0,1], 6);
    for (y=[fsb_y0 + 2, fsb_y0 + fsb_w - 2]) screw([fsb_x, y, fsb_z0 + fsb_h - 2], [1,0,0], 4);
}
if (step == 5) {          // servo between the mast's ear boss and the rear block; ear screws from the -Y side, block screw from below
    done(4);
    moving([0, 0, 14], [pivot[0] - 6, 0, pivot[1] + 6]) servo9g();
    color([0.85,0.85,0.85]) servo_block();
    for (x=ear_x) screw([x, ear_y - 2.5, pivot[1]], [0,1,0], 6);
    screw([servo_x0 - 2.3, ear_y + 2.15, pcb_z], [0,0,1], 6);
}
if (step == 6) {          // pivot bracket for the -Y arm (2 x M2 x 6 from below)
    done(5);
    moving([0, 0, 10], [pivot[0], -26, pcb_top + 4]) color([0.85,0.85,0.85]) hoop_bracket();
    for (dx=[-2.5, 2.5]) screw([pivot[0] + dx, -27.3, pcb_z], [0,0,1], 6);
}
if (step == 7) {          // kicker up under the board (front M2 from the top), battery cradle on top (2 x M2 from below, one through the kicker's rear tab)
    done(6); kick_cap();
    moving([0, 0, -12], [0, -9, pcb_z - 6]) kicker_sub();
    moving([0, 0, 12], [batt_x, 0, pcb_top + 10]) color([0.8,0.8,0.85]) batt_cradle();
    for (k=[kb_front, kb_rear]) screw([k[0], k[1], pcb_top], [0,0,-1], 6);
    for (c=cradle_screws) screw([c[0], c[1], pcb_z], [0,0,1], 6);
}
if (step == 8) {          // deck: antenna stuck underneath, LED ring + dome on top; 2 x M2 down into the mast, 2 x M2 up into the legs
    done(7);
    moving([0, 0, 14], [0, 0, mast_top + 10]) { color([0.85,0.85,0.85]) top_deck(); led_ring(); antenna(); color([1,1,1], 0.55) dome(); }
    for (y=[-8, 8]) screw([mast_x + 1.5, y, mast_top + cap_t + 14], [0,0,-1], 4);
    for (l=deck_legs) screw([l[0], l[1], pcb_z], [0,0,1], 6);
}
if (step == 9) {          // chassis
    color([0.9,0.9,0.92]) chassis();
}
if (step == 10) {         // wheels on the motors, motors into the saddles, clamp caps (6 x M2 x 6)
    chassis_done(9);
    for (i=[0:2]) moving([0, 0, 18], at_pos(i)) at_wheel(i) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); }
    moving([0, 0, 26], [0, 0, axle_z + 4]) color([0.8,0.8,0.82]) motor_caps();
}
function at_pos(i) = [ (wf - wheel_w/2)*cos(wheel_ang[i]) - e*sin(wheel_ang[i]), (wf - wheel_w/2)*sin(wheel_ang[i]) + e*cos(wheel_ang[i]), axle_z + 12 ];
if (step == 11) {         // plug in 3 motor cables + kicker cable, lower the board in (switch and USB drop into their slots), 4 x M2 x 6 into the posts
    chassis_done(10);
    translate([0, 0, 22]) { done(8); }
    arrow([0, -32, pcb_top + 22 + 10], [0, -32, pcb_top + 22 - 8]);
    for (a=boss_ang) screw([boss_r*cos(a), boss_r*sin(a), pcb_top + 22 + 12], [0,0,-1], 6);
}
if (step == 12) {         // gripper: +Y arm onto the hub, -Y arm on its M2 axle + nyloc nut, TPU sleeve between, steel pin in from the -Y side
    chassis_done(10); done(8);
    moving([0, 8, 0], [pivot[0] + 20, hoop_y, pivot[1]]) { color([0.95,0.3,0.25]) hoop_arm(1); servo_horn(); }   // horn screwed to the arm first
    screw([pivot[0], hoop_y + 8 + 6, pivot[1]], [0,-1,0], 6, 2, 3.6);                                     // horn centre screw, through the access hole
    moving([0, -8, 0], [pivot[0] + 20, -hoop_y, pivot[1]]) color([0.95,0.3,0.25]) hoop_arm(-1);
    color([0.15,0.15,0.17]) hoop_sleeve();
    translate([pivot[0] + bar[0], -30, pivot[1] + bar[1]]) rotate([-90,0,0]) color([0.72,0.72,0.75]) cylinder(d=rod_d, h=rod_l, $fn=24);
    arrow([pivot[0] + bar[0], -36, pivot[1] + bar[1] + 4], [pivot[0] + bar[0], -26, pivot[1] + bar[1] + 4]);
    screw([pivot[0], -hoop_y - hoop_arm[1]/2 - 0.4 - 3.2 - 8, pivot[1]], [0,1,0], 8);
    ball();
}
if (step == 13) {         // battery into the cradle, strap, plug in: done
    assembly();
}
