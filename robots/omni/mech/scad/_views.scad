include <bugbot_chassis.scad>
view = "top";
if (view == "top" || view == "side" || view == "front") assembly();
if (view == "under") {   // underside: chassis see-through, everything below the board
    %chassis();
    pcb(); solenoid(); color([0.95,0.55,0.2]) kick_bracket(); kick_cap();
    for (i=[0:2]) at_wheel(i) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); }
    color([0.8,0.8,0.82]) motor_caps();
}
module cutter() translate([-80, -sol_dy - 100, -5]) cube([180, 100, 120]);   // removes everything nearer than the kicker's axis
module cut(c) difference() { color(c) children(); color(c) cutter(); }
if (view == "section") {   // half model cut through the kicker axis, seen from the right side
    cut([0.88,0.88,0.9]) chassis();
    cut([0.1,0.45,0.25]) pcb();
    cut([0.75,0.75,0.78]) solenoid();
    cut([0.95,0.55,0.2]) kick_bracket();
    cut([0.95,0.65,0.2]) for (i=[0:2]) at_wheel(i) wheel();
    cut([0.4,0.4,0.45]) for (i=[0:2]) at_wheel(i) translate([0,0,-wheel_w/2 - 0.3]) gearmotor();
    cut([0.8,0.8,0.82]) motor_caps();
    cut([1,1,0.92]) ball();
    cut([0.82,0.82,0.84]) { mast(); top_deck(); }
    cut([0.15,0.25,0.65]) servo9g();
    cut([0.97,0.97,0.97]) dome();
    cut([0.08,0.30,0.55]) front_board();
    cut([0.12,0.12,0.13]) kick_cap();
    cut([0.95,0.3,0.25]) hoop(hoop_closed_ang);
}
