# Swap parts in place on a finished board: Value, MPN and LCSC on the board's footprints, the schematic's symbols and
# the JLC BOM (rows regrouped by value / part). Positions, footprints and routing are untouched, so the CPL stays valid.
# Used by retune_nfc_reader.py and jlc_basic_swaps.py.
import csv, io, os


def block(s, ref, kinds):
    """(start, end) of the footprint / symbol instance whose Reference is ref."""
    i = s.index(f'(property "Reference" "{ref}"')
    starts = [s.rfind(k, 0, i) for k in kinds]
    a = max(starts)
    depth = 0
    for j in range(a, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return a, j + 1
    raise ValueError(ref)


def set_prop(b, name, val):
    k = f'(property "{name}" "'
    i = b.find(k)
    if i < 0:
        return b, False
    j = b.index('"', i + len(k))
    return b[:i + len(k)] + val + b[j:], True


def patch(path, kinds, new):
    s = open(path, encoding="utf-8").read()
    for ref, (val, mpn, lcsc) in new.items():
        a, e = block(s, ref, kinds)
        b = s[a:e]
        for name, v in (("Value", val), ("MPN", mpn), ("LCSC", lcsc)):
            b, ok = set_prop(b, name, v)
            if not ok and name == "Value":
                raise ValueError(f"{ref}: no Value in {path}")
        s = s[:a] + b + s[e:]
    open(path, "w", encoding="utf-8").write(s)
    print("patched", os.path.basename(path))


def read_bom(bom):
    """(header line as written, header fields, body rows, quoting of the body) of a JLC BOM csv."""
    text = open(bom, encoding="utf-8").read()
    lines = text.splitlines()
    quoting = csv.QUOTE_ALL if len(lines) > 1 and lines[1].startswith('"') else csv.QUOTE_MINIMAL
    rows = list(csv.reader(io.StringIO(text)))
    return lines[0], rows[0], rows[1:], quoting


def write_bom(bom, header_line, body, quoting):
    out = io.StringIO(); out.write(header_line + "\n")               # header exactly as it was
    csv.writer(out, lineterminator="\n", quoting=quoting).writerows(body)
    open(bom, "w", encoding="utf-8", newline="").write(out.getvalue())


def patch_bom(bom, new):
    """Rewrite the JLC BOM with the new comment / LCSC, regrouping the rows by value / part."""
    header_line, head, body, quoting = read_bom(bom)
    ci = {h.lower(): k for k, h in enumerate(head)}
    kd = ci.get("designator"); kc = ci.get("comment"); kf = ci.get("footprint")
    kl = next((ci[h] for h in ci if "lcsc" in h or "jlc" in h), None)
    items = []
    for r in body:
        for ref in [x.strip() for x in r[kd].split(",") if x.strip()]:
            rr = list(r); rr[kd] = ref
            if ref in new:
                rr[kc] = new[ref][0]
                if kl is not None:
                    rr[kl] = new[ref][2]
            items.append(rr)
    groups = {}
    for rr in items:
        key = (rr[kc], rr[kf], rr[kl] if kl is not None else "")
        groups.setdefault(key, []).append(rr)
    rows = []
    for key, rs in groups.items():
        r0 = list(rs[0]); r0[kd] = ",".join(x[kd] for x in rs); rows.append(r0)
    write_bom(bom, header_line, rows, quoting)
    print("patched", os.path.basename(bom))


def swap(board_dir, name, new):
    """new: {ref: (value, MPN, LCSC)} applied to <name>.kicad_pcb, <name>.kicad_sch and jlc/<name>_BOM_JLC.csv."""
    patch(os.path.join(board_dir, f"{name}.kicad_pcb"), ["\t(footprint ", "(footprint "], new)
    patch(os.path.join(board_dir, f"{name}.kicad_sch"), ["\t(symbol\n", "(symbol\n", "\t(symbol ("], new)
    patch_bom(os.path.join(board_dir, "jlc", f"{name}_BOM_JLC.csv"), new)
