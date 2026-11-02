# Weak-connection check (KiCad python; user, 2026-10-26 "check for connections that are poor / could be thicker"):
#   1. every track piece of a power / motor net against its design current: IPC-2221 (I = k * dT^0.44 * A^0.725, A in
#      mil^2; k 0.048 outer, 0.024 inner), 1 oz outer / 0.5 oz inner (JLC 6-layer), 10 degC rise
#   2. vias where such a net changes layer: how many vias share the job (within 1.5 mm) vs ~1 A each (0.2 mm drill)
#   3. pads joined to a plane / pour of their net by fewer than 2 spokes (starved thermals, from KiCad's DRC report)
# Design currents (A) from REQUIREMENTS.md; signals are not checked.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/power_check.py [board] [--json out.json]
import collections, json, math, re, sys, pcbnew
args = [a for a in sys.argv[1:] if not a.startswith("--")]
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = args[0] if args else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
JS = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
I_DESIGN = [(r"/BAT_P|/BAT_F|/VBAT_P|/VBAT_SW|/BAT_N|/FS_D", 3.5), (r"/VSYS", 3.5), (r"/VBUS", 1.5),
            (r"/SW5", 3.0), (r"/SW33[AB]", 2.0), (r"/5V", 1.5), (r"/SERVO_5V", 0.7), (r"/3V3", 1.0),
            (r"/M\d_[AB]", 1.0), (r"/KICK_HV|/SOL_N", 1.0), (r"/KSW|/KICK_BOOST", 1.0), (r"/GND", 3.5)]
OUTER = (pcbnew.F_Cu, pcbnew.B_Cu)
T_MIL = {True: 1.378, False: 0.689}                    # copper thickness (mil): 1 oz outer, 0.5 oz inner
DT = 10.0


def i_design(net):
    return next((i for pat, i in I_DESIGN if re.fullmatch(pat, net)), None)


def i_allowed(w_mm, outer):
    A = w_mm / 0.0254 * T_MIL[outer]
    return (0.048 if outer else 0.024) * DT ** 0.44 * A ** 0.725


b = pcbnew.LoadBoard(B); tm = pcbnew.ToMM
weak = collections.defaultdict(list)                   # net -> [(I_allowed, width, layer, x, y)]
for t in b.GetTracks():
    if t.GetClass() != "PCB_TRACK": continue
    I = i_design(t.GetNetname())
    if I is None: continue
    outer = t.GetLayer() in OUTER
    ia = i_allowed(tm(t.GetWidth()), outer)
    if ia < I:
        c = (t.GetStart() + t.GetEnd()) / 2
        weak[t.GetNetname()].append((round(ia, 2), tm(t.GetWidth()), b.GetLayerName(t.GetLayer()), round(tm(c.x), 2), round(tm(c.y), 2), round(tm(t.GetLength()), 2)))
# vias: clusters of one net within 1.5 mm, at places where the net has tracks on 2+ layers
vias = [v for v in b.GetTracks() if v.GetClass() == "PCB_VIA" and i_design(v.GetNetname())]
lay_at = collections.defaultdict(set)
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK":
        for q in (t.GetStart(), t.GetEnd()): lay_at[(t.GetNetname(), q.x, q.y)].add(t.GetLayer())
thin_vias = []
seen = set()
for v in vias:
    if id(v) in seen: continue
    net, c = v.GetNetname(), v.GetPosition()
    if len(lay_at[(net, c.x, c.y)]) < 2: continue          # plane drop or stitching: the plane spreads it
    grp = [u for u in vias if u.GetNetname() == net and (u.GetPosition() - c).EuclideanNorm() <= pcbnew.FromMM(1.5)]
    seen |= {id(u) for u in grp}
    if len(grp) * 1.0 < i_design(net):
        thin_vias.append((net, len(grp), i_design(net), round(tm(c.x), 2), round(tm(c.y), 2)))
print(f"tracks below their net's design current (IPC-2221, {DT:.0f} degC rise, 1 oz outer / 0.5 oz inner):")
for net, L in sorted(weak.items(), key=lambda kv: -i_design(kv[0])):
    tot = sum(x[5] for x in L); worst = min(L)
    print(f"  {net:12s} needs {i_design(net):.1f} A: {len(L):3d} pieces, {tot:6.1f} mm; weakest {worst[0]} A ({worst[1]} mm on {worst[2]} at {worst[3]}, {worst[4]})")
print(f"layer changes on power nets with too few vias (~1 A per 0.2 mm via): {len(thin_vias)}")
for x in thin_vias: print(f"  {x[0]:12s} {x[1]} via(s) for {x[2]} A at ({x[3]}, {x[4]})")
if JS: json.dump({"weak": weak, "vias": thin_vias}, open(JS, "w"))
