# Through-hole connectors we solder ourselves instead of JLC (2026-10-31, business/BugBot_kit_costs.md): each one saves
# an Extended part type ($3 per board order in feeder loading) and JLC's hand-soldering (THT) charge. SMD parts all stay
# at JLC (main J1 USB-C has only through-hole shell pegs, its signal pins are SMD: stays at JLC too).
# split() takes these refs out of a board's JLC BOM + CPL and lists them in jlc/HAND_SOLDER.txt (buy them from LCSC);
# the board generators call it after writing their JLC files. Run alone to apply it to the current JLC files:
#   C:/Python312/python.exe design/lib/hand_solder.py
import os
from part_swap import read_bom, write_bom

HAND_SOLDER = {
    "BugBot_Main": ["J11", "J12", "J13", "J18"],      # encoder sockets 1x4 1.27, servo header 1x3 2.54
    "BugBot_Front": ["J1"],                           # 2x10 1.27 right-angle header to the main board
    "BugBot_Enc": ["J1"],                             # 1x4 1.27 right-angle header
}
K = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def split(prj, jlc_dir=None):
    refs = set(HAND_SOLDER.get(prj, ()))
    jlc_dir = jlc_dir or os.path.join(K, prj, "jlc")
    bom, cpl = (os.path.join(jlc_dir, f"{prj}_{k}_JLC.csv") for k in ("BOM", "CPL"))
    header_line, head, body, quoting = read_bom(bom)
    ci = {h.lower(): k for k, h in enumerate(head)}
    kd, kc = ci["designator"], ci["comment"]
    kl = next(ci[h] for h in ci if "lcsc" in h or "jlc" in h)
    keep, removed = [], []
    for r in body:
        des = [x.strip() for x in r[kd].split(",") if x.strip()]
        removed += [(d, r[kc], r[kl]) for d in des if d in refs]
        left = [d for d in des if d not in refs]
        if left:
            r = list(r); r[kd] = ",".join(left); keep.append(r)
    if not removed:                                                  # already split (or nothing to hand-solder)
        return
    write_bom(bom, header_line, keep, quoting)
    lines = open(cpl, encoding="utf-8").read().splitlines()
    open(cpl, "w", encoding="utf-8", newline="").write(
        "\n".join([lines[0]] + [l for l in lines[1:] if l.split(",")[0] not in refs]) + "\n")
    with open(os.path.join(jlc_dir, "HAND_SOLDER.txt"), "w", encoding="utf-8") as fh:
        fh.write("Soldered by us, not JLC (design/lib/hand_solder.py): buy from LCSC\n")
        for d, val, lc in removed:
            fh.write(f"{d}\t{val}\t{lc}\n")
    print(f"{prj}: hand-solder {' '.join(d for d, _, _ in removed)}")


if __name__ == "__main__":
    for prj in HAND_SOLDER:
        split(prj)
