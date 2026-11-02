# Routing plan 2: the connections to plan, grouped (minimum spanning tree per net), over the placed parts, both sides.
#   C:/Python312/python.exe design/lib/route_plan_draw.py [out.png]
import json, math, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/"
nets = json.load(open(P + "_route/nets.json")); bm = json.load(open(P + "_place/board_map.json"))
COL = {"camera": "#e8742a", "usb": "#c040c0", "i2c": "#2a9a8a", "spi_nfc": "#3a6ad0", "motors": "#b02a2a", "encoders": "#7a5ad0",
       "leds": "#d0a020", "kicker": "#e04040", "servo_buzzer": "#6a8a2a", "power": "#555555", "expansion": "#20a0d0", "other": "#999999"}
def mst(pts):
    if len(pts) < 2: return []
    used, edges = {0}, []
    while len(used) < len(pts):
        best = min(((math.dist(pts[i]["xy"], pts[j]["xy"]), i, j) for i in used for j in range(len(pts)) if j not in used))
        edges.append((best[1], best[2])); used.add(best[2])
    return edges
fig, axs = plt.subplots(1, 2, figsize=(22, 11))
for ax, side in zip(axs, ("F", "B")):
    ax.add_patch(Circle((0, 0), 40.6, fc="#f4f4f0", ec="k")); ax.add_patch(Circle((41.5, 0), 18.6, fc="white", ec="k"))
    for f in bm["fps"]:
        if f["ref"].startswith("H"):
            ax.add_patch(Circle(f["pos"], 1.15, fc="white", ec="k", lw=0.5)); continue
        if not f["crt"] or f["pos"][0] > 45: continue
        on = f["side"] == side
        ax.add_patch(Polygon(f["crt"], fc="#cfcfcf" if on else "none", ec="#888" if on else "#ccc", lw=0.5, ls="-" if on else ":"))
        if on: ax.text(*f["pos"], f["ref"], fontsize=6, ha="center", va="center")
    for g, ns in nets.items():
        if g == "planes": continue
        for n, pads in ns.items():
            for i, j in mst(pads):
                a, b = pads[i], pads[j]
                cross = a["side"] != b["side"] and "both" not in (a["side"], b["side"])
                here = side in (a["side"], b["side"]) or "both" in (a["side"], b["side"])
                if not here: continue
                ax.plot([a["xy"][0], b["xy"][0]], [a["xy"][1], b["xy"][1]], color=COL.get(g, "#999"), lw=0.9,
                        ls="--" if cross else "-", alpha=0.85)
    ax.set_xlim(-42, 42); ax.set_ylim(-42, 42); ax.set_aspect("equal"); ax.grid(alpha=0.15)
    ax.set_title(f"{'top' if side == 'F' else 'bottom'} side (seen from above): connections by group; dashed = changes side (needs a via)")
for k, (g, c) in enumerate(COL.items()):
    fig.text(0.02 + 0.08 * k, 0.03, g, color=c, fontsize=11, weight="bold")
fig.savefig(sys.argv[1] if len(sys.argv) > 1 else P + "_route/ratsnest_groups.png", dpi=90)
