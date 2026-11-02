# NFC reader layout shared by build_nfc.py (parts, chassis features) and build_fasteners.py (its screws).
# Approved 2D sketch: sketches/nfc_mount_v3.png.  exec() this with `doc` set; it reads the nfc_* rows of the Params sheet.
#   reader-board frame (u, v): u along the board's long axis (J2 end +), v across, origin = the board centre; KiCad's
#   board frame (grid origin at the centre) maps to it 1:1.
import math


def _q(name):
    v = doc.Params.get(name)
    return float(v.Value) if hasattr(v, "Value") else float(v)


NFC = {k: _q("nfc_" + k) for k in ("coil_d", "coil_t", "pocket_d", "open_x", "open_y", "clamp_r", "clamp_a1", "boss_d", "boss_top",
                                     "ang", "cx", "cy", "tray_z", "tray_t", "post_d", "board_t")}
PLATE_Z, PLATE_TOP = _q("plate_z"), _q("plate_z") + _q("plate_t")
TRAY_TOP = NFC["tray_z"] + NFC["tray_t"]                    # = the reader board's underside
SEAT_Z = TRAY_TOP - 1.6                                     # post-screw heads: counterbored 1.6 (pan head 1.4)
_c, _s = math.cos(math.radians(NFC["ang"])), math.sin(math.radians(NFC["ang"]))


def uv(u, v, z=0.0):
    """reader-board frame -> robot (x, y, z)"""
    return (NFC["cx"] + u * _c - v * _s, NFC["cy"] + u * _s + v * _c, z)


POSTS_UV = [(11.0, 6.0), (12.5, -6.5), (-6.5, 6.0)]        # 1.8+ from the motor caps / gearmotors, floor to tray
# post 1 sits under the reader board's mounting hole H1 (25.0, 3.0 from its corner; approved 2D: sketches/nfc_screw_v2.png):
# its M2x8 comes from the top through the board and the tray (no counterbore); posts 2 and 3: M2x6 from the tray's
# counterbores, under the board
TOP_SCREW_POST = 0
POSTS = [uv(u, v) for u, v in POSTS_UV]
CLAMPS = [(NFC["clamp_r"] * math.cos(math.radians(NFC["clamp_a1"] + 120 * k)),
           NFC["clamp_r"] * math.sin(math.radians(NFC["clamp_a1"] + 120 * k))) for k in range(3)]
NOTCH_UV = (12.4, 14.0, -3.4, -1.6)                        # the board's edge notch beside J2 (u0, u1, v0, v1)
J2_UV = (8.7, -2.5)
# side-entry JST-SH since 2026-10-26 (approved 2D: sketches/nfc_connectors_v1.png): both mouths face +u, 2.9 tall.
# J1 (SM08B) at the near end faces the main board's J20; J2 (SM02B) faces the notch. Plug backs (cable exits), board frame:
J1_PLUG_UV = (-4.9, 0.0)                                   # J1 mouth at u -6.875, plug about 2 mm out
J2_PLUG_UV = (14.0, -2.5)                                  # J2 mouth at u 11.975: the plug back is at the board's end
PLUG_DZ = 1.2                                              # cable height over the board top (centre of the SH opening)
J20_PLUG_XY = (-15.0, 22.6)                                # main board J20 (side-entry, mouth facing -y), plug back, robot frame
# the coil cable: coil JST-SH 2 plug top (0, 0, 13.4) -> z 14.9 out between the gearmotors (sketches/nfc_cable_path.json,
# 1.6 mm channel, round the tray posts) -> up under the notch -> over the board edge -> down into J2
CABLE_Z = 14.9                                              # the run's height: clear of everything from z 14.5 to 15.3
CABLE_XY = [(0.0, 0.0), (-1.5, 0.0), (-2.0, 0.5), (-4.0, 0.75), (-5.0, 0.75), (-8.25, 4.0), (-9.0, 5.0), (-9.0, 8.0), (-7.75, 9.25),
            (-7.5, 10.5), (-7.5, 18.75), (-12.25, 23.5), (-12.25, 32.4)]                                       # round post 3
