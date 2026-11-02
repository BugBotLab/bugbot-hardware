# The solenoid lead's path through a board slot to J19 (plain Python, cable_grid.py): A* below the board from the
# solenoid's leads to under the slot, straight up through it, then A* above the board to J19's plug. -> _cables/j19_slot_path.json
#   C:/Python312/python.exe mech/freecad/j19_slot_path.py [slot_x slot_y]
import heapq, json, math, sys
import numpy as np
from cable_grid import D, S, H, LO, N, occ, dist, cell, centre
SX, SY = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (29.5, -19.5)
PZ, PT = S["pcb_z"], S["pcb_top"]
s, ds, e, de = (np.array(v) for v in S["cables"]["SolenoidCable"][:4])
R = 0.8
for z in np.arange(PZ - 0.5, PT + 0.6, H):                       # cut the slot (3.5 x 2 mm) through the board
    a = cell([SX - 1.75, SY - 1.0, z]); b = cell([SX + 1.75, SY + 1.0, z])
    occ[a[0]:b[0] + 1, a[1]:b[1] + 1, a[2]] = False
from scipy.ndimage import distance_transform_edt
dist = distance_transform_edt(~occ) * H
NB = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dy, dz) != (0, 0, 0)]


def astar(a, b, need, opened):
    g = {a: 0.0}; came = {}; pq = [(0.0, a)]; bb = np.array(b)
    while pq:
        f, c = heapq.heappop(pq)
        if c == b:
            p = [c]
            while c in came: c = came[c]; p.append(c)
            return p[::-1]
        for dx, dy, dz in NB:
            n = (c[0] + dx, c[1] + dy, c[2] + dz)
            if not (0 <= n[0] < N[0] and 0 <= n[1] < N[1] and 0 <= n[2] < N[2]): continue
            if dist[n] < need and n not in opened: continue
            ng = g[c] + math.sqrt(dx * dx + dy * dy + dz * dz) * H * (1 + 0.6 / max(dist[n], 0.3))
            if ng < g.get(n, 1e18): g[n] = ng; came[n] = c; heapq.heappush(pq, (ng + np.linalg.norm(np.array(n) - bb) * H, n))
    return None


def ball(p, r):
    c = np.array(cell(p)); k = int(math.ceil(r / H))
    return {(c[0] + i, c[1] + j, c[2] + l) for i in range(-k, k + 1) for j in range(-k, k + 1) for l in range(-k, k + 1) if i * i + j * j + l * l <= k * k}


below, above = np.array([SX, SY, PZ - 2.0]), np.array([SX, SY, PT + 2.0])
op = ball(s, 3.5) | ball(s + ds * 3, 2) | ball(e, 3.5) | ball(e - de * 3, 2) | ball(below, 1.2) | ball(above, 1.2)
p1 = astar(cell(s + ds * 3), cell(below), R + 0.3, op)
p2 = astar(cell(above), cell(e - de * 3), R + 0.3, op)
pts = [s.tolist()] + [centre(c).tolist() for c in (p1 or [])] + [centre(c).tolist() for c in (p2 or [])] + [e.tolist()]
L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
json.dump({"slot": [SX, SY], "points": pts, "length_mm": round(L, 1), "ok": bool(p1 and p2)}, open(D + "j19_slot_path.json", "w"))
print("slot", (SX, SY), "path ok" if p1 and p2 else "NO PATH", f"{L:.1f} mm")
