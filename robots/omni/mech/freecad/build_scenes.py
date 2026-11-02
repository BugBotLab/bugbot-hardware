# Build the MuJoCo scenes of the style sims ONE AFTER ANOTHER (the Variants object's "After" step, or by hand):
#   C:/Python312/python.exe mech/freecad/build_scenes.py sim sim_ant sim_wasp sim_beetle sim_spider sim_base
# Run outside FreeCAD. Why one runner: six build_scene.py started at once (each with up to 8 coacd workers) swamped the PC,
# and Pythons launched straight from a long-running FreeCAD hung at start-up. Each scene gets a time limit; everything goes
# to mech/freecad/build_scenes.log. A second runner waits for the first, so a quick second save builds the newest export.
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "simlink", "SimLink", "simlink", "sim", "build_scene.py")
LOG = os.path.join(HERE, "build_scenes.log")
LOCK = os.path.join(HERE, "build_scenes.lock")
LIMIT = 20 * 60                                   # s per scene (a first build with new meshes takes ~5-10 min)


def alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


def say(log, msg):
    log.write(time.strftime("%H:%M:%S ") + msg + "\n"); log.flush()


def prune(log):
    """Delete convex-piece cache entries no sim folder uses any more (old versions of changed parts, the board components
    from before the boards collided as plain plates), in each folder's meshes/col/ and in the shared _col_cache/. An entry is
    kept while any folder beside this script (one with a robot.json) still has the mesh it was made from."""
    import glob, hashlib, re
    folders = [os.path.dirname(p) for p in glob.glob(os.path.join(HERE, "*", "robot.json"))]
    keep_all, removed = set(), 0
    for d in folders:
        text = open(os.path.join(d, "robot.json"), encoding="utf-8").read()
        keys = set()
        for rel in set(re.findall(r'"(meshes/[^"/]+\.stl)"', text)):         # the meshes this robot uses (not col/ pieces)
            try:
                k = hashlib.sha1(open(os.path.join(d, rel), "rb").read()).hexdigest()[:16]
                keys |= {k, k + "p"}
            except OSError:
                pass
        keep_all |= keys
        col = os.path.join(d, "meshes", "col")
        keep_files = set()
        for idx in glob.glob(os.path.join(col, "*.json")):
            key = os.path.basename(idx)[:-5]
            if key in keys:
                keep_files |= {os.path.basename(p) for p in json.load(open(idx))} | {os.path.basename(idx)}
        for f in glob.glob(os.path.join(col, "*")):
            if os.path.basename(f) not in keep_files:
                os.remove(f); removed += 1
    sd = os.path.join(HERE, "_col_cache")
    keep_files = set()
    for idx in glob.glob(os.path.join(sd, "*.json")):
        key = os.path.basename(idx)[:-5]
        if key in keep_all:
            keep_files |= set(json.load(open(idx))) | {os.path.basename(idx)}
    for f in glob.glob(os.path.join(sd, "*")):
        if os.path.basename(f) not in keep_files:
            os.remove(f); removed += 1
    say(log, f"cache: removed {removed} unused files ({len(folders)} sim folders)")


def main(dirs):
    with open(LOG, "a", encoding="utf-8") as log:
        while os.path.exists(LOCK):                # an earlier runner: let it finish, then build again (newer export)
            try:
                pid = int(open(LOCK).read().strip() or 0)
            except Exception:
                pid = 0
            if not pid or not alive(pid):
                break
            say(log, f"waiting for runner {pid}"); time.sleep(10)
        open(LOCK, "w").write(str(os.getpid()))
        try:
            say(log, f"== building {len(dirs)} scenes: {' '.join(dirs)}")
            ok = True
            for d in dirs:
                out = d if os.path.isabs(d) else os.path.join(HERE, d)
                t0 = time.time()
                try:
                    r = subprocess.run([sys.executable, BUILD, out], capture_output=True, text=True, timeout=LIMIT,
                                       stdin=subprocess.DEVNULL)
                    lines = r.stdout.strip().splitlines() or [""]
                    last = lines[-1]
                    for ln in lines[:-1]:                  # (decomposition progress, slow parts, cache clean-up)
                        say(log, f"   {os.path.basename(out)}: {ln.strip()[:200]}")
                    say(log, f"{os.path.basename(out)}: exit {r.returncode} in {time.time() - t0:.0f} s  {last[:300]}")
                    if r.returncode:
                        ok = False; say(log, (r.stderr or "")[-1500:])
                except subprocess.TimeoutExpired:
                    ok = False; say(log, f"{os.path.basename(out)}: TIMED OUT after {LIMIT} s")
            # (old cache pieces are deleted by build_scene.py itself, as each scene is built: prune() is for a manual clean-up)
            say(log, "== done")
        finally:
            try:
                os.remove(LOCK)
            except Exception:
                pass


if __name__ == "__main__":
    main(sys.argv[1:])
