# One colour per robot style, from its name (the printed structural parts: chassis, motor caps, wheel frames, mast, deck,
# arms, tray ...). Bought parts, TPU rollers, the dome and the KiCad boards keep their real colours.
#   apply_colours.py colours the master (BugBot_Base) in the Base white; every variant build calls recolour(doc, style) before it saves, which
#   swaps the master's printed colour (or the old all-yellow) for the style's own.
STYLES = {                       # name: (hex, why) - stock PLA / PETG colours
    "Scorpion": ("#A31621", "crimson: a desert scorpion's red-brown"),
    "Wasp": ("#FFC400", "wasp yellow (the old all-robot yellow)"),
    "Ant": ("#E8590C", "fire-ant orange-red"),
    "Beetle": ("#1B7F3A", "jewel-beetle green"),
    "Spider": ("#37474F", "charcoal: the spider class, so the purple tags stand out"),
    "Base": ("#F2F2EE", "plain white: no style yet"),
}


def rgb(hx):
    return (int(hx[1:3], 16) / 255, int(hx[3:5], 16) / 255, int(hx[5:7], 16) / 255)


SOURCES = [rgb(h) for h, _ in STYLES.values()] + [(1.0, 0.769, 0.0)]   # any style's colour, or the old yellow


def _is_source(c, tol=0.02):
    return any(all(abs(a - b) <= tol for a, b in zip(c[:3], s)) for s in SOURCES)


def recolour(doc, style):
    """Every part in `doc` painted in a style colour (or the old yellow) -> `style`'s colour. Returns the parts changed."""
    new = rgb(STYLES[style][0]); n = 0
    for o in doc.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is None or not hasattr(vo, "ShapeColor"):
            continue
        hit = False
        dc = list(getattr(vo, "DiffuseColor", []) or [])
        if dc and any(_is_source(c) for c in dc):
            vo.DiffuseColor = [(new[0], new[1], new[2], c[3] if len(c) > 3 else 0.0) if _is_source(c) else c for c in dc]
            hit = True
        if _is_source(vo.ShapeColor) and not dc:
            vo.ShapeColor = new; hit = True
        n += hit
    return n
