# bugbot_sim

Circuit simulation of the BugBot stack (Motion board + Vision board + Odometry
board) from the real KiCad netlists, using KiCad's bundled ngspice. Every
component value and every connection comes from `golden_netlist.xml`; the ICs
are behavioural models built from their datasheets (`models/stack_models.lib`,
numbers and sources in `parts_spec.py`). Motors are electromechanical, the MCU
is a scripted list of I2C register writes. The Motion and Vision boards join
pin-for-pin at the J8/J9 stack sockets; the Odometry board hangs on the Motion
J7 GH1.25 cable (J7 pin k to J1 pin 11-k since the 2026-09-07 mirror, 120 mOhm per conductor) with its 1.9 V LDO,
the PMW3360 and the BNO055 modelled as loads (added 2026-09-06).

## Run

```
python sim_stack.py        # scenarios A-P (DC, transient, no-cell, USB limits) + datasheet spec checks (~2 min)
python sim_mission.py      # drive / stall / USB missions with running motors (~3 min)
MOTOR=N20_geared_3v python sim_mission.py     # other motor types: see parts_spec.MOTOR_TYPES
python bench/server.py     # interactive schematic bench at http://localhost:8765
python tools/sync_boards.py   # refresh boards/ from the KiCad projects (BUGBOT_HW env)
```

Needs KiCad 10 installed (ngspice.dll, kicad-cli, symbol library). Override with
`NGSPICE_DLL` or `KICAD_DIR`.

## Layout

| path | what |
|---|---|
| `boards/<motion,vision,odometry>/` | snapshot of each project: golden netlist, schematic sheets, sheet SVGs |
| `models/` | SPICE behavioural models (`stack_models.lib` is the current one) |
| `netlist2spice.py` | golden netlist -> SPICE elements, the only source of connectivity |
| `stack_build.py` | the shared deck: Motion + Vision joined at J8/J9, Odometry on the J7 cable, loads, motors, servos |
| `parts_spec.py` | datasheet limits per part, motor types |
| `sim_stack.py` | scenarios A..M and spec checks, prints DESIGN FINDINGS |
| `sim_mission.py` | time-domain missions, writes `out/mission_*.json` |
| `sch_geometry.py` | every wire / pin of every sheet tied to its net (for the bench) |
| `bench/` | interactive viewer: click the switch, USB, motors; ngspice re-solves |
| `legacy/` | the first single-board testbenches (pre-respin Motion, Vision only) |

## Field solver

The openEMS field-solver experiments (impedance and emissions from the PCB layout) are not in this repository: they work from the layout files, which are not published.

## What the simulation can and cannot see

`sim_stack.py` starts with `check_static.py`: every IC pin against its
CONFIRMED datasheet pin table (`parts_spec.PARTS[...]["pinout"]`), the
DRV8830 address straps (unique addresses), the I2C pull-ups, the FB divider,
the charger's ENB/USB_DET/ENPPB/ISET straps, floating inputs. This exists
because the DRV8830 pinout error of 2026-09-04 passed every ngspice scenario:
the sim and the schematic shared the same wrong pin table. A netlist-driven
sim proves board = schematic, not schematic = datasheet.

Still approximate, on purpose:
- the regulators and the H-bridges are average (non-switching) models; the
  inductor checks add the 2.4 MHz / 3 MHz ripple analytically, capacitor
  ripple current is not checked
- an operating point that ngspice cannot converge is taken from a ramped
  transient and counted in the summary line ("N operating point(s) from
  ramped transients"); a real instability would look the same
- the PTC is a resistor: the harness checks the cell current against its
  3 A hold, it never trips in the model
- loads are constant currents except the Wi-Fi burst scenario (N) and the
  missions; the ToF and camera are their typical currents; the Odometry
  board's PMW3360 draws the datasheet's run4 figure (37 mA including the
  LED, PixArt v1.30 Table 5), the BNO055 its 12.3 mA NDOF figure
- numbers still to measure: motor winding resistance, HK-5320 servo currents,
  I2C bus capacitance (~90 pF estimate)

## Current findings

See the DESIGN FINDINGS block printed by `sim_stack.py`. As of 2026-09-04:
the DRV8830s drop below their 2.75 V UVLO on a 3.0 V cell (firmware cut-off
near 3.3 V), and charging at 806 mA while running draws 1.36 A from USB
(needs a 1.5 A-advertising source, or USB_DET/ISET2 for weak ports).
