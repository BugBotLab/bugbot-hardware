# J1 (USB-C, one row of pads) to U2 for D+ / D- (floor plan v3): each pair of same-net pads joined round the pad between
# them at their tips (D+ at the east tips round A7, D- at the west tips round A6), a standard via just past the row, then
# an inner layer to a via in U2's J1-side pin. Tracks start at the pad centres. KiCad mm.
import math, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
J1 = b.FindFootprintByReference("J1"); U2 = b.FindFootprintByReference("U2")
pad = lambda f, n: next(p for p in f.Pads() if p.GetNumber() == n)
P = lambda p: (tm(p.GetPosition().x), tm(p.GetPosition().y))
b6, a6, a7, b7 = (P(pad(J1, n)) for n in ("B6", "A6", "A7", "B7"))
row = ((a6[0] - b6[0]) / 1.0, (a6[1] - b6[1]) / 1.0); rl = math.hypot(*row); row = (row[0] / rl, row[1] / rl)
ax = (row[1], -row[0])                                           # along the pads, toward the east tips
if ax[0] < 0: ax = (-ax[0], -ax[1])
def T(net, layer, pts, w=0.15):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(mm(w)); t.SetNet(b.FindNet(net))
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1))); b.Add(t)
def V(net, x, y, d=0.45, dr=0.2):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(d)); v.SetDrill(mm(dr)); v.SetNet(b.FindNet(net)); b.Add(v)
out = lambda c, s, e=1.075: (c[0] + s * ax[0] * e, c[1] + s * ax[1] * e)
for net, p1, p2, s, upin, layer, way in (("/USB_DP", b6, a6, +1, "6", pcbnew.In2_Cu, [(68.5, 105.6)]),
                                         ("/USB_DN", a7, b7, -1, "4", pcbnew.In3_Cu, [(65.0, 109.5)])):
    o1, o2 = out(p1, s), out(p2, s)
    T(net, pcbnew.B_Cu, [p1, o1, o2, p2])
    m = ((o1[0] + o2[0]) / 2, (o1[1] + o2[1]) / 2); vp = (m[0] + s * ax[0] * 0.5, m[1] + s * ax[1] * 0.5)
    T(net, pcbnew.B_Cu, [m, vp]); V(net, *vp)
    u = P(pad(U2, upin)); V(net, *u)
    T(net, layer, [vp] + way + [u])
    print(net, "tips joined, via at", [round(c, 2) for c in vp], "inner run to U2.", upin)
pcbnew.SaveBoard(B, b)
