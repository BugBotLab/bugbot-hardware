include <bugbot_chassis.scad>
A=0; Bk=0;
module part(k) {
  if (k==1) servo9g(); if (k==2) battery(); if (k==5) mast(); if (k==6) top_deck();
  if (k==7) servo_block(); if (k==8) hoop_bracket(); if (k==9) servo_horn(); if (k==10) solenoid(); if (k==11) kick_cap();
  if (k==12) hoop(hoop_closed_ang); if (k==13) hoop(hoop_open_ang); if (k==14) chassis(); if (k==15) motor_caps(); if (k==16) pcb();
  if (k==17) antenna(); if (k==18) led_ring();
  if (k==19) for (i=[0:2]) at_wheel(i) { wheel(); translate([0,0,-wheel_w/2 - 0.3]) gearmotor(); }
  if (k==20) batt_cradle(); if (k==21) front_board(); if (k==22) ball(); if (k==23) dome();  if (k==25) hoop_sleeve(); if (k==26) servo_horn(hoop_open_ang); if (k==31) translate([0,0,-0.03]) kick_bracket(); if (k==32) { translate([-23, -14.8, pcb_z - 4.32 - 6]) cube([4, 3.6, 6]); translate([-27.5, -14.4, pcb_z - 4.32 - 6]) cube([4, 3.6, 6]); translate([-18, 9.75, pcb_z - 12]) cube([6, 4.5, 6]); translate([-16, 15.2, pcb_z - 4.32 - 6]) cube([4, 3.6, 6]); }
}
intersection() { part(A); part(Bk); }
