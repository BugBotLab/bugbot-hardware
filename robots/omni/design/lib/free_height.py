# Free height under / over the main board at every point (0.25 mm grid, robot frame), over all five styles' 3D parts,
# OUTSIDE FreeCAD (OCP meshes; each triangle marks the cells under its bounding box: conservative).
# -> _place/free_height.npz: below = room under the underside (z 29) down to the first part, above = room over the top
# face (z 30.6) up to the first part; parts that cross the board plane (posts, wall) count as 0.
#   C:/Python312/python.exe design/lib/free_height.py
import json, os
import numpy as np
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape, TopoDS
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
Z0, Z1, RES, HALF, CAP = 29.0, 30.6, 0.25, 42.0, 25.0
N = int(2 * HALF / RES)
below = np.full((N, N), CAP); above = np.full((N, N), CAP); who_b = {}; who_a = {}
lab_b = np.full((N, N), -1, np.int32); lab_a = np.full((N, N), -1, np.int32); names = []
idx = lambda v: int(np.clip((v + HALF) / RES, 0, N - 1))
for dn in sorted(os.listdir(P + "styles")):
    for i, n in enumerate(json.load(open(f"{P}styles/{dn}/names.json"))):
        if "(KiCad)" in n and "NFC" not in n: continue              # the boards themselves (the NFC reader is a part here)
        sh = TopoDS_Shape(); BRepTools.Read_s(sh, f"{P}styles/{dn}/{i}.brep", BRep_Builder())
        BRepMesh_IncrementalMesh(sh, 0.3, False, 0.5, True)
        k = len(names); names.append(f"{dn.replace('BugBot_', '')}:{n}")
        e = TopExp_Explorer(sh, TopAbs_FACE)
        while e.More():
            loc = TopLoc_Location(); tri = BRep_Tool.Triangulation_s(TopoDS.Face_s(e.Current()), loc)
            if tri is not None:
                tr = loc.Transformation()
                pts = np.array([[p.X(), p.Y(), p.Z()] for p in (tri.Node(j).Transformed(tr) for j in range(1, tri.NbNodes() + 1))])
                for t in range(1, tri.NbTriangles() + 1):
                    a, b_, c = tri.Triangle(t).Get()
                    q = pts[[a - 1, b_ - 1, c - 1]]
                    zlo, zhi = q[:, 2].min(), q[:, 2].max()
                    i0, i1, j0, j1 = idx(q[:, 0].min()), idx(q[:, 0].max()), idx(q[:, 1].min()), idx(q[:, 1].max())
                    if zhi >= Z0 - CAP and zlo <= Z0:                   # under the board
                        h = max(0.0, Z0 - min(zhi, Z0)); blk = below[i0:i1 + 1, j0:j1 + 1]
                        m = h < blk; blk[m] = h; lab_b[i0:i1 + 1, j0:j1 + 1][m] = k
                    if zlo <= Z1 + CAP and zhi >= Z1:                   # over it
                        h = max(0.0, max(zlo, Z1) - Z1); blk = above[i0:i1 + 1, j0:j1 + 1]
                        m = h < blk; blk[m] = h; lab_a[i0:i1 + 1, j0:j1 + 1][m] = k
            e.Next()
np.savez_compressed(P + "free_height.npz", below=below, above=above, lab_b=lab_b, lab_a=lab_a, res=RES, half=HALF)
json.dump(names, open(P + "free_height_names.json", "w"))
print("free height map", N, "x", N, "from", len(names), "parts")
