# Routing plan v2 (approved 2026-10-25): shared geometry for the 6-layer board (design/schematics/Main/routing_plan_v2.png).
# In4 (L5) carries VSYS islands round the VSYS pads, kept off the USB pair's path; GND fills the rest. Robot frame mm
# (KiCad x = 100 + X, y = 100 - Y).
import json, math
from shapely.geometry import Point, LineString, MultiPoint
from shapely.ops import unary_union

import os as _os                                  # repo-relative paths: see .bugbot-root
_d = _os.path.dirname(_os.path.abspath(__file__))
while _d != _os.path.dirname(_d) and not _os.path.exists(_os.path.join(_d, ".bugbot-root")): _d = _os.path.dirname(_d)
BB = _os.environ.get("BUGBOT_OMNI", _d)           # the omni robot's root
NETS = BB + "/design/schematics/Main/_route/nets.json"
LANE_SEGS = BB + "/design/schematics/Main/_work/usb_lane_segs.json"
LANE = BB + "/design/schematics/Main/_work/usb_lane.json"
GEOM = BB + "/design/schematics/Main/_place/board_geom.json"
BOARD = Point(0, 0).buffer(40.6, 128).difference(Point(41.5, 0).buffer(18.6, 128))


def _pads():
    """pads by net from the board as it is now (_place/board_geom.json, export_geom.py); nets.json if that is missing"""
    try:
        out = {}
        for f in json.load(open(GEOM))["fps"]:
            for p in f["pads"]:
                if p["net"]: out.setdefault(p["net"], []).append({"ref": f["ref"], "pad": p["n"], "xy": p["pos"], "side": "both" if p["tht"] else f["side"]})
        return out
    except FileNotFoundError:
        return {n: p for g in json.load(open(NETS)).values() for n, p in g.items()}


def usb_path():
    """J1's D+ pin -> the ESD chip U2 -> the module's D+ pad (from the board as placed)"""
    dp = _pads()["/USB_DP"]
    j1 = next(p["xy"] for p in dp if p["ref"] == "J1"); u6 = next(p["xy"] for p in dp if p["ref"] == "U6")
    u2 = [p["xy"] for p in dp if p["ref"] == "U2"]
    u2 = (sum(q[0] for q in u2) / len(u2), sum(q[1] for q in u2) / len(u2))
    return LineString([j1, u2, u6])


def vsys_islands(link=7.0):
    """every VSYS pad grown by 3 mm; pads within `link` mm of each other joined into one island (their hull), so
    each power cluster (power path, converters, motor drivers, kicker boost) gets one solid piece; kept off the USB pair"""
    pts = [tuple(p["xy"]) for p in _pads()["/VSYS"]]
    groups = []
    for q in pts:                                     # single-link clusters
        hit = [g for g in groups if any(math.dist(q, o) <= link for o in g)]
        merged = [q] + [o for g in hit for o in g]
        groups = [g for g in groups if g not in hit] + [merged]
    isl = unary_union([MultiPoint(g).convex_hull.buffer(3.0) for g in groups])
    try:                                              # the USB pair's real copper on B.Cu (usb_lane_export.py), robot frame
        lane = unary_union([LineString(sg).buffer(1.0) for sg in json.load(open(LANE_SEGS))])
    except FileNotFoundError:
      try:                                            # its centre line (usb_pair2.py)
        lane = LineString([(x - 100, 100 - y) for x, y in json.load(open(LANE))]).buffer(1.0)
      except FileNotFoundError:
        lane = usb_path().buffer(1.6)
    return isl.difference(lane).intersection(BOARD.buffer(-0.8))


if __name__ == "__main__":                      # writes the islands for KiCad's python (no shapely there)
    isl = vsys_islands(link=float(__import__("os").environ.get("ISL_LINK", "14.0")))
    polys = [list(g.exterior.coords)[:-1] for g in getattr(isl, "geoms", [isl]) if g.area >= 4]
    json.dump(polys, open(BB + "/design/schematics/Main/_route/vsys_islands.json", "w"))
    print(len(polys), "islands,", round(sum(g.area for g in getattr(isl, "geoms", [isl])), 1), "mm2")
