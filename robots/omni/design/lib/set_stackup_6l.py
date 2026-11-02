# Routing plan v2 step 1b: writes JLC's 6-layer stackup JLC06161H-3313 (1.6 mm) into the main board's file (KiCad's python
# cannot edit dielectric layers). Copper 1 oz outside, 0.5 oz inside.
#   C:/Python312/python.exe design/lib/set_stackup_6l.py
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
B = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
s = open(B, encoding="utf-8").read()
cu = lambda n, t: f'\t\t\t(layer "{n}"\n\t\t\t\t(type "copper")\n\t\t\t\t(thickness {t})\n\t\t\t)\n'
di = lambda k, typ, t, mat, er, lt: (f'\t\t\t(layer "dielectric {k}"\n\t\t\t\t(type "{typ}")\n\t\t\t\t(color "FR4 natural")\n'
                                     f'\t\t\t\t(thickness {t})\n\t\t\t\t(material "{mat}")\n\t\t\t\t(epsilon_r {er})\n\t\t\t\t(loss_tangent {lt})\n\t\t\t)\n')
new = (cu("F.Cu", 0.035) + di(1, "prepreg", 0.0994, "3313", 4.1, 0.02) + cu("In1.Cu", 0.0152)
       + di(2, "core", 0.55, "FR4", 4.6, 0.02) + cu("In2.Cu", 0.0152) + di(3, "prepreg", 0.1088, "2116", 4.16, 0.02)
       + cu("In3.Cu", 0.0152) + di(4, "core", 0.55, "FR4", 4.6, 0.02) + cu("In4.Cu", 0.0152)
       + di(5, "prepreg", 0.0994, "3313", 4.1, 0.02) + cu("B.Cu", 0.035))
st = s.index("(stackup")
a = s.index('(layer "F.Cu"', st); a = s.rindex("\n", 0, a) + 1
b = s.index('(layer "B.Mask"', st); b = s.rindex("\n", 0, b) + 1
s = s[:a] + new + s[b:]
open(B, "w", encoding="utf-8").write(s)
print("stackup: JLC06161H-3313 written")
