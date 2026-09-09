# bugbot-hardware

Everything physical about BugBot: the schematics, the bill of materials, 3D models of the robot and its boards, the assembly guide, and the circuit simulation bench that doubles as the schematics' test suite.

Part of the [BugBot open-source plan](https://github.com/BugBotLab).

## What is public and what is not

The **schematics are public**: every sheet as KiCad source and as PDF, the symbol library, the netlists, and the BOM with part numbers. Anyone can read, simulate and repair every circuit.

The **PCB layout is not published**: no `.kicad_pcb`, no gerbers, no pick-and-place files. The 3D models here were exported without copper, so they show the boards and their parts but not the routing.

## The robot

Three 40 x 40 mm boards stacked on 2 x 5 sockets, on a 3D-printed chassis, moving by four vibration motors on a silicone mat:

| Board | Does |
|---|---|
| Motion | battery, USB-C charging, 3.3 V rail, four DRV8830 motor drivers, two servo outputs, the ToF module connector |
| Vision | ESP32-P4 (plus its C6 for Wi-Fi), OV5647 camera on a 22-pin flex, power switch, boot and reset buttons, LED |
| Odometry | PMW3360 optical-flow sensor and BNO055 IMU, on a 10-way cable to Motion |

## Layout

| path | what |
|---|---|
| `design/schematics/<Board>/` | KiCad schematic sheets, `BugBot.kicad_sym`, the project file, `golden_netlist.xml`, and the schematic PDF |
| `design/bom/` | `BugBot_BOM.xlsx` (parts, per-board sheets, costing, flags) and the JLCPCB BOM CSVs |
| `design/3d/` | `.step` and `.glb` of each board without copper, plus renders |
| `design/mechanical/` | chassis and mat (see its README for where the CAD lives today) |
| `sim/` | the circuit bench: ngspice simulation of the whole stack from the netlists, 89 static checks, scenario runs, and an interactive schematic bench. See `sim/README.md` |
| `docs/` | assembly and bring-up |
| `viewer/` | a web page that spins the board models (uses the `.glb` files), hosted at https://www.bugbotlab.com/bugbot-hardware/viewer/ |

## Simulation is the schematic test suite

`sim/` builds a SPICE model of the three boards from `golden_netlist.xml` and checks it against the datasheets: rails, currents, USB limits, no-cell behaviour, motor stalls. When a schematic changes, `python sim/tools/sync_boards.py` refreshes the snapshot and `python sim/check_static.py` plus `python sim/sim_stack.py` say whether it still holds. That is why the bench lives in this repo rather than beside the firmware.

Needs KiCad 10 installed (for ngspice and kicad-cli).

## Licence

MIT, BugBotLab Ltd. Hardware files under the same licence.
