# 2D concept (to scale): the NFC reader board held by one M2 screw instead of the tray's snap clips.
# Board coordinates as in KiCad (mm, x along the board, y down from its top edge); tray / post heights from nfc_layout.py.
#   C:/Python312/python.exe mech/freecad/sketches/draw_nfc_screw.py   -> sketches/nfc_screw_v2.png
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nfc_screw_v2.png")
PARTS = {"C1": (6.5, 7.5, 2.4, 4.3), "C10": (16.8, 17.8, 12.5, 14.4), "C11": (19.1, 21.0, 16.2, 17.2), "C12": (15.7, 17.6, 14.9, 15.9),
         "C13": (17.1, 19.0, 16.2, 17.2), "C14": (11.7, 12.7, 12.5, 14.4), "C15": (8.3, 9.3, 12.5, 14.4), "C16": (9.5, 10.5, 12.5, 14.4),
         "C17": (12.9, 13.9, 13.5, 15.4), "C18": (6.9, 7.9, 12.5, 14.4), "C2": (12.5, 13.5, 2.4, 4.3), "C3": (13.6, 14.6, 2.7, 4.6),
         "C4": (14.5, 16.4, 8.9, 9.9), "C5": (12.9, 14.8, 12.3, 13.3), "C6": (15.7, 17.6, 2.1, 3.1), "C7": (16.8, 17.8, 3.7, 5.6),
         "C8": (17.1, 19.0, 0.8, 1.8), "C9": (19.1, 21.0, 0.8, 1.8), "J1": (0.4, 5.7, 3.1, 15.0), "J2": (20.6, 25.9, 8.6, 14.5),
         "L1": (15.1, 16.6, 3.9, 6.9), "L2": (15.1, 16.6, 11.1, 14.1), "R1": (13.8, 14.8, 4.9, 6.8), "R3": (14.5, 16.4, 7.5, 8.5),
         "R4": (19.7, 21.2, 2.7, 5.7), "R5": (18.9, 20.4, 12.3, 15.3), "R6": (10.1, 12.0, 14.5, 15.5), "R7": (5.9, 7.8, 4.7, 5.7),
         "U1": (7.4, 13.7, 5.9, 12.6), "Y1": (7.9, 12.2, 1.6, 5.1)}
POSTS = [(25.0, 3.0), (26.5, 15.5), (7.5, 3.0)]          # the tray's 3 chassis posts under the board (v2: post 1 moved)
OLD_POST1 = (26.5, 2.5)
HOLE, HEAD = (25.0, 3.0), 3.8                             # the new hole over post 1; M2 pan head diameter
TRAY_Z, TRAY_T, BOARD_T, POST_D = 16.2, 2.6, 1.6, 5.0
TRAY_TOP = TRAY_Z + TRAY_T; SEAT_Z = TRAY_TOP - 1.6

fig = plt.figure(figsize=(15, 8.6))
a = fig.add_axes([0.03, 0.12, 0.52, 0.72]); b = fig.add_axes([0.60, 0.30, 0.37, 0.55]); n = fig.add_axes([0.575, 0.02, 0.42, 0.25]); n.axis("off")

# ---- top view of the reader board on its tray ----
a.set_title("NFC reader board on its tray, from above (board coordinates, mm)", fontsize=11)
a.add_patch(Rectangle((-1.0, -1.0), 30.0, 20.0, fc="#cfcfca", ec="k", lw=0.8))                 # tray (simplified)
a.add_patch(Polygon([(0, 0), (28, 0), (28, 10.62), (26.43, 10.62), (26.43, 12.43), (28, 12.43), (28, 18), (0, 18)],
                    fc="#1b6638", ec="k", lw=1.0))
for k, (x0, x1, y0, y1) in PARTS.items():
    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#222" if k[0] in "JUY" else "#9a8a6a", ec="none"))
    if k[0] in "JUY":
        a.text((x0 + x1) / 2, (y0 + y1) / 2, k, color="w", ha="center", va="center", fontsize=8)
for i, (x, y) in enumerate(POSTS):
    a.add_patch(Circle((x, y), POST_D / 2, fc="none", ec="#555", lw=0.9, ls="--"))
    a.text(x + 2.7, y + 0.2, f"post {i + 1}", fontsize=7, color="#333")
for y0, y1 in ((-1.0, -0.3), (18.3, 19.0)):                                                      # the 2 snap clips (go)
    a.add_patch(Rectangle((10.0, y0), 8.0, y1 - y0, fc="#e04040", ec="k", lw=0.6, hatch="xx", alpha=0.8))
a.text(14.0, -1.6, "snap clip: REMOVED", ha="center", fontsize=8, color="#b00000")
a.text(14.0, 19.8, "snap clip: REMOVED", ha="center", fontsize=8, color="#b00000")
a.add_patch(Rectangle((28.3, 1.0), 0.6, 7.0, fc="#888", ec="k", lw=0.6)); a.add_patch(Rectangle((-0.9, 5.0), 0.6, 8.0, fc="#888", ec="k", lw=0.6))
a.text(29.2, 4.0, "end stop\n(kept)", fontsize=7)
a.add_patch(Circle(OLD_POST1, POST_D / 2, fc="none", ec="#b00000", lw=0.7, ls=":")); a.text(28.6, -0.4, "post 1 was here", fontsize=6.5, color="#b00000")
a.add_patch(Circle(HOLE, 2.6, fc="none", ec="#f5c242", lw=1.0, ls=":"))                          # ground-pour clearance
a.add_patch(Circle(HOLE, HEAD / 2, fc="#e8742a", ec="k", lw=1.0)); a.add_patch(Circle(HOLE, 1.1, fc="white", ec="k", lw=0.6))
a.annotate("NEW: M2 screw through a 2.2 hole at (25.0, 3.0):\n1.9 mm of board to each edge; parts >= 3.8 away;\nthe antenna track 2.7 from the centre",
           HOLE, (17.5, -5.5), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
a.text(27.3, 11.5, "cable\nnotch", fontsize=6.5, ha="right")
a.set_xlim(-3, 33); a.set_ylim(22, -7.5); a.set_aspect("equal"); a.set_xlabel("x (mm)"); a.set_ylabel("y (mm)")

# ---- section through post 1 ----
b.set_title("Section through post 1 (z, mm)", fontsize=11)
b.add_patch(Rectangle((-POST_D / 2, 8.0), POST_D, TRAY_Z - 8.0, fc="#d9d9d4", ec="k", lw=0.8)); b.text(2.8, 11, "chassis post", fontsize=8)
b.add_patch(Rectangle((-7, TRAY_Z), 14, TRAY_T, fc="#cfcfca", ec="k", lw=0.8)); b.text(-6.7, TRAY_Z + 0.9, "tray", fontsize=8)
b.add_patch(Rectangle((-2.1, SEAT_Z), 4.2, 1.6, fc="white", ec="k", lw=0.5, ls=":"))
b.add_patch(Rectangle((-7, TRAY_TOP), 8.5, BOARD_T, fc="#1b6638", ec="k", lw=0.8)); b.text(-6.7, TRAY_TOP + 0.4, "reader board", color="w", fontsize=8)
top = TRAY_TOP + BOARD_T; L = 8.0
b.add_patch(Rectangle((-1.0, top - L), 2.0, L, fc="#e8742a", ec="k", lw=0.8))
b.add_patch(Polygon([(-1.9, top), (1.9, top), (1.6, top + 1.4), (-1.6, top + 1.4)], fc="#e8742a", ec="k", lw=0.8))
b.add_patch(Rectangle((-0.8, 10.7), 1.6, TRAY_Z - 10.7, fc="none", ec="k", lw=0.5, ls="--"))
b.annotate(f"M2 x {L:.0f} pan, from the top:\nboard + tray + {TRAY_Z - (top - L):.1f} into the post", (1.9, top + 0.7), (3.0, 24.5), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
b.annotate("old counterbore (from the\nunder-board screw): left empty", (2.1, SEAT_Z + 0.8), (3.4, 15.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
b.annotate("existing pilot (to z 10.7)", (0.8, 11.5), (2.8, 9.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
b.set_xlim(-7.5, 12); b.set_ylim(7.5, 26); b.set_aspect("equal")

n.text(0, 1, "\n".join([
    "Change: the reader board is screwed down instead of clipped.",
    "- KiCad (BugBot_NFC): one 2.2 mm hole at (25.0, 3.0), 2.6 mm clearance in the GND",
    "  pour; 1.9 mm of board to the edges (v1 left only 0.4 mm: it would crack)",
    "- post 1 moves 1.5 in / 0.5 across to sit under it (still >= 1.8 from the motors)",
    "- tray: the 2 snap clips go; the 2 end stops stay (they locate the board)",
    "- post 1: its under-board M2x6 becomes an M2x8 from the top, through board +",
    "  tray into the same pilot (3.8 mm of thread in the post); posts 2 and 3 unchanged",
    "- one screw + the end stops + the tray under it: the board cannot lift or slide",
]), va="top", fontsize=8.3, family="monospace")
fig.suptitle("NFC reader board: a screw instead of snap clips (concept v2, to scale)", fontsize=14, weight="bold")
fig.savefig(OUT, dpi=110); print(OUT)
