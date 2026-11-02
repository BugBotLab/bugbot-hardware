# Plug room of the main board's connectors against every style's 3D parts, OUTSIDE FreeCAD (OCP). For each connector
# the courtyard (+0.3 mm) is extruded away from the board on its side (bottom: down from the underside, top: up from
# the top face) and cut with every part; the free height is the distance to the first part it meets. A mated plug plus
# a cable bend needs NEED mm (per connector type). Inputs: _place/board_geom.json (export_geom.py), _place/styles/*.
#   C:/Python312/python.exe design/lib/plug_space.py
import json, os
from shapely.geometry import Polygon
from shapely.ops import unary_union
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Pnt, gp_Vec
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
P = BB + "/design/schematics/Main/_place/"
PCB_Z, PCB_T, REACH = 29.0, 1.6, 20.0
# mated height + cable bend, mm (JST SH vertical: 4.25 housing, plug seats flush, ~4 mm for the wires to turn)
NEED = {"JST_SH": 8.5, "JST_PH": 12.0, "PinSocket_1x04_P1.27": 10.0, "PinHeader_1x03_P2.54": 16.0}
SKIP = {"J1", "J6", "J22", "BT1"}                       # USB-C (side entry through the wall), board-to-board sockets, battery
g = json.load(open(P + "board_geom.json"))
def bb(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); return b.Get() if not b.IsVoid() else None
parts = []
for dn in sorted(os.listdir(P + "styles")):
    for i, n in enumerate(json.load(open(f"{P}styles/{dn}/names.json"))):
        sh = TopoDS_Shape(); BRepTools.Read_s(sh, f"{P}styles/{dn}/{i}.brep", BRep_Builder())
        parts.append((dn.replace("BugBot_", ""), n, sh, bb(sh)))
print(len(parts), "parts")
fpn = {}
import pcbnew_free_names if False else None
