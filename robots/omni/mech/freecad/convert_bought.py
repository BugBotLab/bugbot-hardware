# One-off, headless (freecadcmd): turn bought/*.csg into true-solid bought/*.brep, and the mesh-only parts
# (omni wheel, PCB components) into solid .brep too, so the FreeCAD build only loads files: no OpenSCAD runs, no pop-ups.
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" mech/freecad/convert_bought.py
import os, sys
import FreeCAD as App, Part, Mesh
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/mech/freecad"
exec(open(os.path.join(D, "csg_solid.py"), encoding="utf-8").read())
MAXF = 12000
def stl_solid(p):
    m = Mesh.Mesh(p)
    if m.CountFacets > MAXF: m.decimate(0.02, 1 - MAXF / m.CountFacets)
    sh = Part.Shape(); sh.makeShapeFromMesh(m.Topology, 0.01); sh.sewShape(); out = []
    for s in sh.Shells:
        try:
            x = Part.Solid(s)
            if x.Volume < 0: x.reverse()
            out.append(x.removeSplitter())
        except Exception:
            out.append(s)
    return out[0] if len(out) == 1 else Part.makeCompound(out)
B = os.path.join(D, "bought")
for f in sorted(os.listdir(B)):
    n, ext = os.path.splitext(f)
    MESH_ONLY = {"PCBParts"}          # their OpenSCAD hulls / KiCad STLs do not convert to B-rep
    if n in ("FrontHeader", "Wheel") or ext not in (".csg", ".stl") or (ext == ".csg" and n in MESH_ONLY) or             (ext == ".stl" and n not in MESH_ONLY and os.path.exists(os.path.join(B, n + ".csg"))):
        continue
    if len(sys.argv) > 2 and n not in sys.argv[2:]:
        continue
    if n == "FrontBoard":       # board from CSG; its header from OpenSCAD's own in-place STL (the importer misplaces it)
        sh = Part.makeCompound([csg_shape(os.path.join(B, f), meshes=False)[0], stl_solid(os.path.join(B, "FrontHeader.stl"))])
    else:
        sh = csg_shape(os.path.join(B, f))[0] if ext == ".csg" else stl_solid(os.path.join(B, f))
    sh.exportBrep(os.path.join(B, n + ".brep"))
    print(f"{n}: {'B-rep' if ext == '.csg' else 'mesh solid'}, {len(sh.Faces)} faces, valid {sh.isValid()}, {sh.Volume:.1f} mm3")
