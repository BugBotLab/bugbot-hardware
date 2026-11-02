# PixArt PAA5100JE-Q (28-pin 6 x 6 mm LGA + L214-ZSZ lens) for the BugBot KiCad library: footprint + 3D model (STEP).
# From the PixArt datasheet v1.00 (25 Jul 2018), Fig. 2 (package), Fig. 3 (recommended PCB layout), Fig. 4/6 (lens):
#   28 pads 0.35 x 0.70 mm, 0.65 mm pitch, 7 per side, from the package edge inward; NSMD mask 0.45 x 0.75 (0.05 margin);
#   centre GND pad (29) 2.40 x 1.90 mm, centred; body 2.28 mm, lens dia 3.80 standing 0.80 above it (3.08 total).
#   Optical centre: 0.245 mm towards pins 1-7 and 0.382 mm towards pins 22-28 from the package centre (top view).
# The footprint ORIGIN IS THE OPTICAL CENTRE, so the placement point is the sensor's optical axis.
#   "C:/Program Files/FreeCAD 1.0/bin/freecadcmd.exe" design/lib/make_paa5100.py
import FreeCAD as App, Part
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/lib"
PKG, BODY_H, LENS_D, LENS_H = 6.0, 2.28, 3.80, 0.80
PITCH, PW, PL, MASK = 0.65, 0.35, 0.70, 0.05
GND_W, GND_H = 2.40, 1.90
OX, OY = 0.245, 0.382                      # package centre relative to the optical centre (KiCad y down)


def pads():
    """(number, x, y, w, h) relative to the optical centre, KiCad top-view coordinates (y down)."""
    e = PKG / 2 - PL / 2                       # pad centre from the package centre
    out = []
    for k in range(7):
        t = -3 * PITCH + k * PITCH
        out.append((1 + k, -e, t, PL, PW))      # 1-7   left side, top to bottom
        out.append((8 + k, t, e, PW, PL))       # 8-14  bottom, left to right
        out.append((15 + k, e, -t, PL, PW))     # 15-21 right side, bottom to top
        out.append((22 + k, -t, -e, PW, PL))    # 22-28 top, right to left
    out.sort()
    out.append((29, 0.0, 0.0, GND_W, GND_H))
    return [(n, x + OX, y + OY, w, h) for n, x, y, w, h in out]


if hasattr(Part, "makeBox"):                  # (freecadcmd does not run scripts as __main__)
    # 3D model, KiCad model frame (z up from the board, y up = -KiCad y)
    body = Part.makeBox(PKG, PKG, BODY_H, V(OX - PKG / 2, -OY - PKG / 2, 0.05))
    window = Part.makeCylinder(LENS_D / 2 + 0.05, BODY_H, V(0, 0, 0.05 + BODY_H - 1.1))
    body = body.cut(window)
    lens = Part.makeCylinder(LENS_D / 2, LENS_H + 1.1, V(0, 0, 0.05 + BODY_H - 1.1))
    lens = lens.cut(Part.makeCylinder(1.0, 0.3, V(0, 0, 0.05 + BODY_H + LENS_H - 0.3)))
    lands = [Part.makeBox(w, h, 0.05, V(x - w / 2, -y - h / 2, 0)) for n, x, y, w, h in pads()]
    Part.makeCompound([body, lens] + lands).exportStep(f"{D}/3dmodels/PAA5100JE-Q.step")

    def pad(n, x, y, w, h):
        shape = "rect" if n == 29 else "roundrect"
        rr = "" if n == 29 else " (roundrect_rratio 0.5)"
        return (f'  (pad "{n}" smd {shape} (at {x:.4f} {y:.4f}) (size {w:.2f} {h:.2f}) (layers "F.Cu" "F.Paste" "F.Mask")'
                f'{rr} (solder_mask_margin {MASK}))')
    x0, y0, x1, y1 = OX - PKG / 2, OY - PKG / 2, OX + PKG / 2, OY + PKG / 2
    c = 0.8                                     # silk corner marks
    silk = []
    for (sx, sy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        sx -= 0.15 * dx; sy -= 0.15 * dy
        silk.append(f'  (fp_line (start {sx:.3f} {sy:.3f}) (end {sx + c * dx:.3f} {sy:.3f}) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
        silk.append(f'  (fp_line (start {sx:.3f} {sy:.3f}) (end {sx:.3f} {sy + c * dy:.3f}) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    fp = f'''(footprint "PAA5100JE-Q"
  (version 20240108)
  (generator "bugbot")
  (layer "F.Cu")
  (descr "PixArt PAA5100JE-Q optical tracking chip, 28-LGA 6x6 mm with L214-ZSZ lens, land pattern per datasheet v1.00 Fig. 3. Origin = optical centre. Needs external illumination (LTW-216TS5).")
  (tags "optical flow PAA5100 PixArt LGA-28")
  (attr smd)
  (property "Reference" "REF**" (at {OX:.3f} {y0 - 1.2:.3f} 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
  (property "Value" "PAA5100JE-Q" (at {OX:.3f} {y1 + 1.2:.3f} 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
  (fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_circle (center 0 0) (end {LENS_D / 2:.2f} 0) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_line (start -0.5 0) (end 0.5 0) (stroke (width 0.05) (type solid)) (layer "F.Fab"))
  (fp_line (start 0 -0.5) (end 0 0.5) (stroke (width 0.05) (type solid)) (layer "F.Fab"))
  (fp_rect (start {x0 - 0.25:.3f} {y0 - 0.25:.3f}) (end {x1 + 0.25:.3f} {y1 + 0.25:.3f}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
{chr(10).join(silk)}
  (fp_circle (center {x0 - 0.5:.3f} {y0 + 1.0:.3f}) (end {x0 - 0.35:.3f} {y0 + 1.0:.3f}) (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))
{chr(10).join(pad(*p) for p in pads())}
  (model "${{KIPRJMOD}}/../lib/3dmodels/PAA5100JE-Q.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
    open(f"{D}/BugBot.pretty/PAA5100JE-Q.kicad_mod", "w").write(fp)
    print("pads", len(pads()), "pad1", pads()[0])
