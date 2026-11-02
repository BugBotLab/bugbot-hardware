# End-to-end test of the private KiCad push-and-shove API on a fresh COPY of BugBot_Main (the original is never opened).
# Routes M2_A / M2_B, then a CC2 stub that must shove M2_B, drags M2_B back through CC2 in one call, routes a net with
# a via, optimizes, and checks that DRC has no new errors. Plots go to kicad-dev/work/shove_test/*.png.
#   C:/Python312/python.exe design/tools/pns_api/test_shove.py
import json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pns_client import PNS, DEV                                            # noqa: E402

SRC = os.path.join(HERE, "..", "..", "schematics", "Main", "BugBot_Main")
WD = os.path.join(DEV, "work", "shove_test")
BOX = (66, 94, 92, 106)


def fresh_copy():
    if PNS.running():
        PNS().close()
        time.sleep(2)
    os.makedirs(WD, exist_ok=True)
    for ext in (".kicad_pcb", ".kicad_pro", ".kicad_prl"):
        shutil.copyfile(SRC + ext, os.path.join(WD, "shove_test" + ext))
    return os.path.join(WD, "shove_test.kicad_pcb")


def segs(p, net):
    return sorted((round(t.start.x / 1e6, 3), round(t.start.y / 1e6, 3), round(t.end.x / 1e6, 3),
                   round(t.end.y / 1e6, 3)) for t in p.tracks(net))


def short(r):
    return {"committed": r["committed"], "completed": r["completed"], "msg": r["message"], "added": len(r["added"]),
            "removed": len(r["removed"]), "modified": len(r["modified"]),
            "nets_touched": sorted({c["net"] for c in r["removed"] + r["modified"]})}


def drc_errors(p):
    d = p.drc_summary(max_items=200)
    bad = [i for i in d["items"] if i["type"] in ("clearance", "tracks_crossing", "shorting_items", "hole_clearance",
                                                   "copper_edge_clearance", "track_width", "via_diameter")]
    return d["errors"], d["unconnected"], bad


def main():
    t0 = time.time()
    p = PNS.open(fresh_copy())
    print("opened in %.1f s" % (time.time() - t0))
    e0, u0, bad0 = drc_errors(p)
    print("DRC before: %d errors, %d unconnected, %d copper-clearance items" % (e0, u0, len(bad0)))

    steps = []
    t = time.time()
    r = p.route_track("/M2_A", [(86.64, 98.88), (69.83, 101.0)], layer="B.Cu")
    steps.append(("route M2_A", short(r), time.time() - t))
    t = time.time()
    r = p.route_track("/M2_B", [(69.83, 102.0), (71.5, 102.0), (72.55, 100.95), (84.6, 100.95), (85.4, 100.175),
                                (86.64, 100.175)], layer="B.Cu")
    steps.append(("route M2_B", short(r), time.time() - t))
    p.plot_area(BOX, os.path.join(WD, "1_before_shove.png"), highlight=["/M2_A", "/M2_B", "/CC2"])
    m2b_before = segs(p, "/M2_B")

    t = time.time()
    r = p.route_track("/CC2", [(77.0, 104.01), (75.8, 104.01), (75.8, 101.1), (80.0, 101.1)], layer="B.Cu")
    steps.append(("route CC2 stub into M2_B's corridor (shove)", short(r), time.time() - t))
    moved = segs(p, "/M2_B") != m2b_before
    p.plot_area(BOX, os.path.join(WD, "2_after_shove.png"), highlight=["/M2_A", "/M2_B", "/CC2"])

    bump = [s for s in p.tracks("/M2_B") if abs(s.start.y - s.end.y) < 10 and 76e6 < (s.start.x + s.end.x) / 2 < 80e6]
    t = time.time()
    y = bump[0].start.y / 1e6 if bump else 100.65
    r = p.drag_item(at=(78.0, y), target=(78.0, 101.5))
    steps.append(("drag M2_B through CC2 in one call", short(r), time.time() - t))
    p.plot_area(BOX, os.path.join(WD, "3_after_drag.png"), highlight=["/M2_A", "/M2_B", "/CC2"])

    t = time.time()
    r = p.route_track("/M1_B", [(86.64, 100.83), (85.2, 100.83), (84.6, 101.43), (84.6, 101.9, "F.Cu"),
                                (80.0, 101.9)], allow_partial=False)
    steps.append(("route M1_B with a via to F.Cu", short(r), time.time() - t))

    t = time.time()
    r = p.optimize_nets(["/M2_A", "/M2_B", "/CC2", "/M1_B"])
    steps.append(("optimize", short(r), time.time() - t))
    p.plot_area(BOX, os.path.join(WD, "4_final.png"), highlight=["/M2_A", "/M2_B", "/CC2", "/M1_B"])

    for name, s, dt in steps:
        print("%-46s %5.2f s  %s" % (name, dt, json.dumps(s)))
    print("M2_B moved by the shove:", moved)
    e1, u1, bad1 = drc_errors(p)
    print("DRC after: %d errors (was %d), %d unconnected (was %d), %d copper-clearance items" % (e1, e0, u1, u0, len(bad1)))
    for b in bad1:
        print("  ", b)
    ok = all(s["committed"] for n, s, _ in steps if "optimize" not in n) and moved and e1 <= e0 and not bad1
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
