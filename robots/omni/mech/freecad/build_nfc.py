# BugBot in FreeCAD: the NFC tag reader (approved 2D sketch: mech/freecad/sketches/nfc_mount_v3.png). Base part: every
# variant gets it (it clears the BugBot's kick solenoid). Run after build_chassis.py / build_ecad.py / build_encoder.py,
# before build_fasteners.py (its screws) and build_structure.py (the NFC component). Re-runnable: replaces its own parts.
#   NFCFloor   the NFC floor PCB under the floor plate (kicad/BugBot_NFCfloor): the floor outline with the wheel windows cut
#              out, a 3-turn loop round the edge, the underglow ring, and since 2026-10-31 the READER itself on its underside
#              (approved 2D: sketches/nfc_reader_on_floor.png); 12 solder holes at the centre for the cables
#   NFCLinkCable  the reader cable: the floor PCB's solder holes -> up through the floor opening -> the main board's J20
#              (JST-SH 8, a 1.2 mm tube). The reader board, its printed tray and the antenna cable are gone (2026-10-31);
#              the tray's 3 chassis posts stay (unused) so the chassis does not change
#   Chassis    NfcBoss1-3 + NfcPost1-3 (added), NfcPocket, NfcOpening, NfcClampPilot1-3, NfcPostPilot1-3 (cut)
import json, math, os
import Part
from fusionflow import ecad, params as PP
doc = App.getDocument("BugBot_Base"); App.setActiveDocument("BugBot_Base")
V = App.Vector
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
K = BB + "/design"
OUTD = BB + "/mech/freecad"
# the nfc_* parameters (bugbot_params.py) onto an existing sheet that predates them
_rows = {}
exec(open(os.path.join(OUTD, "bugbot_params.py"), encoding="utf-8").read(), _rows)
for n, e, cm in _rows["PARAMS"]:
    if n.startswith("nfc_") and doc.Params.getCellFromAlias(n) is None:
        PP.set_param(n, e, cm, doc)
doc.recompute()
exec(open(os.path.join(OUTD, "nfc_layout.py"), encoding="utf-8").read())
log = {}


def drop(name):
    o = doc.getObject(name)
    if o:
        if hasattr(o, "KicadPcb"):
            try: ecad.stop(o)
            except Exception: pass
        for p in list(o.InList):
            if hasattr(p, "removeObject") and o in getattr(p, "Group", []): p.removeObject(o)
        doc.removeObject(name)


# ---------- 1. chassis features ----------
ch = doc.getObject("Chassis")
old = [o for o in ch.Group if o.Name.startswith("Nfc")]
if old:
    ch.Tip = old[0].BaseFeature
    for o in old:
        ch.removeObject(o); doc.removeObject(o.Name)
    doc.recompute()
def cyl(kind, name, x, y, z0, z1, r):
    f = ch.newObject("PartDesign::" + kind + "Cylinder", name)
    f.Radius, f.Height = r, z1 - z0
    f.Placement = App.Placement(V(x, y, z0), App.Rotation())
    f.Refine = False
    ch.Tip = f
    return f
feats = []
for k, (x, y) in enumerate(CLAMPS):
    feats.append(cyl("Additive", f"NfcBoss{k + 1}", x, y, PLATE_TOP - 0.1, NFC["boss_top"], NFC["boss_d"] / 2))
for k, (x, y, _) in enumerate(POSTS):
    feats.append(cyl("Additive", f"NfcPost{k + 1}", x, y, PLATE_TOP - 0.1, NFC["tray_z"], NFC["post_d"] / 2))
feats.append(cyl("Subtractive", "NfcPocket", 0, 0, PLATE_Z - 0.1, PLATE_Z + NFC["coil_t"], NFC["pocket_d"] / 2))
bx = ch.newObject("PartDesign::SubtractiveBox", "NfcOpening")
bx.Length, bx.Width, bx.Height = NFC["open_x"], NFC["open_y"], PLATE_TOP - PLATE_Z + 0.2
bx.Placement = App.Placement(V(-NFC["open_x"] / 2, -NFC["open_y"] / 2, PLATE_Z - 0.1), App.Rotation()); bx.Refine = False
ch.Tip = bx; feats.append(bx)
pd = float(doc.Params.get("pilot_d").Value) if hasattr(doc.Params.get("pilot_d"), "Value") else float(doc.Params.get("pilot_d"))
for k, (x, y) in enumerate(CLAMPS):            # M2x5 nylon from below through the antenna PCB: head at 4.9, tip at 9.9
    feats.append(cyl("Subtractive", f"NfcClampPilot{k + 1}", x, y, PLATE_Z - 0.1, PLATE_Z + 4.2, pd / 2))
for k, (x, y, _) in enumerate(POSTS):          # M2x6 pan from the tray's counterbore: tip at SEAT_Z - 6
    feats.append(cyl("Subtractive", f"NfcPostPilot{k + 1}", x, y, SEAT_Z - 6.5, NFC["tray_z"] + 0.1, pd / 2))
doc.recompute()
bad = [f.Name for f in feats if f.Shape.isNull() or "Invalid" in f.State]
assert not bad, f"chassis NFC features failed: {bad}"
log["chassis_valid"] = ch.isValid()

# ---------- 2. the reader's tray: gone since 2026-10-31 (the reader is on the floor PCB); its 3 posts stay on the chassis ----------
drop("NFCTray")

# ---------- 3. the boards (ECAD link): board frame origin = the KiCad grid origin (board centre), z 0 = the underside ----------
drop("NFCCoil"); drop("NFCFlex"); drop("NFCStiffener"); drop("NFCFloor"); drop("NFCReader"); drop("NFCCable")
FP = json.load(open(K + "/schematics/NFCfloor/mcad.json"))["floor_pcb"]
co = ecad.make(doc, "NFCFloor", K + "/schematics/NFCfloor/BugBot_NFCfloor.kicad_pcb")
co.Label = "NFC antenna floor PCB (KiCad)"; co.SubstrateColour = (0.11, 0.40, 0.22)       # green solder mask (like the others)
co.Placement = App.Placement(V(0, 0, PLATE_Z - FP["thickness"]), App.Rotation())       # top face on the floor underside
for b in (co,):
    ecad.sync(b, wait=True)
    bb = b.Shape.BoundBox
    log[b.Name] = {"status": b.Status, "bbox": [round(v, 2) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)]}

# ---------- 4. the cables (tubes): antenna JST-SH 2 (2 x AWG32, 1 mm) and the reader -> main board JST-SH 8 (flat 8 x AWG32, 1.2 mm) ----------
def tube(name, label, pts, r):
    segs = [Part.makeCylinder(r, (b - a).Length, a, b - a) for a, b in zip(pts, pts[1:]) if (b - a).Length > 1e-6]
    segs += [Part.makeSphere(r, p) for p in pts[1:-1]]
    o = doc.getObject(name) or doc.addObject("Part::Feature", name); o.Label = label
    o.Shape = segs[0].multiFuse(segs[1:]).removeSplitter()
    log[name + "_length_mm"] = round(sum((b - a).Length for a, b in zip(pts, pts[1:])), 1)
# the reader cable: from the floor PCB's solder holes (centre) up through the floor opening, then over to J20's side-entry plug
jz = float(doc.Params.get("pcb_z").Value) - 1.45
pts = [V(0, 0, PLATE_Z), V(0, 0, CABLE_Z), V(J20_PLUG_XY[0], J20_PLUG_XY[1] - 3.0, jz - 0.8), V(J20_PLUG_XY[0], J20_PLUG_XY[1], jz)]
tube("NFCLinkCable", "NFC reader cable (floor PCB to main board J20)", pts, 0.6)
doc.recompute()
_g = dict(globals()); exec(open(os.path.join(OUTD, "apply_colours.py"), encoding="utf-8").read(), _g)   # new chassis features reset its colour
result = log                                                 # (build_structure.py saves)
