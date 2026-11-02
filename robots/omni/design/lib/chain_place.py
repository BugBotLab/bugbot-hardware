# Battery-chain placer (KiCad python; 2026-10-26): F1 -> Q1 -> Q6 -> Q2 placed one after another, each at the nearest
# legal spot to the previous part (F1 to BT1's + pad), on either side (bottom preferred: top only if 2+ mm nearer), both
# turns tried. Legal = clear (0.15 mm) of same-side courtyards, every through-hole pin of the other side, the bottom-side
# plug lanes, M2 holes (2.8 mm) and the board edge; parts already placed by this run count as obstacles. Prints the spots
# (robot frame) for power_plan_positions.json; does not change the board.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/chain_place.py board
import math, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); tm = pcbnew.ToMM
MOVE = {"F1": (4.65, 2.35), "Q1": (4.29, 3.89), "Q6": (4.29, 3.89), "Q2": (4.29, 3.89)}
SKIP = set(MOVE) | {"R4", "R5", "R6", "R7", "R47"}
rob = lambda v: (tm(v.x) - 100, 100 - tm(v.y))
obst = {"B": [], "F": []}
for f in b.GetFootprints():
    if f.GetReference() in SKIP: continue
    fb = f.IsFlipped(); c = f.GetCourtyard(pcbnew.B_CrtYd if fb else pcbnew.F_CrtYd)
    if c.OutlineCount():
        bb = c.BBox(); obst["B" if fb else "F"].append((tm(bb.GetLeft()) - 100, 100 - tm(bb.GetBottom()), tm(bb.GetRight()) - 100, 100 - tm(bb.GetTop())))
    for p in f.Pads():
        if p.GetDrillSize().x > 0:
            r = tm(max(p.GetSize().x, p.GetSize().y)) / 2 + 0.25; x, y = rob(p.GetPosition())
            obst["F" if fb else "B"].append((x - r, y - r, x + r, y + r))
obst["B"] += [(-21.7, 1.6, -14.7, 6.8), (-21.7, -14.0, -14.7, -8.7), (-21.7, 8.4, -14.7, 13.6), (-21.7, -7.2, -14.7, 0.1), (-20.1, 15.75, -9.9, 22.75)]
obst["F"] += [(27.7, -20.6, 31.3, -18.4)]; obst["B"] += [(27.7, -20.6, 31.3, -18.4)]      # the J19 slot
holes = [rob(f.GetPosition()) for f in b.GetFootprints() if f.GetReference().startswith("H")]
def legal(side, bx):
    if any(bx[0] < o[2] + 0.15 and o[0] < bx[2] + 0.15 and bx[1] < o[3] + 0.15 and o[1] < bx[3] + 0.15 for o in obst[side]): return False
    if any(math.hypot(min(max(h[0], bx[0]), bx[2]) - h[0], min(max(h[1], bx[1]), bx[3]) - h[1]) < 2.8 for h in holes): return False
    return max(math.hypot(x, y) for x in (bx[0], bx[2]) for y in (bx[1], bx[3])) <= 39.6
prev = (-23.8, -18.91); out = {}
for ref, (W, H) in MOVE.items():
    best = {}
    for side in "BF":
        for i in range(-60, 61):
            for j in range(-60, 61):
                cx, cy = prev[0] + i * 0.25, prev[1] + j * 0.25
                for w, h in ((W, H), (H, W)):
                    bx = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                    # distance between the boxes' edges (parts sit side by side)
                    if not legal(side, bx): continue
                    d = math.hypot(cx - prev[0], cy - prev[1])
                    if side not in best or d < best[side][0]: best[side] = (d, cx, cy, w, h)
    side = "B" if "B" in best and ("F" not in best or best["B"][0] <= best["F"][0] + 2.0) else "F"
    d, cx, cy, w, h = best[side]
    out[ref] = (side, round(cx, 2), round(cy, 2), w, h)
    obst[side].append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)); prev = (cx, cy)
    print(f"{ref}: {side} at ({cx:.2f}, {cy:.2f}) {w}x{h}, {d:.1f} mm from the previous")
