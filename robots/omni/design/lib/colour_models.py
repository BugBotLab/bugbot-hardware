# Give the BugBot library's own 3D models their real colours (STEP colours, which KiCad keeps in its board export).
#   python fusionflow/ffclient.py run design/lib/colour_models.py      (needs the FreeCAD GUI: ImportGui writes colours)
# The shapes stay exactly as make_*.py made them; only colours are added.
import os, ImportGui, Part
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib/3dmodels"
H = lambda h: (int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255, 0.0)


def recolour(fn, face_colour):
    """face_colour(face, shape) -> rgba for every face; the model is re-saved with those colours."""
    path = os.path.join(D, fn)
    doc = App.newDocument("Recolour", hidden=True)
    try:
        sh = Part.Shape(); sh.read(path)
        o = doc.addObject("Part::Feature", os.path.splitext(fn)[0]); o.Shape = sh
        o.ViewObject.DiffuseColor = [face_colour(f, sh) for f in sh.Faces]
        ImportGui.export([o], path)
        return len(sh.Faces)
    finally:
        App.closeDocument(doc.Name)
        App.setActiveDocument("BugBot_Scorpion")


BLACK, STEEL, BLUE, LENS = H("#1A1A1C"), H("#C9CCD1"), H("#1F5FB4"), H("#3B3F44")
GREY_PBT = H("#8E9093")
def holder(f, sh):                                   # Keystone 1051 rev C: grey PBT body, tin-nickel stainless contacts
    p = f.CenterOfMass
    return STEEL if any(c.isInside(p, 1e-4, True) for c in sh.Solids[1:]) else GREY_PBT
def cell(f, sh):                                     # 16340: blue wrap, steel ends
    b = sh.BoundBox; ax = max(((b.XLength, "x"), (b.YLength, "y"), (b.ZLength, "z")))[1]
    if f.Surface.TypeId == "Part::GeomPlane":
        return STEEL
    return BLUE
def paa(f, sh):                                      # PAA5100JE-Q: black body, dark lens, gold lands
    if f.BoundBox.ZMax < 0.06:
        return H("#C8A23C")
    return LENS if f.Surface.TypeId == "Part::GeomCylinder" and abs(f.Surface.Radius - 1.9) < 0.1 else BLACK
def ws2812(f, sh):                                   # WS2812B-2020: white body, pale lens, tin pads
    if f.BoundBox.ZMax < 0.06:
        return STEEL
    if f.Surface.TypeId == "Part::GeomCylinder" or (f.BoundBox.ZMin > 0.83 and f.BoundBox.XLength < 1.5 and f.BoundBox.YLength < 1.5 and f.BoundBox.ZMax < 0.86 and f.Area < 1.7):
        return H("#F3EFC8")
    return H("#F4F4F2")
def vl53(f, sh):                                     # VL53L5CX: black cap, green substrate, dark lens / window
    if f.BoundBox.ZMax < 0.31:
        return H("#2E6B3A")
    return LENS if f.BoundBox.ZMin > 1.34 and f.Area < 0.6 else BLACK
def cam(f, sh):                                      # camera module: black holder + barrel, blue glass, amber flex
    b = f.BoundBox
    if b.XLength > 11.0 or b.ZMin < -0.05:
        return H("#D08A2A")
    return H("#2B3D66") if b.ZMin > 5.29 else BLACK
def fpc(f, sh):                                      # FPC socket: beige LCP body, dark lid, tin tails
    b = f.BoundBox
    if b.ZMax < 0.2:
        return STEEL
    return H("#3A3020") if b.ZMin > 1.4 else H("#E8DCC0")
result = {fn: recolour(fn, fc) for fn, fc in (("ST_VL53L5CX_LGA16.step", vl53), ("Camera_DVP24_Module.step", cam),
                                               ("FPC_SHOUHAN_0.5-24P_HYH2.0.step", fpc),
                                               ("BatteryHolder_Keystone_1051_1xCR123A.step", holder),
                                               ("LED_WS2812B-2020_PLCC4_2.0x2.0mm.step", ws2812),
                                               ("Cell_16340_unprotected.step", cell), ("PAA5100JE-Q.step", paa))}
