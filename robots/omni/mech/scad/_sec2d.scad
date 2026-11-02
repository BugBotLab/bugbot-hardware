include <bugbot_chassis.scad>
k = 0;
module p(k) {
    if (k==1) chassis(); if (k==2) pcb(); if (k==3) solenoid(); if (k==4) kick_bracket();
    if (k==5) for (i=[0:2]) at_wheel(i) wheel();
    if (k==6) for (i=[0:2]) at_wheel(i) translate([0,0,-wheel_w/2 - 0.3]) gearmotor();
    if (k==7) motor_caps(); if (k==8) ball(); if (k==9) { mast(); top_deck(); } if (k==10) servo9g();
    if (k==11) dome(); if (k==12) front_board(); if (k==13) kick_cap(); if (k==14) hoop(hoop_closed_ang);
    if (k==15) battery(); if (k==16) { servo_block(); hoop_bracket(); hoop_hub(); } if (k==17) led_ring();
}
projection(cut=true) rotate([90,0,0]) translate([0, sol_dy, 0]) p(k);   // cut plane = the kicker's axis (Y = -2.8)
