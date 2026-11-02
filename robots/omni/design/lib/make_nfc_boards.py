# BugBot NFC reader: two small boards, generated (parametric like the rest of the robot).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/make_nfc_boards.py
# BugBot_NFC      26 x 18 mm, 1.6 mm, JLC-assembled: WiseSun WS1850S (MFRC522-compatible 13.56 MHz ISO 14443A reader) in
#                 SPI mode, the datasheet's dual-TX circuit (fig. 3) with the matching re-designed for our coil
#                 (design/lib/nfc_design.py + coil_inductance.py), JST-SH 8 to the main board, JST-SH 2 to the coil.
#                 It sits on a printed tray above the gearmotors' caps (see bugbot_freecad: the base's NFC mount).
# BugBot_NFCcoil  22 mm round, 0.8 mm: the antenna, a 2-layer pancake coil (4 + 4 turns, 2.08 uH, both ends at the centre),
#                 an upright JST-SH 2 in its middle; flush in a pocket in the chassis floor at the robot's centre.
# Every part checked on JLC (2026-10-21, design/lib/jlc_find.py); LCSC numbers in the BOM.
import json, math, os, re, subprocess, sys, uuid
import pcbnew

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
ROOTDIR = BB + "/design"
KS = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"
KF = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
JAVA = os.path.expanduser("~/.gradle/jdks/eclipse_adoptium-25-amd64-windows.2/bin/java.exe")
FREEROUTING = "C:/Users/Jerome/Documents/GitHub/freerouting/build/dist/freerouting-executable.jar"
U = lambda: str(uuid.uuid4())
mm = pcbnew.FromMM

# ------------------------------------------------------------------ shared: schematic writer (as make_front_board.py)
def pin_sx(num, name, x, y, rot, typ="passive"):
    return (f'\t\t\t(pin {typ} line\n\t\t\t\t(at {x:.2f} {y:.2f} {rot})\n\t\t\t\t(length 2.54)\n'
            f'\t\t\t\t(name "{name}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n'
            f'\t\t\t\t(number "{num}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n')
def custom_symbol(lib_id, ref, left, right, w=12.7, fp=""):
    name = lib_id.split(":")[1]
    n = max(len(left), len(right)); h = (n + 1) * 2.54 / 2
    eff = '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n'
    s = (f'(symbol "{lib_id}"\n\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n'
         f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 {h + 1.27:.2f} 0)\n{eff}\t\t)\n'
         f'\t\t(property "Value" "{name}"\n\t\t\t(at 0 {-h - 1.27:.2f} 0)\n{eff}\t\t)\n'
         f'\t\t(property "Footprint" "{fp}"\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(property "Datasheet" ""\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(property "Description" ""\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n{eff}\t\t)\n'
         f'\t\t(symbol "{name}_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start {-w / 2:.2f} {h:.2f})\n\t\t\t\t(end {w / 2:.2f} {-h:.2f})\n'
         '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
         f'\t\t(symbol "{name}_1_1"\n')
    for i, (num, nm, typ) in enumerate(left):
        s += pin_sx(num, nm, -w / 2 - 2.54, h - 2.54 * (i + 1), 0, typ)
    for i, (num, nm, typ) in enumerate(right):
        s += pin_sx(num, nm, w / 2 + 2.54, h - 2.54 * (i + 1), 180, typ)
    return s + '\t\t)\n\t\t(embedded_fonts no)\n\t)'
def sexp_block(t, i):
    d = 0
    for j in range(i, len(t)):
        if t[j] == "(": d += 1
        elif t[j] == ")":
            d -= 1
            if d == 0: return t[i:j + 1]
def pin_table(blk):
    return {m.group(9): (float(m.group(3)), float(m.group(4)), float(m.group(5)), m.group(8)) for m in re.finditer(
        r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]*)"', blk, re.S)}
def prop(name, val, x, y, hide=False):
    return (f'\t\t(property "{name}" "{val}"\n\t\t\t(at {x:.2f} {y:.2f} 0)\n' + ("\t\t\t(hide yes)\n" if hide else "") +
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
OUTW = {0: (-1, 0, 0, "right bottom"), 180: (1, 0, 0, "left bottom"), 90: (0, 1, 90, "right bottom"), 270: (0, -1, 90, "left bottom")}
G = lambda v: round(v / 2.54) * 2.54


class Design:
    def __init__(self, prj, title, comments, custom):
        self.prj, self.out = prj, f"{ROOTDIR}/{prj}"
        os.makedirs(self.out, exist_ok=True)
        self.title, self.comments, self.custom = title, comments, custom
        self.PARTS, self.NC, self.JLC = [], set(), {}
        self.root = U()

    def part(self, ref, lib, val, fp, nets, at, jlc=None, dnp=False):
        self.PARTS.append((ref, lib, val, fp, nets, at, dnp)); self.JLC[ref] = jlc

    def schematic(self, flags=("3V3", "GND")):
        libs, pins, body, self.sym_uuid = {}, {}, [], {}
        def lib_symbol(lid):
            if lid in self.custom:
                return self.custom[lid], self.custom[lid]
            lib, name = lid.split(":")
            t = open(KS + lib + ".kicad_sym", encoding="utf-8").read()
            blk = sexp_block(t, t.index(f'(symbol "{name}"'))
            return blk.replace(f'(symbol "{name}"', f'(symbol "{lid}"', 1), blk
        need = sorted({p[1] for p in self.PARTS} | {"power:PWR_FLAG"})
        for lid in need:
            libs[lid], raw = lib_symbol(lid); pins[lid] = pin_table(raw)
        self.pins = pins
        def place(lid, ref, value, fp, x, y, hide_ref=False, dnp=False):
            su = U(); self.sym_uuid[ref] = su
            s = (f'\t(symbol\n\t\t(lib_id "{lid}")\n\t\t(at {x:.2f} {y:.2f} 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom {"no" if ref[0] in "#H" else "yes"})\n'
                 f'\t\t(on_board {"no" if ref.startswith("#") else "yes"})\n\t\t(dnp {"yes" if dnp else "no"})\n\t\t(uuid "{su}")\n')
            pj = self.JLC.get(ref)
            s += prop("Reference", ref, x + 2, y - 6, hide_ref) + prop("Value", value, x + 2, y + 6) + prop("Footprint", fp, x, y, True) + prop("Datasheet", "", x, y, True)
            if pj:
                s += prop("MPN", pj[0], x, y, True) + prop("LCSC", pj[1], x, y, True)
            for num in pins[lid]:
                s += f'\t\t(pin "{num}"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
            s += f'\t\t(instances\n\t\t\t(project "{self.prj}"\n\t\t\t\t(path "/{self.root}"\n\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
            body.append(s)
        def label(net, x, y, ang=0, just="left bottom"):
            body.append(f'\t(label "{net}"\n\t\t(at {x:.2f} {y:.2f} {ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
        def wire(x0, y0, x1, y1):
            body.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {x0:.2f} {y0:.2f}) (xy {x1:.2f} {y1:.2f})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
        for ref, lid, val, fp, netmap, (sx, sy), dnp in self.PARTS:
            sx, sy = G(sx), G(sy)
            place(lid, ref, val, fp, sx, sy, dnp=dnp)
            for num, (px, py, prot, pname) in pins[lid].items():
                X, Y = sx + px, sy - py
                if (ref, num) in self.NC:
                    body.append(f'\t(no_connect\n\t\t(at {X:.2f} {Y:.2f})\n\t\t(uuid "{U()}")\n\t)\n')
                elif num in netmap:
                    dx, dy, ang, just = OUTW[int(prot) % 360]
                    X1, Y1 = X + 2.54 * dx, Y + 2.54 * dy
                    wire(X, Y, X1, Y1); label(netmap[num], X1, Y1, ang, just)
        for i, net in enumerate(flags):
            x, y = G(30 + 20 * i), G(190)
            place("power:PWR_FLAG", f"#FLG0{i + 1}", "PWR_FLAG", "", x, y, True); label(net, x, y)
        cm = "".join(f'\t\t(comment {i + 1} "{c}")\n' for i, c in enumerate(self.comments))
        sch = (f'(kicad_sch\n\t(version 20250610)\n\t(generator "bugbot")\n\t(generator_version "10.0")\n\t(uuid "{self.root}")\n\t(paper "A4")\n'
               f'\t(title_block\n\t\t(title "{self.title}")\n\t\t(rev "1")\n{cm}\t)\n'
               '\t(lib_symbols\n' + "".join("\t\t" + libs[l].replace("\n", "\n\t\t") + "\n" for l in need) + '\t)\n' + "".join(body) +
               f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
        open(f"{self.out}/{self.prj}.kicad_sch", "w", encoding="utf-8").write(sch)

    # ---- board helpers
    def new_board(self, thickness):
        b = pcbnew.BOARD(); b.SetCopperLayerCount(2)
        ds = b.GetDesignSettings(); ds.SetBoardThickness(mm(thickness))
        ds.SetGridOrigin(self.P(0, 0)); ds.SetAuxOrigin(self.P(0, 0))
        ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15); ds.m_ViasMinSize = mm(0.45); ds.m_MinThroughDrill = mm(0.25)
        ds.m_CopperEdgeClearance = mm(0.3)
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetTrackWidth(mm(0.2)); nc.SetClearance(mm(0.15)); nc.SetViaDiameter(mm(0.5)); nc.SetViaDrill(mm(0.3))
        self.board, self.nets, self.fps = b, {}, {}
        self.partmap = {p[0]: p for p in self.PARTS}
        return b

    @staticmethod
    def P(X, Y):
        return pcbnew.VECTOR2I(mm(100 + X), mm(100 - Y))

    @staticmethod
    def xy(o):
        v = o.GetPosition(); return (pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y))

    def net(self, n):
        n = n if n.startswith("/") or n.startswith("unconnected") else "/" + n
        if n not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.board, n); self.board.Add(ni); self.nets[n] = ni
        return self.nets[n]

    def add_fp(self, ref, X, Y, rot):
        _, lid, val, fp, netmap, _, dnp = self.partmap[ref]
        lib, name = fp.split(":")
        f = pcbnew.FootprintLoad(globals().get("LIBS", {}).get(lib) or                   # LIBS: {lib name: .pretty path} of a project's own libs
                                 (globals().get("LIBDIR", "") if lib == "BugBot" else KF + lib) + ".pretty", name)
        f.SetReference(ref); f.SetValue(val); f.SetFPIDAsString(fp)
        self.board.Add(f); f.SetPosition(self.P(X, Y)); f.SetOrientationDegrees(rot)
        f.SetPath(pcbnew.KIID_PATH(f"/{self.sym_uuid[ref]}"))
        pj = self.JLC.get(ref)
        if pj:
            for k, v in zip(("MPN", "LCSC"), pj):
                f.SetField(k, v); fld = f.GetField(k); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
        for p in f.Pads():
            num = p.GetNumber()
            if (ref, num) in self.NC:
                p.SetNet(self.net(f"unconnected-({ref}-{self.pins[lid][num][3]}-Pad{num})"))
            elif num in netmap:
                p.SetNet(self.net(netmap[num]))
        f.Value().SetVisible(False)
        f.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5))); f.Reference().SetTextThickness(mm(0.08))
        f.Reference().SetVisible(False)
        self.fps[ref] = f
        return f

    def edge_poly(self, pts):
        for a, b in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(self.board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
            s.SetStart(self.P(*a)); s.SetEnd(self.P(*b)); s.SetWidth(mm(0.05)); self.board.Add(s)

    def edge_circle(self, r):
        s = pcbnew.PCB_SHAPE(self.board); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetLayer(pcbnew.Edge_Cuts)
        s.SetCenter(self.P(0, 0)); s.SetEnd(self.P(r, 0)); s.SetWidth(mm(0.05)); self.board.Add(s)

    def track(self, pts, n, w=0.2, layer=pcbnew.F_Cu, locked=True):
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.board); t.SetStart(self.P(*a)); t.SetEnd(self.P(*b)); t.SetWidth(mm(w)); t.SetLayer(layer)
            t.SetNet(self.net(n)); t.SetLocked(locked); self.board.Add(t)

    def via(self, X, Y, n, size=0.5, drill=0.3):
        v = pcbnew.PCB_VIA(self.board); v.SetPosition(self.P(X, Y)); v.SetDrill(mm(drill)); v.SetWidth(mm(size)); v.SetNet(self.net(n))
        v.SetLocked(True); self.board.Add(v)

    def pour(self, layer, pts, n="GND"):
        z = pcbnew.ZONE(self.board); z.SetLayer(layer); z.SetNet(self.net(n))
        ol = z.Outline(); ol.NewOutline()
        for q in pts: ol.Append(self.P(*q))
        z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetAssignedPriority(0); self.board.Add(z)

    def keepout(self, pts, tracks=True, vias=True, pours=True, layers=None):
        k = pcbnew.ZONE(self.board); k.SetIsRuleArea(True)
        k.SetLayerSet(layers if layers is not None else pcbnew.LSET.AllCuMask())
        k.SetDoNotAllowTracks(tracks); k.SetDoNotAllowVias(vias); k.SetDoNotAllowZoneFills(pours); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
        ol = k.Outline(); ol.NewOutline()
        for q in pts: ol.Append(self.P(*q))
        self.board.Add(k)

    @staticmethod
    def cy_box(f, m=0.0):
        """courtyard box (KiCad mm, y down) on the footprint's own side, grown by m"""
        c = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
        return (pcbnew.ToMM(bb.GetLeft()) - m, pcbnew.ToMM(bb.GetTop()) - m, pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m)

    def place_legal(self, place, inside, keep=(), soft=None, free=(), bottom=False, gap=0.075, step=0.2, rings=40):
        """add the parts at (X, Y, rot); a part whose courtyard (+gap) would overlap another on its side, a keep box or
        leave the area (inside(box) on its courtyard shrunk by its soft margin) moves to the nearest free spot on a step
        grid. free: refs that may sit on keep boxes. Returns {ref: (X, Y)} of the parts that moved."""
        soft = soft or {}
        hits = lambda a_, b_: a_[0] < b_[2] and b_[0] < a_[2] and a_[1] < b_[3] and b_[1] < a_[3]
        moved = {}
        for ref, X, Y, rot in place:
            f = self.add_fp(ref, X, Y, rot)
            if bottom: f.SetLayerAndFlip(pcbnew.B_Cu)
            sm = soft.get(ref, 0.0)
            others = [self.cy_box(self.fps[r]) for r in self.fps if r != ref and self.fps[r].IsFlipped() == f.IsFlipped()] + \
                     ([] if ref in free else [(k[0] + sm, k[1] + sm, k[2] - sm, k[3] - sm) for k in keep])
            best = None
            for ring in range(rings):
                cand = sorted(((dx, dy) for dx in range(-ring, ring + 1) for dy in range(-ring, ring + 1) if max(abs(dx), abs(dy)) == ring),
                              key=lambda d: d[0] ** 2 + d[1] ** 2)
                for dx, dy in cand:
                    f.SetPosition(self.P(X + step * dx, Y + step * dy))
                    if inside(self.cy_box(f, -sm)) and not any(hits(self.cy_box(f, gap), o) for o in others):
                        best = (X + step * dx, Y + step * dy); break
                if best: break
            assert best, f"no room for {ref}"
            f.SetPosition(self.P(*best))
            if abs(best[0] - X) + abs(best[1] - Y) > 1e-6: moved[ref] = best
        return moved

    def clean_route(self, min_w=0.127):
        """after Freerouting: widen necked tracks to JLC's 2-layer minimum, drop vias left on one layer"""
        for t in list(self.board.GetTracks()):
            if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(min_w): t.SetWidth(mm(min_w))
        self.board.BuildConnectivity(); cn = self.board.GetConnectivity()
        for v in [t for t in self.board.GetTracks() if t.GetClass() == "PCB_VIA" and not t.IsLocked()]:
            lay = set()
            for it in cn.GetConnectedItems(v):
                if it.GetClass() == "PCB_TRACK": lay.add(it.GetLayer())
                elif it.GetClass() == "PAD": lay.add(pcbnew.F_Cu)
            if len(lay) < 2: self.board.Remove(v)

    def save(self, rules):
        self.board.BuildConnectivity()
        self.pcb = f"{self.out}/{self.prj}.kicad_pcb"
        pcbnew.SaveBoard(self.pcb, self.board)

    def route(self, board=None):
        board = board or self.board
        dsn, ses = f"{self.out}/_route/{self.prj}.dsn", f"{self.out}/_route/{self.prj}.ses"
        os.makedirs(f"{self.out}/_route", exist_ok=True)
        assert pcbnew.ExportSpecctraDSN(board, dsn), "DSN export failed"
        if os.path.exists(ses): os.remove(ses)
        try:
            r = subprocess.run([JAVA, "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", str(getattr(self, "passes", 300)), "--gui.enabled=false"],
                               capture_output=True, text=True, timeout=getattr(self, "route_timeout", 900))
            open(f"{self.out}/_route/freerouting.log", "w").write(r.stdout[-20000:] + r.stderr[-5000:])
        except subprocess.TimeoutExpired as e:
            open(f"{self.out}/_route/freerouting.log", "w").write(f"timed out after {e.timeout} s\n" + str(e.stdout or "")[-20000:])
            raise
        assert os.path.exists(ses), "Freerouting wrote no session: see _route/freerouting.log"
        assert pcbnew.ImportSpecctraSES(board, ses), "SES import failed"

    def route_without(self, drop_nets, remove=lambda t: False, remove_refs=(), keepouts=(), terminals=()):
        """Freerouting on a simplified copy of the board (it hangs on the floor loop's thousands of segments and on the
        underglow's long lanes). On the copy: the drop_nets copper goes and their pads each get a net of their own (the
        router leaves them); tracks / vias where remove(item) and the footprints remove_refs go; keepouts
        [(layers LSET, [(X, Y), ...])] stand in for what was removed; terminals [(X, Y, net, layer, d)] add a round pad
        there (the router joins pads, not track ends). The new (unlocked) tracks and vias come back into this board."""
        tmp = f"{self.out}/_route/{self.prj}_route.kicad_pcb"
        self.board.BuildConnectivity(); pcbnew.SaveBoard(tmp, self.board)
        b = pcbnew.LoadBoard(tmp)
        drop = {n if n.startswith("/") else "/" + n for n in drop_nets}
        k = 0
        for t in list(b.GetTracks()):
            if t.GetNetname() in drop or remove(t): b.Delete(t)
        for f in list(b.GetFootprints()):
            if f.GetReference() in remove_refs: b.Delete(f); continue
            for p in f.Pads():
                if p.GetNetname() in drop:
                    k += 1; ni = pcbnew.NETINFO_ITEM(b, f"/_KEEP{k}"); b.Add(ni); p.SetNet(ni)
        for layers, pts in keepouts:
            z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetLayerSet(layers)
            z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
            ol = z.Outline(); ol.NewOutline()
            for q in pts: ol.Append(self.P(*q))
            b.Add(z)
        for i, (x, y, net, layer, d) in enumerate(terminals):
            fp = pcbnew.FOOTPRINT(b); fp.SetReference(f"TERM{i + 1}"); fp.SetFPIDAsString("Route:Terminal")   # (the SES import needs a name)
            pd = pcbnew.PAD(fp); pd.SetShape(pcbnew.PAD_SHAPE_CIRCLE); pd.SetAttribute(pcbnew.PAD_ATTRIB_SMD); pd.SetNumber("1")
            pd.SetSize(pcbnew.VECTOR2I(mm(d), mm(d))); ls = pcbnew.LSET(); ls.AddLayer(layer); pd.SetLayerSet(ls)
            fp.Add(pd); b.Add(fp); fp.SetPosition(self.P(x, y))
            n_ = "/" + net.lstrip("/"); pd.SetNet(b.FindNet(n_))
        pcbnew.SaveBoard(tmp, b); b = pcbnew.LoadBoard(tmp)        # route a clean reload (in-memory edits crash the SES import)
        self.route(b)
        for t in b.GetTracks():
            if t.IsLocked(): continue
            if t.GetClass() == "PCB_VIA":
                v = pcbnew.PCB_VIA(self.board); v.SetPosition(t.GetPosition()); v.SetDrill(t.GetDrillValue()); v.SetWidth(t.GetWidth(pcbnew.F_Cu))
                v.SetNet(self.net(t.GetNetname())); self.board.Add(v)
            elif t.GetClass() == "PCB_TRACK":
                n = pcbnew.PCB_TRACK(self.board); n.SetStart(t.GetStart()); n.SetEnd(t.GetEnd()); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer())
                n.SetNet(self.net(t.GetNetname())); self.board.Add(n)

    def project_rules(self):
        pro = f"{self.out}/{self.prj}.kicad_pro"; dj = json.load(open(pro))
        ru = dj["board"]["design_settings"]["rules"]
        ru.update(min_copper_edge_clearance=0.3, min_track_width=0.127, min_clearance=0.127, min_text_height=0.5, min_resolved_spokes=1)
        json.dump(dj, open(pro, "w"), indent=2)

    def jlc_files(self):
        os.makedirs(f"{self.out}/jlc", exist_ok=True)
        key = lambda r: (re.match(r"\D+", r).group(), int(re.search(r"\d+", r).group()))
        groups = {}
        for ref, lid, val, fp, netmap, _, dnp in self.PARTS:
            if self.JLC.get(ref) and not dnp:
                groups.setdefault((val, fp.split(":")[1], self.JLC[ref][1]), []).append(ref)
        with open(f"{self.out}/jlc/{self.prj}_BOM_JLC.csv", "w", newline="", encoding="utf-8") as fh:
            fh.write("Comment,Designator,Footprint,LCSC\n")
            for (val, fpn, lc), refs in sorted(groups.items(), key=lambda g: key(min(g[1], key=key))):
                fh.write(f'"{val}","{",".join(sorted(refs, key=key))}","{fpn}","{lc}"\n')
        with open(f"{self.out}/jlc/{self.prj}_CPL_JLC.csv", "w", newline="", encoding="utf-8") as fh:
            fh.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
            for ref in sorted((r for r in self.fps if self.JLC.get(r)), key=key):
                f = self.fps[ref]; X, Y = self.xy(f)
                fh.write(f"{ref},{X:.4f}mm,{Y:.4f}mm,{'Bottom' if f.IsFlipped() else 'Top'},{f.GetOrientationDegrees() % 360:g}\n")
        # rotations + centres from JLC's own footprints (cpl_rot_check.py; CPL origin = the aux origin, as the gerbers)
        subprocess.run([sys.executable, f"{ROOTDIR}/lib/cpl_rot_check.py", self.pcb, f"{self.out}/jlc/{self.prj}_BOM_JLC.csv",
                        f"{self.out}/jlc/{self.prj}_CPL_JLC.csv", "--fix", "--origin=aux"], check=False)
        return groups


# ================================================================== the reader board
R = Design("BugBot_NFC", "BugBot NFC reader (WS1850S)",
           ["WS1850S 13.56 MHz ISO14443A reader, SPI; dual-TX matching for the 2.08 uH floor coil (BugBot_NFCcoil)",
            "Matching (nfc_design.py): EMC 2.2 uH + 47 pF, series 47 pF, parallel 68 + 22 pF, damping 2.2 R (Q ~34)",
            "J1 to the main board: 3V3 GND SCK MOSI MISO NSS RST IRQ.  J2 to the coil (2-wire)"], {})
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nfc_reader_circuit import add_reader, SIGNALS
add_reader(R, custom_symbol)
J8 = {**{str(i + 1): n for i, n in enumerate(SIGNALS)}, "MP": "GND"}
R.part("J1", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "To the main board (JST-SH 8)",
       "Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal", J8, (30, 80), ("SM08B-SRSS-TB(LF)(SN)", "C160407"))
R.part("J2", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "To the coil (JST-SH 2)",
       "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", {"1": "ANT_A", "2": "ANT_B", "MP": "GND"}, (200, 80),
       ("SM02B-SRSS-TB(LF)(SN)", "C160402"))
R.schematic()

R.new_board(1.6)
W2, H2 = 14.0, 9.0                                          # 28 x 18 board (tray: corners clear by 0.7 at 42 deg)
NOTCH, NY = 1.6, -2.5                                        # the coil's 2-wire cable comes up through a 1.8 x 1.6 notch beside J2
# (J2 and the notch sit 2.5 mm off the axis: a 6 x 6 part under the main board hangs over the other side, down to z 25.8)
OUTL = [(-W2, -H2), (W2, -H2), (W2, NY - 0.9), (W2 - NOTCH, NY - 0.9), (W2 - NOTCH, NY + 0.9), (W2, NY + 0.9), (W2, H2), (-W2, H2)]
R.edge_poly(OUTL)
# H1: one M2 hole over tray post 1 (approved 2D: mech/freecad/sketches/nfc_screw_v2.png). legalise() moves any part whose
# courtyard would overlap another, the plug lanes or H1 (0.15 mm apart) to the nearest free spot on the board.
# Side-entry JST-SH since 2026-10-26 (approved 2D: mech/freecad/sketches/nfc_connectors_v1.png): J1 SM08B at the near end,
# mouth +u toward the main board's J20; J2 SM02B mouth +u at the notch (the coil cable comes up through it into the plug).
# Kept free: J1's plug lane (KEEP below) and H1's screw head (H1 is placed first, as add_nfc_reader_hole.py did).
# Round the fixed blocks: the crystal and its caps in the strip above J1's lane, next to U1's OSC pins (21 / 22 on its top
# edge); U1 above J2 (SPI pins toward J1, TX pins toward the chains); decoupling under U1; the RX parts and pull-ups below;
# the two TX matching chains in rows above and below J2 (J2's pins face U1). Tracks may cross the lane: only parts may not.
PLACE = [("J1", -10.15, 0.0, 90), ("J2", 8.7, -2.5, 90), ("U1", 3.4, 3.7, 90),
         ("Y1", -2.1, 7.0, 0), ("C1", -5.0, 6.4, 90), ("C2", -6.2, 6.4, 90),
         ("C5", 1.2, -1.0, 0), ("C14", 3.6, -1.0, 0), ("C15", 1.2, -2.3, 0), ("C16", 3.6, -2.3, 0), ("C17", 1.2, -3.6, 0), ("C18", 3.6, -3.6, 0),
         ("R1", 1.2, -6.0, 0), ("C3", 3.6, -6.0, 0), ("R3", 1.2, -7.4, 0), ("C4", 3.6, -7.4, 0),
         ("R7", -3.2, -6.8, 90), ("R6", -4.4, -6.8, 90),
         ("L1", 8.2, 2.65, 0), ("R4", 11.6, 2.65, 0), ("C7", 7.8, 1.2, 0), ("C6", 9.9, 1.2, 0), ("C8", 12.0, 1.2, 0),
         ("L2", 7.2, -6.3, 0), ("R5", 10.6, -6.3, 0), ("C10", 6.0, -7.95, 0), ("C12", 8.1, -7.95, 0), ("C13", 10.2, -7.95, 0),
         ("C11", 12.3, -7.95, 0), ("C9", 13.0, -6.3, 90)]
# Y1 (0.8 mm tall) may put its courtyard margin over the lane's edge and nearer the board edge: its body still clears the
# 10 mm plug by >= 0.4 and its pads the edge by 0.6
SOFT = {"Y1": 0.55}
LANE_U = float(os.environ.get("NFC_LANE", "7.0"))           # J1's plug lane length from its mouth (u -6.875)
KEEP = [(100 - 6.875, 100 - 5.15, 100 - 6.875 + LANE_U, 100 + 5.15),          # J1 plug lane from its mouth (KiCad mm, y down)
        (100 + 12.0, 100 + 2.5 - 2.15, 100 + 14.0, 100 + 2.5 + 2.15)]           # J2's plug over the notch
h1 = pcbnew.FootprintLoad(KF + "MountingHole.pretty", "MountingHole_2.2mm_M2")
h1.SetReference("H1"); h1.SetValue("M2 (NFC tray post 1)"); h1.SetFPIDAsString("MountingHole:MountingHole_2.2mm_M2")
R.board.Add(h1); h1.SetPosition(R.P(11.0, 6.0)); h1.Reference().SetVisible(False); h1.Value().SetVisible(False)
def inside(bx):
    in_notch = bx[2] > 100 + W2 - NOTCH - 0.35 and bx[1] < 100 - NY + 0.9 + 0.35 and bx[3] > 100 - NY - 0.9 - 0.35
    return bx[0] >= 100 - W2 + 0.35 and bx[2] <= 100 + W2 - 0.35 and bx[1] >= 100 - H2 + 0.35 and bx[3] <= 100 + H2 - 0.35 and not in_notch
moved = R.place_legal(PLACE, inside, KEEP + [R.cy_box(h1)], SOFT, free=("J1", "J2"))
print("legalised:", {k: (round(v[0], 2), round(v[1], 2)) for k, v in moved.items()})
if os.environ.get("NFC_PLACE_ONLY"):
    pcbnew.SaveBoard(f"{R.out}/_place_check.kicad_pcb", R.board); raise SystemExit("placed only: _place_check.kicad_pcb")
ep = R.xy(R.fps["U1"].FindPadByNumber("33"))
for dx in (-0.8, 0.8):
    for dy in (-0.8, 0.8):
        R.via(ep[0] + dx, ep[1] + dy, "GND")                   # the exposed pad to the back GND pour
R.keepout([(-W2, -H2), (W2, -H2), (W2, -H2 + 0.35), (-W2, -H2 + 0.35)]); R.keepout([(-W2, H2 - 0.35), (W2, H2 - 0.35), (W2, H2), (-W2, H2)])
R.keepout([(-W2, -H2), (-W2 + 0.35, -H2), (-W2 + 0.35, H2), (-W2, H2)]); R.keepout([(W2 - 0.35, -H2), (W2, -H2), (W2, H2), (W2 - 0.35, H2)])
# AVDD (15) and VMID (16) sit among the TX pins on U1's right side: give each its own via to the back first, staggered
# (relative to the pins; TVDD (12) is left to the router since side-entry layout put L1 where its via went)
p15 = R.xy(R.fps["U1"].FindPadByNumber("15")); p16 = R.xy(R.fps["U1"].FindPadByNumber("16"))
R.track([p15, (p15[0] + 0.86, p15[1])], "3V3"); R.via(p15[0] + 0.86, p15[1], "3V3")
R.track([p16, (p16[0] + 1.46, p16[1])], "VMID"); R.via(p16[0] + 1.46, p16[1], "VMID")
R.save(None)
R.route()
R.clean_route()
R.pour(pcbnew.F_Cu, OUTL); R.pour(pcbnew.B_Cu, OUTL)
t = pcbnew.PCB_TEXT(R.board); t.SetText("BugBot NFC v2"); t.SetPosition(R.P(0.0, 0.0)); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
t.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6))); t.SetTextThickness(mm(0.1)); R.board.Add(t)
R.save(None); R.project_rules(); g_r = R.jlc_files()

if os.environ.get("NFC_READER_ONLY"):
    tr = [x for x in R.board.GetTracks() if x.GetClass() == "PCB_TRACK"]
    print("reader:", len(R.fps), "parts,", len(tr), "tracks; BOM lines", len(g_r)); raise SystemExit
# ================================================================== the coil board
C = Design("BugBot_NFCcoil", "BugBot NFC floor coil",
           ["2-layer pancake coil, 4 + 4 turns, trace 0.30 / gap 0.20, 2.08 uH (design/lib/coil_inductance.py)",
            "22 mm round, 0.8 mm; flush in the chassis floor at the robot centre; copper-free rim r > 10 for the clamp screws"], {})
C.part("J1", "Connector_Generic:Conn_01x02", "Coil (JST-SH 2)",                 # (the mounting tabs: footprint only)
       "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical", {"1": "COIL", "2": "COIL"}, (60, 60),        # one copper path from pin 1 to pin 2: one net
       ("BM02B-SRSS-TB(LF)(SN)", "C160388"))
C.schematic(flags=())
C.new_board(0.8)
C.edge_circle(11.0)
j = C.add_fp("J1", 0.0, 0.0, 180)                              # pins toward the spiral's ends, mounting tabs away
for pd in j.Pads():                                              # the mounting tabs: mechanical only, no net
    if pd.GetNumber() == "MP":
        pd.SetNetCode(0)
pads = {p.GetNumber(): C.xy(p) for p in j.Pads()}
Wt, St, NT, ROUT = 0.30, 0.20, 4, 10.0
p_ = Wt + St
r_in = ROUT - (NT - 1) * p_ - Wt / 2; r_oc = ROUT - Wt / 2
SEG = 72
a0 = math.radians(90)                                        # start: straight above the connector's pads
th = [a0 + 2 * math.pi * NT * k / (SEG * NT) for k in range(SEG * NT + 1)]
top = [((r_in + (r_oc - r_in) * (t_ - a0) / (th[-1] - a0)) * math.cos(t_), (r_in + (r_oc - r_in) * (t_ - a0) / (th[-1] - a0)) * math.sin(t_)) for t_ in th]
STOP = math.radians(28)                                      # the bottom spiral ends short of the start, so its via clears the top start
thb = [th[-1] + (t_ - a0) * (2 * math.pi * NT - STOP) / (2 * math.pi * NT) for t_ in th]
bot = [((r_oc - (r_oc - r_in) * (t_ - th[-1]) / (thb[-1] - th[-1])) * math.cos(t_), (r_oc - (r_oc - r_in) * (t_ - th[-1]) / (thb[-1] - th[-1])) * math.sin(t_)) for t_ in thb]
C.track(top, "COIL", Wt, pcbnew.F_Cu)
C.via(*top[-1], "COIL", 0.5, 0.3)
C.track(bot, "COIL", Wt, pcbnew.B_Cu)
end_in = (bot[-1][0] * (r_in - 0.9) / r_in, bot[-1][1] * (r_in - 0.9) / r_in)
C.track([bot[-1], end_in], "COIL", Wt, pcbnew.B_Cu)
C.via(*end_in, "COIL", 0.5, 0.3)
start_in = (top[0][0] * (r_in - 0.9) / r_in, top[0][1] * (r_in - 0.9) / r_in)
C.track([top[0], start_in, pads["1"]], "COIL", Wt, pcbnew.F_Cu)
C.track([end_in, pads["2"]], "COIL", Wt, pcbnew.F_Cu)
t = pcbnew.PCB_TEXT(C.board); t.SetText("NFC coil"); t.SetPosition(C.P(0, -3.6)); t.SetLayer(pcbnew.F_SilkS)
t.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6))); t.SetTextThickness(mm(0.1)); C.board.Add(t)
C.save(None); C.project_rules(); g_c = C.jlc_files()
json.dump({"coil": {"turns_per_layer": NT, "trace": Wt, "gap": St, "r_in": r_in, "r_out": r_oc, "L_uH": 2.081},
           "reader": {"size": [2 * W2, 2 * H2], "holes": []}},
          open(f"{ROOTDIR}/schematics/retired/NFC/mcad.json", "w"), indent=1)
tr = [x for x in R.board.GetTracks() if x.GetClass() == "PCB_TRACK"]
print("reader:", len(R.fps), "parts,", len(tr), "tracks;  coil:", len(C.fps), "part;  BOM lines", len(g_r), "+", len(g_c))
