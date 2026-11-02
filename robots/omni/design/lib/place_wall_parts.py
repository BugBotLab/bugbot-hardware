# The two parts that reach the chassis wall, on the main board's underside (approved 2026-10-24,
# mech/freecad/sketches/switch_usb_move_v1.png; clear of every part of all six styles by a sweep):
#   SW1  MSK12C02G25 power switch at 237 deg (Params sw_ang): handle tip at r 39.5, in the wall slot
#   J1   USB-C HRO TYPE-C-31-M-12 at 199 deg (Params usb_ang): mouth flush with the wall's outside (r 40.6)
# Robot frame: KiCad x = 100 + X, y = 100 - Y. Each part is turned so its pin row faces the board centre.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_wall_parts.py
import math, os, shutil, pcbnew

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
KF = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
# ref, lib, footprint, value, MPN, LCSC, angle, origin radius, pads of the inner row, their depth behind the origin
PARTS = [("SW1", BB + "/design/lib/BugBot.pretty", "BugBot:SW_MSK12C02G25_SMD", "Power (MSK12C02G25)",
          "MSK12C02G25-B", "C22435663", 237.0, 39.5 - 4.38, ("1", "2", "3"), 1.58),
         ("J1", BB + "/design/lib/BugBot.pretty", "BugBot:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "USB-C (program + bench power)",
          "TYPE-C-31-M-12", "C165948", 199.0, 40.6 - 3.65, ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
                                                            "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12"), 4.045)]
if not os.path.exists(B + ".before-wall-parts"):
    shutil.copy(B, B + ".before-wall-parts")
board = pcbnew.LoadBoard(B)


def robot(p):
    return pcbnew.ToMM(p.x) - 100, 100 - pcbnew.ToMM(p.y)


for ref, lib, fpid, val, mpn, lcsc, ang, r0, row, depth in PARTS:
    old = board.FindFootprintByReference(ref)
    if old:
        board.Remove(old)
    f = pcbnew.FootprintLoad(lib, fpid.split(":")[1])
    f.SetFPIDAsString(fpid); f.SetReference(ref); f.SetValue(val)
    for k, v in (("MPN", mpn), ("LCSC", lcsc)):
        f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
    board.Add(f)
    f.Flip(f.GetPosition(), False)                               # underside
    a = math.radians(ang)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100 + r0 * math.cos(a)), pcbnew.FromMM(100 - r0 * math.sin(a))))
    best = None
    for deg in range(360):
        f.SetOrientationDegrees(deg)
        pts = [robot(p.GetPosition()) for p in f.Pads() if p.GetNumber() in row]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        # the row's centre must sit on the ray, `depth` inside the origin (any tangential offset of the row is small)
        rad = cx * math.cos(a) + cy * math.sin(a); tan = -cx * math.sin(a) + cy * math.cos(a)
        err = abs(rad - (r0 - depth)) + abs(tan) * 0.2
        if best is None or err < best[0]:
            best = (err, deg)
    f.SetOrientationDegrees(best[1])
    print(f"{ref} at {ang} deg, r {r0:.2f}, rot {best[1]}, err {best[0]:.3f}, side {'B' if f.IsFlipped() else 'F'}")
pcbnew.SaveBoard(B, board)
