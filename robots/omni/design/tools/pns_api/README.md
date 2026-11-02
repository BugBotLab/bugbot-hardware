# pns_api: scripted push-and-shove routing in a private KiCad 10 build

KiCad's interactive router (PNS: push-and-shove, walkaround, drag, optimizer) cannot be reached from KiCad's
Python bindings. SWIG has no router symbols, and the IPC API (`kipy`) only has `run_action` and
`interactive_move`, which both need a mouse. This folder holds:

* a **patched KiCad 10.0.3** that adds IPC API commands which drive `PNS::ROUTER` directly
  (`RouteTrack`, also for differential pairs; `DragItem`; `OptimizeNets`). Phase 2 adds `GetUnrouted`,
  `ProbeClearance`, `GetZoneIslands`, `SetTeardrops`, `UpdateFromNetlist` and `TuneLength`,
* a **Python client**, `pns_client.py`, built on `kipy` 0.8 plus `router_commands_pb2.py`. Higher-level tools live
  in `pns_extras.py` (fan-out, stitching vias, move with push, congestion map, MCAD heights, 3D checks), and
  `pns_3d.py` does the OCP work in a subprocess,
* a **stdlib MCP server**, `mcp_pns.py`, registered as `kicad-pns` in the repo's `.mcp.json` (26 tools).

The installed KiCad (`C:\Program Files\KiCad\10.0`) is not touched. The private build runs with its own config
folder and its own API socket, so both can run at the same time.

## Layout

| Path | What |
|---|---|
| `C:\Users\Jerome\kicad-dev\src` | KiCad source, tag `10.0.3` plus the patch (`kicad-pns-api.patch` here) |
| `C:\Users\Jerome\kicad-dev\vcpkg` | vcpkg at KiCad CI's commit `66c0373d` |
| `C:\Users\Jerome\kicad-dev\src\build\msvc-win64-release` | build tree |
| `C:\Users\Jerome\kicad-dev\src\build\install\msvc-win64-release` | runnable install (`bin\pcbnew.exe`), from `install.bat` |
| `C:\Users\Jerome\kicad-dev\config` | private `KICAD_CONFIG_HOME` (API server enabled) |
| `C:\Users\Jerome\kicad-dev\run\tmp` | private TEMP, so the socket is `ipc://...\run\tmp\kicad\api.sock` |
| `C:\Users\Jerome\kicad-dev\work` | board copies made by `pns_open(copy_from=...)` |

## The patch (`kicad-pns-api.patch`)

* `api/proto/board/router_commands.proto`: new messages `RouteTrack`, `DragItem`, `OptimizeNets`, which all
  return `RouterResult`. The file is new and separate, so stock kipy is unchanged; the client ships its own
  generated `router_commands_pb2.py`.
* `pcbnew/router/router_tool_api.cpp` plus new public methods on `ROUTER_TOOL`: `ApiRouteTrack`, `ApiDragItem`,
  `ApiOptimizeNets`. They drive the tool's own `PNS::ROUTER` and `PNS_KICAD_IFACE`, as the interactive tool does,
  but synchronously and without mouse events:
  * **Route:** `SyncWorld`, pick the start item (`pickSingleItem`), import sizes, then `StartRouting`. Each
    waypoint gets `Move` then `FixRoute`, with *fix all segments* on so every waypoint is a real vertex. A
    waypoint with a new layer arms via placement first, then `SwitchLayer`. The last point snaps to a pad or
    track of the net if one is there. The run ends with `CommitRouting`, a normal undoable commit. If the
    head stops short of a waypoint (blocked), nothing is committed unless `allow_partial`.
  * **Drag:** `StartDragging(DM_ANY [| DM_FREE_ANGLE])`, `Move(target)`, `FixRoute`. In shove mode the router
    falls back to the last valid position, as it does in the GUI.
  * **Optimize:** for every line of the nets, `OPTIMIZER::Optimize` runs on a branch node. Defaults are
    `MERGE_SEGMENTS | SMART_PADS | MERGE_OBTUSE`, with optional `KEEP_TOPOLOGY`. The branch is committed
    through `ROUTER::CommitRouting(NODE*)`.
  * The user's router mode and *fix all segments* setting are restored after each call.
* `pcbnew/api/api_handler_pcb_router.cpp`: the handlers. They resolve the net, layers and item, call the tool,
  and diff the board's tracks before and after. The result lists `added`, `removed` and `modified` (shoved)
  item ids.

## Build (what was done)

Requirements: Visual Studio 2022 with the C++ workload (17.12 / MSVC 14.42), CMake, Git, and about 60 GB of disk.

```
git clone --depth 1 --branch 10.0.3 https://gitlab.com/kicad/code/kicad.git C:\Users\Jerome\kicad-dev\src
git clone https://github.com/microsoft/vcpkg.git C:\Users\Jerome\kicad-dev\vcpkg
cd C:\Users\Jerome\kicad-dev\vcpkg && git checkout 66c0373dc7fca549e5803087b9487edfe3aca0a1 && bootstrap-vcpkg.bat -disableMetrics
cd C:\Users\Jerome\kicad-dev\src && git apply %BUGBOT_HW%\robots\omni\design\tools\pns_api\kicad-pns-api.patch
```

`CMakePresets.json` is the sample with `VCPKG_ROOT` set and the KiCad NuGet binary source. It also sets
`VCPKG_OVERLAY_TRIPLETS=tools/custom_vcpkg_triplets`, `KICAD_BUILD_QA_TESTS=OFF` and
`KICAD_SCRIPTING_WXPYTHON=OFF`. `wxpython-33` is removed from `vcpkg.json`, and the overlay triplet sets
`VCPKG_BUILD_TYPE release`. KiCad's NuGet cache had no packages for this toolchain (every ABI hash missed), so all
dependencies are built from source; that step dominates the build time.

`build.bat [configure]` (a copy is in this folder) runs vcvars64, then `cmake --preset msvc-win64-release`, then
`cmake --build --preset win64-release -- -k 0`. After a source change, `build.bat` alone rebuilds incrementally
(about 20 s for the router files). `install.bat` installs into `src\build\install\msvc-win64-release`; the prefix is
baked in at configure time, so don't pass `--prefix`, because `share\` would land elsewhere. It also copies the
vcpkg DLLs and the embedded Python's `Lib\` next to the binaries; without `Lib\`, pcbnew dies with "failed to get
the Python codec".

Other build fixes that were needed:

* **SWIG**: installed with `winget install SWIG.SWIG` (4.5.1). Its path is set in the presets as `SWIG_EXECUTABLE`.
  SWIG 4.4 and later dropped `PyInt_FromLong` and `PyString_Check`, which KiCad's `.i` files use, so
  `pcbnew/CMakeLists.txt` maps them to the Python 3 names for `pcbnew_wrap.cxx` (this is in the patch).
* **First-run wizard**: the private config (`kicad-dev\config`) is seeded once from `%APPDATA%\kicad\10.0`.
  `pns_client.ensure_config()` does this. Without it, the "KiCad Setup" wizard blocks startup.

**Time and disk (2026-10-24, 12 threads, 64 GB RAM).** Cloning took about 3 min. The vcpkg dependencies took
about 52 min, all 131 packages built from source, release only. The KiCad configure plus compile (2357 steps)
took about 12 min. Overall that is about 1 h 15 min of wall time, plus about 10 min lost on a debug+release
dependency attempt that was restarted. Disk: `src\build` is 11 GB, plus vcpkg's buildtrees and downloads.

## Use

Python:

```python
import sys; sys.path.insert(0, r"%BUGBOT_HW%\robots\omni\design\tools\pns_api")
from pns_client import PNS
p = PNS.open(r"C:\Users\Jerome\kicad-dev\work\test\test.kicad_pcb")      # starts the private pcbnew, or attaches
r = p.route_track("I2C_SDA", [(120.0, 95.5), (126.0, 95.5), (126.0, 99.0, "B.Cu"), (131.2, 101.0)],
                  width=0.15, mode="shove")
print(r["committed"], r["completed"], len(r["modified"]), "shoved")
p.drag_item(at=(124.0, 97.0), target=(124.0, 97.6))      # drag the segment or via under a point
p.optimize_nets(["I2C_SDA"])
print(p.drc_summary(net="I2C_SDA"))                       # kicad-cli DRC on a temp copy, zones refilled
p.plot_area((115, 90, 135, 105), "area.png", highlight=["I2C_SDA"])
p.undo(); p.save()
```

MCP tools (`kicad-pns`): `pns_open` (use `copy_from` to work on a copy; originals are refused), `route_track`,
`drag_item`, `optimize_net`, `ripup_net`, `items_at`, `drc_summary`, `plot_area` (returns the PNG), `pns_undo`,
`pns_save`, `pns_close`.

Notes:

* Units are mm. Layers are KiCad names (`F.Cu`, `In1.Cu`, `In2.Cu`, `B.Cu`).
* `points[0]` must sit on a pad, track or via of the net. The router starts from that item, as a click would.
* Modes: `shove` (push other tracks and vias), `walkaround`, and `highlight` (mark obstacles; never moves
  anything).
* `dry_run` routes or drags and reports `completed` / `reached` without committing.
* A failed route commits nothing. `message` says where it got blocked, and `reached` gives the head position.
* Every committed call is one normal undo step in pcbnew (`pns_undo`).
* `step` (default 0.1 mm): between waypoints, and between grab and target, the router gets a cursor position
  every `step`, like mouse motion. A single long jump can land on the far side of an obstacle; then shove fails,
  because a track cannot be pushed through another one.
* Waypoints must be geometrically sensible. A waypoint inside a pad of another net is "blocked", and the reply's
  `reached` shows where the head stopped. `highlight` mode with `dry_run` is a quick way to see the head go
  everywhere regardless of obstacles.

## Test (`test_shove.py`, 2026-10-24)

The test runs on a fresh copy of `BugBot_Main` in `kicad-dev\work\shove_test` (the board currently has no
tracks):

| Step | Result |
|---|---|
| route M2_A (U8.7 to J15.1, B.Cu) | committed, 4 segments, 0.4 mm from the net class, 0.1 s |
| route M2_B with waypoints below the mounting pads | committed |
| route a CC2 stub into M2_B's corridor | committed; **M2_B shoved** (5 segments replaced by a jog) |
| drag M2_B's jog 0.85 mm down through CC2, one call | committed; **CC2 shoved** and re-routed |
| route M1_B with a layer change | committed; via 0.6/0.3 mm (rules), continues on F.Cu; M2_B shoved again |
| optimize the four nets | 3 of 5 lines simplified |
| DRC (kicad-cli, zones refilled) | 6 errors before and after (all pre-existing courtyard / library items), 0 clearance or crossing items; unconnected 389 → 387 |

`shove_test.png` shows the four stages. Each router call takes 0.01–0.12 s; DRC takes about 2.5 s.

The private pcbnew window is a normal KiCad window. Watching it while routing is fine, but don't start the
interactive router there during a call (the API returns "router in use").

## Phase 2 (2026-10-26)

| # | Request | Where | MCP tool | Notes |
|---|---|---|---|---|
| 1 | GetUnrouted | C++ `GetUnrouted` (ratsnest edges) | `get_unrouted` | both endpoints: xy, copper layers, item type, `REF.PAD`; 0.01 s |
| 2 | CheckPlacement / ClearanceAt | C++ `ProbeClearance` (the router's own collision model) | `clearance_at` | kind point / segment / via; `ok`, `min_margin` (mm, negative = violation), nearest obstacles with distance vs required; 3 ms. Zone fills are not obstacles, as for the router |
| 3 | OptimizeTracks | C++ `OptimizeNets` + `area` | `optimize_tracks`, `optimize_net` | adds MERGE_COLINEAR; a 12-segment staircase became 2 segments |
| 4 | RouteDiffPair | C++ `RouteTrack.diff_pair` + client fallback | `route_diff_pair` | see the note below |
| 4 | TuneLength | C++ `TuneLength` (KiCad's tuning-pattern generator) | `tune_length` | single / diff_pair / skew; hit the target exactly (24.300 mm); dry run = tune and undo |
| 5 | FanoutFootprint | client (`pns_extras.fanout_footprint`): probe + `route_track` with a via waypoint | `fanout_footprint` | U8: 18 of 18 pads, staggered where needed |
| 6 | ZoneIslands | C++ `GetZoneIslands` (connectivity clusters) | `zone_islands` | per fill polygon: area, isolated / single connection, items touching it, pads reachable |
| 7 | AddStitchingVias | client: grid inside the net's fills on all layers, off other nets' pours, each via probed | `add_stitching_vias` | creates vias through kipy; refill afterwards |
| 7 | AddTeardrops | C++ `SetTeardrops` (TEARDROP_MANAGER) | `set_teardrops` | vias / PTH / SMD pads / track-to-track, optional net filter |
| 8 | MoveFootprint push | client: courtyard boxes, cascading shortest-axis push, locked parts reported | `move_footprint` | tracks are not dragged |
| 9 | CongestionMap | client: open ratsnest lines + pads per cell | `congestion_map` | PNG + hottest cells |
| 10 | Height-aware DRC | client + `pns_3d.py`: kicad-cli STEP (real models) meshed in OCP vs MCAD User.1 regions | `height_check` | 83 regions, ~15 s; found U6 1.885 mm deep in a 0.1 mm "Solenoid" region |
| 11 | 3D collision | `pns_3d.py`: board STEP (`--user-origin 100x100`, lifted to `board_z`) vs external STEP | `collision_3d` | overlaps (volume) and gaps < `gap` |
| 12 | RenderArea | client `plot_area` | `plot_area` | layers, zones and highlighted nets |
| 13 | UpdatePcbFromSchematic | C++ `UpdateFromNetlist` (BOARD_NETLIST_UPDATER, as in the dialog) + kicad-cli netlist | `update_from_schematic` | stand-alone pcbnew cannot reach eeschema, hence the netlist file; work copies use the original schematic (`source.json`); dry run by default |

Also new: `refill_zones`. Work copies made by `copy_design` (or `pns_open copy_from`) now get project library
tables with `${KIPRJMOD}` resolved and a `source.json` naming the original.

**Differential pairs.** KiCad's pair placer commits every fixed leg to the board immediately. It also cannot
fit a turn that starts right at a fixed point: straight legs and single-leg turns from a pad work, but a
continuation that changes direction fails in every mode. The router tool now flips posture automatically and
retries, which did not help for pairs. So `route_diff_pair` tries the placer first. If it does not reach the
end, it removes the placer's partial legs and routes both nets as single tracks along exact offset polylines
(centreline ± (width+gap)/2, mitred corners). It reports `method: pair_placer | offset_tracks`. Tested on the
USB pair: 0.2/0.15 mm, constant 0.35 mm pitch through five corners, DRC clean.

Other fixes in this round:
* The route reach check now reads the real head end. The pair placer's `CurrentEnd()` returns the cursor.
* An automatic posture flip retry (like the `/` key) runs when a waypoint is not reached.
* Zero-length stubs at snapped ends are removed.
* The `TuneLength` dry run no longer crashes (it used to cancel a half-built pattern).

## Phase 2 test (`test_phase2.py`)

The test runs on a fresh copy of the current board (2026-10-26, routed by the other session: 1590 tracks,
410 vias, 24 opens) and picks its targets from the live board:
* `route_track` closed the 5 short F.Cu opens at U7 (track end to pad); unconnected went from 24 to 19.
* The USB pair from U6 is now blocked by the new routing. The fallback reported it and left nothing behind.
* Tune and optimize dry runs, fan-out, stitching (262 spots), teardrops (342), islands, move-push, congestion,
  the height check and the schematic dry run (0 errors, 0 warnings) all ran.

DRC: 8 errors before and after (all pre-existing), no new copper items. Result: PASS.

**`collision_3d`** was run against `mech/freecad/BugBot_assembly.step` (2026-10-19; older than the current
placement, so treat the findings as a demo).
* The assembly still contains an older copy of the main board ("MainPCB", "PCBParts"), so pass
  `skip=["MainPCB*", "PCBParts*"]`.
* With that skip it takes 296 s for 141 board parts against 32 assembly parts.
* It found 11 overlaps:
  * BT1 against the cell and cradle (by design).
  * J1 and Q6 against the chassis (12.3 and 2.0 mm³).
  * L2, F1, J18 and Q3 against KickCap.
  * J6 against FrontBoard.
* It also found 15 gaps under 0.3 mm.
