# KiCad python: free spots for a through via of NET near X,Y (KiCad mm): clear of every other net's track / via / pad on
# all copper layers by the 0.15 rule and inside the board. Prints the nearest few.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/via_spot.py NET X Y [R] [board]
import sys, math, pcbnew
net, X, Y = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); R = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[5] if len(sys.argv) > 5 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
VR, CL = 0.225, 0.155
obst = []
for t in b.GetTracks():
    if t.GetNetname() == net: continue
    p, q = t.GetStart(), t.GetEnd()
    if math.hypot(tm(p.x) - X, tm(p.y) - Y) > R + 3 and math.hypot(tm(q.x) - X, tm(q.y) - Y) > R + 3: continue
    obst.append(("seg", tm(p.x), tm(p.y), tm(q.x), tm(q.y), tm(t.GetWidth()) / 2))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == net and p.GetNetname(): continue
        c = p.GetPosition()
        if math.hypot(tm(c.x) - X, tm(c.y) - Y) > R + 4: continue
        obst.append(("pad", p))
def dseg(x, y, a, b_, c, d):
    vx, vy = c - a, d - b_; L = vx * vx + vy * vy
    u = 0 if L == 0 else max(0, min(1, ((x - a) * vx + (y - b_) * vy) / L))
    return math.hypot(x - a - u * vx, y - b_ - u * vy)
out = []
n = int(R / 0.05)
for i in range(-n, n + 1):
    for j in range(-n, n + 1):
        x, y = X + i * 0.05, Y + j * 0.05
        if math.hypot(i, j) * 0.05 > R: continue
        ok = True
        for o in obst:
            if o[0] == "seg":
                if dseg(x, y, *o[1:5]) < o[5] + VR + CL: ok = False; break
            else:
                sh = o[1].GetEffectiveShape(pcbnew.F_Cu if o[1].IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
                if sh.Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(VR + CL)): ok = False; break
        if ok: out.append((math.hypot(x - X, y - Y), round(x, 2), round(y, 2)))
print(sorted(out)[:5])
