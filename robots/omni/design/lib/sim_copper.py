# Copper (DC IR-drop / current-density) simulation of the main board's power nets (C:/Python312/python.exe; user,
# 2026-10-26). Each net's copper (copper_export.py -> _work/copper_nets.json) is rasterised per layer and solved as a
# resistor mesh: sheet resistance 0.49 mOhm/sq (1 oz outer) / 0.97 mOhm/sq (0.5 oz inner), vias and plated pads link
# the layers (barrel 0.018 mm plating). Current enters at the net's source pad and leaves at its loads (the "busy"
# scenario of sim_nodes.py). Results per net: worst voltage drop, path resistance, peak current density against the
# IPC-2221 limit for its layer (10 degC rise), the track pieces over the limit with the current they really carry,
# and a PNG map. Writes _work/copper_res.json (path resistances for sim_nodes.py) and _work/sim_copper.md.
#   C:/Python312/python.exe design/lib/sim_copper.py [net ...]
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
G = json.load(open(R + "_work/copper_nets.json"))
LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
RS = {l: (0.49e-3 if l in ("F.Cu", "B.Cu") else 0.97e-3) for l in LAYERS}      # ohm / square
RHO, PLATE, BOARD_T = 1.72e-8, 0.018e-3, 1.6e-3


def i_ipc(w_mm, outer, dt=10.0):
    A = w_mm / 0.0254 * (1.378 if outer else 0.689)
    return (0.048 if outer else 0.024) * dt ** 0.44 * A ** 0.725


# source pad and loads (ref, pin, amps) per net: the busy case (motors 0.5 A each, 5 V 0.6 A, 3V3 0.7 A, kicker 0.4 A)
I_BATT = 3.6
CASES = {
    "/BAT_P": ("BT1.1", [("F1.1", I_BATT)]), "/BAT_F": ("F1.2", [("Q1.3", I_BATT)]), "/VBAT_P": ("Q1.2", [("Q6.2", I_BATT)]),
    "/VBAT_SW": ("Q6.3", [("Q2.3", I_BATT)]), "/BAT_N": ("Q3.1", [("BT1.2", I_BATT)]),
    "/VSYS": ("Q2.2", [("U8.12", 1.0), ("U9.12", 0.5), ("L2.1", 0.96), ("U4.10", 0.7), ("L3.1", 0.4)]),
    "/5V": ("U5.6", [("R29.1", 0.2), ("J4.1", 0.2), ("J17.1", 0.2)]),
    "/3V3": ("U4.6", [("U6.85", 0.25), ("U6.86", 0.25), ("U15.8", 0.01), ("U7.24", 0.01), ("BZ1.1", 0.1)]),
    "/GND": ("Q3.3", [("U8.17", -1.0), ("U9.17", -0.5), ("U5.4", -0.36), ("U11.2", -0.4), ("J18.1", -0.2), ("J4.3", -0.2),
                      ("J17.3", -0.2), ("U6.GND", -0.5), ("U4.8", -0.04)]),
    "/M1_A": ("U8.2", [("J14.1", 1.0)]), "/M1_B": ("U8.4", [("J14.2", 1.0)]), "/M2_A": ("U8.7", [("J15.1", 1.0)]),
    "/M2_B": ("U8.5", [("J15.2", 1.0)]), "/M3_A": ("U9.2", [("J16.1", 1.0)]), "/M3_B": ("U9.4", [("J16.2", 1.0)]),
    "/SW5": ("U5.5", [("L2.2", 1.0)]), "/SW33A": ("U4.9", [("L1.1", 0.8)]), "/SW33B": ("L1.2", [("U4.7", 0.8)]),
    "/SERVO_5V": ("R29.2", [("J18.2", 0.7)]), "/VBUS": ("J1.A4", [("U3.1", 1.5)])}


def solve(net, src, loads):
    d = G[net]
    h = 0.2 if net == "/GND" else 0.05 if net not in ("/VSYS", "/5V", "/3V3", "/VBUS") else 0.1
    pts = [p for t in d["tracks"] for p in (t["a"], t["b"])] + [p["c"] for p in d["pads"]] + [v["c"] for v in d["vias"]] + \
          [q for z in d["zones"] for q in z["outline"]]
    x0, y0 = min(p[0] for p in pts) - 1.5, min(p[1] for p in pts) - 1.5
    x1, y1 = max(p[0] for p in pts) + 1.5, max(p[1] for p in pts) + 1.5
    W, H = int((x1 - x0) / h) + 1, int((y1 - y0) / h) + 1
    px = lambda p: ((p[0] - x0) / h, (p[1] - y0) / h)
    masks = {}
    for l in LAYERS:
        im = Image.new("1", (W, H), 0); dr = ImageDraw.Draw(im)
        for z in d["zones"]:
            if z["l"] != l: continue
            dr.polygon([px(p) for p in z["outline"]], fill=1)
            for hole in z["holes"]: dr.polygon([px(p) for p in hole], fill=0)
        for p in d["pads"]:
            if l in p["layers"]:
                for o in p["poly"]: dr.polygon([px(q) for q in o], fill=1)
        for t in d["tracks"]:
            if t["l"] != l: continue
            wpx = max(1, t["w"] / h); a, c = px(t["a"]), px(t["b"])
            dr.line([a, c], fill=1, width=int(round(wpx)))
            r = wpx / 2
            for e in (a, c): dr.ellipse([e[0] - r, e[1] - r, e[0] + r, e[1] + r], fill=1)
        for v in d["vias"]:
            c = px(v["c"]); r = v["d"] / 2 / h
            dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=1)
        masks[l] = np.array(im, dtype=bool)
    idx = {}; n = 0
    for l in LAYERS:
        m = masks[l]; ii = -np.ones(m.shape, dtype=np.int64); k = int(m.sum()); ii[m] = np.arange(n, n + k); idx[l] = ii; n += k
    rows, cols, vals = [], [], []
    def link(a, bb, g):
        rows.extend([a, bb, a, bb]); cols.extend([a, bb, bb, a]); vals.extend([g, g, -g, -g])
    for l in LAYERS:
        ii = idx[l]; g = 1.0 / RS[l]
        for sl_a, sl_b in (((slice(None), slice(0, -1)), (slice(None), slice(1, None))), ((slice(0, -1), slice(None)), (slice(1, None), slice(None)))):
            a_, b_ = ii[sl_a], ii[sl_b]; ok = (a_ >= 0) & (b_ >= 0)
            A, Bb = a_[ok], b_[ok]
            rows.extend(np.concatenate([A, Bb, A, Bb])); cols.extend(np.concatenate([A, Bb, Bb, A]))
            vals.extend(np.concatenate([np.full(len(A), g), np.full(len(A), g), np.full(len(A), -g), np.full(len(A), -g)]))
    def barrel(c, drill):                                  # plated hole: links consecutive layers where both have copper
        r_gap = RHO * (BOARD_T / 5) / (math.pi * drill * 1e-3 * PLATE)
        cx, cy = px(c); rr = max(1.0, (drill / 2 + 0.05) / h)
        cells = [(int(round(cy + dy)), int(round(cx + dx))) for dy in range(-int(rr), int(rr) + 1) for dx in range(-int(rr), int(rr) + 1)
                 if dx * dx + dy * dy <= rr * rr]
        for la, lb in zip(LAYERS, LAYERS[1:]):
            pairs = [(idx[la][y, x], idx[lb][y, x]) for y, x in cells if 0 <= y < H and 0 <= x < W and idx[la][y, x] >= 0 and idx[lb][y, x] >= 0]
            for a, bb in pairs: link(a, bb, 1.0 / (r_gap * len(pairs)))
    for v in d["vias"]: barrel(v["c"], v["drill"])
    for p in d["pads"]:
        if p["drill"] > 0: barrel(p["c"], p["drill"])
    Lm = coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()
    def cells_of(name):
        ref, pin = name.split(".")
        ps = [p for p in d["pads"] if p["ref"] == ref and (p["pin"] == pin or (pin == "GND"))]
        out = []
        for p in ps:
            l = p["layers"][0]; cx, cy = px(p["c"])
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    y, x = int(round(cy)) + dy, int(round(cx)) + dx
                    if 0 <= y < H and 0 <= x < W and idx[l][y, x] >= 0: out.append(idx[l][y, x])
        return out
    s_cells = cells_of(src)
    if not s_cells: return None, f"{net}: source pad {src} has no copper cell"
    b = np.zeros(n)
    for name, I in loads:
        cs = cells_of(name)
        if not cs: continue
        b[cs] -= I / len(cs)
    fixed = np.zeros(n, dtype=bool); fixed[s_cells] = True
    free = ~fixed
    # drop islands not connected to the source (zone pieces etc.): keep the component reachable from the source
    from scipy.sparse.csgraph import connected_components
    _, lab = connected_components(Lm, directed=False)
    keep = lab == lab[s_cells[0]]
    free &= keep
    V = np.zeros(n)
    A = Lm[free][:, free]
    V[free] = spsolve(A.tocsc(), b[free])
    lost = sum(I for name, I in loads if not any(keep[c] for c in cells_of(name)))
    # current density per cell: |grad V| / Rs (A per mm of copper width)
    res = {"net": net, "h": h, "cells": int(free.sum())}
    worst = []
    for name, I in loads:
        cs = [c for c in cells_of(name) if keep[c]]
        if cs: worst.append((abs(V[cs].mean()), name, I))
    tot = sum(abs(I) for _, I in loads)
    vmax = max(w[0] for w in worst) if worst else 0
    res.update(drop_mV=round(vmax * 1e3, 1), R_mOhm=round(vmax / max(tot, 1e-9) * 1e3, 2), worst_load=max(worst)[1] if worst else None,
               unreached=round(lost, 2))
    K, over = {}, []
    for l in LAYERS:
        ii = idx[l]; Vg = np.full(ii.shape, np.nan); m = ii >= 0; Vg[m] = V[ii[m]]
        gy, gx = np.gradient(Vg, h)                         # V per mm
        k = np.hypot(np.nan_to_num(gx), np.nan_to_num(gy)) / RS[l]
        k[~m] = 0; K[l] = k
    lim = {l: i_ipc(1.0, l in ("F.Cu", "B.Cu")) for l in LAYERS}         # A per mm of width (1 mm track)
    for t in d["tracks"]:
        a, c = np.array(t["a"]), np.array(t["b"]); L = np.linalg.norm(c - a); ns = max(2, int(L / h))
        ks = []
        for s in np.linspace(0.15, 0.85, ns):
            q = a + (c - a) * s; x, y = int(round((q[0] - x0) / h)), int(round((q[1] - y0) / h))
            if 0 <= y < H and 0 <= x < W: ks.append(K[t["l"]][y, x])
        if not ks: continue
        I_piece = float(np.median(ks)) * t["w"]
        I_lim = i_ipc(t["w"], t["l"] in ("F.Cu", "B.Cu"))
        if I_piece > I_lim and L > 0.3:
            over.append({"l": t["l"], "w": t["w"], "I": round(I_piece, 2), "I_lim": round(I_lim, 2), "a": t["a"], "b": t["b"]})
    res["peak_A_per_mm"] = {l: round(float(K[l].max()), 2) for l in LAYERS if K[l].max() > 0}
    res["over"] = sorted(over, key=lambda o: -o["I"] / o["I_lim"])
    # map
    fig, ax = plt.subplots(figsize=(8, 8 * H / W + 0.5))
    comp = np.zeros((H, W))
    for l in LAYERS: comp = np.maximum(comp, K[l] / lim[l])
    im = ax.imshow(np.ma.masked_where(comp == 0, comp), extent=[x0, x0 + W * h, y0 + H * h, y0], cmap="turbo", vmin=0, vmax=1.5)
    plt.colorbar(im, ax=ax, label="current density / IPC limit (1 = at the 10 degC limit)")
    ax.set_title(f"{net}: {tot:.2f} A, worst drop {res['drop_mV']} mV")
    for o in res["over"][:20]: ax.plot([o["a"][0], o["b"][0]], [o["a"][1], o["b"][1]], color="w", lw=1)
    fn = R + "_work/copper_" + net.strip("/") + ".png"; plt.savefig(fn, dpi=90, bbox_inches="tight"); plt.close()
    res["png"] = fn
    return res, None


nets = sys.argv[1:] or list(CASES)
results, md = {}, ["# Main board copper simulation (busy case: 3.6 A from the cell)", ""]
for net in nets:
    src, loads = CASES[net]
    r, err = solve(net, src, loads)
    if err: md.append(f"- {err}"); print(err); continue
    results[net] = r
    line = (f"- **{net}** {sum(abs(i) for _, i in loads):.2f} A: worst drop {r['drop_mV']} mV at {r['worst_load']} "
            f"({r['R_mOhm']} mOhm); peak {max(r['peak_A_per_mm'].values()):.1f} A/mm; {len(r['over'])} piece(s) over the IPC limit"
            + (f"; {r['unreached']} A of loads not reached by copper!" if r["unreached"] else ""))
    md.append(line); print(line, flush=True)
    for o in r["over"][:6]:
        md.append(f"    - {o['w']} mm on {o['l']} at ({o['a'][0]:.1f}, {o['a'][1]:.1f})-({o['b'][0]:.1f}, {o['b'][1]:.1f}): carries {o['I']} A, limit {o['I_lim']} A")
json.dump({k: {kk: vv for kk, vv in v.items() if kk != "over"} | {"over": v["over"][:30]} for k, v in results.items()}, open(R + "_work/sim_copper.json", "w"), indent=1)
cres = {"BAT_P": sum(results[n]["R_mOhm"] for n in ("/BAT_P", "/BAT_F") if n in results) / 1e3,
        "VBAT": sum(results[n]["R_mOhm"] for n in ("/VBAT_P", "/VBAT_SW") if n in results) / 1e3,
        "BAT_N": results.get("/BAT_N", {}).get("R_mOhm", 0) / 1e3 + results.get("/GND", {}).get("R_mOhm", 0) / 1e3,
        "VSYS": results.get("/VSYS", {}).get("R_mOhm", 0) / 1e3}
json.dump(cres, open(R + "_work/copper_res.json", "w"), indent=1)
open(R + "_work/sim_copper.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print("copper path resistances for sim_nodes:", {k: f"{v*1e3:.1f} mOhm" for k, v in cres.items()})
