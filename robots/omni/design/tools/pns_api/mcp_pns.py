#!/usr/bin/env python3
# KiCad push-and-shove router MCP server (private KiCad build, see README.md). Standard library + kipy; speaks MCP over
# stdio (newline-delimited JSON-RPC 2.0) like fusionflow/mcp_freecad.py. The board stays loaded in the private pcbnew
# between calls; one kipy connection is kept and re-made if pcbnew restarts.
# Register (project scope): .mcp.json -> {"mcpServers": {"kicad-pns": {"command": "python",
#                                          "args": ["design/tools/pns_api/mcp_pns.py"]}}}
import base64, json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pns_client as pc                                                    # noqa: E402
import pns_extras as X                                                     # noqa: E402

PROTOCOL = "2024-11-05"
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
# Original design files the router must never open directly (work on copies)
PROTECTED = [os.path.normcase(os.path.join(REPO, "kicad", "BugBot_Main", "BugBot_Main.kicad_pcb"))]
WORK = os.path.join(pc.DEV, "work")
_P = None

PT = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
BOX = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4,
       "description": "[x0, y0, x1, y1] in mm"}
MODE = {"type": "string", "enum": ["shove", "walkaround", "highlight"], "default": "shove"}
TOOLS = [
    ("pns_open", "Start the private KiCad pcbnew (push-and-shove API build) on a board, or attach if it is running. "
     "Use copy_from to copy a design (board + project files) into a work folder and open the copy; originals are "
     "refused. The board stays loaded for all other tools until pns_close.",
     {"type": "object", "properties": {
         "board": {"type": "string", "description": "board to open (a copy, not an original)"},
         "copy_from": {"type": "string", "description": "copy this .kicad_pcb (+ .kicad_pro/.kicad_prl/.kicad_dru) "
                       "into the work folder and open the copy"},
         "name": {"type": "string", "description": "work copy file name stem (with copy_from)"}}}),
    ("pns_close", "Quit the private pcbnew without saving.", {"type": "object", "properties": {}}),
    ("route_track", "Route one track with KiCad's interactive router (as if clicking each point), shoving other "
     "tracks/vias aside in shove mode, and commit it. points[0] must be on a pad, track or via of the net. A point "
     "given as [x, y, layer] continues on that layer from there (via placed). Fails (nothing committed) if the last "
     "point is not reached, unless allow_partial. Returns added/removed/modified (shoved) item ids.",
     {"type": "object", "required": ["points"], "properties": {
         "net": {"type": "string"},
         "points": {"type": "array", "items": {"type": "array"}, "minItems": 2,
                    "description": "[[x, y] | [x, y, \"B.Cu\"], ...] mm"},
         "layer": {"type": "string", "description": "start layer, e.g. F.Cu (default: layer of the start item)"},
         "width": {"type": "number", "description": "mm; 0 = net class"},
         "via": {"type": "array", "items": {"type": "number"}, "description": "[diameter, drill] mm; default rules"},
         "mode": MODE, "allow_partial": {"type": "boolean"}, "dry_run": {"type": "boolean"},
         "step": {"type": "number", "default": 0.1, "description": "mm between simulated cursor positions"}, }}),
    ("drag_item", "Drag a track segment or via with the router (like the D hotkey), shoving neighbours. Identify it "
     "by id or by a point 'at' on it.",
     {"type": "object", "required": ["target"], "properties": {
         "item": {"type": "string", "description": "KIID"}, "at": PT, "layer": {"type": "string"},
         "target": PT, "grab": PT, "mode": MODE, "free_angle": {"type": "boolean"},
         "force": {"type": "boolean"}, "dry_run": {"type": "boolean"}, "step": {"type": "number", "default": 0.1, "description": "mm between simulated cursor positions"}, }}),
    ("optimize_net", "Run the router's optimizer (merge corners, clean pad exits) on all tracks of the nets "
     "(optionally only lines touching 'area'; with an area and no nets, every net in the area).",
     {"type": "object", "properties": {
         "nets": {"type": "array", "items": {"type": "string"}}, "area": BOX, "keep_topology": {"type": "boolean"},
         "dry_run": {"type": "boolean"}}}),
    ("optimize_tracks", "Clean-up pass for grid-router output in a net set or area: merge collinear segments, smooth "
     "to 45 deg, remove staircases (router optimizer with MERGE_COLINEAR).",
     {"type": "object", "properties": {
         "nets": {"type": "array", "items": {"type": "string"}}, "area": BOX, "keep_topology": {"type": "boolean"},
         "dry_run": {"type": "boolean"}}}),
    ("route_diff_pair", "Route a net and its coupled net (X_P/X_N, XP/XN, X+/X-) as a differential pair along a "
     "centreline (points[0] on a pad of either net). Tries KiCad's pair placer; if it cannot finish (it cannot turn "
     "right after a fixed point), removes its partial legs and routes both nets along exact offset polylines with "
     "the single-track router. 'method' in the reply says which. No dry_run (the pair placer commits each leg).",
     {"type": "object", "required": ["net", "points"], "properties": {
         "net": {"type": "string"}, "points": {"type": "array", "items": {"type": "array"}, "minItems": 2},
         "layer": {"type": "string"}, "width": {"type": "number"}, "gap": {"type": "number"},
         "mode": MODE, "fallback": {"type": "boolean", "default": True}}}),
    ("tune_length", "Length tuning like the meander tool: on a track (id, or nearest to 'at'), between start and end "
     "points on it (default the segment's ends), add meanders to reach 'target' mm (mode single / diff_pair / skew; "
     "0 = rules). dry_run reports the result and undoes it.",
     {"type": "object", "properties": {
         "item": {"type": "string"}, "at": PT, "start": PT, "end": PT, "target": {"type": "number"},
         "mode": {"type": "string", "enum": ["single", "diff_pair", "skew"], "default": "single"},
         "tolerance": {"type": "number", "default": 0.1}, "max_amplitude": {"type": "number"},
         "spacing": {"type": "number"}, "dry_run": {"type": "boolean"}}}),
    ("get_unrouted", "Every open ratsnest link (optionally of some nets): both endpoints with position, copper "
     "layers, item type and name (e.g. U6.48), and the link length. Replaces parsing DRC reports.",
     {"type": "object", "properties": {"nets": {"type": "array", "items": {"type": "string"}}}}),
    ("clearance_at", "Would a track / via here pass the router's clearance rules, and how far is the nearest "
     "obstacle? kind 'point' (a track end of 'width'), 'segment' (start-end) or 'via'. Uses KiCad's own collision "
     "model (tracks, vias, pads, holes, keepouts, edge; zone fills are not obstacles). Reply: ok, min_margin "
     "(mm, negative = violation) and the nearest obstacles with distance / required clearance.",
     {"type": "object", "required": ["at"], "properties": {
         "kind": {"type": "string", "enum": ["point", "segment", "via"], "default": "point"},
         "at": PT, "end": PT, "layer": {"type": "string", "default": "F.Cu"}, "net": {"type": "string"},
         "width": {"type": "number"}, "via": {"type": "array", "items": {"type": "number"}},
         "radius": {"type": "number", "default": 1.0}, "max_results": {"type": "integer", "default": 10}}}),
    ("zone_islands", "Per zone fill polygon (pour island): net, layer, area, isolated / single-connection, the items "
     "touching it and the pads reachable through it. refill=true refills zones first.",
     {"type": "object", "properties": {"nets": {"type": "array", "items": {"type": "string"}},
                                       "refill": {"type": "boolean"}}}),
    ("refill_zones", "Refill all zones of the open board.", {"type": "object", "properties": {}}),
    ("fanout_footprint", "Stub + via for each SMD pad of a footprint (default: pads with a net and no track yet; "
     "'pads' limits it). Escape points straight out of the package side, then +-45 deg, at growing distances, "
     "each checked with clearance probe; stubs routed with shove.",
     {"type": "object", "required": ["ref"], "properties": {
         "ref": {"type": "string"}, "via": {"type": "array", "items": {"type": "number"}},
         "pads": {"type": "array", "items": {"type": "string"}},
         "skip_nets": {"type": "array", "items": {"type": "string"}}, "dry_run": {"type": "boolean"}}}),
    ("add_stitching_vias", "Grid of through vias of a net inside its zone fills (on every layer in 'layers', default "
     "all layers the net is poured on), each clearance-probed and kept off other nets' pours. Refill afterwards.",
     {"type": "object", "properties": {
         "net": {"type": "string", "default": "/GND"}, "area": BOX, "pitch": {"type": "number", "default": 1.5},
         "via": {"type": "array", "items": {"type": "number"}},
         "layers": {"type": "array", "items": {"type": "string"}}, "max_vias": {"type": "integer", "default": 400},
         "dry_run": {"type": "boolean"}}}),
    ("set_teardrops", "Add (enable) or remove teardrops on vias / PTH pads / SMD pads (optionally only some nets), "
     "and track-to-track teardrops; KiCad's own teardrop generator.",
     {"type": "object", "properties": {
         "enable": {"type": "boolean", "default": True}, "vias": {"type": "boolean", "default": True},
         "pth_pads": {"type": "boolean", "default": True}, "smd_pads": {"type": "boolean", "default": True},
         "track_to_track": {"type": "boolean"}, "nets": {"type": "array", "items": {"type": "string"}}}}),
    ("move_footprint", "Move / rotate a footprint; with push, neighbours on the same side are shuffled out along the "
     "shortest axis to keep courtyard clearance (cascading; locked parts are not moved, reported as blocked). "
     "Tracks are not dragged.",
     {"type": "object", "required": ["ref"], "properties": {
         "ref": {"type": "string"}, "at": PT, "rotation": {"type": "number"},
         "push": {"type": "boolean", "default": True}, "clearance": {"type": "number", "default": 0.2},
         "dry_run": {"type": "boolean"}}}),
    ("congestion_map", "Routing-demand heatmap (open ratsnest links + pads per cell) as a PNG, plus the hottest "
     "cells; use before routing to space parts.",
     {"type": "object", "properties": {"area": BOX, "cell": {"type": "number", "default": 1.0}}}),
    ("height_check", "3D height of every component (real models via kicad-cli STEP export) vs. the MCAD max-height "
     "regions on the User.1 layer ('top|bottom: max X mm | part'). Returns violations and all heights. ~15 s.",
     {"type": "object", "properties": {}}),
    ("collision_3d", "Board components vs. an external STEP in the robot frame (e.g. the FreeCAD robot assembly): "
     "overlapping volumes and gaps under 'gap'. Board placed with user_origin (default 100,100) and lifted to "
     "board_z (default mcad.json's). Slow for big assemblies.",
     {"type": "object", "required": ["external_step"], "properties": {
         "external_step": {"type": "string"}, "gap": {"type": "number", "default": 0.5},
         "user_origin": PT, "board_z": {"type": "number"},
         "skip": {"type": "array", "items": {"type": "string"},
                  "description": "part names to ignore, wildcards ok, e.g. [\"MainPCB*\", \"PCBParts*\"] for an older copy of the board inside the assembly"}}}),
    ("update_from_schematic", "Tools > Update PCB from Schematic via a kicad-cli netlist (works on work copies: the "
     "original schematic is used). dry_run (default) only reports the changes.",
     {"type": "object", "properties": {
         "dry_run": {"type": "boolean", "default": True}, "relink_by_reference": {"type": "boolean"},
         "delete_unused": {"type": "boolean"}, "replace_footprints": {"type": "boolean", "default": True},
         "update_fields": {"type": "boolean", "default": True}, "schematic": {"type": "string"}}}),
    ("ripup_net", "Delete a net's tracks (and vias), optionally only on one layer or inside a box.",
     {"type": "object", "required": ["net"], "properties": {
         "net": {"type": "string"}, "layer": {"type": "string"}, "box": BOX, "vias": {"type": "boolean"}}}),
    ("items_at", "List tracks and vias near a point (ids for drag_item).",
     {"type": "object", "required": ["at"], "properties": {
         "at": PT, "radius": {"type": "number", "default": 0.5}, "layer": {"type": "string"},
         "net": {"type": "string"}}}),
    ("drc_summary", "DRC of the open board (saved to a temp copy, kicad-cli, zones refilled): error counts by type "
     "plus violations filtered by net / box.",
     {"type": "object", "properties": {
         "net": {"type": "string"}, "box": BOX, "max_items": {"type": "integer", "default": 30},
         "refill": {"type": "boolean", "default": True}}}),
    ("plot_area", "PNG of a board region's copper (live): tracks, vias, pads, optional zone fills, nets highlighted. "
     "Choose layers with 'layers' (RenderArea).",
     {"type": "object", "required": ["box"], "properties": {
         "box": BOX, "layers": {"type": "array", "items": {"type": "string"}},
         "zones": {"type": "boolean"}, "highlight": {"type": "array", "items": {"type": "string"}},
         "px_per_mm": {"type": "number", "default": 40}, "save_to": {"type": "string"}}}),
    ("pns_undo", "Undo the last change in the private pcbnew.", {"type": "object", "properties": {}}),
    ("pns_save", "Save the open board (or a copy with 'path').",
     {"type": "object", "properties": {"path": {"type": "string"}}}),
]


def P():
    global _P
    if _P is None:
        _P = pc.PNS.open()
    return _P


def _text(obj):
    return [{"type": "text", "text": obj if isinstance(obj, str) else json.dumps(obj, indent=1)}]


def _copy_design(src, name=None):
    return pc.copy_design(src, name, WORK)


def call_tool(name, a):
    global _P
    t0 = time.time()
    if name == "pns_open":
        board = a.get("board")
        if a.get("copy_from"):
            board = _copy_design(a["copy_from"], a.get("name"))
        if board and os.path.normcase(os.path.abspath(board)) in PROTECTED:
            return _text("Refusing to open an original design file; use copy_from."), True
        _P = pc.PNS.open(board)
        return _text({"board": _P.board_path(), "s": round(time.time() - t0, 1)})
    if name == "pns_close":
        if pc.PNS.running():
            P().close()
        _P = None
        return _text("closed")
    for attempt in (1, 2):
        try:
            return _dispatch(name, a)
        except (ConnectionError, OSError) as e:
            _P = None
            if attempt == 2 or not pc.PNS.running():
                raise
        except Exception as e:                       # pynng timeouts/closed sockets: reconnect once
            if type(e).__module__.startswith("pynng") and attempt == 1:
                _P = None
                continue
            raise


def _dispatch(name, a):
    p = P()
    if name == "route_track":
        r = p.route_track(a.get("net"), a["points"], a.get("layer"), a.get("width", 0), a.get("via") or (0, 0),
                          a.get("mode", "shove"), a.get("allow_partial", False), a.get("dry_run", False),
                          a.get("step", 0.1))
        return _text(r), not (r["committed"] or a.get("dry_run"))
    if name == "drag_item":
        r = p.drag_item(a.get("item"), a["target"], a.get("at"), a.get("grab"), a.get("layer"),
                        a.get("mode", "shove"), a.get("free_angle", False), a.get("force", False),
                        a.get("dry_run", False), a.get("step", 0.1))
        return _text(r), not (r["committed"] or a.get("dry_run"))
    if name == "optimize_net":
        return _text(p.optimize_nets(a.get("nets") or [], a.get("keep_topology", False),
                                     dry_run=a.get("dry_run", False), area=a.get("area")))
    if name == "optimize_tracks":
        return _text(p.optimize_tracks(a.get("nets") or [], a.get("area"), a.get("keep_topology", False),
                                       a.get("dry_run", False)))
    if name == "route_diff_pair":
        r = p.route_diff_pair(a["net"], a["points"], a.get("layer"), a.get("width", 0), a.get("gap", 0),
                              mode=a.get("mode", "shove"), fallback=a.get("fallback", True))
        return _text(r), not r["committed"]
    if name == "tune_length":
        return _text(p.tune_length(a.get("item"), a.get("at"), a.get("start"), a.get("end"), a.get("target", 0),
                                   a.get("mode", "single"), a.get("tolerance", 0.1), a.get("max_amplitude", 0),
                                   a.get("spacing", 0), a.get("dry_run", False)))
    if name == "get_unrouted":
        return _text(p.get_unrouted(a.get("nets")))
    if name == "clearance_at":
        at = a["at"]
        return _text(p.probe(a.get("kind", "point"), at, a.get("end"), a.get("layer", "F.Cu"), a.get("net", ""),
                             a.get("width", 0), a.get("via") or (0, 0), a.get("radius", 1.0), a.get("max_results", 10)))
    if name == "zone_islands":
        return _text(p.zone_islands(a.get("nets"), a.get("refill", False)))
    if name == "refill_zones":
        t0 = time.time(); p.board.refill_zones(block=True, max_poll_seconds=300)
        return _text({"refilled_in_s": round(time.time() - t0, 1)})
    if name == "fanout_footprint":
        return _text(X.fanout_footprint(p, a["ref"], a.get("via") or (0, 0), a.get("pads"),
                                        tuple(a.get("skip_nets") or ("",)), dry_run=a.get("dry_run", False)))
    if name == "add_stitching_vias":
        return _text(X.add_stitching_vias(p, a.get("net", "/GND"), a.get("area"), a.get("pitch", 1.5),
                                          a.get("via") or (0, 0), a.get("layers"), max_vias=a.get("max_vias", 400),
                                          dry_run=a.get("dry_run", False)))
    if name == "set_teardrops":
        return _text(p.set_teardrops(a.get("enable", True), a.get("vias", True), a.get("pth_pads", True),
                                     a.get("smd_pads", True), a.get("track_to_track", False), a.get("nets")))
    if name == "move_footprint":
        return _text(X.move_footprint(p, a["ref"], a.get("at"), a.get("rotation"), a.get("push", True),
                                      a.get("clearance", 0.2), dry_run=a.get("dry_run", False)))
    if name == "congestion_map":
        out = os.path.join(tempfile.gettempdir(), "pns_congestion_%d.png" % int(time.time() * 1000))
        r = X.congestion_map(p, a.get("area"), a.get("cell", 1.0), out)
        data = base64.b64encode(open(out, "rb").read()).decode()
        return [{"type": "image", "data": data, "mimeType": "image/png"}] + _text(r)
    if name == "height_check":
        r = X.height_check(p)
        r["components"] = sorted(r["components"], key=lambda c: -c["height"])
        return _text(r)
    if name == "collision_3d":
        return _text(X.collision_3d(p, a["external_step"], tuple(a.get("user_origin") or (100.0, 100.0)),
                                    a.get("board_z"), a.get("gap", 0.5), a.get("skip") or ()))
    if name == "update_from_schematic":
        return _text(p.update_from_schematic(a.get("schematic"), a.get("dry_run", True),
                                             a.get("relink_by_reference", False), a.get("delete_unused", False),
                                             a.get("replace_footprints", True), a.get("update_fields", True)))
    if name == "ripup_net":
        return _text(p.ripup_net(a["net"], a.get("layer"), a.get("box"), a.get("vias", True)))
    if name == "items_at":
        return _text(p.items_at(a["at"][0], a["at"][1], a.get("layer"), a.get("radius", 0.5), a.get("net")))
    if name == "drc_summary":
        return _text(p.drc_summary(a.get("refill", True), a.get("net"), a.get("box"), a.get("max_items", 30)))
    if name == "plot_area":
        out = a.get("save_to") or os.path.join(tempfile.gettempdir(), "pns_plot_%d.png" % int(time.time() * 1000))
        p.plot_area(a["box"], out, tuple(a.get("layers") or ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")),
                    a.get("zones", False), a.get("highlight"), a.get("px_per_mm", 40))
        data = base64.b64encode(open(out, "rb").read()).decode()
        return [{"type": "image", "data": data, "mimeType": "image/png"}] + _text(out)
    if name == "pns_undo":
        return _text({"status": p.undo()})
    if name == "pns_save":
        return _text({"saved": p.save(a.get("path"))})
    raise KeyError(name)


def handle(msg):
    m, mid = msg.get("method"), msg.get("id")
    if m == "initialize":
        return {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "kicad-pns", "version": "1.0"},
                "instructions": "KiCad push-and-shove router on a private KiCad build. pns_open a COPY of a board "
                                "first (copy_from); then route_track / drag_item / optimize_net, check with "
                                "plot_area and drc_summary, pns_undo to back out, pns_save to keep. Units are mm."}
    if m == "ping":
        return {}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s} for n, d, s in TOOLS]}
    if m == "tools/call":
        p = msg.get("params", {})
        try:
            out = call_tool(p.get("name"), dict(p.get("arguments") or {}))
            content, err = out if isinstance(out, tuple) else (out, False)
            return {"content": content, "isError": bool(err)}
        except Exception as e:
            return {"content": _text(f"{type(e).__name__}: {e}"), "isError": True}
    if mid is not None:
        raise KeyError(m)
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:          # notification (e.g. notifications/initialized)
            continue
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
        except KeyError as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": f"method not found: {e}"}}
        except Exception as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(reply) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
