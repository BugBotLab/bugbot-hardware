# Main board routing, in stages (user, 2026-10-25: power planes first, then the high-current and USB / camera nets, then the
# rest). 4 layers: F.Cu signals + parts, In1.Cu solid GND, In2.Cu VSYS plane (the high-current rail: motors, kicker charger,
# both converters, up to ~3 A), B.Cu signals + parts; 3V3 (~1 A) goes as 0.4 mm tracks, 5V / battery as 0.6 mm tracks.
# (v1 had a 3V3 plane and VSYS as tracks: 7 VSYS links would not route at 0.6 mm through the dense areas.) Each Freerouting pass routes only its nets; earlier tracks are locked and go to
# Freerouting as fixed wiring.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_main.py setup
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_main.py pass power|signal|rest
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_main.py finish
import json, os, re, shutil, subprocess, sys, pcbnew

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
ROOT = BB + "/design/schematics/Main/"
B, PRO = ROOT + "BugBot_Main.kicad_pcb", ROOT + "BugBot_Main.kicad_pro"
RD = ROOT + "_route/"
JAVA = os.path.expanduser("~/.gradle/jdks/eclipse_adoptium-25-amd64-windows.2/bin/java.exe")
FREEROUTING = "C:/Users/Jerome/Documents/GitHub/freerouting/build/dist/freerouting-executable.jar"
mm = pcbnew.FromMM

POWER = [r"/GND", r"/3V3", r"/VSYS", r"/VBUS", r"/5V", r"/SERVO_5V", r"/BAT_.*", r"/VBAT_P", r"/VBAT_SW", r"/BAT_F", r"/FS_D",
         r"/M\d_[AB]", r"/KICK_HV", r"/KICK_BOOST", r"/KSW", r"/SOL_N", r"/SW33[AB]", r"/SW5", r"/BUZ_N"]
SIGNAL = [r"/USB_D[PN]", r"/CAM_.*", r"/I2C_.*"]
# widths fit the pads they land on (Freerouting cannot neck a track down at a fine-pitch pin); 0.15 clearance everywhere
CLASSES = {"Battery": dict(track_width=0.6, clearance=0.15, via_diameter=0.6, via_drill=0.3),   # cell -> switch -> VSYS: up to ~3 A
           "Rail3V3": dict(track_width=0.4, clearance=0.15, via_diameter=0.6, via_drill=0.3),
           "Power": dict(track_width=0.4, clearance=0.15, via_diameter=0.6, via_drill=0.3),     # 5V, motors, kicker, USB VBUS
           "Local": dict(track_width=0.3, clearance=0.15, via_diameter=0.5, via_drill=0.25),    # converter switch nodes at 0.5 mm pins
           "USB": dict(track_width=0.2, clearance=0.15, via_diameter=0.5, via_drill=0.25, diff_pair_width=0.2, diff_pair_gap=0.15),
           "Camera": dict(track_width=0.15, clearance=0.15, via_diameter=0.45, via_drill=0.2)}
BATTERY = [r"/BAT_.*", r"/VBAT_P", r"/VBAT_SW", r"/BAT_F", r"/FS_D"]
LOCAL = [r"/SW33[AB]", r"/SW5"]
PATTERNS = ([("Battery", p) for p in BATTERY] + [("Local", p) for p in LOCAL] +
            [("Power", p) for p in POWER if p not in ["/GND", "/3V3", "/VSYS"] + BATTERY + LOCAL] +
            [("Rail3V3", r"/3V3"), ("USB", r"/USB_D[PN]"), ("Camera", r"/CAM_.*")])


def board_outline_pts(b):
    bb = b.GetBoardEdgesBoundingBox()
    return [pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()), pcbnew.VECTOR2I(bb.GetRight(), bb.GetTop()),
            pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()), pcbnew.VECTOR2I(bb.GetLeft(), bb.GetBottom())]


def plane(b, layer, net, prio=0, clearance=0.2):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet(net))
    ol = z.Outline(); ol.NewOutline()
    for p in board_outline_pts(b): ol.Append(p)          # clipped to the board edge when filled
    z.SetLocalClearance(mm(clearance)); z.SetMinThickness(mm(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetAssignedPriority(prio)
    z.SetZoneName(f"{net.strip('/')} {b.GetLayerName(layer)}")
    b.Add(z); return z


def setup(keepouts=True):
    d = json.load(open(PRO))
    ns = d["net_settings"]
    keep = [c for c in ns["classes"] if c.get("name") == "Default"]
    base = keep[0]
    for name, vals in CLASSES.items():
        c = dict(base); c.update(vals); c["name"] = name; keep.append(c)
    ns["classes"] = keep
    ns["netclass_patterns"] = [{"netclass": n, "pattern": p} for n, p in PATTERNS]
    d["board"]["design_settings"]["rules"]["min_resolved_spokes"] = 1     # small pads on the planes get 1 spoke at least
    json.dump(d, open(PRO, "w"), indent=2)
    shutil.copy(B, B + ".before-routing")
    b = pcbnew.LoadBoard(B)
    for z in [z for z in b.Zones() if not z.GetIsRuleArea() or z.GetZoneName().startswith("In2 ")]:
        b.Remove(z)
    # inner layers are planes, not routing layers: Freerouting put signals on them (cutting the GND / VSYS planes) until
    # they were typed 'power' (exported to the DSN as power layers)
    # In1 stays a solid GND plane (return paths, emissions); In2 is MIXED: the VSYS pour fills round signals routed there.
    # (Both inner layers as power left only F / B for signals, with parts on both sides: ~80 links would not route.)
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER); b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_MIXED)
    plane(b, pcbnew.In1_Cu, "/GND")
    plane(b, pcbnew.In2_Cu, "/VSYS")
    # In2 is signal-free under the high-current parts (+2 mm) and along a corridor joining them, so the VSYS pour stays one
    # piece there (In2 signals had cut it into islands: U9's VM pin was left with none). v1 kept the whole power half
    # signal-free: Freerouting then stalled at ~100 open links. KiCad mm boxes; tracks only, the pour is allowed.
    for name, (x0, y0, x1, y1) in () if not keepouts else (("motor drivers", (74.2, 83.8, 95.4, 111.8)), ("power path", (70.5, 105.8, 90.5, 124.2)),
                                   ("3V3 / 5V converters", (81.8, 118.2, 104.0, 136.5)), ("kicker charger", (106.7, 114.9, 126.7, 130.5)),
                                   ("VSYS corridor", (102.0, 122.0, 108.7, 126.0))):
        ls2 = pcbnew.LSET(); ls2.AddLayer(pcbnew.In2_Cu)             # (LSET(layer) is not accepted in KiCad 10)
        k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetLayerSet(ls2); k.SetZoneName(f"In2 no signals: {name}")
        k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(False); k.SetDoNotAllowZoneFills(False); k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        ol = k.Outline(); ol.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)): ol.Append(pcbnew.VECTOR2I(mm(x), mm(y)))
        b.Add(k)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(B, b)
    print("net classes:", list(CLASSES), "| planes: In1.Cu GND, In2.Cu VSYS")


# (2026-10-25: staged passes failed: with GND / VSYS fan-outs locked from the power pass, Freerouting kept re-normalising
# them ("oscillating") and timed out. The board is routed in one pass ("all"); the classes still give power / USB / camera
# their widths.)
def wanted(net, stage):
    if stage in ("all", "fix", "close"): return True
    m = lambda pats: any(re.fullmatch(p, net) for p in pats)
    if stage == "power": return m(POWER)
    if stage == "signal": return m(SIGNAL) or m(POWER)     # the power nets stay: their locked tracks must find their nets
    return True                                            # the last pass: every connection still open (earlier tracks stay locked)


def run_pass(stage, passes=25, timeout=1800, lock=True):
    os.makedirs(RD, exist_ok=True)
    b = pcbnew.LoadBoard(B)
    for t in b.GetTracks():
        t.SetLocked(lock)                                  # locked: earlier passes stay; unlocked ("fix"): rip-up allowed
    # (tracks first: after a b.Remove(zone), KiCad 10's python can no longer list the tracks in the same session)
    for z in [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu)]:
        b.Remove(z)                                        # the outer GND pours come back in finish()
    dsn, ses = RD + f"{stage}.dsn", RD + f"{stage}.ses"
    assert pcbnew.ExportSpecctraDSN(b, dsn), "DSN export failed"
    # keep only this pass's nets in the DSN's network (the rest stay unrouted for later passes)
    txt = open(dsn, encoding="utf-8").read()
    out, i, n_keep, n_drop = [], 0, 0, 0
    for m in re.finditer(r"\(net (\"[^\"]*\"|\S+)", txt):
        s = m.start()
        if txt.rfind("(network", 0, s) == -1:
            continue
        d, j = 0, s
        while True:
            if txt[j] == "(": d += 1
            elif txt[j] == ")":
                d -= 1
                if d == 0: break
            j += 1
        name = m.group(1).strip('"')
        if s < i: continue
        out.append(txt[i:s])
        if wanted(name, stage):
            out.append(txt[s:j + 1]); n_keep += 1
        else:
            n_drop += 1
        i = j + 1
    out.append(txt[i:])
    txt2 = "".join(out)
    if lock:                                               # 'fix', not 'protect': Freerouting then leaves them alone
        txt2 = txt2.replace("(type protect)", "(type fix)")  # (protected wires were re-normalised in a loop: GND / VSYS)
    open(dsn, "w", encoding="utf-8").write(txt2)
    if os.path.exists(ses): os.remove(ses)
    with open(RD + f"{stage}_freerouting.log", "w") as log:      # streamed, so a timeout still leaves the log
        try:
            subprocess.run([JAVA, "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", str(passes), "--gui.enabled=false"],
                           stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"{stage}: Freerouting timed out after {timeout} s")
    assert os.path.exists(ses), f"no session: see {RD}{stage}_freerouting.log"
    shutil.copy(B, B + f".before-{stage}")
    assert pcbnew.ImportSpecctraSES(b, ses), "SES import failed"
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(B, b)
    print(f"{stage}: {n_keep} nets routed in this pass ({n_drop} left for others); tracks now {len(b.GetTracks())}")


def finish():
    b = pcbnew.LoadBoard(B)
    plane(b, pcbnew.F_Cu, "/GND", prio=0, clearance=0.25)    # outer GND pours, then stitch them to In1
    plane(b, pcbnew.B_Cu, "/GND", prio=0, clearance=0.25)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(B, b)
    print("outer GND pours added and filled")


if __name__ == "__main__":
    if sys.argv[1] == "pass" and sys.argv[2] == "all":
        run_pass("all", passes=40, timeout=3600)
    elif sys.argv[1] == "pass" and sys.argv[2] == "fix":       # carry on from the current routing, rip-up allowed
        run_pass("fix", passes=30, timeout=3600, lock=False)
    elif sys.argv[1] == "pass" and sys.argv[2] == "close":     # only the open links: every existing track fixed
        run_pass("close", passes=15, timeout=1500, lock=True)
    elif sys.argv[1] == "setup-planned":                         # planned routing: planes, no In2 keep-outs (the plan decides)
        setup(keepouts=False)
    else:
        {"setup": setup, "finish": finish}.get(sys.argv[1], lambda: run_pass(sys.argv[2]))()
