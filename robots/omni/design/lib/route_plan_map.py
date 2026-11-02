# Routing plan 1: every net's pads (robot frame: x forward, y left; KiCad x = 100 + X, y = 100 - Y) with side and layer, grouped
# by function, -> schematics/Main/_route/nets.json, for drawing and checking the routing plan.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_plan_map.py
import json, re, pcbnew
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
b = pcbnew.LoadBoard(BB + "/design/schematics/Main/BugBot_Main.kicad_pcb")
R = lambda v: (round(pcbnew.ToMM(v.x) - 100, 3), round(100 - pcbnew.ToMM(v.y), 3))
GROUPS = [("planes", r"/GND|/VSYS"), ("camera", r"/CAM_.*"), ("usb", r"/USB_D[PN]|/CC\d|/VBUS"), ("i2c", r"/I2C_.*"),
          ("spi_nfc", r"/SPI_.*|/NFC_.*|/EXP_SPI_CS"), ("motors", r"/MOT\d_IN\d|/M\d_[AB]|/DRV_.*|/U\d_V(CP|INT)"),
          ("encoders", r"/ENC\d_[AB]"), ("leds", r"/LED_.*|/BEACON_.*|/UNDER_.*|/STATUS_LED|/LED_STAT_A"),
          ("kicker", r"/KICK_.*|/KSW|/KFB|/SOL_N"), ("servo_buzzer", r"/SERVO_.*|/ISENSE_RAW|/BUZ.*"),
          ("power", r"/3V3|/5V|/BAT_.*|/VBAT_.*|/FS_D|/DW_.*|/Q\d_G|/SW_.*|/SW33.|/SW5|/FB33|/FB5|/CHIP_PU|/USB_VBUS_DET"),
          ("expansion", r"/EXP_IO\d|/EXPANDER_INT|/IMU_INT\d")]
nets = {}
for f in b.GetFootprints():
    for p in f.Pads():
        n = p.GetNetname()
        if not n or n.startswith("unconnected"): continue
        side = "B" if f.IsFlipped() else "F"
        tht = p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        nets.setdefault(n, []).append({"ref": f.GetReference(), "pad": p.GetNumber(), "xy": R(p.GetPosition()),
                                        "side": "both" if tht else side})
out = {}
for n, pads in nets.items():
    if len(pads) < 2: continue
    g = next((g for g, pat in GROUPS if re.fullmatch(pat, n)), "other")
    out.setdefault(g, {})[n] = pads
json.dump(out, open(BB + "/design/schematics/Main/_route/nets.json", "w"), indent=0)
for g, ns in out.items():
    sides = {}
    for pads in ns.values():
        k = "".join(sorted({p["side"] for p in pads}))
        sides[k] = sides.get(k, 0) + 1
    print(f"{g:13s} {len(ns):3d} nets  pads on sides: {sides}  e.g. {list(ns)[:6]}")
