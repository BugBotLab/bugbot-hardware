# SW1's footprint (power switch v3, 2026-10-25): C&K OS102011MA1QN1 right-angle slide switch AND its SK-12D07 copies
# (Amazon UK sourcingmap B00PDKEX1E, LCSC ROCPU SK-12D07-6). From KiCad's SW_Slide_SPDT_Angled_CK_OS102011MA1Q (pins 1-3 at
# 2.0 pitch, the C&K 3D model), with shell-tab holes that take both: C&K tabs at +-4.2 (holes 1.1 x 1.8, LCSC C226259),
# copies at +-4.0 (0.9 x 1.4, LCSC C16493666) -> slots at +-4.1 from pin 2, 1.3 x 1.8, on 1.9 x 2.4 pads (KiCad's are
# 2.2 x 3.5 on 1.5 holes, which made the part too wide for its place by the wall). Courtyard drawn tight round it.
# (Text edit of the KiCad file: KiCad 10's python breaks after removing a footprint item.)
#   C:/Python312/python.exe design/lib/make_sw1_footprint.py
import re
SRC = "C:/Program Files/KiCad/10.0/share/kicad/footprints/Button_Switch_THT.pretty/SW_Slide_SPDT_Angled_CK_OS102011MA1Q.kicad_mod"
NAME = "SW_Slide_SPDT_Angled_OS102011MA1Q_SK-12D07"
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
DST = BB + f"/design/lib/BugBot.pretty/{NAME}.kicad_mod"
s = open(SRC, encoding="utf-8").read()
s = s.replace('(footprint "SW_Slide_SPDT_Angled_CK_OS102011MA1Q"', f'(footprint "{NAME}"', 1)
s = re.sub(r'\(descr "[^"]*"\)', '(descr "C&K OS102011MA1QN1 right-angle slide switch, SPDT, and its SK-12D07 copies (same body): pins at 2.0, '
           'shell-tab slots 1.3 x 1.8 at +-4.1 from pin 2 take both makers\' tabs; slider toward +y")', s, count=1)


def block(text, start):
    """the balanced (...) block starting at index start"""
    d = 0
    for i in range(start, len(text)):
        d += text[i] == "("; d -= text[i] == ")"
        if d == 0: return i + 1


out, i = [], 0
while True:
    j = s.find("(pad ", i)
    if j < 0: out.append(s[i:]); break
    k = block(s, j); pad = s[j:k]
    if pad.startswith('(pad ""'):                         # shell tabs
        pad = re.sub(r"\(size [\d.]+ [\d.]+\)", "(size 1.9 2.4)", pad, count=1)
        pad = re.sub(r"\(drill [^)]*\)", "(drill oval 1.3 1.8)", pad, count=1)
    else:                                                 # pins 1-3
        pad = re.sub(r"\(size [\d.]+ [\d.]+\)", "(size 1.6 2.2)", pad, count=1)
        pad = re.sub(r"\(drill [^)]*\)", "(drill 1)", pad, count=1)
    out.append(s[i:j]); out.append(pad); i = k
s = "".join(out)
# courtyard: drop KiCad's, draw body + tabs (x -3.3..7.3, y -2.5..2.5) and the slider's sweep (x -0.25..4.25, to y 6.5)
out, i = [], 0
while True:
    j = s.find("(fp_line", i)
    if j < 0: out.append(s[i:]); break
    k = block(s, j); item = s[j:k]
    out.append(s[i:j])
    if '"F.CrtYd"' not in item: out.append(item)
    i = k
s = "".join(out)
pts = [(-3.3, -2.5), (7.3, -2.5), (7.3, 2.5), (4.25, 2.5), (4.25, 6.5), (-0.25, 6.5), (-0.25, 2.5), (-3.3, 2.5)]
crt = "".join(f'\t(fp_line (start {x0} {y0}) (end {x1} {y1}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))\n'
              for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
s = s.replace("\t(pad ", crt + "\t(pad ", 1)
open(DST, "w", encoding="utf-8").write(s)
print("wrote", DST)
