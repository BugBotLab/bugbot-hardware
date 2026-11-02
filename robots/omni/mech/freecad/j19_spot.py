# Where can the solenoid connector J19 go under the main board? (plain Python; user, 2026-10-26: J19 is on top of the
# board but the solenoid is under it, so its lead has no path inside the body.) On the voxel grid (cable_grid.py) every
# spot under the board is tried for a side-entry JST-PH 2 (S2B-PH-SM4-TB: body 8 x 6 x 5.5 mm under the board, plus a
# 7 mm plug lane in front), four mouth directions; a spot counts if body + lane are free. Each free spot is ranked by the
# length of a clear cable path (r 0.8 + 0.3 mm) from the solenoid's leads to the back of the plug (Dijkstra on a 1 mm grid).
# -> _cables/j19_spots.json (best 12) and a plan-view PNG.
#   C:/Python312/python.exe mech/freecad/j19_spot.py
import json, math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from cable_grid import D, S, H, LO, N, occ, dist, cell, centre
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

PCB_Z = S["pcb_z"]
s, ds = np.array(S["cables"]["SolenoidCable"][0]), np.array(S["cables"]["SolenoidCable"][1])
start = s + ds * 3.0
# coarse 1 mm grid of cells with room for the cable
k = int(round(1.0 / H)); C = (N // k)
room = dist[:C[0] * k, :C[1] * k, :C[2] * k].reshape(C[0], k, C[1], k, C[2], k).min(axis=(1, 3, 5))
free = room >= 1.1
idx = -np.ones(C, dtype=np.int64); idx[free] = np.arange(int(free.sum()))
rows, cols, w = [], [], []
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if (dx, dy, dz) <= (0, 0, 0): continue
            a = idx[max(0, -dx):C[0] - max(0, dx), max(0, -dy):C[1] - max(0, dy), max(0, -dz):C[2] - max(0, dz)]
            b = idx[max(0, dx):C[0] + min(0, dx) or None, max(0, dy):C[1] + min(0, dy) or None, max(0, dz):C[2] + min(0, dz) or None]
            m = (a >= 0) & (b >= 0)
            rows.append(a[m]); cols.append(b[m]); w.append(np.full(int(m.sum()), math.sqrt(dx * dx + dy * dy + dz * dz)))
G = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(int(free.sum()),) * 2).tocsr()
sc = tuple(np.floor((start - LO) / 1.0).astype(int))
cand0 = [(sc[0] + a, sc[1] + b, sc[2] + c) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3)]
src = [idx[c] for c in cand0 if all(0 <= c[i] < C[i] for i in range(3)) and idx[c] >= 0]
dmap = dijkstra(G, directed=False, indices=src[0])


def box_free(x0, x1, y0, y1, z0, z1):
    a = np.floor((np.array([x0, y0, z0]) - LO) / H).astype(int); b = np.ceil((np.array([x1, y1, z1]) - LO) / H).astype(int)
    a = np.maximum(a, 0); b = np.minimum(b, N)
    return not occ[a[0]:b[0], a[1]:b[1], a[2]:b[2]].any()


ZB0, ZB1 = PCB_Z - 5.5, PCB_Z - 0.3
spots = []
for x in np.arange(-36, 37, 1.0):
    for y in np.arange(-36, 37, 1.0):
        if math.hypot(x, y) > 36: continue
        for dirn, (ux, uy) in {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}.items():
            hw = 4.0 if ux else 3.0; hd = 3.0 if ux else 4.0            # body: 8 along the pins, 6 deep (mouth side)
            if not box_free(x - hw, x + hw, y - hd, y + hd, ZB0, ZB1): continue
            lx, ly = x + ux * (3.0 + 3.5), y + uy * (3.0 + 3.5)        # plug lane centre, 7 mm in front of the mouth
            if not box_free(lx - (3.5 if ux else 3.0), lx + (3.5 if ux else 3.0), ly - (3.0 if ux else 3.5), ly + (3.0 if ux else 3.5), ZB0 + 1.0, ZB1):
                continue
            back = np.array([x + ux * 6.0, y + uy * 6.0, PCB_Z - 2.8])  # where the cable leaves the plug
            c = tuple(np.floor((back - LO) / 1.0).astype(int))
            if not all(0 <= c[i] < C[i] for i in range(3)) or idx[c] < 0: continue
            L = dmap[idx[c]]
            if np.isfinite(L): spots.append({"x": float(x), "y": float(y), "mouth": dirn, "cable_mm": round(float(L) + 6.0, 1)})
spots.sort(key=lambda s_: s_["cable_mm"])
best, seen = [], []
for s_ in spots:                                      # keep spots at least 4 mm apart
    if all(math.hypot(s_["x"] - t["x"], s_["y"] - t["y"]) >= 4 for t in seen): best.append(s_); seen.append(s_)
    if len(best) >= 12: break
json.dump({"start": start.tolist(), "spots": best, "n_free": len(spots)}, open(D + "j19_spots.json", "w"), indent=1)
for b_ in best: print(b_)
fig, ax = plt.subplots(figsize=(8, 8))
ax.add_patch(plt.Circle((0, 0), 40.6, fc="none", ec="k"))
xs = [s_["x"] for s_ in spots]; ys = [s_["y"] for s_ in spots]; cs = [s_["cable_mm"] for s_ in spots]
sc_ = ax.scatter(xs, ys, c=cs, s=6, cmap="viridis_r"); plt.colorbar(sc_, label="cable length from the solenoid (mm)")
for i, b_ in enumerate(best[:6]): ax.annotate(str(i + 1), (b_["x"], b_["y"]), color="r", fontsize=11, weight="bold")
ax.plot(*start[:2], "r*", ms=14); ax.set_aspect("equal"); ax.set_xlim(-42, 42); ax.set_ylim(-42, 42); ax.grid(alpha=0.3)
ax.set_title("Free spots for a side-entry J19 under the board (robot frame)")
plt.savefig(D + "j19_spots.png", dpi=90, bbox_inches="tight")


# ---- option B: keep J19 on top, pass the lead through a small slot in the board ----
# distances from the solenoid (below the board) and from J19's plug (above it); a slot at (x, y) needs both board faces
# free of parts there (3 x 3 mm column) and costs below-path + board + above-path
e = np.array(S["cables"]["SolenoidCable"][2]); de = np.array(S["cables"]["SolenoidCable"][3]); top = e - de * 3.0
tc = tuple(np.floor((top - LO) / 1.0).astype(int))
cand1 = [(tc[0] + a, tc[1] + b, tc[2] + c) for a in range(-2, 3) for b in range(-2, 3) for c in range(-2, 3)]
tsrc = [idx[c] for c in cand1 if all(0 <= c[i] < C[i] for i in range(3)) and idx[c] >= 0]
tmap = dijkstra(G, directed=False, indices=tsrc[0])
PT = S["pcb_top"]
slots = []
for x in np.arange(-36, 37, 1.0):
    for y in np.arange(-36, 37, 1.0):
        if math.hypot(x, y) > 37: continue
        if not (box_free(x - 1.5, x + 1.5, y - 1.5, y + 1.5, PCB_Z - 2.5, PCB_Z - 0.1) and box_free(x - 1.5, x + 1.5, y - 1.5, y + 1.5, PT + 0.1, PT + 2.5)):
            continue
        lo = tuple(np.floor((np.array([x, y, PCB_Z - 2.0]) - LO) / 1.0).astype(int)); hi = tuple(np.floor((np.array([x, y, PT + 2.0]) - LO) / 1.0).astype(int))
        if min(idx[lo], idx[hi]) < 0: continue
        a, b = dmap[idx[lo]], tmap[idx[hi]]
        if np.isfinite(a) and np.isfinite(b): slots.append({"x": float(x), "y": float(y), "below_mm": round(float(a), 1), "above_mm": round(float(b), 1), "cable_mm": round(float(a + b) + 4.0 + 6.0, 1)})
slots.sort(key=lambda s_: s_["cable_mm"])
bs_, seen = [], []
for s_ in slots:
    if all(math.hypot(s_["x"] - t["x"], s_["y"] - t["y"]) >= 3 for t in seen): bs_.append(s_); seen.append(s_)
    if len(bs_) >= 10: break
json.dump({"start": start.tolist(), "j19_plug": top.tolist(), "slots": bs_}, open(D + "j19_slots.json", "w"), indent=1)
print("slot options:"); [print(" ", b_) for b_ in bs_]
