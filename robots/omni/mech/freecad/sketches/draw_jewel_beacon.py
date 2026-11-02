# 2D (to scale): the LED beacon as a bought 7 x WS2812B-5050 "jewel" (Ø23, AliExpress ~£1) instead of our LED ring PCB
# (2026-10-31: one JLC board design less). Plan of the top deck under the dome, and a section through the beacon.
# Mount: 2 mm double-sided foam pad on the deck, wires from the deck's Ø6.5 hole soldered to the jewel's back pads in the
# pad's gap. The ring board's 2 screw bosses stay (unused) so the deck does not change for the prototypes.
# usage: python draw_jewel_beacon.py out.png
import sys, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon as MPoly
OUT = sys.argv[1]
exec(open("../bugbot_params.py", encoding="utf-8").read())               # PARAMS: name, expression, note
V = {n: e for n, e, *_ in PARAMS}
def mm(n): return float(V[n].split()[0])
DECK_R, DOME_D, DOME_WALL, WIRE_HOLE = mm("deck_r"), mm("dome_d"), mm("dome_wall"), 6.5
SCREW_R, DECK_T = mm("led_screw_r"), mm("deck_t")
JEWEL_D, JEWEL_T, LED, LED_H, LED_R = 23.0, 1.6, 5.0, 1.6, 8.0           # jewel: board Ø, thickness; 5050 LED size, height; ring radius
FOAM_T = 2.0                                                             # double-sided foam pad (wires run in its gap)
LED_A0 = 30.0                                                            # outer LEDs at 30 + 60 k deg: the screw bosses (0 / 180) fall between them
fig = plt.figure(figsize=(16, 8.6))
ax = fig.add_axes([0.03, 0.08, 0.42, 0.8])
ax.add_patch(Circle((0, 0), DECK_R, fc="#d6d6cc", ec="#555", lw=1, zorder=0))
ax.add_patch(Circle((0, 0), DOME_D / 2 - DOME_WALL, fc="none", ec="#1e88e5", ls="--", lw=1.2, zorder=6))
ax.add_patch(Circle((0, 0), DOME_D / 2, fc="none", ec="#1e88e5", lw=1.2, zorder=6))
for sg in (1, -1): ax.add_patch(Circle((sg * SCREW_R, 0), 1.2, fc="#9e9e9e", ec="#333", zorder=1))
ax.add_patch(Circle((0, 0), JEWEL_D / 2, fc="#263238", ec="#000", lw=1, alpha=0.9, zorder=2))
for k in range(7):
    cx, cy = (0, 0) if k == 0 else (LED_R * math.cos(math.radians(LED_A0 + 60 * (k - 1))), LED_R * math.sin(math.radians(LED_A0 + 60 * (k - 1))))
    ax.add_patch(Rectangle((cx - LED / 2, cy - LED / 2), LED, LED, fc="#fafafa", ec="#333", lw=0.6, zorder=3))
    ax.add_patch(Circle((cx, cy), 1.6, fc="#fff9c4", ec="#bbb", lw=0.4, zorder=4))
ax.add_patch(Circle((0, 0), WIRE_HOLE / 2, fc="none", ec="#6a1b9a", ls=":", lw=1.2, zorder=5))
ax.annotate(f"jewel Ø{JEWEL_D:g}: 7 x WS2812B-5050\n(our ring: 8 x tiny 2020 on Ø25.6)", (0, -JEWEL_D / 2 + 1), (-19, -22), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate(f"dome inside Ø{DOME_D - 2 * DOME_WALL:.1f}:\n{(DOME_D - 2 * DOME_WALL - JEWEL_D) / 2:.1f} mm round the jewel", (DOME_D / 2 - DOME_WALL, 0), (9, 19), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate("old ring's screw bosses\n(kept, unused)", (-SCREW_R, 0), (-21, 17), fontsize=9, arrowprops=dict(arrowstyle="->"))
ax.annotate(f"wires up through the deck's\nØ{WIRE_HOLE:g} hole (purple)", (0, -WIRE_HOLE / 2), (5, -22), fontsize=9, arrowprops=dict(arrowstyle="->", color="#6a1b9a"))
ax.set_aspect("equal"); ax.set_xlim(-22, 22); ax.set_ylim(-24, 22); ax.grid(alpha=0.2)
ax.set_title("Plan, top deck from above (front = right); dome blue", fontsize=10)
s = fig.add_axes([0.5, 0.48, 0.48, 0.4]); Z = 1.0
z0 = 0.0
def bx(x0, x1, z_0, z_1, fc, ec="#333", **k): s.add_patch(Rectangle((x0, z_0), x1 - x0, z_1 - z_0, fc=fc, ec=ec, lw=0.8, **k))
bx(-DECK_R, DECK_R, z0 - DECK_T, z0, "#d6d6cc"); s.text(-DECK_R + 0.5, z0 - DECK_T + 0.5, "top deck 2.0", fontsize=8)
bx(-WIRE_HOLE / 2, WIRE_HOLE / 2, z0 - DECK_T, z0, "white", ec="#6a1b9a")
for x0, x1 in ((-9.5, -3.5), (3.5, 9.5)): bx(x0, x1, z0, z0 + FOAM_T, "#ffcc80")
s.text(6.5, z0 + 0.6, "foam 2", fontsize=7.5, ha="center")
zb = z0 + FOAM_T
bx(-JEWEL_D / 2, JEWEL_D / 2, zb, zb + JEWEL_T, "#263238"); s.text(-JEWEL_D / 2 + 0.3, zb + 0.4, "jewel PCB 1.6", fontsize=7.5, color="white")
for cx in (-LED_R * math.cos(math.radians(LED_A0)), 0, LED_R * math.cos(math.radians(LED_A0))):
    bx(cx - LED / 2, cx + LED / 2, zb + JEWEL_T, zb + JEWEL_T + LED_H, "#fafafa")
s.plot([0, 0, -2.5], [z0 - DECK_T - 3, z0 + 0.7, zb - 0.2], color="#e0b040", lw=2)
s.text(0.6, z0 - DECK_T - 2.6, "3 wires from main J4 (5V DIN GND), soldered to the back pads", fontsize=7.5)
th = [math.radians(a) for a in range(0, 181, 3)]
zc = z0 + mm("dome_groove") * 0 + 2.5                                    # dome hemisphere centre, roughly (bayonet collar below)
s.plot([(DOME_D / 2) * math.cos(t) for t in th], [zc + (DOME_D / 2) * math.sin(t) for t in th], color="#1e88e5", lw=1.2)
s.plot([(DOME_D / 2 - DOME_WALL) * math.cos(t) for t in th], [zc + (DOME_D / 2 - DOME_WALL) * math.sin(t) for t in th], color="#1e88e5", lw=1, ls="--")
top = zb + JEWEL_T + LED_H
s.annotate(f"LED tops {top:.1f} above the deck; dome inside top ~{zc + DOME_D / 2 - DOME_WALL:.0f}", (0, top), (2, top + 6), fontsize=8, arrowprops=dict(arrowstyle="->"))
s.set_aspect("equal"); s.set_xlim(-20, 20); s.set_ylim(-7, 20); s.grid(alpha=0.2)
s.set_title("Section through the beacon (true scale)", fontsize=10)
t = fig.add_axes([0.5, 0.03, 0.48, 0.38]); t.axis("off")
t.text(0, 1, "\n".join([
 "What changes:",
 "  - LED ring PCB (JLC, 8 x WS2812B-2020 + level shifter): GONE",
 "  - bought 7-LED WS2812B-5050 'jewel', Ø23 (22-23 by seller), ~£1 each",
 "  - main board already shifts the data to 5 V (U13 by J4): no shifter needed",
 "  - held by a 2 mm double-sided foam pad (two pieces, wires between them);",
 "    no printed change for the prototypes. Later: a printed seat on the old",
 "    two screws if the foam is not tough enough for crashes",
 "  - 5050 LEDs are brighter than the 2020s; max ~0.4 A at full white",
 "    (firmware caps the brightness, as now)",
 "",
 "Check on the jewel you buy: diameter, where its 4 back pads are",
 "(5V / GND / DIN / DOUT), and that the LEDs are WS2812B / SK6812 (5 V)."]),
 va="top", fontsize=9, family="monospace")
fig.suptitle("LED beacon: bought 7-LED jewel instead of our LED ring board (2D for approval, to scale)", fontsize=14, fontweight="bold", x=0.02, ha="left")
plt.savefig(OUT, dpi=100); print("saved", OUT)
