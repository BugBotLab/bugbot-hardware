# Floor plan v2, 3D fix: each part the 3D check flags (inside a style part, or its box + 0.5 mm touching one) moves to the
# nearest spot round its v2 position that is legal on the board (place_v2's rules) AND clear in 3D (place_check3d's
# test: the part's box grown by 0.5 mm shares no volume with any style part). Outside FreeCAD (OCP), as the check.
# (The 3D bodies are those of the board as built, at the part's current spot; a v1 search assumes the same turn.)
# Reads _place/board_parts.step (exported from the board built from placement_v2.json); writes placement_v2.json.
#   C:/Python312/python.exe design/lib/place_v2_fix3d.py U13,C17,...
import sys, json, math, os
refs = sys.argv[1].split(",")
sys.argv = [sys.argv[0], "1"]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/design/lib/place_v2.py").read().split("geoms = {r: (outline(r)")[0])
from OCP.STEPControl import STEPControl_Reader
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
PCB_Z = 29.0
def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); return b.Get()
def vol(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()

v2 = json.load(open(P + "placement_v2.json"))
for r in MOVE: state[r] = (v2[r][0], v2[r][1], int(v2[r][2]), v2[r][3])
geoms = {r: (outline(r), state[r][3]) for r in MOVE}
# board solids, named by the nearest part on their side (as the check does)
rd = STEPControl_Reader(); rd.ReadFile(P + "board_parts.step"); rd.TransferRoots()
tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, PCB_Z))
board3d = BRepBuilderAPI_Transform(rd.OneShape(), tr, True).Shape()
pos = {f["ref"]: (f["pos"][0], f["pos"][1], f["side"]) for f in json.load(open(P + "board_map.json"))["fps"]}
pos.update({r: (v[0], v[1], v[3]) for r, v in v2.items()})
boxes = {}
e = TopExp_Explorer(board3d, TopAbs_SOLID)
while e.More():
    b = bbox(e.Current())
    if b[3] - b[0] < 60:
        cx, cy, cz = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2
        side = "B" if cz < PCB_Z + 0.8 else "F"
        cand = [(math.hypot(x - cx, y - cy), r) for r, (x, y, s) in pos.items() if s == side and not r.startswith("H")]
        if cand: boxes.setdefault(min(cand)[1], []).append(b)
    e.Next()
style = []
for dn in sorted(os.listdir(P + "styles")):
    for i, n in enumerate(json.load(open(f"{P}styles/{dn}/names.json"))):
        sh = TopoDS_Shape(); BRepTools.Read_s(sh, f"{P}styles/{dn}/{i}.brep", BRep_Builder())
        style.append((dn, n, sh, bbox(sh)))


def clear3d(ref, dx, dy, g=0.5):
    for b in boxes.get(ref, []):
        lo = (b[0] + dx - g, b[1] + dy - g, b[2] - g); hi = (b[3] + dx + g, b[4] + dy + g, b[5] + g)
        probe = None
        for dn, n, sh, ob in style:
            if lo[0] > ob[3] or hi[0] < ob[0] or lo[1] > ob[4] or hi[1] < ob[1] or lo[2] > ob[5] or hi[2] < ob[2]: continue
            probe = probe or BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Shape()
            if vol(BRepAlgoAPI_Common(probe, sh).Shape()) > 0.001: return False
    return True


for r in refs:                                       # "REF@v1": search round its v1 spot instead
    r, _, start = r.partition("@")
    if r not in state: print(r, "is not a movable part: skipped"); continue
    xs, ys, a, side = state[r]
    x0, y0 = (placed[r][0], placed[r][1]) if start == "v1" else (xs, ys)
    if start == "v1": a, side = int(placed[r][2]), placed[r][3]
    if r not in boxes: print(r, "has no 3D body on the board: skipped"); continue
    done = None
    for rad in [k * 0.25 for k in range(0, 33)]:
        for t in (range(0, 360, 15) if rad else [0]):
            dx, dy = rad * math.cos(math.radians(t)), rad * math.sin(math.radians(t))
            st = (round((x0 + dx) / 0.05) * 0.05, round((y0 + dy) / 0.05) * 0.05, a, side)
            keep = (state[r], geoms[r]); state[r] = st; geoms[r] = (outline(r, st), side)
            if legal_hard(r, st) and overlap_of(r, geoms) == 0 and clear3d(r, st[0] - xs, st[1] - ys):
                done = (rad, st); break
            state[r], geoms[r] = keep
        if done: break
    if done:
        v2[r] = [done[1][0], done[1][1], a, side, 0]
        print(f"{r}: {'already clear' if done[0] == 0 else f'moved {done[0]} mm'}")
    else:
        print(f"{r}: NO clear spot within 8 mm")
json.dump(v2, open(P + "placement_v2.json", "w"), indent=0)
