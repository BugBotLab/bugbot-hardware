# BugBot colour scheme (the user's choice): every printed structural part in the robot style's colour (style_colours.py); the functional printed parts
# (black TPU rollers + kick disc, white diffuser dome, grey PETG sleeve) and the bought parts in their real colours.
#   python fusionflow/ffclient.py run mech/freecad/apply_colours.py      (build_all.py runs it last)
# Printed parts: PLA / PETG / TPU colours. Bought parts: as they come. The KiCad boards keep KiCad's own colours.
doc = App.getDocument("BugBot_Base")
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
exec(open(BB + "/mech/freecad/style_colours.py", encoding="utf-8").read())
SC = STYLES["Base"][0]                                     # the master is the plain base: white; each style build recolours it (style_colours.py)
H = lambda h: (int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255)
SCHEME = {
    # printed
    "Chassis": SC,                                   # every printed structural part: the style colour
    "Mast": SC, "TopDeck": SC, "ServoBlock": SC, "TagBar": SC,   # (top; TagBar: the rear ID tag bar, tag_mounts.py)
    "HoopArmL": SC, "HoopArmR": SC, "HoopBracket": SC, "KickBracket": SC,
    "WheelFrame": SC, "WheelHalfOuter": SC, "WheelFrameOne": SC, "WheelHalfMotor": SC, "MotorCap": SC, "MotorCapR": SC,
    "Roller": "#141414", "KickDisc": "#161616",            # black TPU
    "HoopSleeve": "#161616",                                # black PLA sleeve (the user's choice)
    "Dome": "#E6EEF2",                                      # frosted clear PLA (the LED ring shines through it)
    # bought
    "FrontBar": "#C9A44C", "BrassLiner": "#C9A44C", "PivotTube": "#C9A44C", "PivotBushing": "#B07A3A", "BarWashers": "#C4C8CE", "BarScrew": "#2A2A2C", "BarNut": "#C4C8CE", "WheelPin": "#C4C8CE", "M3ThinNut": "#C4C8CE", "SolenoidPlunger": "#C4C8CE",
    "SolenoidSpring": "#D0D3D8", "Solenoid": "#B9BDC3", "DeckStandoffs": SC,   # steel / zinc / brass standoffs
    "SolenoidCoil": "#264DBF",                              # the JF-0520B's blue tape
    "Servo": "#2B4C9B", "ServoHorn": "#E2E2DA",             # SG90 (off-white: not the base white, or a recolour would paint it)
    "Gearmotor": "#B8BCC2",                                 # Pololu 2358 (metal can)
    "LEDCable": "#1F1F21", "NFCCable": "#1F1F21", "Antenna": "#C8A23C", "Ball": "#FF7A1A",          # orange ping-pong ball
}
done, missing = [], []
for name, hx in SCHEME.items():
    o = doc.getObject(name)
    if o is None or not hasattr(o, "ViewObject") or o.ViewObject is None:
        missing.append(name); continue
    vo = o.ViewObject
    vo.ShapeColor = H(hx)
    if name == "Dome":
        vo.Transparency = 45                               # clear PLA prints frosted: half see-through
    done.append(name)
result = {"coloured": len(done), "missing": missing}
