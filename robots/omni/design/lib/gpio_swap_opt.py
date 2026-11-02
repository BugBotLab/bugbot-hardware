# GPIO swaps for routing (plan step, 2026-10-25): give each movable P4 signal the module pad nearest where it goes.
# Fixed: USB on GPIO24/25 (USB-Serial/JTAG), the strapping pins 34-38 (their pull-ups / pull-downs were chosen for their
# signals), GPIO0/1 (32 kHz crystal), GPIO6/54 (the C6 link). ADC signals only on ADC1 (GPIO20-23) or ADC2 (GPIO49-53).
# Camera, encoders (PCNT), LEDs (RMT), SPI, I2C and plain I/O go through the GPIO matrix: any pin (datasheet 2.3.5).
#   C:/Python312/python.exe design/lib/gpio_swap_opt.py      -> prints the new map and _route/gpio_swap.json
import json, math
import numpy as np
from scipy.optimize import linear_sum_assignment
import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
nets = json.load(open(BB + "/design/schematics/Main/_route/nets.json"))
PAD_GPIO = {}
for i, g in enumerate((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 20, 21, 22, 23)): PAD_GPIO[16 + i] = g
PAD_GPIO.update({50: 24, 51: 25}); PAD_GPIO.update({53 + i: 26 + i for i in range(13)}); PAD_GPIO.update({67 + i: 39 + i for i in range(16)})
FIXED_GPIO = {24, 25, 34, 35, 36, 37, 38, 0, 1, 6, 54}
ADC = set(range(20, 24)) | set(range(49, 54))
ADC_SIGNALS = {"/VBAT_SENSE", "/SERVO_ISENSE", "/KICK_VSENSE", "/EXP_IO0"}
pad_xy, sig_dest, cur = {}, {}, {}
for g, ns in nets.items():
    for n, pads in ns.items():
        others = [p for p in pads if p["ref"] != "U6"]
        for p in pads:
            if p["ref"] == "U6" and int(p["pad"]) in PAD_GPIO:
                pad_xy[int(p["pad"])] = tuple(p["xy"])
                if others:
                    sig_dest[n] = (sum(o["xy"][0] for o in others) / len(others), sum(o["xy"][1] for o in others) / len(others))
                    cur[n] = int(p["pad"])
movable = sorted(n for n, pad in cur.items() if PAD_GPIO[pad] not in FIXED_GPIO)
slots = sorted(pad for pad in pad_xy if PAD_GPIO[pad] not in FIXED_GPIO)
# every free GPIO pad is a slot, used or not (pads with no net are in pad_xy only if they carry a net: add the idle ones)
for pad, g in PAD_GPIO.items():
    if g not in FIXED_GPIO and pad not in slots:
        slots.append(pad)
slots.sort()
U6 = (5.0, 19.0)
def xy_of(pad):
    if pad in pad_xy: return pad_xy[pad]
    # idle pad: place it from its neighbours' layout (same edge, 1 mm pitch) - only needed if used
    return None
known = [s for s in slots if xy_of(s) is not None]
# bundles by module edge (planner's choice: each edge gets the bundles heading its way; the distance only orders them)
EDGES = {"south": set(range(39, 54)), "east": set(range(26, 34)), "west": {2, 3, 4, 5, 7}, "north": set(range(8, 14)) | set(range(20, 24))}
BUNDLE = {}
for n in ("/CAM_D2", "/CAM_D3", "/CAM_D4", "/CAM_D5", "/CAM_D6", "/CAM_D7", "/CAM_D8", "/CAM_D9", "/CAM_PCLK", "/CAM_VSYNC",
          "/CAM_HREF", "/CAM_XCLK", "/VBAT_SENSE", "/SERVO_ISENSE", "/KICK_VSENSE"): BUNDLE[n] = "south"
for n in ("/KICK_FIRE", "/SERVO_PWM", "/ENC1_A", "/ENC1_B", "/BUZZER", "/ENC3_A", "/ENC3_B", "/IMU_INT1"): BUNDLE[n] = "east"
for n in ("/MOT1_IN1", "/MOT1_IN2", "/MOT2_IN1", "/MOT2_IN2", "/NFC_IRQ"): BUNDLE[n] = "west"
for n in ("/MOT3_IN1", "/MOT3_IN2", "/I2C_SDA", "/I2C_SCL", "/SPI_SCK", "/SPI_MOSI", "/SPI_MISO", "/EXP_IO0", "/ENC2_A", "/ENC2_B"):
    BUNDLE[n] = "north"
def cost(n, pad):
    x, y = pad_xy[pad]; d = math.dist((x, y), sig_dest[n])
    if n in BUNDLE and PAD_GPIO[pad] not in EDGES[BUNDLE[n]]: d += 1e4
    if y > 28: d += 12                                  # the edge facing the rim: the track must go round the module
    if n in ADC_SIGNALS and PAD_GPIO[pad] not in ADC: d += 1e4
    return d
C = np.array([[cost(n, s) for s in known] for n in movable])
r, c = linear_sum_assignment(C)
new = {movable[i]: known[j] for i, j in zip(r, c)}
before = sum(cost(n, cur[n]) for n in movable); after = sum(C[i, j] for i, j in zip(r, c))
print(f"movable signals {len(movable)}, slots {len(known)}: {before:.0f} mm -> {after:.0f} mm")
moves = [(n, cur[n], new[n]) for n in movable if new[n] != cur[n]]
for n, a, b in sorted(moves, key=lambda m: PAD_GPIO[m[2]]):
    print(f"  {n:16s} GPIO{PAD_GPIO[a]:2d} (pad {a}) -> GPIO{PAD_GPIO[b]:2d} (pad {b})   {cost(n, a):5.1f} -> {cost(n, b):5.1f} mm")
json.dump({n: PAD_GPIO[p] for n, p in new.items()}, open(BB + "/design/schematics/Main/_route/gpio_swap.json", "w"), indent=0)
