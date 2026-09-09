"""Interactive bench: the real schematic sheets, live from ngspice.

    python bench/server.py            ->  http://localhost:8765

The page shows every sheet of both boards (the kicad-cli SVG export) with
the wires and pins from sch_geometry.py laid over it. Click the switch, the
USB socket, the battery, a motor or the NTC and the server re-solves the
whole stack (stack_build.solve: .op, or a ramped transient when the .op
will not converge) and returns every node voltage and every element
current; the page colours the wires by voltage and animates the current.
Results are cached per state (out/bench/cache.json), so a state you have
seen before comes back instantly.
"""
import hashlib
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from paths import BOARDS, OUT, ROOT_SCH, netlist                     # noqa: E402
from stack_build import (M, V, O, NODES, MOTORS, R_ISENSE, SENSE_R,   # noqa: E402
                         motor_state, solve, stack_deck)
from ngspice_run import run_circuit, final                            # noqa: E402
from parts_spec import MOTOR_TYPES, motor_bemf                        # noqa: E402
import sch_geometry                                                   # noqa: E402

BENCH_OUT = os.path.join(OUT, "bench")
os.makedirs(BENCH_OUT, exist_ok=True)
CACHE_FILE = os.path.join(BENCH_OUT, "cache.json")
LOCK = threading.Lock()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8765"))

DEFAULT_STATE = {"sw": 1, "vbus": 0.0, "vbat": 3.7, "rt1": 10000.0, "servo_a": 0.0,
                 "motor": "0615_coreless",
                 "motors": {"U6": "off", "U7": "off", "U8": "off", "U9": "off"}}

# series in out/mission_*.json -> the SPICE node each one is a voltage of
MISSION_NODES = {"VSYS": NODES["VSYS"], "VSYS_SW": NODES["VSYS_SW"], "VMOT": NODES["VMOT"],
                 "3V3": NODES["3V3_M"], "MOD_3V3": NODES["MOD_3V3"], "MOT_INT": NODES["MOT_INT_V"],
                 "GATE": NODES["GATE"], "VBAT_SENSE": NODES["VBAT_SENSE_M"]}


# --------------------------------------------------------------- geometry
def build_geometry():
    boards = {}
    for bd, pre, B in (("motion", "M", M), ("vision", "V", V), ("odometry", "O", O)):
        _, sheets = sch_geometry.load_project(netlist(bd), BOARDS[bd], ROOT_SCH[bd], pre)
        svgs = sorted(os.listdir(os.path.join(BOARDS[bd], "sheets")))
        base = ROOT_SCH[bd][:-len(".kicad_sch")]
        out = []
        for sh in sheets:
            if sh["name"] == "root":
                svg = base + ".svg"
            else:
                svg = next((s for s in svgs if s.startswith(base + "-") and s[len(base) + 1:].lower().startswith(sh["name"].lower()[:2])), None)
                if svg is None:
                    svg = next((s for s in svgs if sh["name"].split(" ", 1)[-1][:8].lower() in s.lower()), None)
            nets = sorted({w["net"] for w in sh["wires"] if w["net"]} | {p["net"] for p in sh["pins"] if p["net"]})
            out.append({"name": sh["name"], "svg": "/sheets/%s/%s" % (bd, svg) if svg else None,
                        "size": sh["size"], "wires": sh["wires"], "junctions": sh["junctions"],
                        "labels": sh["labels"], "symbols": sh["symbols"], "pins": sh["pins"],
                        "spice": {n: B.node(n).lower() for n in nets}})
        boards[bd] = {"prefix": pre, "sheets": out,
                      "values": {r: c["value"] for r, c in B.comps.items()}}
    return {"boards": boards, "motor_types": {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))}
                                              for k, v in MOTOR_TYPES.items()},
            "default": DEFAULT_STATE, "r_isense": R_ISENSE}


GEOMETRY = None


def geometry():
    global GEOMETRY
    if GEOMETRY is None:
        GEOMETRY = build_geometry()
    return GEOMETRY


# ------------------------------------------------------------------ solve
def state_key(st):
    return hashlib.sha1(json.dumps(st, sort_keys=True).encode()).hexdigest()[:16]


def load_cache():
    try:
        return json.load(open(CACHE_FILE))
    except Exception:
        return {}


CACHE = load_cache()


def element_currents(v, B):
    """{ref: I} for every modelled element of board B, + = into pin 1 (R/C/L),
    drain current for the FETs, output current for the ICs where the model
    has a sensing source."""
    out = {}
    pre = B.prefix.lower()
    for ref in B.comps:
        tag = "%s_%s" % (pre, ref.lower())
        kind = ref.rstrip("0123456789")
        cand = []
        if kind in ("R", "RSH", "RT", "F"):
            cand = ["@r%s[i]" % tag]
        elif kind in ("C", "CB"):
            cand = ["@c%s[i]" % tag]
        elif kind == "L":
            cand = ["l%s#branch" % tag, "@l%s[i]" % tag]
        elif kind == "Q":
            cand = ["@m%s[id]" % tag]
        elif kind == "U":
            cand = ["v.x%s.vosns#branch" % tag, "v.x%s.viset#branch" % tag]
        for c in cand:
            if c in v:
                out[ref] = final(v, c)
                break
    return out


def pin_currents(v, nodes, st, ro):
    """{board: {ref: {pin: I}}}, + = current flowing INTO the pin from the
    wire, for the parts whose element current does not say it: the ICs, the
    connectors (cell, USB, motors, loads) and the J8/J9 socket links."""
    pc = {"M": {}, "V": {}, "O": {}}

    def put(b, ref, pin, i):
        pc[b].setdefault(ref, {})[pin] = i

    def vn(node):
        return nodes.get((node or "").lower(), 0.0)

    from stack_build import I_MODULE, I_CAM, I_TOF, I_LED, CAM_3V3_PIN
    from parts_spec import PARTS
    # drivers + their motors: ISENSE current, direction from the output voltages
    for sref, drv in SENSE_R.items():
        i = ro.get("I_" + drv, 0.0)
        o1, o2 = M.pin(drv, "1"), M.pin(drv, "3")
        hi, lo = ("1", "3") if vn(o1) >= vn(o2) else ("3", "1")
        put("M", drv, hi, -i); put("M", drv, lo, i); put("M", drv, "5", i); put("M", drv, "2", -i)
        jref = dict(MOTORS)[drv]
        p1, p2 = M.pin(jref, "1"), M.pin(jref, "2")
        if vn(p1) >= vn(p2):
            put("M", jref, "1", i); put("M", jref, "2", -i)
        else:
            put("M", jref, "2", i); put("M", jref, "1", -i)
    # cell and USB
    ic, iu = ro.get("I_CELL", 0.0), ro.get("I_USB", 0.0)
    for (r, p), n in M.pinnet.items():
        if r == "J2":
            put("M", "J2", p, ic if n == "GND" else -ic)
        if r == "J1" and n.endswith("VBUS"):
            put("M", "J1", p, -iu / 4)
    # charger: USB in, battery in (discharging) / out (charging), SYS out
    isw = ro.get("I_SW", 0.0)
    put("M", "U1", "2", iu)
    for p in ("14", "16"):
        put("M", "U1", p, ic / 2)
    for p in ("1", "15"):
        put("M", "U1", p, -isw / 2)
    # buck-boost: output current from the model's sense source, input by power balance
    iout = abs(final(v, "v.xm_u3.vosns#branch")) if "v.xm_u3.vosns#branch" in v else 0.0
    vin, vout = vn(M.pin("U3", "10")), vn(M.pin("U3", "4"))
    iin = iout * vout / max(vin, 0.5) / 0.9 if vout > 0.5 else 0.0
    for p in ("4", "5"):
        put("M", "U3", p, -iout / 2)
    for p in ("10", "11"):
        put("M", "U3", p, iin / 2)
    # socket links: R_J8_k from the Motion pin to the Vision pin
    for j in ("J8", "J9"):
        for k in range(1, 11):
            vec = "@r_%s_%d[i]" % (j.lower(), k)
            if vec in v:
                i = final(v, vec)
                put("M", j, str(k), i); put("V", j, str(k), -i)
    # the J7 cable: R_J7_k from the Motion pin to the Odometry J1 pin
    for k in range(1, 11):
        vec = "@r_j7_%d[i]" % k
        if vec in v:
            i = final(v, vec)
            put("M", "J7", str(k), i); put("O", "J1", str(11 - k), -i)   # mirrored connector (2026-09-07)
    # the Odometry board's own parts: the LDO from its sense source, the two
    # sensors from their modelled currents once their rails are up
    ildo = abs(final(v, "v.xo_u1.vsns#branch")) if "v.xo_u1.vsns#branch" in v else 0.0
    put("O", "U1", "1", ildo + 60e-6); put("O", "U1", "5", -ildo)
    up19 = 1.0 if vn(O.pin("U2", "4")) > 1.7 else 0.0
    up33 = 1.0 if vn(O.pin("U3", "3")) > 2.3 else 0.0
    pm, bn = PARTS["PMW3360"]["model"], PARTS["BNO055"]["model"]
    put("O", "U2", "4", pm["i_run"] * up19); put("O", "U2", "15", pm["i_led"] * up19)
    put("O", "U2", "5", pm["i_vddio"] * up19); put("O", "U2", "8", -(pm["i_run"] + pm["i_led"] + pm["i_vddio"]) * up19)
    put("O", "U3", "3", bn["i_ndof"] * up33); put("O", "U3", "28", bn["i_vddio"] * up33)
    put("O", "U3", "2", -bn["i_ndof"] * up33)
    # the loads the harness hangs on the Vision board
    put("V", "U3", "85", I_MODULE); put("V", "J3", str(CAM_3V3_PIN), I_CAM); put("V", "J7", "1", I_TOF)
    put("V", "J10", "1", I_LED)
    if st.get("servo_a"):
        put("M", "J10", "2", float(st["servo_a"])); put("M", "J11", "2", float(st["servo_a"]))
    return pc


def run_state(st):
    st = dict(DEFAULT_STATE, **st)
    st["motors"] = dict(DEFAULT_STATE["motors"], **st.get("motors", {}))
    key = state_key(st)
    if key in CACHE and "pincur" in CACHE[key]:
        return CACHE[key]
    os.environ["MOTOR"] = st["motor"]
    import stack_build
    stack_build.MOTOR_TYPE = st["motor"]
    kw = dict(vbat=float(st["vbat"]), vbus=float(st["vbus"]), sw=int(st["sw"]),
              motors=motor_state(**{k: (v if v != "stall" else "stall") for k, v in st["motors"].items()}),
              servo_a=float(st["servo_a"]), rt1=float(st["rt1"]), extra=[".options savecurrents"])
    with LOCK:
        v = solve("bench", **kw)
    nodes = {k: final(v, k) for k in v if not k.startswith(("@", "_")) and "#branch" not in k and k != "time"}
    currents = {"M": element_currents(v, M), "V": element_currents(v, V), "O": element_currents(v, O)}
    # readouts
    ro = {"I_CELL": -final(v, "vbat#branch"), "I_USB": -final(v, "vbus#branch") if st["vbus"] else 0.0}
    for name, node in NODES.items():
        ro[name] = nodes.get(node.lower(), 0.0)
    ro["I_SW"] = final(v, "@s_sw1[i]") if "@s_sw1[i]" in v else 0.0
    mt = MOTOR_TYPES[st["motor"]]
    for sref, drv in SENSE_R.items():
        i = nodes.get(M.pin(sref, "1").lower(), 0.0) / R_ISENSE
        ro["I_" + drv] = i
        s = st["motors"][drv]
        vm = ro.get("VMOT", 0.0)
        # DC motors here: speed from the back-EMF the model was given (parts_spec)
        if s in ("fwd", "rev") and vm > 2.75:
            ro["RPM_" + drv] = (1 if s == "fwd" else -1) * 0.8 * mt["rpm_noload_3v"] * min(vm, 3.0) / 3.0
        else:
            ro["RPM_" + drv] = 0.0
    pc = pin_currents(v, nodes, st, ro)
    res = {"key": key, "state": st, "nodes": nodes, "currents": currents, "pincur": pc, "readouts": ro,
           "via_tran": bool(v.get("_via_tran")), "warning": run_circuit.last_warning}
    CACHE[key] = res
    try:
        json.dump(CACHE, open(CACHE_FILE, "w"))
    except Exception:
        pass
    return res


def missions():
    out = {}
    for f in sorted(os.listdir(OUT)):
        if f.startswith("mission_") and f.endswith(".json"):
            m = json.load(open(os.path.join(OUT, f)))
            m["node_of"] = {k: n.lower() for k, n in MISSION_NODES.items()}
            out[m["name"]] = m
    return out


# ------------------------------------------------------------------- http
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(HERE, "static"), **k)

    def log_message(self, fmt, *args):
        if "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)

    def handle(self):
        try:
            super().handle()
        except ConnectionAbortedError:
            pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self.path = "/index.html"
        if self.path.startswith("/sheets/"):
            bd, _, name = self.path[len("/sheets/"):].partition("/")
            from urllib.parse import unquote
            p = os.path.join(BOARDS.get(bd, ""), "sheets", unquote(name))
            if os.path.isfile(p):
                data = open(p, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
            return
        if self.path == "/api/geometry":
            return self._json(geometry())
        if self.path == "/api/missions":
            return self._json(missions())
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/solve":
            try:
                return self._json(run_state(body))
            except Exception as e:
                import traceback
                traceback.print_exc()
                return self._json({"error": str(e)}, 500)
        self.send_error(404)


if __name__ == "__main__":
    print("building geometry ...")
    g = geometry()
    for bd, b in g["boards"].items():
        for sh in b["sheets"]:
            print("  %s %-32s %3d wires  %3d pins  svg=%s" % (bd, sh["name"], len(sh["wires"]), len(sh["pins"]), sh["svg"]))
    print("warming the default state ...")
    run_state({})
    print("bench at http://localhost:%d" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
