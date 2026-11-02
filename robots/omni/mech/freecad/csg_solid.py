# Turn an OpenSCAD .csg file into one FreeCAD B-rep shape (true faces and edges, not triangles).
# Parts that OpenSCAD itself imports from STL come along as refined mesh solids.
import FreeCAD as App
App.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD").SetString("openscadexecutable", r"C:\Program Files\OpenSCAD\openscad.com")


def csg_shape(path, meshes=True):
    import importCSG, Part
    cur = App.ActiveDocument
    tmp = App.newDocument("CSGTmp", hidden=True)
    try:
        importCSG.insert(path, tmp.Name)
        tmp.recompute()
        shapes, meshes = [], 0
        for o in tmp.Objects:
            if o.InList:
                continue
            if o.TypeId.startswith("Mesh::"):
                if not meshes:
                    continue
                sh = Part.Shape(); sh.makeShapeFromMesh(o.Mesh.Topology, 0.01); sh.sewShape()
                for s in sh.Shells:
                    try:
                        x = Part.Solid(s); shapes.append(x.removeSplitter())
                    except Exception:
                        shapes.append(s)
                meshes += 1
            elif hasattr(o, "Shape") and not o.Shape.isNull():
                shapes.append(o.Shape.copy())
        sh = shapes[0] if len(shapes) == 1 else Part.makeCompound(shapes)
        try:
            sh = sh.removeSplitter()
        except Exception:
            pass
        return sh, meshes
    finally:
        App.closeDocument(tmp.Name)
        if cur: App.setActiveDocument(cur.Name)
