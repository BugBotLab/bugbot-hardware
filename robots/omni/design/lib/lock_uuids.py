# Lock (or with --unlock, unlock) the tracks / vias whose uuids are listed in a file (KiCad python). Used to freeze hand
# edits while the clean-up scripts run (they and the router optimiser leave locked pieces alone).
#   "C:/Program Files/KiCad/10.0/bin/python.exe" design/lib/lock_uuids.py board uuids.txt [--unlock]
import sys, pcbnew
B, U = sys.argv[1], set(open(sys.argv[2]).read().split())
lock = "--unlock" not in sys.argv
b = pcbnew.LoadBoard(B); n = 0
for t in b.GetTracks():
    if t.m_Uuid.AsString() in U: t.SetLocked(lock); n += 1
pcbnew.SaveBoard(B, b)
print(("locked" if lock else "unlocked"), n, "of", len(U))
