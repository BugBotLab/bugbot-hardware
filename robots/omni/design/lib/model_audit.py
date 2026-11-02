# 3D model audit of the main board (KiCad python): every footprint's 3D model(s), whether the file exists (KiCad's
# ${KICAD10_3DMODEL_DIR} and the project's paths resolved), and the footprint's LCSC number. -> _place/model_audit.json
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/model_audit.py
import json, os, re, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
ENV = {"KICAD10_3DMODEL_DIR": "C:/Program Files/KiCad/10.0/share/kicad/3dmodels",
       "KICAD9_3DMODEL_DIR": "C:/Program Files/KiCad/10.0/share/kicad/3dmodels",
       "KIPRJMOD": BB + "/design/schematics/Main"}
def resolve(p):
    for k, v in ENV.items(): p = p.replace("${%s}" % k, v)
    return p
b = pcbnew.LoadBoard(B)
out = []
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref.startswith("H"): continue
    lcsc = ""
    for fld in f.GetFields():
        if re.match(r"(?i)lcsc", fld.GetName()): lcsc = fld.GetText()
    models = [(m.m_Filename, os.path.exists(resolve(m.m_Filename)), m.m_Show) for m in f.Models()]
    out.append({"ref": ref, "fp": f.GetFPIDAsString(), "value": f.GetValue(), "lcsc": lcsc, "models": models,
                "side": "B" if f.IsFlipped() else "F"})
json.dump(out, open(BB + "/design/schematics/Main/_place/model_audit.json", "w"), indent=0)
none = [o for o in out if not o["models"]]; missing = [o for o in out if o["models"] and not any(e for _, e, _ in o["models"])]
ok = [o for o in out if any(e for _, e, _ in o["models"])]
print(f"{len(out)} footprints: {len(ok)} with a model file found, {len(missing)} with a model path that does not exist, {len(none)} with no model")
for o in sorted(missing + none, key=lambda o: o["fp"]):
    print(f"  {o['ref']:5s} {o['fp'][:62]:62s} lcsc={o['lcsc'] or '-':10s} {o['models'][0][0][-60:] if o['models'] else '(none)'}")
