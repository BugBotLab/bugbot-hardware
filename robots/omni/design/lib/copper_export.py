# Copper geometry of chosen nets for sim_copper.py (KiCad python): per net and copper layer the track segments
# (start, end, width), pad polygons (with ref / pin / layers / centre), zone fill polygons (outlines + holes), and vias
# (centre, diameter, drill). Zones are refilled first. mm, board coordinates.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/copper_export.py [board] [out.json] [net ...]
import json, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
OUT = sys.argv[2] if len(sys.argv) > 2 else BB + "/design/schematics/Main/_work/copper_nets.json"
NETS = set(sys.argv[3:]) or {"/VSYS", "/GND", "/5V", "/3V3", "/BAT_P", "/BAT_F", "/VBAT_P", "/VBAT_SW", "/BAT_N", "/FS_D",
                             "/M1_A", "/M1_B", "/M2_A", "/M2_B", "/M3_A", "/M3_B", "/VBUS", "/SERVO_5V", "/SW5", "/SW33A", "/SW33B", "/KICK_HV", "/SOL_N"}
b = pcbnew.LoadBoard(B)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
tm = pcbnew.ToMM
CU = {b.GetLayerName(l): l for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)}
P = lambda v: [round(tm(v.x), 4), round(tm(v.y), 4)]


def chain(c):
    return [P(c.CPoint(i)) for i in range(c.PointCount())]


out = {n: {"tracks": [], "pads": [], "zones": [], "vias": []} for n in NETS}
for t in b.GetTracks():
    n = t.GetNetname()
    if n not in NETS: continue
    if t.GetClass() == "PCB_VIA":
        out[n]["vias"].append({"c": P(t.GetPosition()), "d": tm(t.GetWidth(pcbnew.F_Cu)), "drill": tm(t.GetDrillValue())})
    else:
        out[n]["tracks"].append({"l": b.GetLayerName(t.GetLayer()), "a": P(t.GetStart()), "b": P(t.GetEnd()), "w": tm(t.GetWidth())})
for f in b.GetFootprints():
    for p in f.Pads():
        n = p.GetNetname()
        if n not in NETS: continue
        poly = p.GetEffectivePolygon(pcbnew.ERROR_INSIDE)
        outl = [chain(poly.Outline(i)) for i in range(poly.OutlineCount())]
        out[n]["pads"].append({"ref": f.GetReference(), "pin": p.GetNumber(), "c": P(p.GetPosition()), "poly": outl,
                               "layers": [ln for ln, l in CU.items() if p.IsOnLayer(l)], "drill": tm(p.GetDrillSize().x)})
for z in b.Zones():
    n = z.GetNetname()
    if n not in NETS or z.GetIsRuleArea(): continue
    for ln, l in CU.items():
        if not z.IsOnLayer(l): continue
        fp = z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            out[n]["zones"].append({"l": ln, "outline": chain(fp.Outline(i)), "holes": [chain(fp.Hole(i, h)) for h in range(fp.HoleCount(i))]})
json.dump(out, open(OUT, "w"))
print("copper_export:", {n: (len(d["tracks"]), len(d["pads"]), len(d["zones"]), len(d["vias"])) for n, d in sorted(out.items())})
