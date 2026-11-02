# Plot small board areas: copper tracks, vias and pads round given points, to look at routing details without opening
# KiCad. -> one PNG with a grid of tiles. Run with KiCad python: it exports the geometry (KiCad's python has no
# matplotlib) and hands the drawing to C:/Python312.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/plot_spots.py board out.png r_mm x,y[,title] ...
import json, os, subprocess, sys
PY = "C:/Python312/python.exe"

if sys.argv[1] == "--draw":                       # stage 2 (C:/Python312): draw the exported geometry
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Pg, Circle
    d = json.load(open(sys.argv[2])); R = d["r"]; spots = d["spots"]
    COL = {"F.Cu": "#c83434", "B.Cu": "#3a6bd1", "In2.Cu": "#c2a03a", "In3.Cu": "#3aa86a", "In4.Cu": "#a04ac2"}
    n = len(spots); cols = min(4, n); rows = (n + cols - 1) // cols; tile = 4.2
    fig, axs = plt.subplots(rows, cols, figsize=(tile * cols, tile * rows), squeeze=False)
    for k, s in enumerate(spots):
        ax = axs[k // cols][k % cols]; x, y = s["x"], s["y"]
        for ref, num, polys in s["pads"]:
            for pts in polys: ax.add_patch(Pg(pts, fc="#9e9e9e", ec="#555", lw=0.4, alpha=0.55, zorder=1))
            cx = sum(p[0] for p in polys[0]) / len(polys[0]); cy = sum(p[1] for p in polys[0]) / len(polys[0])
            ax.text(cx, cy, f"{ref}.{num}", fontsize=6, ha="center", va="center", zorder=5, clip_on=True)
        pt_per_mm = tile * 72 / (2 * R) * 0.95                      # axes fill ~95 % of the tile
        for lay, a, e, w in s["tracks"]:
            if lay in COL:
                ax.plot([a[0], e[0]], [a[1], e[1]], color=COL[lay], lw=w * pt_per_mm, solid_capstyle="round", alpha=0.7, zorder=3)
        for c, r in s["vias"]: ax.add_patch(Circle(c, r, fc="#e0e0e0", ec="k", lw=0.5, zorder=4))
        ax.set_xlim(x - R, x + R); ax.set_ylim(y + R, y - R); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(s["title"], fontsize=8)
    for k in range(n, rows * cols): axs[k // cols][k % cols].axis("off")
    plt.subplots_adjust(0.01, 0.01, 0.99, 0.96, 0.04, 0.12); plt.savefig(d["out"], dpi=110); print(d["out"])
    sys.exit()

import pcbnew                                     # stage 1 (KiCad python): export
B, OUT, R = sys.argv[1], sys.argv[2], float(sys.argv[3])
b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
near = lambda px, py, x, y, m: abs(px - x) < R + m and abs(py - y) < R + m
pads = [(f.GetReference(), p) for f in b.GetFootprints() for p in f.Pads()]
spots = []
for a in sys.argv[4:]:
    s = a.split(","); x, y = float(s[0]), float(s[1])
    sp = {"x": x, "y": y, "title": s[2] if len(s) > 2 else f"{x:.1f}, {y:.1f}", "pads": [], "tracks": [], "vias": []}
    for ref, p in pads:
        c = p.GetPosition()
        if not near(tm(c.x), tm(c.y), x, y, 3): continue
        poly = p.GetEffectivePolygon(pcbnew.ERROR_INSIDE); polys = []
        for i in range(poly.OutlineCount()):
            o = poly.Outline(i); polys.append([(tm(o.CPoint(j).x), tm(o.CPoint(j).y)) for j in range(o.PointCount())])
        if polys: sp["pads"].append((ref, p.GetNumber(), polys))
    for t in b.GetTracks():
        a_, e_ = t.GetStart(), t.GetEnd()
        if not (near(tm(a_.x), tm(a_.y), x, y, 3) or near(tm(e_.x), tm(e_.y), x, y, 3)): continue
        if t.GetClass() == "PCB_VIA":
            sp["vias"].append(((tm(a_.x), tm(a_.y)), tm(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            sp["tracks"].append((b.GetLayerName(t.GetLayer()), (tm(a_.x), tm(a_.y)), (tm(e_.x), tm(e_.y)), tm(t.GetWidth())))
    spots.append(sp)
js = os.path.splitext(OUT)[0] + "_geom.json"
json.dump({"r": R, "out": OUT, "spots": spots}, open(js, "w"))
env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}       # KiCad python's PYTHONHOME breaks the other python
r = subprocess.run([PY, os.path.abspath(__file__), "--draw", js], capture_output=True, text=True, env=env)
print(r.stdout.strip() or r.stderr[-800:])
