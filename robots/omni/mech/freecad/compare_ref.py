# Compare FreeCAD bodies with OpenSCAD reference STLs (same robot coordinates): volume, bounding box, overlap.
import os, Mesh
REF = globals().get("REF", os.path.join(os.environ["TEMP"], "ref"))
doc = App.getDocument("BugBot_Base"); out = {}
def bb(b): return [round(v, 2) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]
for f in sorted(os.listdir(REF)):
    name = f[:-4]; o = doc.getObject(name)
    if not o: continue
    m = Mesh.Mesh(os.path.join(REF, f)); fc = o.Shape
    row = {"fc_vol": round(fc.Volume, 1), "scad_vol": round(m.Volume, 1), "dvol_pct": round(100*(fc.Volume - m.Volume)/m.Volume, 2),
           "dbbox": round(max(abs(a - b) for a, b in zip(bb(fc.BoundBox), bb(m.BoundBox))), 2)}
    try:
        sh = Part.Shape(); sh.makeShapeFromMesh(m.Topology, 0.05); sh.sewShape()
        sols = []
        for s in sh.Shells:
            x = Part.Solid(s)
            if x.Volume < 0: x.reverse()
            sols.append(x)
        ref = Part.makeCompound(sols)
        com = sum(fc.common(x).Volume for x in sols)
        row["miss_pct"] = round(100*(m.Volume - com)/m.Volume, 2)      # in OpenSCAD, not in FreeCAD
        row["extra_pct"] = round(100*(fc.Volume - com)/m.Volume, 2)    # in FreeCAD, not in OpenSCAD
    except Exception as e:
        row["overlap_err"] = str(e)[:60]
    out[name] = row
result = out
