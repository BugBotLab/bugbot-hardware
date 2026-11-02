# Connector plan v1 (approved 2026-10-26, design/schematics/Main/connector_plan_v1.png + J16 west of the module): moves the
# cable connectors to _place/connector_choice.json. Each stays on the bottom side; its KiCad turn is the one whose
# courtyard and signal-pad row land where the plan put them (the planner works in the robot frame seen from above).
# Removes their lines' tracks / vias (whole for their own nets, only round the old / new spots for shared ones).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/place_connectors.py
import json, math, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
D = BB + "/design/schematics/Main/"
B = D + "BugBot_Main.kicad_pcb"
ch = json.load(open(D + "_place/connector_choice_full.json"))["choice"]; fps = json.load(open(D + "_place/jst_fps.json"))   # plan v4 (approved)
tm, mm = pcbnew.ToMM, pcbnew.FromMM
R = lambda p: (tm(p.x) - 100, 100 - tm(p.y))
def plan_xy(px, py, x, y, rot):                   # footprint coords (KiCad y down) -> robot frame, as the planner does
    qx, qy = px, -py; a = math.radians(rot)
    return (x + qx * math.cos(a) - qy * math.sin(a), y + qx * math.sin(a) + qy * math.cos(a))
b = pcbnew.LoadBoard(B)
nets = set(); boxes = []
LOCAL_ONLY = 3                                    # a net with at most this many pads elsewhere is ripped whole
for ref, (L, kind, x, y, rot, fn) in ch.items():
    f = b.FindFootprintByReference(ref)
    assert f.GetFPID().GetUniStringLibItemName() == fn, (ref, f.GetFPID().GetUniStringLibItemName(), fn)
    nets |= {p.GetNetname() for p in f.Pads() if p.GetNetname() and p.GetNetname() != "/GND"}
    ob = f.GetBoundingBox(False); ob.Inflate(mm(1.5)); boxes.append(ob)              # the old spot
    if not f.IsFlipped(): f.Flip(f.GetPosition(), False)
    sig = [(px, py) for n, px, py in fps[fn]["pads"] if n != "MP"]
    want = [plan_xy(px, py, x, y, rot) for px, py in sig]           # where each signal pad should land (either order)
    wc = (sum(p[0] for p in want) / len(want), sum(p[1] for p in want) / len(want))
    best = None
    for o in range(0, 360, 45):
        f.SetOrientationDegrees(o); f.SetPosition(pcbnew.VECTOR2I(mm(100 + x), mm(100 - y)))
        got = [R(p.GetPosition()) for p in f.Pads() if p.GetNumber() != "MP"]
        gc = (sum(p[0] for p in got) / len(got), sum(p[1] for p in got) / len(got))
        err = math.dist(gc, wc) + sum(min(math.dist(g, w) for w in want) for g in got) / len(got)
        if best is None or err < best[0]: best = (err, o)
    f.SetOrientationDegrees(best[1]); f.SetPosition(pcbnew.VECTOR2I(mm(100 + x), mm(100 - y)))
    nb = f.GetBoundingBox(False); nb.Inflate(mm(1.5)); boxes.append(nb)               # the new spot
    print(f"{ref} {kind:8s} at ({x:.2f}, {y:.2f}) KiCad turn {best[1]} (pad fit {best[0]:.3f} mm)")
npads = {}
for g_ in b.GetFootprints():
    for p in g_.Pads(): npads[p.GetNetname()] = npads.get(p.GetNetname(), 0) + 1
whole = {n for n in nets if npads.get(n, 0) <= LOCAL_ONLY + 1}      # motor / NFC / underglow lines: ripped whole
inside = lambda q: any(bx.Contains(q) for bx in boxes)
def hit(t):
    n = t.GetNetname()
    if n in whole: return True
    if n not in nets: return False
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    return any(inside(q) for q in pts)                                # shared nets (3V3, 5V, SPI): only round the connectors
gone = [t for t in b.GetTracks() if hit(t)]
for t in gone: b.Remove(t)
pcbnew.SaveBoard(B, b); print("removed", len(gone), "tracks / vias of", sorted(nets))
json.dump(sorted(nets), open(D + "_route/clash_nets.json", "w"))
