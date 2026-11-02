# Fab clean-up (KiCad python), driven by KiCad's own DRC so nothing that carries a connection is touched: removes the
# second via of each hole_to_hole pair of one net, every via_dangling via and every track_dangling piece, re-running DRC
# once per run (tracks only with TRACKS=1: KiCad flags U8/U9 pad-escape stubs as dangling and removing them opens nets); run it again until it removes nothing (removing a stub can leave the next one dangling).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/fab_cleanup.py [board]
import os, re, subprocess, sys, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = sys.argv[1] if len(sys.argv) > 1 else BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
CLI = "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
RPT = B + ".cleanup.rpt"
ITEM = re.compile(r"@\((-?[\d.]+) mm, (-?[\d.]+) mm\): (Via|Track) \[([^\]]*)\](?: on ([^\s,]+))?(?:, length ([\d.]+) mm)?")


def drc():
    subprocess.run([CLI, "pcb", "drc", "--severity-all", "-o", RPT, B], capture_output=True)
    out, cur = [], None
    for line in open(RPT, encoding="utf-8"):
        if line.startswith("["): cur = [line[1:line.index("]")], []]; out.append(cur)
        elif cur and (m := ITEM.search(line)): cur[1].append(m.groups())
    return out


def near(a, b, tol=0.002): return abs(pcbnew.ToMM(a.x) - b[0]) < tol and abs(pcbnew.ToMM(a.y) - b[1]) < tol


tot = {"hole_to_hole": 0, "via_dangling": 0, "track_dangling": 0}
for rnd in range(1):                              # one round per process: a 2nd LoadBoard breaks KiCad python
    want = []                                     # (x, y, Via|Track, net, layer, length)
    for kind, items in drc():
        if kind == "hole_to_hole" and len(items) == 2 and all(i[2] == "Via" for i in items) and items[0][3] == items[1][3]:
            want.append(items[1])
        elif (kind == "via_dangling" or kind == "track_dangling" and os.environ.get("TRACKS")) and items:
            want.append(items[0])
        else: continue
        tot[kind] += 1
    if not want: break
    b = pcbnew.LoadBoard(B)
    kill = []
    for t in b.GetTracks():
        isvia = t.Type() == pcbnew.PCB_VIA_T
        for x, y, typ, net, layer, length in want:
            if t.GetNetname() != net or isvia != (typ == "Via"): continue
            p = (float(x), float(y))
            if isvia and near(t.GetPosition(), p): kill.append(t); break
            if not isvia and b.GetLayerName(t.GetLayer()) == layer and abs(pcbnew.ToMM(t.GetLength()) - float(length)) < 0.002 \
                    and t.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1])), pcbnew.FromMM(0.01)): kill.append(t); break
    for t in kill: b.Remove(t)
    pcbnew.SaveBoard(B, b)
    print(f"round {rnd + 1}: {len(want)} flagged, {len(kill)} removed", flush=True)
    if not kill: break
print("fab_cleanup:", tot)
