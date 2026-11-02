# FusionFlow <-> KiCad, KiCad side. Runs in KiCad's own Python ("C:/Program Files/KiCad/10.0/bin/python.exe").
#   ff_kicad.py push   <board.kicad_pcb> <mcad.json>   board outline (Edge.Cuts), mounting holes and keep-outs from FreeCAD
#   ff_kicad.py create <board.kicad_pcb> <mcad.json>   new, empty board with the same (components are KiCad's: never placed here)
# Coordinates: robot (x, y) mm -> KiCad (ORIGIN_X + x, ORIGIN_Y - y); the grid / aux origin sits on the robot origin,
# so a STEP export "--grid-origin" comes back in robot coordinates.
import json, os, sys
import pcbnew
DEBUG = os.environ.get("FF_DEBUG")
log = (lambda *a: print(*a, file=sys.stderr, flush=True)) if DEBUG else (lambda *a: None)

ORIGIN = (100.0, 100.0)
STD = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
HERE = os.path.dirname(os.path.abspath(__file__))
LIBS = {"BugBot": os.path.join(HERE, "lib", "BugBot.pretty")}
HOLE_TAG = "MCAD hole"                        # Value of the mounting-hole footprints FreeCAD owns


def P(x, y):
    return pcbnew.VECTOR2I_MM(ORIGIN[0] + x, ORIGIN[1] - y)


def load_fp(libname):
    lib, name = libname.split(":")
    return pcbnew.FootprintLoad(LIBS.get(lib, os.path.join(STD, lib + ".pretty")), name)


def push(board, mcad):
    """Replace the board outline and the FreeCAD-owned mounting holes; everything else is left alone."""
    old = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    old += [fp for fp in board.GetFootprints() if fp.GetValue().startswith(HOLE_TAG)]
    log("removing", len(old))
    for item in old:
        board.Delete(item)            # (Remove() hands the item to Python, which then crashes pcbnew)
    for e in mcad["outline"]:
        s = pcbnew.PCB_SHAPE(board)
        if "arc" in e:
            a, m, b = e["arc"]
            s.SetShape(pcbnew.SHAPE_T_ARC); s.SetArcGeometry(P(*a), P(*m), P(*b))
        else:
            a, b = e["line"]
            s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(P(*a)); s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)
    log("outline done")
    for k, h in enumerate(mcad["holes"], 1):
        fp = load_fp("MountingHole:MountingHole_2.2mm_M2" if h["d"] < 3 else "MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(f"H{k}"); fp.SetValue(f"{HOLE_TAG} d={h['d']:.2f}")
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)     # no silkscreen for FreeCAD's holes
        for pad in fp.Pads():
            pad.SetDrillSize(pcbnew.VECTOR2I_MM(h["d"], h["d"])); pad.SetSize(pcbnew.VECTOR2I_MM(h["d"], h["d"]))
        fp.SetPosition(P(*h["at"]))
        board.Add(fp)
    if "keepouts" in mcad:
        keepouts(board, mcad["keepouts"])
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(pcbnew.FromMM(mcad.get("thickness", 1.6)))
    ds.SetAuxOrigin(P(0, 0)); ds.SetGridOrigin(P(0, 0))


MCAD_LAYER = pcbnew.User_1          # owned by FreeCAD: every MCAD outline + label lives here


def keepouts(board, kos):
    """Where mechanical parts touch the board (from FreeCAD): a rule area that keeps footprints out (KiCad's DRC
    enforces it), plus its outline and the part's name on the MCAD layer."""
    board.SetLayerName(MCAD_LAYER, "MCAD")
    old = [z for z in board.Zones() if z.GetZoneName().startswith("MCAD")]
    old += [d for d in board.GetDrawings() if d.GetLayer() == MCAD_LAYER]
    for item in old:
        board.Delete(item)
    for k in kos:
        pts = [P(x, y) for x, y in k["polygon"]]
        side = "top" if k["side"] == "F" else "bottom"
        if k["gap"] == 0:
            z = pcbnew.ZONE(board)
            z.SetIsRuleArea(True); z.SetDoNotAllowFootprints(True)
            z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False)
            z.SetLayer(pcbnew.F_Cu if k["side"] == "F" else pcbnew.B_Cu)
            z.SetZoneName(f"MCAD keepout {side}: {k['name']}")
            ol = z.Outline(); ol.NewOutline()
            for q in pts:
                ol.Append(q.x, q.y)
            for hp in k.get("holes", []):          # voids, e.g. round a mounting hole the part stands all round
                h = ol.NewHole()
                for x, y in hp:
                    q = P(x, y); ol.Append(q.x, q.y, 0, h)
            board.Add(z)
        for poly in [pts] + [[P(x, y) for x, y in hp] for hp in k.get("holes", [])]:
            s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetPolyPoints(poly)
            s.SetLayer(MCAD_LAYER); s.SetWidth(pcbnew.FromMM(0.08)); board.Add(s)
        cx = sum(x for x, y in k["polygon"]) / len(k["polygon"]); cy = sum(y for x, y in k["polygon"]) / len(k["polygon"])
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText((f"KEEP-OUT {side}" if k["gap"] == 0 else f"{side}: max {k['gap']:.1f} mm") + " | " + k["name"].split("/")[-1])
        tx.SetPosition(P(cx, cy)); tx.SetLayer(MCAD_LAYER)
        tx.SetTextSize(pcbnew.VECTOR2I_MM(0.6, 0.6)); tx.SetTextThickness(pcbnew.FromMM(0.08))
        board.Add(tx)
    log("keepouts", len(kos))


def project_files(path, lib=None):
    """The project around a board: .kicad_pro, an empty .kicad_sch, and (optionally) a footprint library table."""
    import uuid
    d, base = os.path.split(path); name = os.path.splitext(base)[0]
    pro = os.path.join(d, name + ".kicad_pro")
    if not os.path.exists(pro):
        json.dump({"meta": {"filename": name + ".kicad_pro", "version": 1}}, open(pro, "w"))
    sch = os.path.join(d, name + ".kicad_sch")
    if not os.path.exists(sch):              # an empty schematic, so the project manager shows both editors
        open(sch, "w").write(SCH.format(uuid=uuid.uuid4()))
    lt = os.path.join(d, "fp-lib-table")
    if lib and not os.path.exists(lt):
        open(lt, "w").write(LIBT.format(name=lib[0], uri=lib[1]))


SCH = """(kicad_sch
  (version 20231120)
  (generator "fusionflow")
  (uuid "{uuid}")
  (paper "A4")
  (lib_symbols)
  (sheet_instances (path "/" (page "1")))
)
"""
LIBT = """(fp_lib_table
  (version 7)
  (lib (name "{name}")(type "KiCad")(uri "{uri}")(options "")(descr ""))
)
"""


if __name__ == "__main__":
    cmd, path, mcad = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    if cmd == "create":
        board = pcbnew.BOARD()          # (pcbnew.NewBoard needs the GUI settings manager and crashes headless)
        push(board, mcad)
        project_files(path)
    else:
        board = pcbnew.LoadBoard(path)
        push(board, mcad)
    pcbnew.SaveBoard(path, board)
    print(json.dumps({"ok": True, "footprints": len(board.GetFootprints()),
                      "outline": len([d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts])}))
