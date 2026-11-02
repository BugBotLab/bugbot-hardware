# Placement helper 2/3: places the main board's parts to floor plan v1 (approved 2026-10-24,
# design/schematics/Main/floorplan_v1.png). Greedy: each part, in the order below, goes to the free spot nearest its anchor (its
# main chip, or its group's area), any of 4 turns, on its group's side. A spot is free if the courtyard stays inside the
# board (0.6 mm in), clear of every courtyard already there (0.1 mm), the hard keep-outs and holes (from FreeCAD), and of
# any 'max height' outline lower than the part + 0.3 mm. Through-hole parts must be clear on both sides.
# Reads schematics/Main/_place/{shapes.json, free_area.pkl}; writes _place/placement.json for place_apply.py.
#   C:/Python312/python.exe design/lib/place_floorplan.py
import json, pickle, math, re, os
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import affinity

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
shapes = json.load(open(P + "shapes.json"))
free = pickle.load(open(P + "free_area.pkl", "rb"))             # {side: (free polygon, {max height: polygon})}
SIDE = {"top": "F", "bottom": "B"}

# part heights (mm) by footprint name
HEIGHT = [("CP_Elec_10x10.5", 10.6), ("PinSocket_2x06_P2.54mm_Vertical_SMD", 8.6), ("PinHeader_1x03", 8.6),
          ("JST_PH_B2B", 6.0), ("JST_SH_BM", 4.3), ("JST_SH_SM", 3.0), ("ZX-QC4545", 4.3), ("MLT-8530", 3.0),
          ("SWPA4030", 3.0), ("SWPA4020", 2.1), ("D_SMB", 2.4), ("D_SMA", 2.3), ("C_1206", 1.8), ("C_0805", 1.35),
          ("R_1206", 0.7), ("R_0805", 0.6), ("TSSOP", 1.2), ("HTSSOP", 1.2), ("SOT-23", 1.45), ("SOT-363", 1.1), ("SOT-563", 0.6),
          ("LGA-14", 0.9), ("VSON", 1.0), ("LED_0603", 0.8), ("D_SOD-123", 1.35), ("Fuse_1206", 0.9), ("0603", 0.9), ("0402", 0.55)]
def height(fp):
    for k, h in HEIGHT:
        if k in fp: return h
    return 3.0

# floor plan v1: group -> (side, area x0 y0 x1 y1, [parts in order; "REF@ANCHOR" = near that part])
GROUPS = [
    # big or tall parts first, so the small ones fill in round them (v1.1: board outline with the front cut-out)
    ("top", (-4, 29, 14, 37), ["J22"]),
    ("top", (20, 18, 31, 29), ["BZ1", "Q5@BZ1", "D4@BZ1", "R41@Q5", "R42@Q5"]),
    ("top", (-6, -38, 6, -28), ["C34", "R35@C34", "R34@C34", "J19@C34", "D3@J19"]),     # solenoid plug on top: 6 mm tall
    ("top", (10, -38, 20, -31), ["J18", "R29@J18", "U10@R29", "C28@U10", "R30@U10", "C29@R30", "C30@J18", "R31@J18"]),
    ("top", (14, 29, 21, 35), ["J21"]),
    ("top", (-16, 28, -5, 35), ["SW2", "SW3", "LED1", "R28@LED1"]),
    ("top", (-9, 17, 1, 25), ["U13", "R43@U13", "C37@U13", "U14", "R44@U14", "C38@U14"]),
    ("top", (-8, -24, 0, -17), ["U15", "C39@U15", "C40@U15", "R22@U15", "R23@U15"]),
    ("top", (13.5, -17, 17.5, -12), ["R45", "R46", "C41", "C42"]),     # camera XCLK / PCLK series R + 3V3 decoupling by J6
    # v1.2: with every style's arms kept out, the top lost its upper and lower-right areas: the motor drivers and the GPIO
    # expander go under the board, below the NFC reader (4.2 mm headroom), next to the motor connectors
    ("bottom", (-30, 8, -16, 26), ["U8", "C20@U8", "C21@U8", "C22@U8", "C23@U8", "U9", "C24@U9", "C25@U9", "C26@U9", "C27@U9"]),
    ("bottom", (-16, 8, -6, 20), ["U7", "C19@U7", "R24@U7", "R25@U7", "R26@U7", "R27@U7"]),
    ("bottom", (-30, -21, -14, -6), ["U1", "Q3@U1", "R2@U1", "C1@U1", "R3@U1", "F1", "Q1@F1", "R1@Q1", "Q6@Q1", "R47@Q6", "R48@Q6",
                                      "Q2@Q6", "R4@Q2", "R5@Q2", "R6@Q2", "R7@R6", "C2@R7", "U3", "D1@U3", "U2", "C6@U3",
                                      "R8@U2", "R9@U2", "R10@U3", "R11@R10"]),
    ("bottom", (-16, -32, -5, -23), ["U4", "L1@U4", "C7@U4", "C8@U4", "C9@U4", "C10@U4", "R12@U4", "R13@U4",
                                      "U5", "L2@U5", "C11@U5", "C12@U5", "C14@U5", "C15@U5", "R15@U5", "C13@U5", "R16@U5",
                                      "C3@U5", "C4@U5", "C5@U5"]),
    ("bottom", (8, -26, 24, -12), ["U11", "L3@U11", "D2@U11", "C31@U11", "C32@D2", "C33@D2", "R32@U11", "R33@U11",
                                    "R36@U11", "R37@R36", "C35@R37", "Q4@U11", "U12@Q4", "C36@U12", "R38@U12", "R39@Q4", "R40@Q4"]),
    ("bottom", (-16, -14, -4, -6), ["J20", "J14", "J15", "J16", "J17"]),
    ("bottom", (-16, 19, -10.3, 32), ["C16", "C17", "C18", "R17", "R18", "R19", "R20", "R21"]),   # just outside the module's ring
]
FIXED = {"BT1", "J4", "J6", "J11", "J12", "J13", "SW1", "J1", "U6"}
listed = {r.split("@")[0] for g in GROUPS for r in g[2]}
missing = set(shapes) - listed - FIXED
assert not missing, f"not in any group: {sorted(missing)}"

# the board: a 40.6 circle less the front cut-out for the ball (arc r 18.6 centred at (41.5, 0)), 0.8 mm in
board = Point(0, 0).buffer(40.6 - 0.8, 128).difference(Point(41.5, 0).buffer(18.6 + 0.8, 128))
occupied = {"F": [], "B": []}                                  # (courtyard, its routing margin)
# routing room (user, 2026-10-25): 0.5 mm between courtyards, 1 mm round the bigger chips, and a 2.5 mm escape ring round
# the module's 88 pads for their fan-out (the first placement left 0.14 mm median gaps: the router could not get through)
GAP, BIG_GAP, RING = 0.5, 1.0, 2.5
BIG = {"U4", "U5", "U7", "U8", "U9", "U11"}
margin = lambda ref: BIG_GAP if ref in BIG else GAP
bmap = {f["ref"]: f for f in json.load(open(P + "board_map.json"))["fps"]}
for ref in FIXED:                                               # their real courtyards (any angle), from the board map
    side = shapes[ref]["placed"][3]
    g = Polygon(bmap[ref]["crt"]).buffer(0)
    occupied[side].append((g, GAP))
    if ref == "U6":                                             # the escape ring (its courtyard is 0.25 beyond the pads)
        occupied[side].append((g.buffer(RING - 0.25), 0.0))
    if ref == "BT1":                                            # only its pins and peg come through, not the holder
        for px, py, r in ((-23.8, -18.91, 1.6), (-23.8, 18.91, 1.6), (-31.9, -18.91, 1.3)):
            occupied["B"].append((Point(px, py).buffer(r), GAP))
    elif shapes[ref]["tht"] or ref in ("SW1", "J1"):        # (SW1 / J1: their locating holes come through the board)
        occupied["B" if side == "F" else "F"].append((g, GAP))
hard = {SIDE[k]: board.difference(v[0]).buffer(0) for k, v in free.items()}    # everything not free (incl. fixed parts) per side
limits = {SIDE[k]: v[1] for k, v in free.items()}

def ok(g, side, h, tht, m):
    sides = (side, "B" if side == "F" else "F") if tht else (side,)
    if not board.contains(g): return False
    for s in sides:
        if g.buffer(0.1).intersects(hard[s]): return False
        if any(g.distance(o) < max(m, mo) for o, mo in occupied[s]): return False
        for mh, poly in limits[s].items():
            if h + 0.3 > mh and g.intersects(poly) and g.intersection(poly).area > 0.01: return False
    return True

placed = {}
for side_name, (x0, y0, x1, y1), parts in GROUPS:
    side = SIDE[side_name]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for item in parts:
        ref, _, anchor = item.partition("@")
        s = shapes[ref]; h = height(s["fp"])
        s["tht"] = s["tht"] and "ThermalVias" not in s["fp"]          # thermal vias are not leads
        ax, ay = (placed[anchor][0], placed[anchor][1]) if anchor in placed else (cx, cy)
        cands = []
        for i in range(-60, 61):
            for j in range(-60, 61):
                x, y = ax + i * 0.5, ay + j * 0.5
                if math.hypot(x, y) > 40: continue
                # stay near the group's area: outside it costs extra
                out = max(0, x0 - x, x - x1) + max(0, y0 - y, y - y1)
                cands.append((math.hypot(x - ax, y - ay) + 2.0 * out, x, y))
        cands.sort()
        done = False
        for cost, x, y in cands:
            for rot in (0, 90, 180, 270):
                g = affinity.translate(Polygon(s["v"][f"{side}{rot}"]), x, y)
                if "ThermalVias" in s["fp"]:
                    o = "B" if side == "F" else "F"; pad = Point(x, y).buffer(3.0)
                    if any(pad.distance(q) < max(GAP, mo) for q, mo in occupied[o]): continue
                if ok(g, side, h, s["tht"], margin(ref)):
                    occupied[side].append((g, margin(ref)))
                    if s["tht"]: occupied["B" if side == "F" else "F"].append((g, margin(ref)))
                    elif "ThermalVias" in s["fp"]: occupied["B" if side == "F" else "F"].append((Point(x, y).buffer(3.0), GAP))
                    placed[ref] = (x, y, rot, side, round(cost, 1)); done = True; break
            if done: break
        if not done:
            print("NO ROOM for", ref, "near", anchor or "group", side_name)
json.dump(placed, open(P + "placement.json", "w"), indent=0)
far = {r: v[4] for r, v in placed.items() if v[4] > 8}
print(f"placed {len(placed)} of {len(listed)}; far from their anchor (cost > 8): {far}")
