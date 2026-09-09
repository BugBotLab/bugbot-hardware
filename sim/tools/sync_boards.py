"""Refresh boards/<board>/ from the KiCad projects.

    python tools/sync_boards.py            (BUGBOT_HW env or the default Bugbot Final path)

Copies golden_netlist.xml, every .kicad_sch, and the exported sheet SVGs
(from <project>/sim_sheets/ if present, else re-exports them with kicad-cli).
Run it after any schematic change, then re-run the simulations.
"""
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import BOARDS, HW_DIRS, ROOT_SCH, kicad_file

KICAD_CLI = kicad_file(r"bin\kicad-cli.exe")

for bd, src in HW_DIRS.items():
    dst = BOARDS[bd]
    os.makedirs(os.path.join(dst, "sheets"), exist_ok=True)
    files = [os.path.join(src, "golden_netlist.xml")] + glob.glob(os.path.join(src, "*.kicad_sch"))
    for f in files:
        shutil.copy2(f, dst)
    print("%s: %d files from %s" % (bd, len(files), src))
    if KICAD_CLI:
        r = subprocess.run([KICAD_CLI, "sch", "export", "svg", "--no-background-color", "--exclude-drawing-sheet",
                            "-o", os.path.join(dst, "sheets"), os.path.join(src, ROOT_SCH[bd])],
                           capture_output=True, text=True)
        print("  sheets:", "exported" if r.returncode == 0 else r.stderr.strip()[:200])
