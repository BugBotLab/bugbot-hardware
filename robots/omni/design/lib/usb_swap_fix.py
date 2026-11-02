# The D+ / D- swap at the module end, placed by hand between J22's top-side pads (floor plan v3): D- leaves its B line at
# x 114.4, steps to a via at (115.1, 74.85), runs on In2 under D+ to a via at (115.6, 73.1), and reaches pad 48 on B.
# Removes the first try (vias under J22's pads) and its GND return vias. KiCad mm.
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
R = lambda p: (tm(p.x), tm(p.y))
inbox = lambda p: 114.3 < p[0] < 117.6 and 72.7 < p[1] < 75.4
gone = []
for t in b.GetTracks():
    n = t.GetNetname()
    if t.GetClass() == "PCB_VIA":
        if n in ("/USB_DN", "/GND") and inbox(R(t.GetPosition())) and R(t.GetPosition())[0] > 115.9: gone.append(t)
    elif n == "/USB_DN" and (inbox(R(t.GetStart())) or inbox(R(t.GetEnd()))): gone.append(t)
for t in gone: b.Remove(t)
net = b.FindNet("/USB_DN")
def T(layer, pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(mm(0.15)); t.SetNet(net)
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1))); b.Add(t)
def V(x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(net); b.Add(v)
T(pcbnew.B_Cu, [(111.772487, 74.175), (114.4, 74.175), (115.075, 74.85), (115.1, 74.85)])
V(115.1, 74.85); T(pcbnew.In2_Cu, [(115.1, 74.85), (115.6, 73.1)]); V(115.6, 73.1)   # spots from via_spot.py
pad48 = next(p for p in b.FindFootprintByReference("U6").Pads() if p.GetNumber() == "48")
T(pcbnew.B_Cu, [(115.6, 73.1), (115.95, 73.45), R(pad48.GetPosition())])
pcbnew.SaveBoard(B, b); print("removed", len(gone), "pieces; swap re-placed")
