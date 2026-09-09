"""Geometry of a KiCad schematic sheet with every wire and pin tied to its net.

Parses a .kicad_sch (the generated sheets: no mirrored symbols) into wires,
junctions, labels and symbol instances, computes each pin's sheet position
from the embedded library symbol, then unions everything that touches
(wire ends, junctions, pins, labels, T-joins of a wire ending on another
wire) and names each group from the golden netlist (pin -> net) or, for
groups with no pin, from a label. The bench viewer paints wires by their
net's simulated voltage and animates current on them.

    sheets = load_project(xml_path, sch_dir, root_sch)   # every sheet
    sheet["wires"] -> [{pts, net}] ; sheet["pins"] -> [{ref, num, x, y, net}]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib as S
from netlist2spice import Board

XY = re.compile(r"\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)")
AT = re.compile(r"\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)")


def blocks(text, head):
    """Top-level (one tab) blocks starting with `head`."""
    out, i = [], 0
    while True:
        p = text.find("\n\t" + head, i)
        if p < 0:
            return out
        p += 2
        if not text[p + len(head)].isspace():      # "(sheet" must not match "(sheet_instances"
            i = p + 1
            continue
        blk = S._tokenise(text, p)
        out.append(blk)
        i = p + len(blk)


def embedded_pins(text):
    """{lib_id: [(num, name, x, y, ang)]} from the sheet's lib_symbols block."""
    i = text.find("(lib_symbols")
    lib = S._tokenise(text, i)
    pins = {}
    pos = 0
    while True:
        j = lib.find('\n\t\t(symbol "', pos)
        if j < 0:
            break
        j += 3
        blk = S._tokenise(lib, j)
        name = re.match(r'\(symbol\s+"([^"]+)"', blk).group(1)
        seen, lst = set(), []
        for m in S.PIN_RE.finditer(blk):
            x, y, ang, pname, num = m.groups()
            if num in seen:
                continue
            seen.add(num)
            lst.append((num, pname, float(x), float(y), float(ang)))
        pins[name] = lst
        pos = j + len(blk)
    return pins


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def key(x, y):
    return (round(x * 100), round(y * 100))


def on_segment(pt, a, b, tol=0.02):
    (x, y), (ax, ay), (bx, by) = pt, a, b
    if abs(ay - by) < tol and abs(y - ay) < tol and min(ax, bx) - tol <= x <= max(ax, bx) + tol:
        return True
    if abs(ax - bx) < tol and abs(x - ax) < tol and min(ay, by) - tol <= y <= max(ay, by) + tol:
        return True
    return False


def parse_sheet(path, board):
    text = open(path, encoding="utf-8").read()
    libpins = embedded_pins(text)
    paper = re.search(r'\(paper\s+"([^"]+)"', text)
    size = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420)}.get(paper.group(1) if paper else "A3", (420, 297))
    wires, juncs, labels, hlabels, syms, pins, powers = [], [], [], [], [], [], []
    for blk in blocks(text, "(wire"):
        pts = [(float(a), float(b)) for a, b in XY.findall(blk)]
        for a, b in zip(pts, pts[1:]):
            wires.append({"pts": [a, b], "net": None})
    for blk in blocks(text, "(junction"):
        m = AT.search(blk)
        juncs.append((float(m.group(1)), float(m.group(2))))
    for head, lst in (("(label", labels), ("(hierarchical_label", hlabels), ("(global_label", labels)):
        for blk in blocks(text, head):
            name = re.match(r'\(\w+\s+"([^"]+)"', blk).group(1)
            m = AT.search(blk)
            lst.append({"name": name, "x": float(m.group(1)), "y": float(m.group(2))})
    sheetrefs = []
    for blk in blocks(text, "(sheet"):                # hierarchical sheet boxes: their pins join the root wires
        m = AT.search(blk)
        sz = re.search(r"\(size\s+([\d.]+)\s+([\d.]+)\)", blk)
        sname = re.search(r'\(property\s+"Sheetname"\s+"([^"]+)"', blk)
        x, y = float(m.group(1)), float(m.group(2))
        w, h = (float(sz.group(1)), float(sz.group(2))) if sz else (10, 10)
        sheetrefs.append({"ref": "sheet:" + (sname.group(1) if sname else "?"), "lib": "sheet", "value": "",
                          "x": x, "y": y, "rot": 0, "bbox": [x, y, x + w, y + h]})
        for pm in re.finditer(r'\(pin\s+"([^"]+)"\s+\w+\s*\n?\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)', blk):
            hlabels.append({"name": pm.group(1), "x": float(pm.group(2)), "y": float(pm.group(3))})
    for blk in blocks(text, "(symbol"):
        lib_id = re.search(r'\(lib_id\s+"([^"]+)"', blk)
        if not lib_id:
            continue
        lib_id = lib_id.group(1)
        m = AT.search(blk)
        x, y, rot = float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', blk).group(1)
        val = re.search(r'\(property\s+"Value"\s+"([^"]*)"', blk)
        val = val.group(1) if val else ""
        ppins = []
        for num, pname, px, py, pang in libpins.get(lib_id, []):
            sx, sy = S.pin_xy(px, py, (x, y), int(rot) % 360)
            ppins.append({"ref": ref, "num": num, "name": pname, "x": sx, "y": sy, "net": None})
        if ref.startswith("#"):
            for p in ppins:
                p["net"] = "GND" if lib_id.endswith(":GND") else None
                p["flag"] = lib_id.endswith("PWR_FLAG")
            powers.extend(ppins)
        else:
            pins.extend(ppins)
        xs = [p["x"] for p in ppins] or [x]
        ys = [p["y"] for p in ppins] or [y]
        syms.append({"ref": ref, "lib": lib_id, "value": val, "x": x, "y": y, "rot": rot,
                     "bbox": [min(xs) - 1.5, min(ys) - 1.5, max(xs) + 1.5, max(ys) + 1.5]})
    # ---- connectivity
    uf = UF()
    ends = []
    for i, w in enumerate(wires):
        a, b = w["pts"]
        uf.union(("w", i), key(*a))
        uf.union(("w", i), key(*b))
        ends.append((a, i))
        ends.append((b, i))
    for j in juncs:
        for i, w in enumerate(wires):
            if on_segment(j, *w["pts"]):
                uf.union(key(*j), ("w", i))
    for pt, wi in ends:                          # a wire ending on another wire connects
        for i, w in enumerate(wires):
            if i != wi and on_segment(pt, *w["pts"]):
                uf.union(("w", wi), ("w", i))
    for p in pins + powers:
        k = key(p["x"], p["y"])
        uf.union(k, k)
        for i, w in enumerate(wires):
            a, b = w["pts"]
            if key(*a) == k or key(*b) == k or (on_segment((p["x"], p["y"]), a, b) and any(key(*j) == k for j in juncs)):
                uf.union(k, ("w", i))
    for l in labels + hlabels:
        k = key(l["x"], l["y"])
        uf.union(k, k)
        for i, w in enumerate(wires):
            if on_segment((l["x"], l["y"]), *w["pts"]):
                uf.union(k, ("w", i))
    # ---- names: netlist pins first, then labels, then power symbols
    gname = {}
    for p in pins:
        raw = board.pinnet.get((p["ref"], p["num"]))
        if raw:
            gname.setdefault(uf.find(key(p["x"], p["y"])), raw)
    leaf = {}
    for n in board.nets:
        leaf.setdefault(n.rsplit("/", 1)[-1], n)
    for l in labels + hlabels:
        g = uf.find(key(l["x"], l["y"]))
        if g not in gname:
            full = leaf.get(l["name"], l["name"])
            gname[g] = full
    for p in powers:
        g = uf.find(key(p["x"], p["y"]))
        if p.get("net") == "GND":
            gname[g] = "GND"
    for w_i, w in enumerate(wires):
        w["net"] = gname.get(uf.find(("w", w_i)))
    for p in pins:
        p["net"] = board.pinnet.get((p["ref"], p["num"])) or gname.get(uf.find(key(p["x"], p["y"])))
    for l in labels + hlabels:
        l["net"] = gname.get(uf.find(key(l["x"], l["y"])))
    named = sum(1 for w in wires if w["net"])
    return {"file": os.path.basename(path), "size": size, "wires": wires, "junctions": juncs,
            "labels": labels + hlabels, "symbols": syms + sheetrefs, "pins": pins, "power": powers,
            "stats": "%d wires (%d named), %d symbols, %d pins" % (len(wires), named, len(syms), len(pins))}


def load_project(xml_path, sch_dir, root_name, prefix):
    board = Board(xml_path, prefix)
    text = open(os.path.join(sch_dir, root_name), encoding="utf-8").read()
    files, names = [root_name], {root_name: "root"}
    for blk in blocks(text, "(sheet"):
        sf = re.search(r'\(property\s+"Sheetfile"\s+"([^"]+)"', blk)
        sn = re.search(r'\(property\s+"Sheetname"\s+"([^"]+)"', blk)
        if sf:
            files.append(sf.group(1))
            names[sf.group(1)] = sn.group(1) if sn else sf.group(1)
    sheets = []
    for f in files:
        sh = parse_sheet(os.path.join(sch_dir, f), board)
        sh["name"] = names.get(f, f)
        sh["board"] = prefix
        sheets.append(sh)
    return board, sheets


if __name__ == "__main__":
    from paths import BOARDS, ROOT_SCH, netlist
    for bd, pre in (("motion", "M"), ("vision", "V"), ("odometry", "O")):
        b, sheets = load_project(netlist(bd), BOARDS[bd], ROOT_SCH[bd], pre)
        for sh in sheets:
            unnamed = [w for w in sh["wires"] if not w["net"]]
            print("%s %-34s %s%s" % (pre, sh["name"], sh["stats"], "" if not unnamed else "  UNNAMED at %s" % [w["pts"][0] for w in unnamed[:4]]))
