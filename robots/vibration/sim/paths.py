"""Where everything lives. The repo carries a snapshot of both boards
(boards/<board>/golden_netlist.xml + .kicad_sch + sheets/*.svg) so it runs
on its own; tools/sync_boards.py refreshes that snapshot from the KiCad
projects (BUGBOT_HW env, default the Bugbot Final folder)."""
import glob
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")
OUT = os.path.join(ROOT, "out")
BOARDS = {"motion": os.path.join(ROOT, "boards", "motion"),
          "vision": os.path.join(ROOT, "boards", "vision"),
          "odometry": os.path.join(ROOT, "boards", "odometry")}
ROOT_SCH = {"motion": "BugBot_Motion_Board.kicad_sch", "vision": "BugBot_Vision_Board.kicad_sch",
            "odometry": "BugBot_Odometry_Board.kicad_sch"}
HW = os.environ.get("BUGBOT_HW", r"D:\My Drive\Business\BugBotLab\Electronic design\Bugbot Final")
HW_DIRS = {"motion": os.path.join(HW, "BugBot_Motion_Board"), "vision": os.path.join(HW, "BugBot_Vision_Board"),
           "odometry": os.path.join(HW, "BugBot_Odometry_Board")}


def netlist(board):
    return os.path.join(BOARDS[board], "golden_netlist.xml")


def model_lib(name):
    return os.path.join(MODELS, name)


def kicad_file(rel):
    """<newest KiCad install>/rel, e.g. kicad_file('bin/kicad-cli.exe'). KICAD_DIR env overrides."""
    base = os.environ.get("KICAD_DIR")
    if base:
        return os.path.join(base, rel)
    vers = glob.glob(r"C:\Program Files\KiCad\*")

    def vkey(p):
        try:
            return tuple(int(x) for x in os.path.basename(p).split("."))
        except ValueError:
            return (0,)
    for v in sorted(vers, key=vkey, reverse=True):
        if os.path.exists(os.path.join(v, rel)):
            return os.path.join(v, rel)
    raise FileNotFoundError("%s not found under C:\\Program Files\\KiCad (set KICAD_DIR)" % rel)


def ngspice_dll():
    """NGSPICE_DLL env, else KiCad's bundled engine (newest version first)."""
    return os.environ.get("NGSPICE_DLL") or kicad_file(r"bin\ngspice.dll")


os.makedirs(OUT, exist_ok=True)
