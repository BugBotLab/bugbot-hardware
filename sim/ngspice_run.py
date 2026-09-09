"""Minimal ctypes driver for KiCad's bundled ngspice.dll.

run_circuit(deck) -> dict of vector name -> list of floats (final values for
.op, full waveforms for .tran/.dc). Loads a fresh engine per call for
isolation.
"""
import ctypes
import ctypes.util
import os

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ngspice_dll

DLL = ngspice_dll()


class _VecValues(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("creal", ctypes.c_double),
                ("cimag", ctypes.c_double), ("is_scale", ctypes.c_bool),
                ("is_complex", ctypes.c_bool)]


class _VecInfo(ctypes.Structure):
    _fields_ = [("v_name", ctypes.c_char_p), ("v_type", ctypes.c_int),
                ("v_flags", ctypes.c_short),
                ("v_realdata", ctypes.POINTER(ctypes.c_double)),
                ("v_compdata", ctypes.c_void_p), ("v_length", ctypes.c_int)]


def run_circuit(deck_lines, want_vectors=None):
    """deck_lines: list of card strings (no trailing newlines).
    Returns {vector_name: [floats...]} for all result vectors."""
    spice = ctypes.CDLL(DLL)
    log = []

    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    def send_char(msg, _id, _user):
        log.append(msg.decode(errors="replace"))
        return 0

    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    def send_stat(msg, _id, _user):
        return 0

    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
                      ctypes.c_int, ctypes.c_void_p)
    def controlled_exit(status, unload, quit_, _id, _user):
        return 0

    spice.ngSpice_Init(send_char, send_stat, controlled_exit, None, None, None, None)

    arr = (ctypes.c_char_p * (len(deck_lines) + 1))()
    for i, line in enumerate(deck_lines):
        arr[i] = line.encode()
    arr[len(deck_lines)] = None
    rc = spice.ngSpice_Circ(arr)
    if rc != 0:
        raise RuntimeError("ngSpice_Circ failed:\n" + "\n".join(log[-25:]))
    rc_run = spice.ngSpice_Command(b"run")
    # The return of "run" used to be discarded, so a non-converged analysis
    # came back looking like clean data. Surface it: ngspice reports trouble
    # through the log rather than the return code, so scan both.
    bad = [l for l in log if any(k in l.lower() for k in
                                 ("error", "singular", "no convergence",
                                  "iteration limit", "aborted", "fatal"))]
    if rc_run != 0 or bad:
        run_circuit.last_warning = (rc_run, bad[-6:])
        print("  !! ngspice reported trouble (rc=%s):" % rc_run)
        for l in bad[-6:]:
            print("     " + l.strip()[:160])
    else:
        run_circuit.last_warning = None

    spice.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
    spice.ngSpice_CurPlot.restype = ctypes.c_char_p
    spice.ngGet_Vec_Info.restype = ctypes.POINTER(_VecInfo)

    plot = spice.ngSpice_CurPlot()
    names = spice.ngSpice_AllVecs(plot)
    out = {}
    i = 0
    while names[i]:
        nm = names[i].decode()
        full = (plot.decode() + "." + nm).encode()
        vi = spice.ngGet_Vec_Info(full)
        if vi and vi.contents.v_realdata:
            n = vi.contents.v_length
            out[nm] = [vi.contents.v_realdata[k] for k in range(n)]
        i += 1
    out["_log"] = log
    return out


def final(vecs, name):
    v = vecs.get(name) or vecs.get(name.lower())
    return v[-1] if v else None
