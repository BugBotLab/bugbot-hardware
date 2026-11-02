# The NFC reader board's mounting hole (approved 2D: mech/freecad/sketches/nfc_screw_v2.png): one M2 (2.2 mm, NPTH) at
# (25.0, 3.0) from the board's corner = the board centre (100, 100) + (11.0, -6.0); an M2x8 from the top through it and the
# tray into the chassis post under it replaces the tray's snap clips. 1.9 mm of board to the edges; nothing within 3.8.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/add_nfc_reader_hole.py
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/retired/NFC/BugBot_NFC.kicad_pcb"
LIB = "C:/Program Files/KiCad/10.0/share/kicad/footprints/MountingHole.pretty"
board = pcbnew.LoadBoard(B)
old = board.FindFootprintByReference("H1")
if old is not None:
    board.Delete(old)
fp = pcbnew.FootprintLoad(LIB, "MountingHole_2.2mm_M2")
fp.SetParent(board)
fp.SetReference("H1"); fp.SetValue("M2 (NFC tray post 1)")
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(111.0), pcbnew.FromMM(94.0)))
fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_2.2mm_M2"))
fp.Reference().SetVisible(False)
board.Add(fp)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(B)
print("H1 at", [round(pcbnew.ToMM(v), 2) for v in (fp.GetPosition().x, fp.GetPosition().y)], "pads", [p.GetAttribute() for p in fp.Pads()])
