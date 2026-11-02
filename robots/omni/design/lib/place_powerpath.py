# Battery-path rework, placement (KiCad python; approved 2026-10-26, design/schematics/Main/power_path_v1.png): puts the moved
# parts at the clash-checked positions (_work/power_plan_positions.json, robot frame: kicad x = 100 + x, y = 100 - y), on
# the bottom side, and turns each power part so its pins face the way the chain runs (the rotation whose pads score best):
#   (chain from chain_place.py: F1 west of BT1+, then Q1, Q6, Q2 eastward) F1 BAT_P north, BAT_F south; Q1 drain toward
#   the BAT_F corridor under the + pad; Q6 source toward Q1, drain toward Q2; Q2 drain toward Q6, source south to the VSYS
#   vias; Q3 (AO8810) S1 toward BT1-, S2 west to its GND vias.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_powerpath.py [board]
import json, math, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
P = json.load(open(BB + "/design/schematics/Main/_work/power_plan_positions.json"))
b = pcbnew.LoadBoard(B); mm, tm = pcbnew.FromMM, pcbnew.ToMM
rob = lambda v: (tm(v.x) - 100, 100 - tm(v.y))
# pad number -> robot-frame point it should be nearest to (a score of distances: lower is better)
AIM = {"F1": {"1": (-26.55, -15.0), "2": (-26.55, -23.0)},          # BAT_P north (toward the + pad's side), BAT_F south
       "Q1": {"3": (-22.5, -21.6), "2": (-16.05, -18.91)},           # drain to the BAT_F corridor under the + pad
       "Q6": {"2": (-20.3, -18.91), "3": (-11.8, -20.66)},
       "Q2": {"3": (-16.05, -18.91), "2": (-11.8, -25.0)},           # source south, to the VSYS vias
       "Q3": {"1": (-23.8, 18.9), "3": (-36.0, 17.0)},
       "U1": {"1": (-30.3, 16.9), "3": (-30.3, 16.9)}}
ROT = {"R47": 0, "R6": 90, "R7": 90, "R4": 90, "R5": 90, "C1": 0, "R2": 0, "R3": 0}
ONLY = {"F1": (90, 270), "Q3": (0, 180)}                  # F1 upright (the 1206 courtyard is 4.65 long); Q3 laid wide
for ref, v in P.items():
    if ref.startswith("_"): continue                      # via arrays: placed with the pours
    x, y, w, h = v
    f = b.FindFootprintByReference(ref)
    if f is None: continue                                 # via arrays are not parts
    if not f.IsFlipped(): f.Flip(f.GetPosition(), False)   # everything here goes on the bottom
    f.SetPosition(pcbnew.VECTOR2I(mm(100 + x), mm(100 - y)))
    if ref in AIM:
        best = None
        for r in ONLY.get(ref, (0, 90, 180, 270)):
            f.SetOrientationDegrees(r)
            score = 0.0
            for num, aim in AIM[ref].items():
                ps = [rob(p.GetPosition()) for p in f.Pads() if p.GetNumber() == num]
                cx, cy = sum(q[0] for q in ps) / len(ps), sum(q[1] for q in ps) / len(ps)
                score += math.hypot(cx - aim[0], cy - aim[1])
            if best is None or score < best[0]: best = (score, r)
        f.SetOrientationDegrees(best[1])
    else:
        f.SetOrientationDegrees(ROT.get(ref, 0))
    print(f"{ref:4s} at robot ({x:6.1f}, {y:6.1f}) rot {f.GetOrientationDegrees():5.0f}")
pcbnew.SaveBoard(B, b)
