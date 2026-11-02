# 3D models (STEP) for the front sensor board's own footprints, in each footprint's frame (KiCad model frame: y up = -footprint y).
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_front_models.py      then design/lib/colour_models.py
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib/3dmodels"

# ---- VL53L5CX: cap 6.4 x 3.03 x 1.5 on a 6.2 x 2.83 substrate; Rx lens (left) and Tx window (right) in the top
sub = Part.makeBox(6.2, 2.83, 0.3, V(-3.1, -1.415, 0))
cap = Part.makeBox(6.4, 3.03, 1.2, V(-3.2, -1.515, 0.3))
cap = cap.cut(Part.makeCylinder(0.26, 0.2, V(-2.05, 0.1, 1.35))).cut(Part.makeBox(0.7, 0.7, 0.2, V(1.6, -0.25, 1.35)))
rx = Part.makeCylinder(0.26, 0.05, V(-2.05, 0.1, 1.4)); tx = Part.makeBox(0.7, 0.7, 0.05, V(1.6, -0.25, 1.4))
Part.makeCompound([sub, cap, rx, tx]).exportStep(f"{D}/ST_VL53L5CX_LGA16.step")

# ---- 24-pin DVP camera module, taped (0.3) on the front face; origin = lens centre on the board's front copper.
# The flex leaves the module's top edge (+y = robot up), goes through the board slot (y 4.7 .. 5.7) and down the back
# (z < -1.6) into J2, bowing out behind the board on the way (21 mm flex, ~10 mm of it used by the straight path).
M = 8.5
base = Part.makeBox(M, M, 0.6, V(-M / 2, -M / 2, 0.3))
holder = Part.makeBox(M, M, 2.5, V(-M / 2, -M / 2, 0.9))
barrel = Part.makeCylinder(3.3, 1.9, V(0, 0, 3.4)); glass = Part.makeCylinder(1.6, 0.05, V(0, 0, 5.3))
pts = [V(0, 4.25, 0.45), V(0, 4.85, 0.35), V(0, 5.2, -0.3), V(0, 5.2, -1.3), V(0, 5.15, -2.6), V(0, 4.3, -3.9),
       V(0, 3.1, -3.7), V(0, 2.4, -2.75), V(0, 1.8, -2.62), V(0, 0.4, -2.6), V(0, -1.0, -2.6)]
bs = Part.BSplineCurve(); bs.interpolate(pts)
# a polyline through the spline (a smooth B-spline sweep tessellates to ~300k triangles in the sim / render meshes);
# 40 segments (16 until 2026-10-27 looked faceted and broken in the bends) is smooth to the eye and still light
NSEG = 40
spine = Part.makePolygon([bs.value(bs.FirstParameter + (bs.LastParameter - bs.FirstParameter) * k / NSEG) for k in range(NSEG + 1)])
t0 = bs.tangent(bs.FirstParameter)[0]
w, th = 12.0, 0.15
n = V(0, -t0.z, t0.y); n.normalize()                         # in-plane normal of the spine at its start
c = pts[0]; ex = V(1, 0, 0)
prof = Part.makePolygon([c - ex * (w / 2) - n * (th / 2), c + ex * (w / 2) - n * (th / 2), c + ex * (w / 2) + n * (th / 2), c - ex * (w / 2) + n * (th / 2), c - ex * (w / 2) - n * (th / 2)])
flex = spine.makePipeShell([prof], True, False)
print("flex length", round(spine.Length, 2), "valid", flex.isValid())
Part.makeCompound([base, holder, barrel, glass, flex]).exportStep(f"{D}/Camera_DVP24_Module.step")

# ---- SHOU HAN FPC 0.5-24P HYH2.0 (C6364666): 24 tails at footprint y 0 (model y 0), body toward footprint +y (model -y),
# 15.45 wide, 2.0 high, opening at the front (model y -5.4); mounting tabs at x +/-7.4.
body = Part.makeBox(15.45, 4.8, 1.45, V(-7.725, -5.4, 0)).cut(Part.makeBox(12.6, 3.6, 0.5, V(-6.3, -5.5, 0.5)))
lid = Part.makeBox(14.2, 1.6, 0.55, V(-7.1, -2.2, 1.45))
tails = [Part.makeBox(0.3, 0.9, 0.12, V(-5.75 + 0.5 * k - 0.15, -0.6, 0)) for k in range(24)]
tabs = [Part.makeBox(1.6, 1.8, 0.15, V(s * 7.4 - 0.8, -4.05, 0)) for s in (-1, 1)]
Part.makeCompound([body, lid] + tails + tabs).exportStep(f"{D}/FPC_SHOUHAN_0.5-24P_HYH2.0.step")
print("ok")
