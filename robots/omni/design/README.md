# BugBot KiCad projects (linked to the FreeCAD assembly)

| Project | Board | In FreeCAD |
|---|---|---|
| `schematics/Main/BugBot_Main.kicad_pcb` | main board (ESP32-P4, power, motor drivers, sensors, connectors), 35 parts + 16 holes | `Electronics / MainBoard (KiCad)` |
| `schematics/Front/BugBot_Front.kicad_pcb` | front sensor board v2, **generated** by `lib/make_front_board.py` (schematic + PCB, Freerouting): VL53L5CX + 24-pin DVP camera module (OV2640 / OV5640, taped on, flex through the board slot to a 0.5 mm FPC socket on the back), 2V8 / 1V2 LDOs, 2 x 10 1.27 mm RA header into J6; 1 M2 screw; JLC BOM / CPL in `schematics/Front/jlc/` | `Electronics / FrontSensorBoard (KiCad)` |

## The link (FusionFlow ECAD)

Who owns what: **KiCad owns the components** (footprints, schematic, routing); they only ever flow KiCad → FreeCAD.
**FreeCAD owns the mechanics**: the board outline, the mounting holes and the keep-outs where 3D-printed parts touch the
board; they only ever flow FreeCAD → KiCad. FreeCAD never adds, moves or deletes a component footprint.

- **KiCad → FreeCAD:** open a board in KiCad, edit, press **Save**. FreeCAD (with BugBot open) notices within a second,
  re-exports the STEP with `kicad-cli` in the background (no windows), and replaces the board in the assembly with its
  colours: about 7 s for the main board, 2 s for the front board.
- **FreeCAD → KiCad:** the board outline and the mounting holes belong to FreeCAD (the hidden `MainPCB` / `FrontPCB`
  bodies, driven by the Params sheet). After a change, **ECAD → Push to KiCad** (or right-click the board) rewrites
  Edge.Cuts and the `H*` mounting holes in the `.kicad_pcb`; footprints, tracks and zones are not touched. KiCad then
  offers to reload the file.
- **Mechanical keep-outs (also on Push):** FreeCAD sends only what the mechanics own: the board outline, the mounting
  holes, and where a **3D-printed part touches the board** (its contact area at the board face, within 0.3 mm: battery
  cradle, mast base, gripper pivot bracket, kicker bracket). Each becomes a KiCad **rule area that keeps footprints out**
  (`MCAD keepout top/bottom: <part>`), outlined and named on the **MCAD** layer (User.1); KiCad's DRC flags any
  footprint inside one. Everything else (components, bought parts like the servo and solenoid) is placed in KiCad.
  Zones are cut back 2.6 mm round the mounting holes (the servo block, deck legs and chassis posts stand on them; the
  holes' courtyards keep footprints away). FreeCAD owns the MCAD layer and the `MCAD keepout` areas: each push replaces them.
- Coordinates: the KiCad grid origin is the robot origin (KiCad x = robot X, KiCad y = −robot Y on the main board; on the
  front board KiCad x/y = robot Y/Z and KiCad's top side faces the front of the robot).

## Starter state (what is still to do in KiCad)

- **No schematic yet**: footprints are placed with references and values, without nets. Draw the schematic, then
  *Update PCB from Schematic* (keep the references so the placements stay).
- **Placeholders** (`lib/BugBot.pretty`, marked `PLACEHOLDER` on F.Fab): outline + 3D model only, **no pads**:
  BNO085 (LGA-28), ESP32-P4 module (simplified box model), ZX-QC4545 buttons, C&K L101011ML04Q power
  switch. (The front board is no longer a starter board: see `lib/make_front_board.py`.)
- **Check pin 1 / rotation** of the library footprints: positions come from the 3D model, rotations from its OpenSCAD
  statements, but a library footprint's own zero-angle convention can differ.
- `J7` (JST-PH SM4-TB) uses the B2B-PH-K vertical 3D model (KiCad has none for it); the HTSSOP-16 footprints point at a
  misnamed model in KiCad 10's library, so their model path is overridden.

New board: `KiCad python kicad/ff_kicad.py create <board.kicad_pcb> <mcad.json>` makes an empty board with the
outline, holes and keep-outs; components are then added in KiCad. (`kicad/_retired/` holds the scripts that placed the
starter footprints from the OpenSCAD model; they are no longer used.)

## Front sensor board v2 (generated)

`"C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_front_board.py` rewrites `BugBot_Front.kicad_sch/.kicad_pcb` from
the Params-driven outline in `schematics/Front/mcad.json` (run `mech/freecad/build_frontpcb.py` first), places the parts, hand-routes
the tight spots (ToF fan-out, header GND links, the ear's DOVDD / GND spines) and lets Freerouting (`~/.gradle/jdks/...25.../java.exe`,
`freerouting-executable.jar`) do the rest; GND pours on both layers are filled by `kicad-cli pcb drc --refill-zones --save-board`.
Footprints / models: `lib/make_front_parts.py`, `lib/make_front_models.py`, colours in `lib/colour_models.py`. J6 on the main board: `lib/add_j6.py`.

- **Header J1 / J6 (2 x 10, 1.27 mm):** 1 SDA, 3 SCL, 5 VSYNC, 7 GND, 9 HREF, 11 D9, 13 XCLK, 15 D8, 17 D7, 19 PCLK (row away from the edge);
  2 3V3, 4 3V3, 6 GND, 8 GND, 10 GND, 12 D6, 14 D2, 16 D5, 18 D3, 20 D4 (edge row). XCLK comes from the ESP32-P4. 15 P4 GPIOs incl. I2C.
- **I2C pull-ups (2.2k to 3V3) go on the main board** (shared with the Qwiic port / IMU). OV2640 0x30 / OV5640 0x3C, VL53L5CX 0x29.
- ToF: LPn tied high, INT pulled up but not wired to the header (poll `vl53l5cx_check_data_ready`), I2C_RST pulled down.
- Camera: DOVDD = 3V3 via R9 (OV2640). For an OV5640 fit R10 instead of R9 (DOVDD 2V8) and U4 = XC6206P152MR (1V5, LCSC C424701).
- **Check before ordering:** the camera FPC's pin 1 end against the module you buy (the socket has contacts on both sides, so the
  flex can face either way, but pin 1 must be at the board's -Y end, the LDO side).
