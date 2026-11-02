# U7 (TCA9535) left corner rebuilt by hand (user, 2026-10-26: "not cleaned, not connected smoothly"; "should be a star
# ground"): pins 2 / 3 (address straps to GND) run straight out, then 45 deg into ONE plane via between them (a star);
# DRV_nSLEEP / DRV_nFAULT come in on 45-deg lines that end level with their pads, then one straight piece to the centre.
# The old GND fragments and both old vias in the corner go. Board coords mm.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/fix_u7_corner.py [board]
import sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
P = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
inb = lambda p: 96.0 <= tm(p.x) <= 100.3 and 130.6 <= tm(p.y) <= 134.0
F = b.GetLayerID("F.Cu")
kill = [t for t in b.GetTracks() if t.GetNetname() in ("/GND", "/DRV_nSLEEP", "/DRV_nFAULT") and (inb(t.GetStart()) or inb(t.GetEnd()))
        and not (t.GetClass() == "PCB_VIA" and t.GetNetname() == "/DRV_nFAULT")
        and not (t.GetNetname() == "/DRV_nFAULT" and t.GetLayer() != F)]
nets = {n: b.FindNet(n) for n in ("/GND", "/DRV_nSLEEP", "/DRV_nFAULT")}
for t in kill: b.Remove(t)


def track(net, pts, w):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(F); t.SetNet(nets[net]); t.SetWidth(mm(w)); t.SetStart(P(*a)); t.SetEnd(P(*c)); b.Add(t)


VX, VY = 98.40, 131.95                                  # the star point: one GND via to the planes
v = pcbnew.PCB_VIA(b); v.SetPosition(P(VX, VY)); v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(nets["/GND"]); b.Add(v)
track("/GND", [(99.688, 131.625), (VX + 0.325, 131.625), (VX, VY)], 0.3)
track("/GND", [(99.688, 132.275), (VX + 0.325, 132.275), (VX, VY)], 0.3)
track("/DRV_nSLEEP", [(92.2, 127.45), (97.675, 132.925), (99.688, 132.925)], 0.2)
track("/DRV_nFAULT", [(96.55, 132.55), (97.575, 133.575), (99.688, 133.575)], 0.2)
pcbnew.SaveBoard(B, b)
print("U7 corner: removed", len(kill), "old pieces / vias; star GND via at", (VX, VY))
