# J1 (USB-C) to U2's J1-side pins for D+ / D- (floor plan v3), placed by hand with the via spots from via_spot.py:
# D+ joins B6 / A6 round A7's east end, D- joins A7 / B7 round A6's west end (on B, tracks from the pad centres), a
# standard via each, then In2 (D+) / In3 (D-) round J1's shield pins to a via beside U2, and a stub onto U2's pin link.
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm = pcbnew.FromMM
def T(net, layer, pts, w=0.15):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(mm(w)); t.SetNet(b.FindNet(net))
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1))); b.Add(t)
def V(net, x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(b.FindNet(net)); b.Add(v)
DP, DN = "/USB_DP", "/USB_DN"
T(DP, pcbnew.B_Cu, [(68.644, 110.004), (69.66, 109.655), (69.985, 110.60), (68.969, 110.949)])
T(DP, pcbnew.B_Cu, [(69.8225, 110.1275), (70.6, 110.0)]); V(DP, 70.6, 110.0)
T(DP, pcbnew.In2_Cu, [(70.6, 110.0), (67.9, 105.4), (63.0, 103.5)]); V(DP, 63.0, 103.5); T(DP, pcbnew.B_Cu, [(63.0, 103.5), (63.55, 103.5)])
T(DN, pcbnew.B_Cu, [(68.806, 110.477), (67.79, 110.83), (68.116, 111.77), (69.132, 111.422)])
T(DN, pcbnew.B_Cu, [(67.953, 111.30), (67.4, 111.5)]); V(DN, 67.4, 111.5)
T(DN, pcbnew.In3_Cu, [(67.4, 111.5), (64.6, 108.0), (66.15, 103.5)]); V(DN, 66.15, 103.5); T(DN, pcbnew.B_Cu, [(66.15, 103.5), (65.45, 103.5)])
pcbnew.SaveBoard(B, b); print("J1 links placed")
