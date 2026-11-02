# 3D check of the main board's parts against every style's parts, OUTSIDE FreeCAD (a loop like this inside FreeCAD crashed
# it twice). Inputs: schematics/Main/_place/board_parts.step (kicad-cli pcb export step --user-origin 100x100mm: robot frame,
# board underside at z 0) and _place/styles/<doc>/<i>.brep + names.json (exported from FreeCAD). Each board solid is named
# by the nearest footprint in placement.json / board_map.json. Plugs that sit in their sockets by design are skipped.
#   C:/Python312/python.exe design/lib/place_check3d.py      (run it memory-capped)
import json, math, os
from OCP.STEPControl import STEPControl_Reader
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
PCB_Z = 29.0                                                  # the board's underside in the robot


def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); return b.Get()


def vol(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()


r = STEPControl_Reader(); r.ReadFile(P + "board_parts.step"); r.TransferRoots()
tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, PCB_Z))
board = BRepBuilderAPI_Transform(r.OneShape(), tr, True).Shape()
solids = []
e = TopExp_Explorer(board, TopAbs_SOLID)
while e.More():
    s = e.Current(); b = bbox(s)
    if b[3] - b[0] < 60:                                      # not the PCB itself
        solids.append((s, b))
    e.Next()
pos = {}
for f in json.load(open(P + "board_map.json"))["fps"]:
    pos[f["ref"]] = (f["pos"][0], f["pos"][1], f["side"])
import sys
PL = sys.argv[1] if len(sys.argv) > 1 else "placement.json"      # the placement the board was built from (placement_v2.json)
for ref, v in json.load(open(P + PL)).items():
    pos[ref] = (v[0], v[1], v[3])


def name_of(b):
    cx, cy, cz = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2
    side = "B" if cz < PCB_Z + 0.8 else "F"
    cand = [(math.hypot(x - cx, y - cy), ref) for ref, (x, y, s) in pos.items() if s == side and not ref.startswith("H")]
    return min(cand)[1] if cand else "?"


bz = [b[2] for s, b in solids]
print(f"{len(solids)} board solids, z {min(bz):.1f}..{max(b[5] for s, b in solids):.1f}")
hits, near = [], []
for dn in sorted(os.listdir(P + "styles")):
    names = json.load(open(f"{P}styles/{dn}/names.json"))
    for i, n in enumerate(names):
        sh = TopoDS_Shape(); BRepTools.Read_s(sh, f"{P}styles/{dn}/{i}.brep", BRep_Builder()); ob = bbox(sh)
        for s, b in solids:
            M = 0.5                                           # boxes within 0.5 mm: test the clearance too
            if b[0] > ob[3] + M or b[3] < ob[0] - M or b[1] > ob[4] + M or b[4] < ob[1] - M or b[2] > ob[5] + M or b[5] < ob[2] - M:
                continue
            v = vol(BRepAlgoAPI_Common(s, sh).Shape())
            if v > 0.001:
                hits.append((dn.replace("BugBot_", ""), n.split("/")[-1], name_of(b), round(v, 3)))
            else:
                # clearance, cheaply: the part's box grown by 0.5 mm against the shape (exact gaps on the wheels' meshes
                # took over 40 minutes). A box is bigger than the part, so a flag here means "maybe under 0.5 mm".
                g = 0.5
                probe = BRepPrimAPI_MakeBox(gp_Pnt(b[0] - g, b[1] - g, b[2] - g), gp_Pnt(b[3] + g, b[4] + g, b[5] + g)).Shape()
                vv = vol(BRepAlgoAPI_Common(probe, sh).Shape())
                if vv > 0.001:
                    near.append((round(vv, 3), dn.replace("BugBot_", ""), n.split("/")[-1], name_of(b)))
by = {}
for st, part, ref, v in hits:
    by.setdefault((ref, part), []).append((st, v))
print(f"{len(hits)} overlaps")
for (ref, part), lst in sorted(by.items()):
    print(f"  {ref:6s} x {part:40s} {', '.join(f'{st} {v}' for st, v in lst)}")
best = {}
for g, st, part, ref in near:
    if (ref, part) not in best or g > best[(ref, part)][0]: best[(ref, part)] = (g, st)
print(f"maybe under 0.5 mm (part box + 0.5 touches it): {len(best)} pairs")
for (ref, part), (g, st) in sorted(best.items(), key=lambda kv: -kv[1][0])[:30]:
    print(f"  {ref:6s} - {part} ({st}; overlap of the grown box {g} mm3)")
json.dump({"hits": hits, "near": near}, open(P + "check3d.json", "w"))
