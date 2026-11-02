# BT1 on BugBot_Main: datasheet, part numbers and how it is fitted (the Keystone 1051 is bought and hand-soldered,
# not JLC-assembled: JLC/LCSC C238066 had 0 stock on 2026-10-23). Also sets the library footprint's datasheet.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/set_bt1_fields.py
import re
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
MOD = BB + "/design/lib/BugBot.pretty/BatteryHolder_Keystone_1051_1xCR123A.kicad_mod"
DS = "https://www.keyelco.com/userAssets/file/K75p27.pdf"
FIELDS = {
    "Datasheet": DS,
    "Description": "Keystone 1051 THM CR123A holder, 1 cell. Inside 34.67 mm between the end walls (drawing 1051 rev C): "
                   "CR123A / UNPROTECTED 16340 only (<= 34.5 mm); a protected 16340 (35.5-37.5 mm) does not fit",
    "MPN": "Keystone 1051",
    "LCSC": "C238066",
    "Fitting": "bought separately and hand-soldered (not JLC assembly)",
}
board = pcbnew.LoadBoard(B)
fp = board.FindFootprintByReference("BT1")
for k, v in FIELDS.items():
    fp.SetField(k, v)
    f = fp.GetField(k)
    if k not in ("Datasheet", "Description"):
        f.SetVisible(False)
board.Save(B)
print("BT1:", {k: fp.GetFieldText(k) for k in FIELDS})

s = open(MOD, encoding="utf-8").read()
s2 = re.sub(r'\(property "Datasheet" "[^"]*"', f'(property "Datasheet" "{DS}"', s, count=1)
if s2 != s:
    open(MOD, "w", encoding="utf-8").write(s2); print("library footprint datasheet set")
else:
    print("library footprint: no Datasheet property found (left as it is)")
