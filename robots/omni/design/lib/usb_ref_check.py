# KiCad python: what the USB pair (B.Cu) has under it on In4: other-net tracks crossing it, and how much of the pair's
# length runs over In4 GND fill (refilled first).
import pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM; mm = pcbnew.FromMM
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pair = [t for t in b.GetTracks() if t.GetNetname() in ("/USB_DP", "/USB_DN") and t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.B_Cu]
gnd4 = [z for z in b.Zones() if z.GetLayer() == pcbnew.In4_Cu and z.GetNetname() == "/GND" and not z.GetIsRuleArea()]
fill = pcbnew.SHAPE_POLY_SET()
for z in gnd4: fill.Append(z.GetFilledPolysList(pcbnew.In4_Cu))
tot = over = 0.0; gaps = []
for t in pair:
    a, c = t.GetStart(), t.GetEnd(); L = tm((c - a).EuclideanNorm()); n = max(1, int(L / 0.1))
    for k in range(n):
        p = pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * (k + 0.5) / n), int(a.y + (c.y - a.y) * (k + 0.5) / n))
        tot += L / n; over += L / n if fill.Contains(p) else 0
        if not fill.Contains(p): gaps.append((round(tm(p.x), 1), round(tm(p.y), 1)))
cross = set()
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.In4_Cu:
        for q in pair:
            if t.GetEffectiveShape().Collide(q.GetEffectiveShape(), mm(0.3)): cross.add(t.GetNetname())
print(f"pair on B.Cu {tot:.1f} mm, over In4 GND fill {over:.1f} mm ({100 * over / tot:.0f}%); In4 tracks under it: {sorted(cross)}")
import itertools
runs = []
for g in gaps:
    if runs and abs(runs[-1][-1][0] - g[0]) < 0.3 and abs(runs[-1][-1][1] - g[1]) < 0.3: runs[-1].append(g)
    else: runs.append([g])
print("no GND under:", [(r[0], r[-1], len(r)) for r in runs if len(r) > 2])
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.In4_Cu and t.GetNetname() == "/M1_B":
        print("M1_B In4", round(tm(t.GetStart().x), 2), round(tm(t.GetStart().y), 2), "->", round(tm(t.GetEnd().x), 2), round(tm(t.GetEnd().y), 2), tm(t.GetWidth()))
