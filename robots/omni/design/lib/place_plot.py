# Placement view: the floor plan's free area, the fixed parts, and every placed courtyard with its reference.
#   C:/Python312/python.exe design/lib/place_plot.py [out.png]
import json, pickle, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as Pg
from shapely.geometry import Polygon
from shapely import affinity
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
shapes = json.load(open(P + "shapes.json")); pl = json.load(open(P + "placement.json"))
free = pickle.load(open(P + "free_area.pkl", "rb")); bmap = {f["ref"]: f for f in json.load(open(P + "board_map.json"))["fps"]}
OUT = sys.argv[1] if len(sys.argv) > 1 else P + "placement.png"
fig, axs = plt.subplots(1, 2, figsize=(20, 10))
def draw(ax, g, **kw):
    for p in getattr(g, "geoms", [g]):
        if p.is_empty or p.geom_type != "Polygon": continue
        ax.add_patch(Pg(list(p.exterior.coords), **kw))
        for h in p.interiors: ax.add_patch(Pg(list(h.coords), fc="white", ec="none"))
for ax, (sn, sd) in zip(axs, (("top", "F"), ("bottom", "B"))):
    fr, lim = free[sn]
    ax.add_patch(Circle((0, 0), 40.6, fc="#dddddd", ec="k"))
    from shapely.geometry import Point as Pt
    draw(ax, fr.difference(Pt(41.5, 0).buffer(18.6, 128)), fc="#eef7ee", ec="#aaa", lw=0.3)
    ax.add_patch(Circle((41.5, 0), 18.6, fc="white", ec="k", lw=0.8))
    for h, g in lim.items():
        if h < 6: draw(ax, g, fc="#f4e6b0" if h < 3 else "#dcedf6", ec="none")
    for ref, f in bmap.items():
        if f["pos"][0] > 45 or ref.startswith("H") or ref in pl: continue
        if (f["side"] == "F") == (sn == "top") and f["crt"]:
            ax.add_patch(Pg(f["crt"], fc="#999", ec="k", lw=0.5)); ax.text(*f["pos"], ref, fontsize=7, ha="center", weight="bold")
    for ref, (x, y, rot, side, cost) in pl.items():
        if side != sd: continue
        g = affinity.translate(Polygon(shapes[ref]["v"][f"{side}{rot}"]), x, y)
        ax.add_patch(Pg(list(g.exterior.coords), fc="#e06060" if cost > 8 else "#6a8ad8", ec="k", lw=0.4, alpha=0.75))
        ax.text(x, y, ref, fontsize=4.5, ha="center", va="center")
    ax.set_xlim(-42, 42); ax.set_ylim(-42, 42); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.set_title(f"{sn} (seen from above): blue placed, red = far from its group (cost > 8)")
fig.savefig(OUT, dpi=110); print(OUT)
