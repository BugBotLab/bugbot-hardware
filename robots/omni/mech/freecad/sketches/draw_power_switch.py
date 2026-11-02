# 2D concept (to scale): the power switch, C&K L101011ML04Q ($7.12, 0 at LCSC) vs XKB SS-12D11G5R (C388633, $0.50, 3 A).
# Local frame at the slot (sw_ang 237 deg): t = along the wall, r = radius; z = height. Numbers: bugbot_params.py (r_inner,
# wall_t, pcb_z, sw_slot_w / sw_slot_z, sw_r), the C&K catalog (L series ML / 04) and the SS-12D11G5R drawing
# (design/lib/datasheets/SS-12D11G5R_C388633.pdf) + LCSC's footprint for it.
#   C:/Python312/python.exe mech/freecad/sketches/draw_power_switch.py   -> sketches/power_switch_v1.png
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "power_switch_v1.png")
R_IN, WALL, PCB_Z, PCB_T = 38.8, 1.8, 29.0, 1.6
R_OUT = R_IN + WALL
SLOT_W, SLOT_Z = 7.8, PCB_Z - 8.6
# C&K L101011ML04Q (right angle, on the PCB underside): actuator face at sw_r 34.9; pins at r 29.7 (old plan + model)
CK = dict(face=34.9, act=2.54, depth=10.46, len=19.30, h=8.51, act_w=3.18, act_h=5.08, travel=3.56, pins_r=29.7, pitch=4.75)
# SS-12D11G5R: body 13.5 x 6.3 x 6.6 (high off the board), knob 2.45 x 4.0 standing 5.0 proud of the case, 2.4 travel;
# 2 case tabs (d 1.5 holes, 13.29 apart) 1.58 inside its front face, 3 pins (d 1.6, 4.8 pitch) 9.2 behind the tabs
NEW_TIP = R_IN - 0.9                                         # knob tip 0.9 inside the wall (C&K's actuator: 3.9 inside)
SS = dict(knob=5.0, depth=6.3, len=13.5, h=6.6, knob_w=2.45, knob_h=4.0, knob_zc=3.3, travel=2.4)
SS["face"] = NEW_TIP - SS["knob"]; SS["tabs_r"] = SS["face"] - 1.58; SS["pins_r"] = SS["tabs_r"] - 9.2

fig = plt.figure(figsize=(16, 9))
a = fig.add_axes([0.03, 0.08, 0.40, 0.80]); b = fig.add_axes([0.46, 0.40, 0.32, 0.48]); n = fig.add_axes([0.46, 0.02, 0.53, 0.33]); n.axis("off")
c = fig.add_axes([0.79, 0.40, 0.21, 0.48]); c.axis("off")

# ---- top view (looking down; both switches hang under the PCB)
a.set_title("From above, through the PCB (t along the wall, r outward; mm)", fontsize=11)
th = math.degrees(math.asin(14 / R_IN))
for r0, r1, col in ((R_IN, R_OUT, "#d9d9d4"),):
    a.add_patch(Wedge((0, 0), r1, 90 - th, 90 + th, width=r1 - r0, fc=col, ec="k", lw=0.8))
a.add_patch(Rectangle((-SLOT_W / 2, R_IN - 0.4), SLOT_W, WALL + 1.2, fc="white", ec="k", lw=0.8))
a.text(0, R_OUT + 1.0, f"wall slot {SLOT_W} wide (unchanged)", ha="center", fontsize=8.5)
a.plot([-14, 14], [R_OUT, R_OUT], alpha=0)                      # (PCB edge = wall outside, r 40.6)
# C&K (grey, dashed)
f, d, L = CK["face"], CK["depth"], CK["len"]
a.add_patch(Rectangle((-L / 2, f - CK["act"] - d), L, d, fc="#bbbbbb", ec="#555", lw=1.0, ls="--", alpha=0.55))
a.add_patch(Rectangle((-CK["act_w"] / 2, f - CK["act"]), CK["act_w"], CK["act"], fc="#999", ec="#555", lw=1.0, ls="--", alpha=0.7))
for k in (-1, 0, 1):
    a.add_patch(Circle((k * CK["pitch"], CK["pins_r"]), 0.825, fc="#777", ec="none"))
a.text(-L / 2 - 0.3, f - CK["act"] - d / 2, "C&K L101011ML04Q\n19.3 x 10.5 body", ha="right", va="center", fontsize=8.5, color="#444")
# SS-12D11G5R (orange)
f, d, L = SS["face"], SS["depth"], SS["len"]
a.add_patch(Rectangle((-L / 2, f - d), L, d, fc="#e8742a", ec="k", lw=1.0, alpha=0.85))
for x0 in (-SS["travel"] / 2 - SS["knob_w"] / 2, SS["travel"] / 2 - SS["knob_w"] / 2):
    a.add_patch(Rectangle((x0, f), SS["knob_w"], SS["knob"], fc="#c0541a", ec="k", lw=0.8, alpha=0.6 if x0 > 0 else 0.95))
for k in (-1, 0, 1):
    a.add_patch(Circle((k * 4.8, SS["pins_r"]), 0.8, fc="#c8a040", ec="k", lw=0.6))
    a.plot([k * 4.8, k * 4.8], [SS["pins_r"], f - d], color="#8a6a20", lw=1.6)
for s in (-1, 1):
    a.add_patch(Circle((s * 13.29 / 2, SS["tabs_r"]), 0.75, fc="#c8a040", ec="k", lw=0.6))
a.text(L / 2 + 0.3, f - d / 2, "SS-12D11G5R\n13.5 x 6.3 body", va="center", fontsize=8.5)
a.annotate(f"knob tip r {NEW_TIP:.1f}: 0.9 inside the wall\n(C&K's face: r {CK['face']}, 3.9 inside)", (0, NEW_TIP), (3.5, 44.5),
           fontsize=8.5, arrowprops=dict(arrowstyle="->"))
a.annotate(f"3 pins (d 1.6 holes, 4.8 pitch) at r {SS['pins_r']:.1f}:\nthe legs bend back under the PCB", (-4.8, SS["pins_r"]), (-15, 16.8),
           fontsize=8.5, arrowprops=dict(arrowstyle="->"))
a.annotate(f"2 case tabs (d 1.5) at r {SS['tabs_r']:.1f}", (13.29 / 2, SS["tabs_r"]), (5.5, 25.5), fontsize=8.5,
           arrowprops=dict(arrowstyle="->"))
a.annotate(f"C&K pins at r {CK['pins_r']}", (CK["pitch"], CK["pins_r"]), (9.5, 33.0), fontsize=8, color="#444",
           arrowprops=dict(arrowstyle="->", color="#444"))
a.set_xlim(-17, 17); a.set_ylim(15, 47); a.set_aspect("equal"); a.set_xlabel("t (mm)"); a.set_ylabel("r (mm)")

# ---- section through the slot (r vs z)
b.set_title("Section through the slot (r vs z, mm)", fontsize=11)
b.add_patch(Rectangle((15, PCB_Z), R_OUT - 15, PCB_T, fc="#1b6638", ec="k", lw=0.8)); b.text(16, PCB_Z + 0.35, "main PCB", color="w", fontsize=8)
b.add_patch(Rectangle((R_IN, 12), WALL, SLOT_Z - 12, fc="#d9d9d4", ec="k", lw=0.8))
b.add_patch(Rectangle((R_IN, SLOT_Z), WALL, PCB_Z - SLOT_Z, fc="white", ec="k", lw=0.6, ls=":"))
b.text(R_OUT + 0.3, SLOT_Z + 1, f"slot: {PCB_Z - SLOT_Z:.1f} high\n(C&K body 8.5)", fontsize=8)
f = CK["face"]
b.add_patch(Rectangle((f - CK["act"] - CK["depth"], PCB_Z - CK["h"]), CK["depth"], CK["h"], fc="#bbbbbb", ec="#555", ls="--", alpha=0.5))
b.add_patch(Rectangle((f - CK["act"], PCB_Z - CK["h"] / 2 - CK["act_h"] / 2), CK["act"], CK["act_h"], fc="#999", ec="#555", ls="--", alpha=0.6))
f = SS["face"]
b.add_patch(Rectangle((f - SS["depth"], PCB_Z - SS["h"]), SS["depth"], SS["h"], fc="#e8742a", ec="k", alpha=0.85))
b.add_patch(Rectangle((f, PCB_Z - SS["knob_zc"] - SS["knob_h"] / 2), SS["knob"], SS["knob_h"], fc="#c0541a", ec="k"))
b.plot([SS["pins_r"], SS["pins_r"], f - SS["depth"]], [PCB_Z + PCB_T + 0.8, PCB_Z - 1.6, PCB_Z - 1.6], color="#8a6a20", lw=2)
b.plot([SS["tabs_r"]] * 2, [PCB_Z + PCB_T + 0.8, PCB_Z - 0.3], color="#8a6a20", lw=2)
b.annotate("finger / nail in the slot\nmoves the knob 2.4 along the wall", (NEW_TIP, PCB_Z - 3.3), (25.0, 14.2), fontsize=8.5,
           arrowprops=dict(arrowstyle="->"))
b.annotate("pin and tab ends stand ~0.8 above the PCB:\nthe printed part above needs its relief moved", (SS["pins_r"], PCB_Z + PCB_T + 0.8), (15.5, 34.5),
           fontsize=8, arrowprops=dict(arrowstyle="->"))
b.set_xlim(15, 46); b.set_ylim(12, 37); b.set_aspect("equal")

c.text(0, 1, "\n".join([
    "                 C&K L101011  SS-12D11G5R",
    "LCSC             C2799508     C388633",
    r"price (1 pc)     \$7.12       \$0.50",
    "LCSC stock       0            16,985",
    "rating           4 A 28 V DC  3 A (125 V AC)",
    "contacts         SPST         SPDT (2 = common)",
    "body (t x r x h) 19.3x10.5x8.5 13.5x6.3x6.6",
    "actuator reach   3.9 in wall  0.9 in wall",
]), va="top", fontsize=7.6, family="monospace")
n.text(0, 1, "\n".join([
    "Change: power switch C&K L101011ML04Q -> XKB SS-12D11G5R",
    "(14x cheaper, in stock, rated 3 A: the cell's peak)",
    "- the wall slot stays (7.8 wide, 8.6 high); the knob sits at mid-height of it, 3 mm further out",
    "- KiCad: new footprint from its drawing (3 x d1.6 + 2 plated tab holes d1.5); SW1 -> SPDT symbol,",
    "  pin 2 common, pin 1 = on, pin 3 open; silkscreen ON / OFF arrow at the slot",
    "- FreeCAD: the printed part's SwitchRelief (r 27.9-30.7, for the C&K pins) moves to the new pins",
    "  and tabs; the C&K model is swapped for the SS-12D11 one (LCSC's STEP)",
    "- the legs reach in to r 22.1: nothing else is placed there yet (the battery holder ends at |y| ~10)",
    "Cheaper still (not drawn): a 5 c MSK12C02 switching a P-FET gate (+ 1 SI2333),",
    "  but that adds a FET in the 3 A path",
]), va="top", fontsize=8.6, family="monospace")
fig.suptitle("Power switch: the C&K L101011 vs the SS-12D11G5R (concept v1, to scale)", fontsize=14, weight="bold")
fig.savefig(OUT, dpi=110); print(OUT)
