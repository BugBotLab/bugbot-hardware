# Power switch v3 (approved 2026-10-25, mech/freecad/sketches/power_switch_v3.png), KiCad python: puts SW1 (C&K
# OS102011MA1QN1, right-angle) under the board at 231 deg, slider pointing straight out through the wall with its tip
# 0.3 mm inside the wall's outer face (r 40.3); nudges Q6 0.25 mm clear; removes the old switch's tracks and vias
# (SW_ON / GND ends left on the old pads' spots). The new SW_ON / GND links are routed afterwards.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_sw1_v3.py
import math, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
ANG, R_TIP = 235.5, 40.3                                  # (233 with the power corner re-placed; 235.5 so its tab clears H3: the slider itself lands at 234.0, the wall slot sw_ang follows it)
Q6_MOVE = (0.0, 0.0)                                     # (Q6 now placed with the power corner: placement_sw1.json)
mm, tm = pcbnew.FromMM, pcbnew.ToMM
b = pcbnew.LoadBoard(B)
f = b.FindFootprintByReference("SW1")
old_box = f.GetBoundingBox(False)                         # (the swapped footprint still sits where the old one was)
old_box.Inflate(mm(1.5))
q6 = b.FindFootprintByReference("Q6")
q6_old = {p.GetNumber(): p.GetPosition() for p in q6.Pads()}

# old switch copper: tracks / vias of SW_ON and GND with an end in the old switch's area (not the pours)
kill = {}
for t in b.GetTracks():
    if t.GetNetname() not in ("/SW_ON", "/GND"): continue
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if any(old_box.Contains(p) for p in pts): kill[t.m_Uuid.AsString()] = t

if not f.IsFlipped(): f.Flip(f.GetPosition(), False)
n = (math.cos(math.radians(ANG)), math.sin(math.radians(ANG)))
best = None
fab = [g for g in f.GraphicalItems() if g.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab) and g.GetClass() == "PCB_SHAPE"]
for rot in [k / 2 for k in range(720)]:                   # the turn whose slider points straight out
    f.SetOrientationDegrees(rot)
    cen = next(p for p in f.Pads() if p.GetNumber() == "2").GetPosition()        # body centre line (middle pin)
    # the slider's tip line: the Fab segment farthest from the middle pin (measured on the board, flip and turn included)
    tipg = max(fab, key=lambda g: math.hypot(g.GetBoundingBox().GetCenter().x - cen.x, g.GetBoundingBox().GetCenter().y - cen.y))
    tp = tipg.GetBoundingBox().GetCenter()
    p1 = next(p for p in f.Pads() if p.GetNumber() == "1").GetPosition(); p3 = next(p for p in f.Pads() if p.GetNumber() == "3").GetPosition()
    rx, ry = tm(p3.x - p1.x), -tm(p3.y - p1.y)            # pin row, robot frame (y up)
    nx, ny = -ry, rx                                      # its normal, turned to the slider's side
    if nx * tm(tp.x - cen.x) - ny * tm(tp.y - cen.y) < 0: nx, ny = -nx, -ny
    L = math.hypot(nx, ny); score = (nx * n[0] + ny * n[1]) / L
    if best is None or score > best[0]:
        o = f.GetPosition(); best = (score, rot, (tm(tp.x - o.x), tm(tp.y - o.y)), None)
score, rot, tip, cen = best
f.SetOrientationDegrees(rot)
# slider tip at r 40.3 along 231 deg: footprint origin = target tip - tip offset (robot -> KiCad: x = 100 + X, y = 100 - Y)
tx, ty = R_TIP * n[0], R_TIP * n[1]
f.SetPosition(pcbnew.VECTOR2I(mm(100 + tx - tip[0]), mm(100 - ty - tip[1])))
q6.SetPosition(q6.GetPosition() + pcbnew.VECTOR2I(mm(Q6_MOVE[0]), mm(-Q6_MOVE[1])))
for t in kill.values(): b.Remove(t)
pcbnew.SaveBoard(B, b)
c = f.GetPosition()
print(f"SW1: bottom side, turn {rot} (alignment {score:.3f}), origin robot ({tm(c.x) - 100:.2f}, {100 - tm(c.y):.2f}); "
      f"removed {len(kill)} old SW_ON / GND tracks / vias; Q6 moved {math.hypot(*Q6_MOVE):.2f} mm")
for p in f.Pads(): print("  pad", p.GetNumber() or "tab", p.GetNetname(), round(tm(p.GetPosition().x) - 100, 2), round(100 - tm(p.GetPosition().y), 2))
