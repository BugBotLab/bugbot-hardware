#!/usr/bin/env bash
# Re-export the bought-part shapes for the FreeCAD model: CSG (imported as true solids) and STL fallbacks.
set -e
cd "$(dirname "$0")"
OS="/c/Program Files/OpenSCAD/openscad.com"
for n in Gearmotor Solenoid M3ThinNut Servo Cell KickCap LEDRing Antenna FrontBoard; do
  "$OS" -D "what=\"$n\"" -o "bought/$n.csg" bought_src.scad > /dev/null 2>&1 &
done
wait
# OpenSCAD writes STL imports relative to the source; make them absolute for FreeCAD's importer
sed -i "s#import(file = \"models/#import(file = \"$(cd .. && pwd -W)/models/#g" bought/FrontBoard.csg
cp ../stl/wheel_assembly.stl bought/Wheel.stl      # the omni wheel stays a mesh solid (its hulls do not convert)
