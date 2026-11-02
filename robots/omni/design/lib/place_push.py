# Group push (user, 2026-10-25): moves a group of parts together by one vector, as far as the floor plan's rules allow
# (place_nudge.py's checks), pulling in any movable part the group runs into (cascade), and draws the moves to scale.
# Writes _place/push.json + placement_pushed.json and design/schematics/Main/push_v1.png for approval; nothing is applied.
#   C:/Python312/python.exe design/lib/place_push.py U8,U9,U2,J20,Q2,R5 225
import sys, json, math
sys.argv = [sys.argv[0], "none"] + sys.argv[1:]          # place_nudge's setup reads argv[1] as a log; give it none
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
src = open(BB + "/design/lib/place_nudge.py").read().split("# the jams:")[0]
exec(src)
from shapely import affinity

group = sys.argv[2].split(",")
heading = float(sys.argv[3]) if len(sys.argv) > 3 else 225.0   # degrees, robot frame (180 = rear, 270 = right side)
MAX_PUSH, MAX_CASCADE = 2.0, 6
orig = {r: list(v) for r, v in placed.items()}


def try_push(members, dx, dy):
    """returns (ok, refs that block the moved members)"""
    moved = {r: [orig[r][0] + dx, orig[r][1] + dy] + orig[r][2:] for r in members}
    saved = {r: placed[r] for r in members}
    placed.update(moved)
    blocking = set()
    ok = True
    try:
        for r in members:
            g = outline(r)
            obs, sides = blockers(r)
            if not board.contains(g): ok = False; continue
            h = height(shapes[r]["fp"])
            for s in sides:
                if g.buffer(0.1).intersects(hard[s]): ok = False
                for mh, poly in limits[s].items():
                    if h + 0.3 > mh and g.intersects(poly) and g.intersection(poly).area > 0.01: ok = False
            for o in (set(placed) | FIXED) - set(members):
                so = {side_of(o)} | ({"F", "B"} if through(o) else set())
                if o == "BT1": so = {"F"}
                if not (sides & so): continue
                m = max(margin(r), margin(o))
                if g.distance(outline(o)) < m - 1e-6: ok = False; blocking.add(o)
                if o == "U6" and g.distance(outline(o).buffer(RING - 0.25)) < 1e-6: ok = False; blocking.add(o)
    finally:
        placed.update(saved)
    return ok, blocking


best = None
for k in range(int(MAX_PUSH / 0.25), 0, -1):
    s = k * 0.25
    for da in (0, 15, -15, 30, -30):
        a = math.radians(heading + da)
        dx, dy = round(s * math.cos(a) / 0.05) * 0.05, round(s * math.sin(a) / 0.05) * 0.05
        members = list(group)
        for _ in range(MAX_CASCADE + 1):
            ok, bl = try_push(members, dx, dy)
            if ok: break
            if bl & FIXED: break                         # fixed parts never move
            members += sorted(bl - set(members))
        if ok:
            best = (dx, dy, members); break
    if best: break

if not best:
    print("no push fits"); sys.exit(1)
dx, dy, members = best
print(f"push {dx:+.2f}, {dy:+.2f} mm ({math.hypot(dx, dy):.2f} mm); moves {members}")
for r in members: placed[r] = [orig[r][0] + dx, orig[r][1] + dy] + orig[r][2:]
json.dump({"by": [dx, dy], "parts": members}, open(P + "push.json", "w"), indent=1)
json.dump(placed, open(P + "placement_pushed.json", "w"), indent=0)

# gap the push opens between the module's SW corner and U8's input pins (the jam)
u6 = outline("U6")
def gap(ref, pl):
    keep = placed[ref]; placed[ref] = pl
    d = outline(ref).distance(u6); placed[ref] = keep; return d
print(f"U8 to module courtyard: {gap('U8', orig['U8']):.2f} -> {gap('U8', placed['U8']):.2f} mm")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Circle
fig, ax = plt.subplots(figsize=(13, 11))
ax.add_patch(Circle((0, 0), 40.6, fc="#f6f6f2", ec="k")); ax.add_patch(Circle((41.5, 0), 18.6, fc="white", ec="k"))
for k2, v in hard.items():
    for g in getattr(v, "geoms", [v]):
        if g.area > 0.5: ax.add_patch(MP(list(g.exterior.coords), fc="#f0c0c0" if k2 == "F" else "#c0c8f0", ec="none", alpha=0.25))
for ref in set(placed) | FIXED:
    g = outline(ref)
    col = "#a03030" if side_of(ref) == "F" else "#3050a0"
    if ref in members:
        g0 = affinity.translate(g, -dx, -dy)
        ax.add_patch(MP(list(g0.exterior.coords), fc="none", ec="#666", lw=0.8, ls="--"))
        ax.add_patch(MP(list(g.exterior.coords), fc="#ffd24d", ec="k", lw=1.0, alpha=0.8))
        ax.annotate(ref, g.centroid.coords[0], fontsize=8, ha="center", va="center", weight="bold")
    else:
        ax.add_patch(MP(list(g.exterior.coords), fc="none", ec=col, lw=0.5, ls="-" if side_of(ref) == "F" else "--"))
        if g.centroid.x < 4 and -20 < g.centroid.y < 34 and side_of(ref) == "B":
            ax.annotate(ref, g.centroid.coords[0], fontsize=6, ha="center", va="center", color=col)
ax.annotate("", (-3, -14), (-3 - dx * 3, -14 - dy * 3), arrowprops=dict(arrowstyle="<-", lw=2))
ax.text(-3, -15.2, f"push {dx:+.2f}, {dy:+.2f} mm", fontsize=9, ha="center")
ax.set_xlim(-36, 6); ax.set_ylim(-18, 34); ax.set_aspect("equal"); ax.grid(alpha=0.2)
ax.set_title(f"Group push v1 (seen from above, to scale, mm): yellow = moved ({', '.join(members)}), dashed = where they were;\n"
             "blue dashed = bottom-side parts, red = top; shaded = keep-outs from every style. Rules kept: 0.5 mm between courtyards,\n"
             "1 mm round the bigger chips, 2.5 mm escape ring round the module.", fontsize=9)
out = BB + "/design/schematics/Main/push_v1.png"
fig.savefig(out, dpi=100); print(out)
