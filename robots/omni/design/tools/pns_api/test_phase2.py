# Phase 2 test of the private KiCad API on a fresh COPY of BugBot_Main (the original is never opened). Picks its targets
# from the live board (whatever its routing state): routes short open links, the USB pair from U6 (pair placer +
# offset fallback), then dry runs / checks of the other tools, and compares DRC before and after.
#   MSYS_NO_PATHCONV=1 C:/Python312/python.exe design/tools/pns_api/test_phase2.py
import json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pns_client import PNS, copy_design, DEV                              # noqa: E402
import pns_extras as X                                                     # noqa: E402

SRC = os.path.normpath(os.path.join(HERE, "..", "..", "schematics", "Main", "BugBot_Main.kicad_pcb"))
OUT = os.path.join(DEV, "work", "p2_suite")
COPPER = ("clearance", "tracks_crossing", "shorting_items", "hole_clearance", "copper_edge_clearance")


def copper_errors(d):
    return [i for i in d["items"] if i["type"] in COPPER]


def main():
    os.makedirs(OUT, exist_ok=True)
    if PNS.running():
        PNS().close(); time.sleep(2)
    p = PNS.open(copy_design(SRC, "p2_suite"))
    res = []

    def step(name, fn, ok=lambda r: True):
        t = time.time()
        try:
            r = fn(); good = bool(ok(r))
        except Exception as e:                                         # noqa: BLE001
            r, good = "%s: %s" % (type(e).__name__, e), False
        res.append((name, good, time.time() - t, r))
        return r

    d0 = p.drc_summary(max_items=2000)
    u = step("get_unrouted", p.get_unrouted, lambda r: "links" in r)

    # short pad <-> track links on one layer: route them with shove
    routed = []
    for l in sorted(u["links"], key=lambda l: l["length"]):
        a, b = l["a"], l["b"]
        common = set(a["layers"]) & set(b["layers"])
        if l["length"] > 3 or not common or {a["type"], b["type"]} != {"pad", "track"}:
            continue
        pad, trk = (a, b) if a["type"] == "pad" else (b, a)
        r = p.route_track(l["net"], [pad["pos"], trk["pos"]], layer=sorted(common)[0])
        routed.append((l["net"], pad["desc"], r["committed"], r["message"]))
    res.append(("route_track short open links", any(c for _, _, c, _ in routed), 0.0,
                [x for x in routed]))

    step("clearance_at (track end on a U7 pad)",
         lambda: p.clearance_at(*[l for l in u["links"] if "U7" in l["a"]["desc"] + l["b"]["desc"]][0]["b"]["pos"],
                                layer="F.Cu", radius=0.8),
         lambda r: "obstacles" in r)

    usb = [t for n in ("/USB_DP", "/USB_DN") for t in p.tracks(n)]
    pts = [(117.5, 74.5), (121.0, 74.0), (126.0, 74.0), (129.0, 77.0), (129.0, 84.0), (126.0, 87.0)]
    r = step("route_diff_pair USB from U6 (pair placer / offset fallback)",
             lambda: p.route_diff_pair("/USB_DP", pts, layer="B.Cu"))
    after = [t for n in ("/USB_DP", "/USB_DN") for t in p.tracks(n)]
    res.append(("diff pair leaves nothing half-done", isinstance(r, dict) and (r["committed"] or len(after) == len(usb)),
                0.0, {"before": len(usb), "after": len(after)}))

    sig = [t for t in p.board.get_tracks() if t.net.name and not any(k in t.net.name for k in ("GND", "VSYS", "3V3", "VBAT"))
           and hasattr(t, "start") and type(t).__name__ == "Track"]
    longest = max(sig, key=lambda t: math.dist((t.start.x, t.start.y), (t.end.x, t.end.y)))
    L = math.dist((longest.start.x, longest.start.y), (longest.end.x, longest.end.y)) / 1e6
    s = (longest.start.x / 1e6, longest.start.y / 1e6); e = (longest.end.x / 1e6, longest.end.y / 1e6)
    a = (s[0] + (e[0] - s[0]) * 0.2, s[1] + (e[1] - s[1]) * 0.2); b = (s[0] + (e[0] - s[0]) * 0.8, s[1] + (e[1] - s[1]) * 0.8)
    step("tune_length dry run on longest signal segment (%s, %.1f mm)" % (longest.net.name, L),
         lambda: p.tune_length(item=longest.id.value, start=a, end=b, target=0, dry_run=True),
         lambda r: r["status"] in ("tuned", "too_short", "too_long") and not r["committed"])
    step("optimize_tracks dry run (U7 area)", lambda: p.optimize_tracks(area=(95, 128, 110, 140), dry_run=True),
         lambda r: "lines optimized" in r["message"])
    step("fanout_footprint U9 dry run", lambda: X.fanout_footprint(p, "U9", dry_run=True), lambda r: "pads" in r)
    step("refill zones", lambda: p.board.refill_zones(block=True, max_poll_seconds=120) or True)
    step("add_stitching_vias GND dry run", lambda: X.add_stitching_vias(p, "/GND", pitch=2.0, layers=["F.Cu", "In1.Cu", "B.Cu"],
                                                                         dry_run=True), lambda r: "placed" in r)
    step("set_teardrops on vias", lambda: p.set_teardrops(True, vias=True, pth_pads=False, smd_pads=False),
         lambda r: r["teardrop_zones"] >= 0)
    isl = step("zone_islands", lambda: p.zone_islands(refill=True), lambda r: len(r) > 0)
    step("move_footprint R43 push dry run", lambda: X.move_footprint(p, "R43", (99.05, 86.3), dry_run=True),
         lambda r: "moved" in r)
    step("congestion_map", lambda: X.congestion_map(p, out_png=os.path.join(OUT, "congestion.png")), lambda r: "max" in r)
    step("height_check (MCAD regions)", lambda: X.height_check(p), lambda r: r["regions"] > 0)
    step("update_from_schematic dry run", lambda: p.update_from_schematic(dry_run=True),
         lambda r: not r["applied"] and any("errors: 0" in c for c in r["changes"]))
    d1 = p.drc_summary(max_items=2000)
    p.plot_area((114, 68, 138, 90), os.path.join(OUT, "usb_pair.png"), layers=("F.Cu", "B.Cu"),
                highlight=["/USB_DP", "/USB_DN"])

    for name, good, dt, r in res:
        short = r if isinstance(r, str) else json.dumps(r, default=str)[:200]
        print("%-4s %-62s %6.2f s  %s" % ("ok" if good else "FAIL", name, dt, short))
    if isinstance(isl, list):
        print("islands: %d, isolated: %s" % (len(isl), [(i["net"], i["layer"], i["area"]) for i in isl if i["isolated"]][:8]))
    e0, e1 = copper_errors(d0), copper_errors(d1)
    print("DRC before: %d errors, %d unconnected, %d copper; after: %d errors, %d unconnected, %d copper"
          % (d0["errors"], d0["unconnected"], len(e0), d1["errors"], d1["unconnected"], len(e1)))
    new = [x for x in e1 if x not in e0]
    for b in new[:10]:
        print("   NEW:", b["type"], b["desc"], b["items"][:2])
    ok = all(g for _, g, _, _ in res) and not new
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
