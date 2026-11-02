# JLCPCB fab pack for the main board (KiCad python): fills the zones (push-and-shove saves don't), then writes
# schematics/Main/jlc/: gerbers + Excellon drills (gerbers.zip), BOM and CPL csv in JLC's format, from the footprints'
# LCSC fields. Parts with no LCSC number, or marked DNP / not-in-BOM, are hand-fitted and listed as such.
# CPL: board coordinates as the gerbers (absolute, Y flipped so up is +), rotation = KiCad's + JLC footprint offsets
# (JLC/EasyEDA library footprints are turned against KiCad's for some packages); check the JLC placement preview.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_main_jlc.py
import csv, os, re, subprocess, sys, zipfile, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
R = BB + "/design/schematics/Main/"
B = R + "BugBot_Main.kicad_pcb"
OUT = R + "jlc/"
CLI = "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
LAYERS = "F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
# fallback only (parts with no JLC footprint fetched): footprint-name pattern -> degrees added for JLC; bottom parts get (-)
SYMMETRIC = ["J6", "J22", "SW2", "SW3"]           # unpolarised sockets / buttons: CPL turn by pad shape (cpl_rot_check.py)
HAND = {"SW1"}                                   # bought parts we fit ourselves (SW1: right-angle slide, hand-soldered)
ROT_OFS = [(r"^SOT-23", 180), (r"^SOT-223", 180), (r"^SOT-89", 180), (r"^SOT-353", 180), (r"^SC-70", 180),
           (r"^(QFN|DFN|LQFP|TQFP|SOIC|SOP|TSSOP|HTSSOP|MSOP)-", 270), (r"^VSSOP-", 180)]

b = pcbnew.LoadBoard(B)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(B, b)
os.makedirs(OUT + "gerbers", exist_ok=True)
for f in os.listdir(OUT + "gerbers"): os.remove(OUT + "gerbers/" + f)
subprocess.run([CLI, "pcb", "export", "gerbers", "-o", OUT + "gerbers", "-l", LAYERS, "--subtract-soldermask", B], check=True)
subprocess.run([CLI, "pcb", "export", "drill", "-o", OUT + "gerbers/", "--format", "excellon", "--excellon-units", "mm",
                "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", B], check=True)
with zipfile.ZipFile(OUT + "BugBot_Main_gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT + "gerbers")): z.write(OUT + "gerbers/" + f, f)


def rot_ofs(fpn):
    for pat, d in ROT_OFS:
        if re.match(pat, fpn): return d
    return 0


def field(f, name):
    for fd in f.GetFields():
        if fd.GetName() == name: return fd.GetText().strip()
    return ""


key = lambda r: (re.match(r"\D+", r).group(), int(re.search(r"\d+", r).group()))
groups, cpl, hand = {}, [], []
for f in b.GetFootprints():
    ref = f.GetReference()
    lc = field(f, "LCSC")
    if ref.startswith(("H", "#", "G", "TP", "FID")) and not lc: continue
    if f.IsDNP() or f.IsExcludedFromBOM() or not lc.startswith("C") or ref in HAND:
        hand.append((ref, f.GetValue(), lc or "-")); continue
    fpn = f.GetFPID().GetLibItemName().wx_str()
    groups.setdefault((f.GetValue(), fpn, lc), []).append(ref)
    bot = f.IsFlipped(); p = f.GetPosition()
    rot = (f.GetOrientationDegrees() + (-1 if bot else 1) * rot_ofs(fpn)) % 360
    cpl.append((ref, pcbnew.ToMM(p.x), -pcbnew.ToMM(p.y), "Bottom" if bot else "Top", rot))
with open(OUT + "BugBot_Main_BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL); w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
    for (val, fpn, lc), refs in sorted(groups.items(), key=lambda g: key(min(g[1], key=key))):
        w.writerow([val, ",".join(sorted(refs, key=key)), fpn, lc])
with open(OUT + "BugBot_Main_CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
    fh.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
    for ref, x, y, side, rot in sorted(cpl, key=lambda c: key(c[0])):
        fh.write(f"{ref},{x:.4f}mm,{y:.4f}mm,{side},{rot:g}\n")
# rotations + centres from JLC's own footprints (cpl_rot_check.py; the table above is only the fallback for parts without one)
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpl_rot_check.py"), B,
                OUT + "BugBot_Main_BOM_JLC.csv", OUT + "BugBot_Main_CPL_JLC.csv", "--fix", "--symmetric=" + ",".join(SYMMETRIC)], check=True)
from hand_solder import split                    # through-hole connectors we solder: out of the JLC files
split("BugBot_Main", OUT)
with open(OUT + "HAND_FIT.txt", "w", encoding="utf-8") as fh:
    fh.write("Not assembled by JLC (no LCSC number, DNP or not in BOM):\n")
    for ref, val, lc in sorted(hand, key=lambda h: key(h[0])): fh.write(f"{ref}\t{val}\t{lc}\n")
nb = sum(1 for c in cpl if c[3] == "Bottom")
print(f"gerbers: {len(os.listdir(OUT + 'gerbers'))} files; BOM {len(groups)} lines, CPL {len(cpl)} parts "
      f"({len(cpl) - nb} top, {nb} bottom); hand-fit {len(hand)}: {' '.join(h[0] for h in sorted(hand, key=lambda h: key(h[0])))}")
