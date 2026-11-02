# SW1 on the main board: the power switch, XKB SS-12D11G5R (approved 2D: mech/freecad/sketches/power_switch_v1.png), on the
# underside at the wall slot (Params sw_ang 237 deg): knob tip at r 37.9 (0.9 inside the wall), body centre at r 29.75, the
# pins at r 22.1 and the case tabs at r 31.3. Robot frame: KiCad x = 100 + X, y = 100 - Y.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/add_sw1.py
import math, shutil, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
import os
ANG, R_BODY = math.radians(float(os.environ.get("SW_ANG", "237"))), 29.75
R_TABS = R_BODY + 3.15 - 1.58                                    # 1.58 inside the front face
R_PINS = R_TABS - 9.2
if not os.path.exists(B + ".before-sw1"):
    shutil.copy(B, B + ".before-sw1")
board = pcbnew.LoadBoard(B)
old = board.FindFootprintByReference("SW1")
if old:
    board.Remove(old)
f = pcbnew.FootprintLoad(BB + "/design/lib/BugBot.pretty", "SW_XKB_SS-12D11G5R_RA")
f.SetFPIDAsString("BugBot:SW_XKB_SS-12D11G5R_RA")
f.SetReference("SW1"); f.SetValue("Power (SS-12D11G5R)")
for k, v in (("MPN", "SS-12D11G5R"), ("LCSC", "C388633")):
    f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
board.Add(f)
f.Flip(f.GetPosition(), False)                                   # to the underside
X, Y = R_BODY * math.cos(ANG), R_BODY * math.sin(ANG)
f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + X), pcbnew.FromMM(100 - Y)))
def robot(p):
    return pcbnew.ToMM(p.x) - 100, 100 - pcbnew.ToMM(p.y)
best = None
for deg in range(0, 360):                                        # the turn that puts the pins (pad 2) inboard on the ray
    f.SetOrientationDegrees(deg)
    px, py = robot(next(p for p in f.Pads() if p.GetNumber() == "2").GetPosition())
    err = math.hypot(px - R_PINS * math.cos(ANG), py - R_PINS * math.sin(ANG))
    if best is None or err < best[0]:
        best = (err, deg)
f.SetOrientationDegrees(best[1])
pcbnew.SaveBoard(B, board)
pads = {p.GetNumber() or "tab": robot(p.GetPosition()) for p in f.Pads()}
print("SW1 rot", best[1], "err", round(best[0], 3), "side", "B" if f.IsFlipped() else "F")
for n, (x, y) in sorted(pads.items()):
    print(f"  pad {n}: r {math.hypot(x, y):.2f}  ang {math.degrees(math.atan2(y, x)) % 360:.1f}")
