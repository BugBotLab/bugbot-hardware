# BugBot omni

The driven robot: three 24 mm omni wheels on Pololu 136:1 sub-micro gearmotors, round body, one main
board instead of a stack. Where the vibration robot shuffles on a silicone mat, this one steers.

Six body styles share one base: Ant, Base, Beetle, Scorpion, Spider and Wasp.

## The boards

| Board | Does |
|---|---|
| Main | Ø77 mm round, 1.6 mm. ESP32-P4, power and charging, motor drivers, LSM6DSV16X IMU, buzzer, buttons, the front-board socket and every connector |
| Front sensor | 19.0 × 22.1 mm. SC035HGS camera sensor soldered on the board under an M7 lens holder, VL53L7CX ToF above it, camera LDOs. Plugs straight into Main through a 2 × 8 2.0 mm right-angle header, no cable |
| Wheel encoder (× 3) | 8 × 16.7 × 0.8 mm. One MT6701QT-ACD magnetic angle sensor per wheel on the axle line, A/B quadrature, into a 1 × 4 1.27 mm socket on Main's underside |
| NFC floor | 78 × 81 mm. A 3-turn loop round the floor's edge so tags anywhere under the robot are read, a WS1850S reader packed into 22 × 13 mm on the underside, and 7 WS2812B-4020 side-view LEDs as underglow |

Retired, kept under `design/schematics/retired/`: the LED ring board (replaced by a bought 7-LED jewel,
2026-10-31) and the separate NFC reader, coil and flex boards (folded into the NFC floor board, 2026-10-31).

Two things that earlier notes get wrong: there is **no magnetometer** — the wheels' encoder magnets swamp
it, so the IMU is 6-axis only — and odometry is the three wheel encoders, not the trackball that an early
session sketched.

## Layout

| path | what |
|---|---|
| `design/schematics/<Board>/` | the KiCad project: schematic, project file, lib tables, the geometry FreeCAD pushes in (`mcad.json`, `keepouts.json`, `placements.json`) |
| `design/lib/` | the generators and layout tools: board makers, placement and routing passes, JLC fab output, the `BugBot.pretty` footprints |
| `design/tools/pns_api/` | the KiCad push-and-shove fork: the patch, its protobuf client and the scriptable router |
| `design/README.md` | the FreeCAD ↔ KiCad link: who owns the outline, the holes and the keep-outs, and which way each change flows |
| `mech/scad/` | OpenSCAD: the chassis, the parts, and `micro_omni_wheel.scad` |
| `mech/freecad/` | the FreeCAD assembly's build scripts, the approved 2D sketches, and the MuJoCo studies |
| `docs/PARTS.md` | every part in the chassis with the size used in the model, and where each size comes from |

## Paths

Scripts find their way from the `.bugbot-root` marker in this folder, walking up from their own location,
so the tree can move again without another pass over every file. `BUGBOT_OMNI` overrides it.

```
"C:/Program Files/KiCad/10.0/bin/python.exe" robots/omni/design/lib/make_enc_board.py
```

One script reaches outside this repo: `mech/freecad/sim/nfc_study.py` wants the separate SimLink project,
through `SIMLINK_SIM`.

## What is not in git

The schematics are public; the PCB layout is not, as everywhere else in this repo. On top of that the CAD
and the build output sit in these folders but are deliberately unversioned (see the repo's `.gitignore`):
the FreeCAD documents, the STL/STEP/BREP output, the renders, the per-board `_route/` `_place/` `_work/`
folders and the `jlc/` fab packages. What is versioned is everything needed to rebuild them.
