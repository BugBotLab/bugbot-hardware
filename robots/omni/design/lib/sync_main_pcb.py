# Schematic -> PCB for the main board (KiCad's "Update PCB from schematic", scripted): regenerates BugBot_Main.kicad_sch
# (make_main_schematic.py), then in BugBot_Main.kicad_pcb gives every footprint its nets and its link to the schematic.
# Parts already on the board keep their place (and side); new ones are parked in rows to the right of the board, to be
# placed. Footprints that left the schematic are removed (the MCAD holes H* stay). The board is 6 layers (plan v2, 2026-10-25).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/sync_main_pcb.py
import os, shutil, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.join(HERE, "BugBot").replace("\\", "/")
src = open(os.path.join(HERE, "make_main_schematic.py"), encoding="utf-8").read()
exec(src)                                                     # builds D and writes the schematic (D.sym_uuid, D.pins)
B = os.environ.get("SYNC_BOARD") or f"{ROOTDIR}/schematics/Main/BugBot_Main.kicad_pcb"   # SYNC_BOARD: work on a copy
shutil.copy(B, B + ".before-sync")
board = pcbnew.LoadBoard(B)
if board.GetCopperLayerCount() != 6:
    board.SetCopperLayerCount(6)                               # routing plan v2 (2026-10-25): 6 layers
D.board, D.fps, D.partmap = board, {}, {p[0]: p for p in D.PARTS}
D.nets = {n: board.FindNet(n) for n in [str(k) for k in board.GetNetsByName().keys()] if n}

kept, added, removed = [], [], []
for f in list(board.GetFootprints()):
    ref = f.GetReference()
    if ref.startswith("H"):
        continue
    if ref not in D.partmap:
        board.Remove(f); removed.append(ref)
COLS, X0, Y0, DX, DY = 12, 60.0, 40.0, 7.0, -7.0              # parking grid, robot frame (right of the board)
k = 0
for ref, lid, val, fp, netmap, at, dnp in D.PARTS:
    f = board.FindFootprintByReference(ref)
    if f is not None and f.GetFPIDAsString() == fp:
        D.fps[ref] = f; kept.append(ref)
        f.SetPath(pcbnew.KIID_PATH(f"/{D.sym_uuid[ref]}")); f.SetValue(val)
        pj = D.JLC.get(ref)
        if pj:
            for key, v in zip(("MPN", "LCSC"), pj):
                f.SetField(key, v); fld = f.GetField(key); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
        for p in f.Pads():
            num = p.GetNumber()
            if (ref, num) in D.NC:
                p.SetNet(D.net(f"unconnected-({ref}-{D.pins[lid][num][3]}-Pad{num})"))
            elif num in netmap:
                p.SetNet(D.net(netmap[num]))
        continue
    if f is not None:                                         # footprint changed: replace it in the same place
        pos, rot, flipped = D.xy(f), f.GetOrientationDegrees(), f.IsFlipped()
        board.Remove(f)
        g = D.add_fp(ref, pos[0], pos[1], rot)
        if flipped:
            g.Flip(g.GetPosition(), False)
        kept.append(ref + "*")
        continue
    D.add_fp(ref, X0 + DX * (k % COLS), Y0 + DY * (k // COLS), 0); added.append(ref); k += 1
board.BuildConnectivity()
pcbnew.SaveBoard(B, board)
print(f"kept {len(kept)} {kept}\nadded {len(added)}\nremoved {removed}\nnets {board.GetNetCount()}  layers {board.GetCopperLayerCount()}")
