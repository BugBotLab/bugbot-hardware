# Cable routing, step 2 of 3 (plain Python: C:/Python312/python.exe): the obstacle meshes from export_cable_scene.py are
# voxelised (0.5 mm, surfaces sampled at 0.2 mm), a distance-to-obstacle field is computed, and each cable gets the
# shortest path with A* (26 neighbours) through cells that keep its radius + 0.8 mm clear (0.5 / 0.3 if that finds no
# way), slightly preferring more room, never outside the body; the path is then shortcut where a straight line stays
# clear. -> _cables/paths.json (waypoints, length, clearance). The voxel grid comes from cable_grid.py.
#   C:/Python312/python.exe mech/freecad/route_cables.py
import heapq, json, math
import numpy as np
from scipy.ndimage import distance_transform_edt
from cable_grid import D, S, H, LO, HI, N, occ, dist, cell, centre
NB = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dy, dz) != (0, 0, 0)]
NBL = [math.sqrt(dx * dx + dy * dy + dz * dz) * H for dx, dy, dz in NB]


def astar(a, b, need, opened):
    """opened: cells near the two ends that are allowed whatever their clearance (the connector / terminal itself)"""
    ok = lambda c: 0 <= c[0] < N[0] and 0 <= c[1] < N[1] and 0 <= c[2] < N[2] and (dist[c] >= need or c in opened)
    g = {a: 0.0}; came = {}; pq = [(0.0, a)]; bb = np.array(b)
    while pq:
        f, c = heapq.heappop(pq)
        if c == b:
            path = [c]
            while c in came: c = came[c]; path.append(c)
            return path[::-1], g[b]
        gc = g[c]
        for (dx, dy, dz), L in zip(NB, NBL):
            n = (c[0] + dx, c[1] + dy, c[2] + dz)
            if not ok(n): continue
            room = dist[n] if n not in opened else need
            ng = gc + L * (1.0 + 0.6 / max(room, 0.3))                # a little extra cost close to parts
            if ng < g.get(n, 1e18):
                g[n] = ng; came[n] = c
                heapq.heappush(pq, (ng + np.linalg.norm(np.array(n) - bb) * H, n))
    return None, None


def clear_line(p, q, need, opened):
    L = np.linalg.norm(q - p); n = max(2, int(L / (H / 2)))
    for s in np.linspace(0, 1, n):
        c = cell(p + (q - p) * s)
        if c in opened: continue
        if not (0 <= c[0] < N[0] and 0 <= c[1] < N[1] and 0 <= c[2] < N[2]) or dist[c] < need: return False
    return True


def ball(p, r):
    c = np.array(cell(p)); k = int(math.ceil(r / H)); out = set()
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            for dz in range(-k, k + 1):
                if dx * dx + dy * dy + dz * dz <= k * k: out.add((c[0] + dx, c[1] + dy, c[2] + dz))
    return out


res = {}
for name, (s, ds, e, de, r, nw, module, label) in S["cables"].items():
    s, ds, e, de = map(np.array, (s, ds, e, de))
    s1, e1 = s + ds * 3.0, e - de * 3.0                               # straight lead-ins out of the plug / into the part
    opened = ball(s, 3.5) | ball(s1, 2.0) | ball(e, 3.5) | ball(e1, 2.0)
    for need in (r + 0.8, r + 0.5, r + 0.3):                         # most room first, less if that finds no way
        path, cost = astar(cell(s1), cell(e1), need, opened)
        if path is not None: break
    if path is None:
        res[name] = {"label": label, "ok": False, "why": "no clear path"}; print(name, "NO PATH", flush=True); continue
    pts = [centre(c) for c in path]; pts[0], pts[-1] = s1, e1
    keep = [pts[0]]; i = 0                                            # shortcut: furthest point still in clear sight
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not clear_line(pts[i], pts[j], need, opened): j -= 1
        keep.append(pts[j]); i = j
    way = [s] + keep + [e]
    L = sum(np.linalg.norm(way[k + 1] - way[k]) for k in range(len(way) - 1))
    minroom = min(float(dist[cell(p)]) for p in pts[2:-2]) if len(pts) > 4 else None
    res[name] = {"label": label, "ok": True, "margin_mm": round(need - r, 1), "points": [list(map(float, p)) for p in way], "length_mm": round(float(L), 1),
                 "min_room_mm": minroom, "radius": r, "wires": nw, "module": module}
    print(f"{name:15s} {label:24s} {L:6.1f} mm, {len(way)} points, tightest room {minroom} mm", flush=True)
    # this cable is now an obstacle for the next ones (they keep their own radius + margin from it)
    for k in range(len(way) - 1):
        a_, b_ = way[k], way[k + 1]; n = max(2, int(np.linalg.norm(b_ - a_) / (H / 2)))
        for t in np.linspace(0, 1, n):
            for c in ball(a_ + (b_ - a_) * t, r):
                if 0 <= c[0] < N[0] and 0 <= c[1] < N[1] and 0 <= c[2] < N[2]: occ[c] = True
    dist = distance_transform_edt(~occ) * H
json.dump(res, open(D + "paths.json", "w"), indent=1)
