# BugBot in FreeCAD: the assembly. Every part is a component (App::Link) of one Assembly.
# Parts that do not move are grounded, and their placement follows the part (so parameter changes carry through).
# The gripper (both arms, the steel front bar, the TPU sleeve and the servo horn) turns about the servo axis by the
# parameter grip_ang (0 = closed, 105 deg = raised).
# Run after the other build scripts:  python fusionflow/ffclient.py run mech/freecad/build_assembly.py
import os
import JointObject
from fusionflow import helpers as H, extrude as X

doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
E = lambda s: X.expand(s, doc)

STATIC = ["Chassis", "MotorCaps", "MainPCB", "KickBracket", "KickDisc", "BattCradle", "Mast", "TopDeck", "Dome", "ServoBlock",
          "HoopBracket", "Wheel1", "Wheel2", "Wheel3", "Motor1", "Motor2", "Motor3", "Solenoid", "M3ThinNut", "Servo", "Cell",
          "KickCap", "PCBParts", "FrontBoard", "LEDRing", "Antenna", "Ball"]
GRIPPER = ["HoopArmL", "HoopArmR", "FrontBar", "HoopSleeve", "ServoHorn"]

old = doc.getObject("Assembly")
if old:
    for o in list(old.OutListRecursive):
        if o.isDerivedFrom("App::Link") or o.TypeId == "App::FeaturePython" or o.isDerivedFrom("Assembly::JointGroup"):
            try: doc.removeObject(o.Name)
            except Exception: pass
    doc.removeObject("Assembly")
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Label = "BugBot Assembly"
joints = asm.newObject("Assembly::JointGroup", "Joints")

link = {}
for name in STATIC + GRIPPER:
    src = doc.getObject(name)
    l = asm.newObject("App::Link", name + "_")
    l.LinkedObject = src
    l.Label = name + ":1"           # Fusion-style occurrence name
    l.LinkTransform = True          # the component sits wherever its part is (parameters, gripper turn)
    link[name] = l
    src.ViewObject.Visibility = False      # the assembly shows the parts; the bodies stay editable in the tree
doc.recompute()

for name in STATIC:                         # grounded
    g = joints.newObject("App::FeaturePython", "Ground_" + name)
    JointObject.GroundedJoint(g, link[name])
    g.Label = "Ground " + name
    JointObject.ViewProviderGroundedJoint(g.ViewObject)


# gripper: the five parts turn together about the servo axis (Y through the pivot) by grip_ang. FreeCAD 1.0's solver can
# land on a 180-deg-flipped solution for a joint driven this far, so the turn is an exact placement expression instead.
TURN = "translationm(pivot_x; 0 mm; pivot_z) * rotationy(-grip_ang) * translationm(-pivot_x; 0 mm; -pivot_z)"   # the parts are modelled in place
for name in GRIPPER:
    doc.getObject(name).setExpression("Placement", E(TURN))
    g = joints.newObject("App::FeaturePython", "Ground_" + name)
    JointObject.GroundedJoint(g, link[name])
    g.Label = f"Gripper {name} (turned by grip_ang)"
    JointObject.ViewProviderGroundedJoint(g.ViewObject)
doc.recompute()
doc.save()
result = {"links": len(link), "joints": len(joints.Group), "arm": str(link["HoopArmL"].Placement)}
