# Routes one stage of routing plan v1 with route_engine.py on top of what is already on the board, then (with "apply")
# adds it to the board, refills, runs DRC and draws the stage. Stages as approved: 1 power, 2 USB + camera,
# 3 sense / motors / encoders, 4 I2C + SPI, 5 the rest.
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_fill_export.py      (board -> _route/copper.json)
#   C:/Python312/python.exe design/lib/route_stage.py 1                               (-> _route/stage1.json + log)
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/route_fill_apply.py design/schematics/Main/_route/stage1.json
#   C:/Python312/python.exe design/lib/route_stage.py 1 draw                          (DRC summary + stage picture)
import sys, json, time, subprocess
from route_engine import Board, R, net_class

# lanes from routing plan v1 (robot frame, design/schematics/Main/draw_routing_plan.py), slack added to the widths
LANES = {
    "/3V3": [("B", [(-10.5, -26.5), (-4.5, -18), (-4.0, 2.5), (-2.5, 6.0)], 2.0)],
    "/5V": [("F", [(-6.5, -23.5), (-8.5, -6), (-8.5, 12), (-4, 15.5)], 2.2)],
}
USB_LANE = [("B", [(-31, -11), (-18, -3.5), (-15.5, 3.2), (-8, 4.2)], 1.8), ("I", [(-8, 4.0), (-5, 8), (12, 20), (17.5, 24)], 1.8)]
CAM_LANE = [("F", [(17.5, -17), (17.5, 3.4)], 6.0), ("B", [(16.5, 3.6), (10, 4.6), (4, 5.4)], 4.0)]
for n in ("/USB_DP", "/USB_DN"): LANES[n] = USB_LANE
CAMERA = ["/CAM_D4", "/CAM_D3", "/CAM_D5", "/CAM_D2", "/CAM_D6", "/CAM_D7", "/CAM_D8", "/CAM_D9", "/CAM_HREF", "/CAM_VSYNC",
          "/CAM_PCLK", "/CAM_XCLK", "/CAM_PCLK_J", "/CAM_XCLK_J"]          # by U6 pad, east (nearest J6) first
for n in CAMERA: LANES[n] = CAM_LANE
SENSE_LANE = [("I", [(2.5, 5.5), (2.5, -10), (4.5, -22)], 2.6), ("B", [(2.5, 5.5), (-6.0, 2.5), (-19.0, -5.5)], 1.8)]
EAST_LANE = [("I", [(18.6, 15), (20.5, 8), (20.5, -11), (14, -22), (12, -33)], 3.2)]
EAST1_LANE = [("B", [(18.6, 20), (22.5, 27.5)], 2.2)]
WEST_LANE = [("I", [(-6.5, 27), (-4.5, 8), (-7.5, 3.0), (-10.5, 1.0)], 2.6)]
MOT3_LANE = [("I", [(-3, 30.5), (-2.5, 8), (-1, 3.5)], 2.6), ("F", [(-1, 3.5), (-1.5, -12), (-1.5, -18)], 1.8)]
ENC2_LANE = [("B", [(-6, 33.2), (-22, 30), (-33, 14), (-36, 7)], 1.8)]
for ns, ln in ((("/VBAT_SENSE", "/SERVO_ISENSE", "/KICK_VSENSE"), SENSE_LANE),
               (("/KICK_FIRE", "/SERVO_PWM", "/ENC3_A", "/ENC3_B", "/IMU_INT1"), EAST_LANE),
               (("/ENC1_A", "/ENC1_B", "/BUZZER"), EAST1_LANE),
               (("/MOT1_IN1", "/MOT1_IN2", "/MOT2_IN1", "/MOT2_IN2", "/NFC_IRQ"), WEST_LANE),
               (("/MOT3_IN1", "/MOT3_IN2"), MOT3_LANE), (("/ENC2_A", "/ENC2_B"), ENC2_LANE)):
    for n in ns: LANES[n] = ln
# planned by hand (2026-10-25): module pad -> via just inside U6 -> In2 south -> via at the driver pin's fan-out stub
for n in ("/MOT2_IN1", "/MOT2_IN2"): LANES[n] = [("I", [(-6.3, 27.5), (-6.0, 8.0), (-5.6, 1.8)], 1.6), ("B", [(-7.5, 27), (-6.3, 27)], 1.2)]
for n in ("/MOT3_IN1", "/MOT3_IN2"): LANES[n] = [("I", [(-0.2, 30.5), (-0.5, 8.0), (-5.0, 4.0), (-5.4, -6.5)], 1.6), ("B", [(0, 31.5), (-0.2, 30.4)], 1.2)]
# routing plan v2 (6 layers): the inner layers are free signal layers with their own directions, so only lanes on the
# outer layers stay (power trunks, camera, rim strips); the USB pair runs on B along plan_v2.USB_PATH
LANES = {n: v for n, v in LANES.items() if all(l in ("F", "B") for l, _, _ in v)}
# floor plan v2 (2026-10-25) moved the parts: the v1 lanes no longer fit; the inner layers' directions do the planning.
# Only the USB pair keeps a lane: on B along J1 -> U2 -> the module, over In4 GND (plan_v2.usb_path)
import plan_v2
LANES = {n: [("B", list(plan_v2.usb_path().coords), 1.8)] for n in ("/USB_DP", "/USB_DN")}
ACT_POWER = ["/M1_A", "/M1_B", "/M2_A", "/M2_B", "/M3_A", "/M3_B", "/U8_VCP", "/U8_VINT", "/U9_VCP", "/U9_VINT",
             "/KSW", "/KFB", "/KICK_BOOST", "/KICK_HV", "/SOL_N", "/KICK_G", "/KICK_GY", "/ISENSE_RAW", "/SERVO_5V", "/SERVO_SIG"]
STAGE3_SIG = ["/VBAT_SENSE", "/SERVO_ISENSE", "/KICK_VSENSE", "/MOT1_IN1", "/MOT1_IN2", "/MOT2_IN2", "/MOT2_IN1",
              "/MOT3_IN1", "/MOT3_IN2", "/KICK_FIRE", "/SERVO_PWM", "/ENC3_A", "/ENC3_B", "/ENC1_A", "/ENC1_B",
              "/ENC2_A", "/ENC2_B", "/DRV_nSLEEP", "/DRV_nFAULT", "/KICK_CHG_EN"]
POWER_LOCAL = ["/SW33A", "/SW33B", "/SW5", "/FB33", "/FB5", "/DW_CS", "/DW_OD", "/DW_OC", "/DW_VCC", "/FS_D", "/BAT_N",
               "/BAT_P", "/BAT_F", "/Q1_G", "/Q2_G", "/VBAT_P", "/VBAT_SW", "/SW_G", "/SW_ON", "/VBUS"]
STAGES = {
    1: dict(nets=POWER_LOCAL + ["/5V", "/3V3"], planes=[("/GND", "GND"), ("/VSYS", "VSYS")], fanout=["U8", "U9", "U7"]),
    2: dict(nets=["/CC1", "/CC2"] + CAMERA),                     # the USB pair: usb_pair2.py afterwards (high speed, B.Cu over In4 GND)
    3: dict(nets=ACT_POWER + STAGE3_SIG),
    5: dict(nets=["/USB_VBUS_DET", "/CHIP_PU", "/EXPANDER_INT", "/IMU_INT1", "/IMU_INT2", "/EXP_IO0", "/EXP_IO1", "/EXP_IO2",
                  "/EXP_IO3", "/EXP_IO4", "/LED_BEACON_DIN", "/BEACON_DY", "/BEACON_DATA", "/LED_UNDER_DIN", "/UNDER_DY",
                  "/UNDER_DATA", "/STATUS_LED", "/LED_STAT_A", "/BUZZER", "/BUZ_G", "/BUZ_N"], stitch=True),
    4: dict(nets=["/I2C_SDA", "/I2C_SCL", "/SPI_SCK", "/SPI_MOSI", "/SPI_MISO", "/EXP_SPI_CS", "/NFC_NSS", "/NFC_RST",
                  "/NFC_IRQ"]),
    "fix": dict(nets=["/MOT1_IN2", "/MOT2_IN1", "/MOT2_IN2", "/MOT3_IN1", "/MOT3_IN2"],
                fanout=["U8", "U9"], rippable=True),
}


def run(stage):
    # stage "123": those stages' nets in one pass, all plane vias last (early plane vias boxed in the drivers' signal pins)
    keys = [stage] if stage in STAGES else [int(k) for k in str(stage)]
    st = {"nets": [n for k in keys for n in STAGES[k]["nets"]],
          "planes": [p for k in keys for p in STAGES[k].get("planes", [])],
          "fanout": [r for k in keys for r in STAGES[k].get("fanout", [])],
          "rippable": any(STAGES[k].get("rippable") for k in keys)}
    t0 = time.time()
    b = Board(rippable=st.get("rippable", False))
    for n, ln in LANES.items(): b.lanes.setdefault(n, b.lane_mask(ln))      # so re-routed nets keep their lanes
    print(f"board loaded {time.time() - t0:.0f} s")
    for ref in st.get("fanout", []):                 # motor drivers: GND pins into the exposed pad; U7 has none
        b.fanout(ref, ep="17", inward=("/GND",)) if ref in ("U8", "U9") else b.fanout(ref, ep=None, inward=())
    log = []
    for net in st["nets"]:
        lane = b.lane_mask(LANES[net]) if net in LANES else None
        t = time.time()
        done, fail = b.route_net(net, lane)
        log.append((net, done, fail)); print(f" {net:16s} {net_class(net)[0]:8s} joined {done:2d} failed {fail}  {time.time() - t:.0f} s", flush=True)
    for net, plane in st.get("planes", []):
        t = time.time()
        done, fail = b.plane_drops(net, plane)
        log.append((net + " vias", done, fail)); print(f" {net:16s} plane vias {done:3d} failed {fail}  {time.time() - t:.0f} s", flush=True)
    if any(STAGES[k].get("stitch") for k in keys):
        placed, tried = b.stitch_edge()
        log.append(("GND stitching vias", placed, tried - placed)); print(f" GND stitching vias {placed} of {tried} spots")
    import route_engine
    route_engine.MAX_RIPS = 6
    planes = dict(st.get("planes", []))
    for rnd in range(3):                                  # repair: open connections again, with more rip-ups allowed
        todo = sorted(b.failed); b.failed = set()
        if not todo: break
        print(f"repair round {rnd + 1}: {todo}")
        for net in todo:
            done, fail = (b.plane_drops(net, planes[net]) if net in planes else b.route_net(net, b.lanes.get(net)))
            log.append((net + f" (repair {rnd + 1})", done, fail))
    print("still open:", sorted(b.failed))
    b.save(R + f"stage{stage}.json")
    json.dump(log, open(R + f"stage{stage}_log.json", "w")); json.dump(b.necked, open(R + f"stage{stage}_necked.json", "w"))
    print(f"stage {stage}: {len(b.out_tracks)} tracks, {len(b.out_vias)} vias, {time.time() - t0:.0f} s")


def draw(stage):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle
    import os as _os                                  # repo-relative paths: see .bugbot-root
    _d = _os.path.dirname(_os.path.abspath(__file__))
    while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
    BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
    pcb = BB + "/design/schematics/Main/BugBot_Main.kicad_pcb"
    rep = R + f"drc_stage{stage}.json"
    subprocess.run(["C:/Program Files/KiCad/10.0/bin/kicad-cli.exe", "pcb", "drc", "--format", "json", "--severity-error",
                    "-o", rep, pcb], capture_output=True)
    drc = json.load(open(rep))
    kinds = {}
    for v in drc.get("violations", []): kinds[v["type"]] = kinds.get(v["type"], 0) + 1
    unconn = len(drc.get("unconnected_items", []))
    cu = json.load(open(R + "copper.json")); new = json.load(open(R + f"stage{stage}.json"))
    log = json.load(open(R + f"stage{stage}_log.json"))
    fig = plt.figure(figsize=(18, 11))
    ax = fig.add_axes([0.01, 0.02, 0.62, 0.93]); tx = fig.add_axes([0.64, 0.02, 0.35, 0.93]); tx.axis("off")
    big = max(cu["edge"], key=lambda e: e["r"]); cut = min(cu["edge"], key=lambda e: e["r"])
    ax.add_patch(Circle((big["cx"], big["cy"]), big["r"], fc="#f6f6f2", ec="k"))
    ax.add_patch(Circle((cut["cx"], cut["cy"]), cut["r"], fc="white", ec="k"))
    for p in cu["pads"]:
        if len(p["poly"]) < 3: continue
        col = "#999" if len(p["layers"]) > 1 else ("#e0a0a0" if p["layers"] == ["F"] else "#a0b0e0")
        ax.add_patch(Polygon(p["poly"], fc=col, ec="none", alpha=0.6))
    COL = {"F": "#d03030", "I2": "#2a9a4a", "I3": "#9a5ad0", "B": "#3060d0"}
    for src, a in ((cu, 0.35), (new, 0.95)):
        for t in src["tracks"]:
            ax.plot([t["x0"], t["x1"]], [t["y0"], t["y1"]], color=COL[t["l"]], lw=t["w"] * 6, alpha=a, solid_capstyle="round")
        for v in src["vias"]:
            ax.add_patch(Circle((v["x"], v["y"]), v["d"] / 2, fc="#333", ec="none", alpha=a))
    ax.set_xlim(58, 142); ax.set_ylim(142, 58); ax.set_aspect("equal")
    ax.set_title(f"Stage {stage} (bold = this stage; red top, green In2, purple In3, blue bottom; seen from above)", fontsize=10)
    lines = [f"Stage {stage}: {len(new['tracks'])} track segments, {len(new['vias'])} vias", "", "Net                 joined  failed"]
    lines += [f" {n:20s} {d:4d}  {f:4d}" for n, d, f in log]
    lines += ["", "KiCad DRC (errors):"] + [f" {k:28s} {n}" for k, n in sorted(kinds.items())] + [f" unconnected items (all nets) {unconn}"]
    tx.text(0, 1, "\n".join(lines), va="top", fontsize=9, family="monospace")
    out = BB + f"/design/schematics/Main/routing_stage{stage}.png"
    fig.savefig(out, dpi=90); print(out); print(kinds, "unconnected", unconn)


if __name__ == "__main__":
    s = sys.argv[1]
    draw(s) if len(sys.argv) > 2 and sys.argv[2] == "draw" else run(s)
