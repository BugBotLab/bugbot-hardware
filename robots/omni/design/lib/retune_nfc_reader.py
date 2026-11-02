# Retune the NFC reader board's antenna matching for the floor PCB loop (2026-10-23, design/lib/nfc_floor_calc.py):
# per side Cs 10 pF (C6, C12), Cp 47 + 47 pF (C8 + C9, C13 + C11). Edits values, MPN and LCSC in place on the board,
# the schematic and the JLC BOM (positions, footprints and routing untouched; make_nfc_boards.py has the same values).
#   C:/Python312/python.exe design/lib/retune_nfc_reader.py
import os
from part_swap import swap

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schematics", "retired", "NFC")
NEW = {"C6": ("10pF", "CL05C100JB5NNNC", "C32949"), "C12": ("10pF", "CL05C100JB5NNNC", "C32949"),
       "C8": ("47pF", "0402CG470J500NT", "C1567"), "C13": ("47pF", "0402CG470J500NT", "C1567"),
       "C9": ("47pF", "0402CG470J500NT", "C1567"), "C11": ("47pF", "0402CG470J500NT", "C1567")}

swap(D, "BugBot_NFC", NEW)
