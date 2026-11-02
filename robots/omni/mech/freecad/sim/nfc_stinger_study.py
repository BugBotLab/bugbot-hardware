# NFC "stinger" study: robot A carries an NTAG213 coin on a low tongue at its front; it is read when it slides under
# robot B's floor, by B's edge loop (kicad/BugBot_NFCfloor: 3 turns round the floor outline, top copper against the floor).
#   C:/Python312/python.exe mech/freecad/sim/nfc_stinger_study.py
# Physics as robot_io.NfcReader: Biot-Savart field of the real copper path (floor_geom.json spiral), averaged over the tag's
# coil along its normal; read when it reaches h_min. Drive current: the same WS1850S as the old centre coil, so the same
# current per turn as that coil needed for its 15 mm read range (sim_profile: ESTIMATE until the first boards are measured).
# Outputs: nfc_stinger_map.png / .json (B's read zone at the tag height, "how far under the rim"), the speed limit
# (time in the zone vs poll + transaction), and A's own reader on A's own stinger.
import json, math, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "bugbot_freecad"))
import sim_profile as SP
G = json.load(open(os.path.join(ROOT, "design/schematics/NFCfloor/floor_geom.json")))
H_MIN, TAG_D, DETUNE = 1.5, SP.NFC["tag_coil"] * 1e-3, SP.NFC["detune"]
POLL, TXN = SP.NFC["poll_ms"] * 1e-3, SP.NFC["txn_ms"] * 1e-3
Z_COPPER = 6.5e-3                         # the loop: top copper of the floor board, against the floor underside
Z_TAGS = [1.5e-3, 2.5e-3, 3.5e-3]         # tag mid-plane on the stinger (the tongue: 1.5-3.5 mm over the mat)


def segs_of(pts, z):
    P = np.c_[np.asarray(pts) * 1e-3, np.full(len(pts), z)]
    return P[:-1], P[1:]


def field_z(A, B, X, I=1.0):
    """Hz (A/m) at points X (N x 3) from straight segments A->B (M x 3) carrying I (Biot-Savart, exact per segment)."""
    out = np.zeros(len(X))
    for k in range(0, len(X), 4000):
        x = X[k:k + 4000][:, None, :]
        r1, r2 = x - A[None], x - B[None]
        n1, n2 = np.linalg.norm(r1, axis=2), np.linalg.norm(r2, axis=2)
        cr = np.cross(r1, r2)
        den = n1 * n2 * (n1 * n2 + (r1 * r2).sum(2)) + 1e-30
        out[k:k + 4000] = (I / (4 * math.pi) * cr[..., 2] * (n1 + n2) / den).sum(1)
    return out


def tag_pts(r):
    pts = [(0.0, 0.0)]
    for ring in (0.33, 0.66, 1.0):
        n = int(8 * ring * 3)
        pts += [(ring * r * math.cos(2 * math.pi * k / n), ring * r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return np.array(pts)


TP = tag_pts(TAG_D / 2)


def coupling(A, B, centres, z, I):
    X = np.concatenate([np.c_[c[0] + TP[:, 0], c[1] + TP[:, 1], np.full(len(TP), z)] for c in centres])
    return np.abs(field_z(A, B, X, I).reshape(len(centres), len(TP)).mean(1))


# ---- the drive current: the old centre coil (one equivalent loop, d18.3, 8 turns) read 15 mm on axis ----
th = np.linspace(0, 2 * math.pi, 65); rr = 18.3e-3 / 2
OA, OB = segs_of(np.c_[rr * 1e3 * np.cos(th), rr * 1e3 * np.sin(th)], 0.0)
hz1 = abs(field_z(OA, OB, np.array([[0, 0, -SP.NFC["range_mm"] * 1e-3]]))[0])
I_AT = H_MIN / hz1                         # amp-turns the old model needed
I_TURN = I_AT / 8 * DETUNE                 # per turn (8 turns), with the same detune for the motors above the floor
SA, SB = segs_of(G["spiral"], Z_COPPER)    # the edge loop, 3 turns: current I_TURN in every turn
rim = Polygon(G["outline"][0]) if len(G["outline"][0]) > 10 else None
outer = max((Polygon(o) for o in G["outline"]), key=lambda p: p.area)
print(f"drive: old model {I_AT * 1e3:.0f} mA-turns -> {I_TURN * 1e3:.0f} mA per turn in the edge loop (ESTIMATE)")

# ---- B's read zone at each tag height: a grid over B's floor ----
xs = np.arange(-50, 50.1, 1.0); ys = np.arange(-50, 50.1, 1.0)
GX, GY = np.meshgrid(xs, ys); C = np.c_[GX.ravel(), GY.ravel()] * 1e-3
maps = {}
for z in Z_TAGS:
    maps[z] = coupling(SA, SB, C, z, I_TURN).reshape(GX.shape) / H_MIN
# radial lines every 10 deg: k(r) per height (field / ISO minimum at the assumed current), for the current multipliers
RAD = {}
for z in Z_TAGS:
    for a in range(0, 360, 10):
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        rim_r = max(t for t in np.arange(0, 45, 0.25) if outer.contains(Point(t * ux, t * uy)))
        rs = np.arange(rim_r + 15, 0, -0.5)
        RAD[(z, a)] = (rim_r, rs, coupling(SA, SB, np.c_[rs * ux, rs * uy] * 1e-3, z, I_TURN) / H_MIN)
front_rim = max(t for t in np.arange(0, 45, 0.25) if outer.contains(Point(t, 0)))
OWN = {}
for z in Z_TAGS:
    for gap in (0.0, 2.0, 5.0, 10.0):
        cx = (front_rim + gap) * 1e-3 + TAG_D / 2 + 1e-3
        OWN[(z, gap)] = float(coupling(SA, SB, [(cx, 0.0)], z, I_TURN)[0] / H_MIN)
MULT = (1.0, 1.5, 2.0, 3.0)
res = {"I_turn_mA_x1": round(I_TURN * 1e3, 1), "need_ms": (POLL + TXN) * 1e3, "front_rim_x": front_rim, "by_current": {}}
for mlt in MULT:
    out = {}
    for z in Z_TAGS:
        fr, dz, peaks = [], [], []
        for a in range(0, 360, 10):
            rim_r, rs, k = RAD[(z, a)]
            inside = rim_r - rs; read = inside[k * mlt >= 1.0]; peaks.append(float(k.max() * mlt))
            if len(read):
                fr.append(float(read.min())); dz.append(float(read.max() - read.min()))
        out[f"z {z * 1e3:.1f}"] = {"angles_read": f"{len(fr)} of 36",
                                   "tag_centre_first_read_inside_rim_mm": round(float(np.median(fr)), 1) if fr else None,
                                   "zone_depth_mm_median": round(float(np.median(dz)), 1) if dz else 0.0,
                                   "max_speed_m_s_straight_in": round(float(np.median(dz)) * 1e-3 / ((POLL + TXN)), 2) if dz else 0.0,
                                   "own_stinger_x_hmin_max": round(max(v for (zz, g), v in OWN.items() if zz == z) * mlt, 2)}
    res["by_current"][f"x{mlt:g} ({I_TURN * mlt * 1e3:.0f} mA/turn)"] = out
json.dump(res, open(os.path.join(HERE, "nfc_stinger_map.json"), "w"), indent=1)
np.savez(os.path.join(HERE, "nfc_stinger_maps.npz"), GX=GX, GY=GY, **{f"z{z * 1e4:.0f}": maps[z] for z in Z_TAGS})
fig, axs = plt.subplots(1, 3, figsize=(19, 6.6))
for ax, z in zip(axs, Z_TAGS):
    im = ax.contourf(GX, GY, np.clip(maps[z], 0, 1.2), levels=[0, 0.2, 1 / 3, 0.5, 2 / 3, 1.0, 1.2], cmap="Greens")
    cs = ax.contour(GX, GY, maps[z], levels=[1 / 3, 0.5, 2 / 3, 1.0], colors=["#1b5e20", "#2e7d32", "#43a047", "k"], linewidths=[1, 1, 1, 1.6])
    ax.clabel(cs, fmt={1 / 3: "x3", 0.5: "x2", 2 / 3: "x1.5", 1.0: "x1"}, fontsize=8)
    for o in G["outline"]:
        o = np.asarray(o); ax.plot(o[:, 0], o[:, 1], color="#c77800", lw=1)
    ax.add_patch(plt.Circle((front_rim + 1 + TAG_D * 500, 0), TAG_D * 500, fill=False, ls="--", color="#6a1b9a"))
    ax.set_title(f"tag at z {z * 1e3:.1f} mm: read inside the black line", fontsize=11)
    ax.set_aspect("equal"); ax.set_xlim(-50, 50); ax.set_ylim(-50, 50); ax.grid(alpha=0.2)
fig.colorbar(im, ax=axs, label="field over the tag / ISO minimum at x1 current; lines: read limit at x1 / x1.5 / x2 / x3")
fig.suptitle(f"Edge loop read zone for a 25 mm NTAG213 lying flat under the robot (3 turns, {I_TURN * 1e3:.0f} mA per turn, ESTIMATE); "
             "dashed purple: this robot's own stinger tag", fontsize=12)
plt.savefig(os.path.join(HERE, "nfc_stinger_map.png"), dpi=90)
print(json.dumps(res, indent=1))
