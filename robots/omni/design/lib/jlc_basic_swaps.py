# Swap Extended JLC parts for Basic ones where nothing else changes (2026-10-31, business/BugBot_kit_costs.md): each
# Extended type costs $3 per order in feeder loading. In place on the board, the schematic and the JLC BOM
# (make_main_schematic.py, make_nfc_boards.py and nfc_design.py carry the same parts).
#   C:/Python312/python.exe design/lib/jlc_basic_swaps.py
import os
from part_swap import swap

K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# NFC matching Cs: same 10 pF C0G 0402, Basic maker
swap(os.path.join(K, "schematics", "retired", "NFC"), "BugBot_NFC",
     {"C6": ("10pF", "CL05C100JB5NNNC", "C32949"), "C12": ("10pF", "CL05C100JB5NNNC", "C32949")})
# Main: 5 V boost feed-forward 220 pF C0G -> X7R (Basic); kicker bleed 47k -> 100k 1206 (Basic: ~50 s to < 5 V)
swap(os.path.join(K, "schematics", "Main"), "BugBot_Main",
     {"C13": ("220pF", "0402B221K500NT", "C1530"), "R35": ("100k 1206 (bleed)", "1206W4F1003T5E", "C17900")})
