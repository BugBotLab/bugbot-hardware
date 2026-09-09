"""Extract symbol definitions and pin geometry from stock KiCad .kicad_sym files.

Lets us write symbol instances straight into a .kicad_sch without needing
KiCad's IPC link. Nothing here guesses: pin positions come from the library.
"""
import os
import re

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from paths import kicad_file
LIBDIR = kicad_file(r"share\kicad\symbols")


def _tokenise(text, start):
    """Return the substring of one balanced (...) expression starting at `start`."""
    depth = 0
    i = start
    in_str = False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise ValueError("unbalanced expression")



EXTENDS_RE = re.compile(r'\(extends "([^"]+)"\)')


def resolve(lib, name):
    """Return a symbol block with (extends ...) inheritance flattened.

    KiCad derived parts (e.g. AP2112K-3.3) carry only properties and inherit
    every pin and graphic from a base symbol. Reading them without following
    the link yields zero pins, silently.
    """
    blk = get_symbol(lib, name)
    m = EXTENDS_RE.search(blk)
    if not m:
        return blk
    base = resolve(lib, m.group(1))
    # keep the base's geometry, rename its sub-symbols to this part
    out = base.replace(f'"{m.group(1)}_', f'"{name}_')
    out = out.replace(f'(symbol "{m.group(1)}"', f'(symbol "{name}"', 1)
    # carry over the child's Value so the part reads correctly on the sheet
    cv = re.search(r'\(property "Value" "([^"]*)"', blk)
    if cv:
        out = re.sub(r'\(property "Value" "[^"]*"',
                     f'(property "Value" "{cv.group(1)}"', out, count=1)
    return out


_cache = {}


def _load(lib):
    if lib not in _cache:
        with open(os.path.join(LIBDIR, lib + ".kicad_sym"), encoding="utf-8") as f:
            _cache[lib] = f.read()
    return _cache[lib]


def get_symbol(lib, name):
    """Return the raw (symbol "name" ...) block from the library."""
    text = _load(lib)
    needle = f'(symbol "{name}"'
    idx = text.find(needle)
    if idx < 0:
        raise KeyError(f"{lib}:{name} not found")
    return _tokenise(text, idx)


def lib_symbol_block(lib, name):
    """The same block, re-keyed as "Lib:Name" for a schematic's lib_symbols."""
    block = resolve(lib, name)
    return block.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


PIN_RE = re.compile(
    r'\(pin\s+\w+\s+\w+\s*\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)'
    r'.*?\(name\s+"([^"]*)".*?\(number\s+"([^"]*)"',
    re.S)


def get_pins(lib, name):
    """[(number, pinname, x, y, angle)] in library coordinates (Y up)."""
    block = resolve(lib, name)
    pins = []
    for m in PIN_RE.finditer(block):
        x, y, ang, pname, num = m.groups()
        pins.append((num, pname, float(x), float(y), float(ang)))
    # de-duplicate: alternate pin functions repeat the same number
    seen, out = set(), []
    for p in pins:
        if p[0] in seen:
            continue
        seen.add(p[0])
        out.append(p)
    return out


def pin_xy(px, py, origin, rotation):
    """Library pin coords -> sheet coords for a symbol placed at `origin`.

    Schematic Y runs downward while library Y runs upward, hence the sign flip.
    """
    ox, oy = origin
    if rotation == 0:
        return (round(ox + px, 4), round(oy - py, 4))
    if rotation == 180:
        return (round(ox - px, 4), round(oy + py, 4))
    # Screen y points DOWN, so KiCad's on-screen 90-degree CCW rotation maps
    # (px, -py) through [[0,1],[-1,0]]: sheet = (ox - py, oy - px). The old
    # code had the signs negated (= a 270 rotation) - proven by the netlist
    # putting every rot-90 wire on the OPPOSITE pin. Symmetric parts hid it.
    if rotation == 90:
        return (round(ox - py, 4), round(oy - px, 4))
    if rotation == 270:
        return (round(ox + py, 4), round(oy + px, 4))
    raise ValueError(rotation)


if __name__ == "__main__":
    for lib, nm in [("Connector_Generic", "Conn_01x02"),
                    ("Connector_Generic", "Conn_02x06_Odd_Even"),
                    ("Connector", "USB_C_Receptacle_USB2.0_16P"),
                    ("Mechanical", "MountingHole_Pad")]:
        ps = get_pins(lib, nm)
        print(f"{lib}:{nm} -> {len(ps)} pins")
        for p in ps[:6]:
            print("   ", p)
