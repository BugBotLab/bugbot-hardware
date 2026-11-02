# BugBot in FreeCAD: the LED beacon under the dome, a bought 7 x WS2812B-5050 "jewel" (Ø23, AliExpress) on a 2 mm
# double-sided foam pad on the top deck (2026-10-31, approved 2D: sketches/jewel_beacon.png). It replaces the KiCad LED
# ring board (LEDBoard / LEDPCB, kicad/BugBot_LED, retired); the main board's U13 already shifts its data to 5 V.
# LEDJewel: the board, its 7 LEDs and the foam pad, one bought-part solid (looks + mass). Re-runnable.
import os
import Part
from fusionflow import params as PP, ecad
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
OUT = BB + "/mech/freecad"
for f in ("bugbot_params.py", "bb_lib.py", "bb_geo.py"):
    exec(open(os.path.join(OUT, f), encoding="utf-8").read())
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
for name in ("LEDBoard", "LEDPCB", "LEDJewel"):                # the retired ring board (+ its hidden outline body), and an older jewel
    o = doc.getObject(name)
    if o is None: continue
    if hasattr(o, "KicadPcb"):
        try: ecad.stop(o)
        except Exception: pass
    for p in list(o.InList):
        if hasattr(p, "removeObject") and o in getattr(p, "Group", []): p.removeObject(o)
    if o.TypeId == "PartDesign::Body":
        for c in list(o.Group): doc.removeObject(c.Name)
    doc.removeObject(name)
# (dropped first, so the parameter change below does not rebuild the retired board)
# the led_* parameters onto the sheet: only the cells that change or are new (PP.set_param rewrites every row and
# recomputes the whole robot on each call: 7 calls hung the master for over an hour), then one recompute
sh = PP.sheet(doc)
rows = {sh.getAlias(f"B{r}"): r for r in range(2, PP.MAXROWS) if sh.getAlias(f"B{r}")}
free = (r for r in range(2, PP.MAXROWS) if not sh.getContents(f"A{r}") and not sh.getAlias(f"B{r}"))
changed = []
for n, e, cm in PARAMS:
    if not n.startswith("led_"): continue
    r = rows.get(n)
    if r is not None and sh.getContents(f"B{r}") == "=" + e: continue
    r = r or next(free)
    sh.set(f"A{r}", n); sh.set(f"B{r}", "=" + e); sh.set(f"C{r}", cm)
    if sh.getAlias(f"B{r}") != n: sh.setAlias(f"B{r}", n)
    changed.append(n)
doc.recompute()
z0 = num("mast_top") + num("deck_t")
zb = z0 + num("led_foam_t")
foam = Part.makeCylinder(num("led_d") / 2 - 1.5, num("led_foam_t"), V(0, 0, z0))
foam = foam.cut(Part.makeCylinder(num("led_ring_r") / 2, num("led_foam_t") + 0.2, V(0, 0, z0 - 0.1)))   # the wires' gap
board = Part.makeCylinder(num("led_d") / 2, num("led_t"), V(0, 0, zb))
s, h = num("led_pkg"), num("led_pkg_h")
leds = [(0.0, 0.0)] + [(num("led_ring_r") * math.cos(math.radians(num("led_ang0") + 60 * k)),
                        num("led_ring_r") * math.sin(math.radians(num("led_ang0") + 60 * k))) for k in range(6)]
shape = board.fuse([foam] + [Part.makeBox(s, s, h, V(x - s / 2, y - s / 2, zb + num("led_t"))) for x, y in leds]).removeSplitter()
o = doc.addObject("Part::Feature", "LEDJewel"); o.Label = "LEDJewel"; o.Shape = shape
o.ViewObject.ShapeColor = (0.15, 0.17, 0.19)
doc.recompute()
bb = shape.BoundBox
result = {"valid": shape.isValid(), "z": [round(bb.ZMin, 2), round(bb.ZMax, 2)], "d": round(bb.XLength, 2), "params_changed": changed}
