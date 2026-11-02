# Copies the 3D models of the main board's own-library parts (BugBot.pretty) from the board into the library footprints,
# so a schematic sync (sync_main_pcb.py) keeps them. Run after model_fit.py.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/model_to_library.py [board]
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
LIB = BB + "/design/lib/BugBot.pretty"
b = pcbnew.LoadBoard(B)
done = {}
for f in b.GetFootprints():
    fpid = f.GetFPIDAsString()
    if ":" not in fpid: continue                     # (MCAD holes etc. have no library)
    lib, name = fpid.split(":", 1)
    if lib != "BugBot" or name in done or f.GetReference() not in ("BZ1", "U4", "SW1", "SW2", "BT1", "U6"): continue
    lf = pcbnew.FootprintLoad(LIB, name)
    lf.Models().clear()
    for m in f.Models(): lf.Models().push_back(m)
    pcbnew.FootprintSave(LIB, lf); done[name] = f.GetReference()
print("library footprints updated:", done)
