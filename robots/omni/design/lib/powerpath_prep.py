# Battery-path rework, step 2 (KiCad python; approved 2026-10-26): the J19 wire slot (3.5 x 2 mm, rounded ends, Edge.Cuts,
# robot (29.5, -19.5) = KiCad (129.5, 119.5); mech/freecad/j19_slot_path.py routes the solenoid lead through it) and the
# rip-up for the re-route: every track / via of the moved parts' nets, VSYS / GND pieces in the old power corner, and
# whatever crosses the slot. Pours and signal routing follow (powerpath_pours.py, rip_route.py).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/powerpath_prep.py [board]
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
K = lambda x, y: pcbnew.VECTOR2I(mm(100 + x), mm(100 - y))          # robot frame -> KiCad
EC = b.GetLayerID("Edge.Cuts")
# ---- the slot: two half circles r 1.0 joined by straight sides, 3.5 x 2.0 overall
SX, SY, HL, R = 29.5, -19.5, 0.75, 1.0
for d in list(b.GetDrawings()):                                     # re-runnable: drop an earlier slot
    if d.GetLayer() == EC and abs(tm(d.GetCenter().x) - (100 + SX)) < 2.5 and abs(tm(d.GetCenter().y) - (100 - SY)) < 2.0:
        b.Remove(d)
def seg(a, c):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(EC); s.SetWidth(mm(0.05)); s.SetStart(a); s.SetEnd(c); b.Add(s)
def arc(cx, start, mid, end):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(EC); s.SetWidth(mm(0.05)); s.SetArcGeometry(start, mid, end); b.Add(s)
seg(K(SX - HL, SY + R), K(SX + HL, SY + R)); seg(K(SX - HL, SY - R), K(SX + HL, SY - R))
arc(None, K(SX + HL, SY + R), K(SX + HL + R, SY), K(SX + HL, SY - R))
arc(None, K(SX - HL, SY - R), K(SX - HL - R, SY), K(SX - HL, SY + R))
# ---- rip
NETS = {"/BAT_P", "/BAT_F", "/VBAT_P", "/VBAT_SW", "/BAT_N", "/FS_D", "/DW_OD", "/DW_OC", "/DW_CS", "/DW_VCC", "/Q1_G", "/SW_G", "/Q2_G", "/VBAT_SENSE"}
def in_box(p, x0, y0, x1, y1):
    x, y = tm(p.x) - 100, 100 - tm(p.y); return x0 <= x <= x1 and y0 <= y <= y1
CORNER = (-34.0, -27.5, -3.0, -12.5)                                # old + new battery chain area (robot)
NORTH = (-36.0, 8.5, -26.0, 21.5)                                   # the protection pair's new spot
SLOT = (SX - 2.3, SY - 1.6, SX + 2.3, SY + 1.6)
kill = []
for t in b.GetTracks():
    n = t.GetNetname(); pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if n in NETS: kill.append(t); continue
    if n in ("/VSYS", "/GND") and any(in_box(p, *CORNER) or in_box(p, *NORTH) for p in pts): kill.append(t); continue
    if any(in_box(p, *SLOT) for p in pts): kill.append(t)
by = {}
for t in kill: by[t.GetNetname()] = by.get(t.GetNetname(), 0) + 1
for t in kill: b.Remove(t)
pcbnew.SaveBoard(B, b)
print("slot added at robot", (SX, SY), "| ripped", len(kill), by)
