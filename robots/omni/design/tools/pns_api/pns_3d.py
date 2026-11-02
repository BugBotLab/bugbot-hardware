# 3D checks for the pns_api tools, OUTSIDE KiCad/FreeCAD (OCP), run as a subprocess by pns_extras:
#   heights:  every component's height over / under the board vs. the MCAD "max height" regions
#   collide:  board components (KiCad STEP export) vs. an external STEP (the robot assembly): overlaps and small gaps
#   python pns_3d.py heights <board.step> <regions.json> <out.json>
#   python pns_3d.py collide <board.step> <external.step> <opts.json> <out.json>
import json, sys, time

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.gp import gp_Trsf, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform


def parts(path):
    """[(name, shape)] for the components of each top-level assembly (located), or the free shapes themselves."""
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True)
    if r.ReadFile(path) != 1:
        raise RuntimeError("cannot read " + path)
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name(l):
        n = TDataStd_Name()
        s = n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"
        return "board_body" if s.startswith("=>") else s
    free = TDF_LabelSequence(); st.GetFreeShapes(free)
    out = []
    for i in range(1, free.Length() + 1):
        root = free.Value(i)
        comps = TDF_LabelSequence(); st.GetComponents_s(root, comps, False)
        if comps.Length() == 0:
            out.append((name(root), st.GetShape_s(root)))
        for k in range(1, comps.Length() + 1):
            c = comps.Value(k)
            out.append((name(c), st.GetShape_s(c)))
    return out


def bbox(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); return b.Get()


def vertices(s, defl=0.1):
    BRepMesh_IncrementalMesh(s, defl, False, 0.5, True)
    pts = []
    e = TopExp_Explorer(s, TopAbs_FACE)
    while e.More():
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(TopoDS.Face_s(e.Current()), loc)
        if tri is not None:
            tr = loc.Transformation()
            for j in range(1, tri.NbNodes() + 1):
                q = tri.Node(j).Transformed(tr)
                pts.append((q.X(), q.Y(), q.Z()))
        e.Next()
    return pts


def heights(step, regions_path, out_path):
    from matplotlib.path import Path
    t0 = time.time()
    regions = json.load(open(regions_path))
    ps = parts(step)
    # the board body is the part with the largest footprint
    bi = max(range(len(ps)), key=lambda i: (lambda b: (b[3] - b[0]) * (b[4] - b[1]))(bbox(ps[i][1])))
    bb = bbox(ps[bi][1]); bot_z, top_z = bb[2], bb[5]
    comps = []
    for i, (n, s) in enumerate(ps):
        if i == bi:
            continue
        b = bbox(s)
        side = "top" if b[2] >= top_z - 0.3 else "bottom" if b[5] <= bot_z + 0.3 else "through"
        h = (b[5] - top_z) if side == "top" else (bot_z - b[2]) if side == "bottom" else max(b[5] - top_z, bot_z - b[2])
        comps.append({"ref": n, "side": side, "height": round(h, 3), "bbox": [b[0], -b[4], b[3], -b[1]], "_s": s})
    violations, checked = [], 0
    cache = {}
    for reg in regions:
        poly = [(x, -y) for x, y in reg["polygon"]]                # KiCad y-down -> STEP y-up
        path = Path(poly)
        xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
        for c in comps:
            if c["side"] not in (reg["side"], "through"):
                continue
            x0, y0, x1, y1 = c["bbox"]
            if x1 < min(xs) or x0 > max(xs) or -y0 < min(ys) or -y1 > max(ys):
                continue
            if c["ref"] not in cache:
                cache[c["ref"]] = vertices(c["_s"])
            pts = cache[c["ref"]]
            inside = [z for (x, y, z), ok in zip(pts, path.contains_points([(x, y) for x, y, _ in pts])) if ok]
            checked += 1
            if not inside:
                continue
            h = max(z - top_z for z in inside) if reg["side"] == "top" else max(bot_z - z for z in inside)
            if h > reg["max"] + 1e-6:
                violations.append({"ref": c["ref"], "part": reg["part"], "side": reg["side"], "max": reg["max"],
                                   "height": round(h, 3), "excess": round(h - reg["max"], 3), "label_at": reg["label_at"]})
    for c in comps:
        c.pop("_s")
    json.dump({"board_thickness": round(top_z - bot_z, 3), "components": comps, "violations": violations,
               "pairs_checked": checked, "seconds": round(time.time() - t0, 1)}, open(out_path, "w"))


def collide(board_step, ext_step, opts_path, out_path):
    t0 = time.time()
    o = json.load(open(opts_path))
    gap = o.get("gap", 0.5)
    dz = o.get("board_z", 0.0)
    import fnmatch
    pats = o.get("skip", [])
    skipped = lambda n: any(fnmatch.fnmatch(n, q) for q in pats)            # noqa: E731
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, dz))
    board = [(n, BRepBuilderAPI_Transform(s, tr, True).Shape()) for n, s in parts(board_step)]
    ext = parts(ext_step)
    eb = [(n, s, bbox(s)) for n, s in ext]
    overlaps, near, pairs = [], [], 0
    for bn, bs in board:
        if skipped(bn):
            continue
        b = bbox(bs)
        for en, es, e in eb:
            if skipped(en) or b[3] + gap < e[0] or e[3] + gap < b[0] or b[4] + gap < e[1] or e[4] + gap < b[1] \
                    or b[5] + gap < e[2] or e[5] + gap < b[2]:
                continue
            pairs += 1
            d = BRepExtrema_DistShapeShape(bs, es)
            if not d.IsDone():
                continue
            dist = d.Value()
            if dist <= 1e-6:
                common = BRepAlgoAPI_Common(bs, es).Shape()
                g = GProp_GProps(); BRepGProp.VolumeProperties_s(common, g)
                vol = g.Mass()
                if vol > o.get("min_volume", 1e-3):
                    overlaps.append({"board": bn, "part": en, "volume_mm3": round(vol, 4)})
                else:
                    near.append({"board": bn, "part": en, "gap": 0.0})
            elif dist < gap:
                near.append({"board": bn, "part": en, "gap": round(dist, 3)})
    json.dump({"overlaps": overlaps, "near": sorted(near, key=lambda x: x["gap"]), "pairs_checked": pairs,
               "board_parts": len(board), "external_parts": len(ext), "seconds": round(time.time() - t0, 1)},
              open(out_path, "w"))


if __name__ == "__main__":
    if sys.argv[1] == "heights":
        heights(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "collide":
        collide(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
