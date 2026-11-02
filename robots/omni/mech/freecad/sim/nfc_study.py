# NFC read-zone study (robot_io.NfcReader physics): where must a tag on the floor be, relative to the reader, to be read?
# Three antenna options for the base robot. The reader drive (amp-turns) is calibrated ONCE on the mini RC522's own coil
# (28 x 21 mm) to read a flat 25 mm NTAG213 coin straight below at 20 mm (ESTIMATE: measure the real module); the other
# antennas get the same drive. Moving tags: a read needs the tag in the field for one poll gap + one transaction.
#   C:/Python312/python.exe mech/freecad/sim/nfc_study.py
import os, sys, math, json
import numpy as np
import mujoco
# SimLink is a separate project, outside this repo: point SIMLINK_SIM at its simlink/sim folder
sys.path.insert(0, os.environ.get("SIMLINK_SIM", "C:/Users/Jerome/test_01111/simlink/SimLink/simlink/sim"))
from robot_io import NfcReader
HERE = os.path.dirname(os.path.abspath(__file__))
XML = '<mujoco><worldbody><site name="nfc" pos="0 0 0" quat="0 1 0 0"/></worldbody></mujoco>'   # z axis down
m = mujoco.MjModel.from_xml_string(XML); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
cal = NfcReader(m, "nfc", {"ant": "28x21", "range_mm": 20})
I0 = cal.I                                                    # the RC522's drive, from its own coil
TAG_Z = 0.45                                                  # tag coil mid-plane above the floor (0.9 mm coin)
OPTIONS = [
    ("A: custom round coil, 24 mm, flush in the floor at the centre", {"ant": "d24", "detune": 0.8}, 6.6),
    ("B: mini RC522 above the gearmotors (motors in between)", {"ant": "28x21", "detune": 0.5}, 16.0),
    ("C: mini RC522 flush in the floor (does not fit: reference)", {"ant": "28x21", "detune": 0.8}, 6.6),
]
xs = np.arange(-40, 40.01, 1.0) * 1e-3
res = {}
for name, p, z_ant in OPTIONS:
    r = NfcReader(m, "nfc", {**p, "range_mm": 20}); r.I = I0
    gap = (z_ant - TAG_Z) * 1e-3
    F = r.field_map(d, xs, xs, gap)                           # ratio field / h_min over the floor (flat tag)
    ok = F >= 1.0
    rad = [math.hypot(xs[ix], xs[iy]) for iy in range(len(xs)) for ix in range(len(xs)) if ok[iy, ix]]
    # straight passes: lateral offset y -> chord length through the zone (along x)
    passes = {}
    for y_mm in range(0, 41, 2):
        iy = int(round((y_mm * 1e-3 - xs[0]) / 1e-3))
        chord = ok[iy].sum() * 1e-3 if 0 <= iy < len(xs) else 0.0
        passes[y_mm] = chord
    need = r.poll + r.txn                                     # worst case: just missed a poll, then a full transaction
    speed = {}
    for v in (0.1, 0.3, 0.5):
        reads = [y for y, c in passes.items() if c / v >= need]
        speed[v] = max(reads) if reads else None
    # height: on-axis ratio vs gap (flat) and at a 4 deg tilt (a tag resting on another)
    gaps = np.arange(2, 31, 1.0)
    onaxis = [float(r.field_map(d, [0.0], [0.0], g * 1e-3)[0, 0]) for g in gaps]
    on_range = max([g for g, f in zip(gaps, onaxis) if f >= 1.0], default=0.0)
    res[name] = {"gap_mm": round(gap * 1000, 2), "ratio_centre": round(float(F[len(xs)//2, len(xs)//2]), 2),
                 "max_offset_mm": round(max(rad) * 1000, 1) if rad else 0.0,
                 "zone_width_x_mm": round(float(passes[0] * 1000), 1),
                 "max_lateral_offset_read_mm": speed, "on_axis_range_mm": on_range, "map": F.tolist()}
    print(f"{name}\n   gap {gap*1000:.1f} mm: centre field {F[len(xs)//2, len(xs)//2]:.2f} x h_min; reads out to {res[name]['max_offset_mm']} mm from the centre;"
          f" on-axis range {on_range:.0f} mm\n   max lateral offset that still reads at 0.1 / 0.3 / 0.5 m/s: {speed}")
json.dump({"options": [o[0] for o in OPTIONS], "xs_mm": (xs * 1000).tolist(), "res": res}, open(os.path.join(HERE, "nfc_study.json"), "w"))

# chart: read zones (top view, floor) for the three options
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 3, figsize=(15, 5.3))
for a, (name, p, z) in zip(ax, OPTIONS):
    F = np.array(res[name]["map"])
    cs = a.contourf(xs * 1000, xs * 1000, F, levels=[0, 0.5, 1, 2, 4, 8, 100], colors=["#f5f5f5", "#ffe0b2", "#a5d6a7", "#66bb6a", "#388e3c", "#1b5e20"])
    a.contour(xs * 1000, xs * 1000, F, levels=[1.0], colors="k", linewidths=1.5)
    if p["ant"].startswith("d"):
        a.add_patch(plt.Circle((0, 0), float(p["ant"][1:]) / 2, fill=False, ls="--", color="#6a1b9a"))
    else:
        w, h = [float(v) for v in p["ant"].split("x")]
        a.add_patch(plt.Rectangle((-w / 2, -h / 2), w, h, fill=False, ls="--", color="#6a1b9a"))
    a.add_patch(plt.Circle((0, 0), 12.5, fill=False, color="#8e4dd0", lw=0.8))
    a.set_title(name.split(":")[0] + f":  reads within {res[name]['max_offset_mm']:.0f} mm", fontsize=11)
    a.set_aspect("equal"); a.set_xlabel("tag centre x (mm, forward)"); a.set_ylabel("y (mm)"); a.grid(alpha=0.3)
fig.suptitle("Where a 25 mm NTAG213 on the floor gets read (green = field above the tag's 1.5 A/m; black line = edge)\n"
             "purple dashed = reader antenna, purple circle = a tag at the centre.  Drive calibrated: RC522 coil reads 20 mm straight below (ESTIMATE)", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "nfc_read_zone.png"), dpi=110)
print("chart:", os.path.join(HERE, "nfc_read_zone.png"))
