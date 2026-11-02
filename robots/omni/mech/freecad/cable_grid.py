# Voxel grid of the robot for cable routing / connector-spot searches (plain Python), shared by route_cables.py and
# j19_spot.py: the obstacle meshes from export_cable_scene.py, voxelised at 0.5 mm (surfaces sampled at 0.2 mm), with
# everything outside the body (r > 40 mm) blocked, and the distance-to-obstacle field.
import json, math, struct
import numpy as np
from scipy.ndimage import distance_transform_edt

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/mech/freecad/_cables/"
S = json.load(open(D + "scene.json"))
H = 0.5
LO = np.array([-46.0, -46.0, -3.0]); HI = np.array([46.0, 46.0, 72.0])
N = np.ceil((HI - LO) / H).astype(int) + 1


def read_stl(fn):
    b = open(fn, "rb").read()
    if b[:5] == b"solid" and b"facet" in b[:400]:                     # ascii
        v = [list(map(float, l.split()[1:4])) for l in b.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(v, dtype=float).reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return a["v"].reshape(-1, 3, 3).astype(float)


occ = np.zeros(N, dtype=bool)


def mark(pts):
    ijk = np.floor((pts - LO) / H).astype(int)
    ok = np.all((ijk >= 0) & (ijk < N), axis=1); ijk = ijk[ok]
    occ[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True


for name, g in S["groups"].items():  # noqa
    T = read_stl(g["stl"])
    while len(T):
        e = np.max(np.linalg.norm(T[:, [1, 2, 0]] - T, axis=2), axis=1)
        small = e <= 0.2
        mark(T[small].reshape(-1, 3)); mark(T[small].mean(axis=1))
        B = T[~small]
        if not len(B): break
        a, b, c = B[:, 0], B[:, 1], B[:, 2]; ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        T = np.concatenate([np.stack([a, ab, ca], 1), np.stack([ab, b, bc], 1), np.stack([ca, bc, c], 1), np.stack([ab, bc, ca], 1)])
gx, gy = np.meshgrid(LO[0] + (np.arange(N[0]) + 0.5) * H, LO[1] + (np.arange(N[1]) + 0.5) * H, indexing="ij")
occ |= (np.hypot(gx, gy) > 40.0)[:, :, None]                          # nothing may leave the body (shell r 40.6)
dist = distance_transform_edt(~occ) * H                               # mm to the nearest obstacle surface
cell = lambda p: tuple(np.floor((np.asarray(p) - LO) / H).astype(int))
centre = lambda c: LO + (np.asarray(c) + 0.5) * H
