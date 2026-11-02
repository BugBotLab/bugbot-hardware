#!/bin/bash
# Routing clean-up for the main board (user, 2026-10-26: "geometry is complicated where it can be simple, connections
# between pads and routes not clean, widths change unnecessarily"). Works on a pns work copy, then the caller copies it back.
#   bash design/lib/route_cleanup.sh <work copy .kicad_pcb>
set -e
W="$1"; L="$(cd "$(dirname "$0")" && pwd)"; KP="/c/Program Files/KiCad/10.0/bin/python.exe"
q() { "$KP" "$@" 2>&1 | grep -v -i -E "leak|image handler" || true; }
merge() { for i in 1 2 3 4 5 6; do o=$(q "$L/merge_collinear.py" "$W" | grep merge_); echo "  $o"; echo "$o" | grep -q ": 0 joints" && break; done; }
q "$L/width_runs.py" "$W"                         # 1. one width per net (necks only where something is in the way)
/c/Python312/python.exe "$L/clean_routes.py" "$W"  # 2. router optimiser, guarded per net
q "$L/pad_joins.py" "$W"                          # 3. no thin stubs inside pads
q "$L/pad_necks.py" "$W"                          # 4. no track wider than its pad
q "$L/pad_entries.py" "$W"                        # 5. straight pad entries
q "$L/via_joins.py" "$W"; q "$L/dedupe_tracks.py" "$W"   # 6. ends on via centres, no near-duplicate vias
q "$L/dead_ends.py" "$W"                          # 6b. dead-end stubs out (kept if they carry a connection)
q "$L/pad_reach.py" "$W"                          # 6c. ends that stop short of / off a pad centre carried on in
q "$L/joint_snap.py" "$W"                         # 6d. near-miss joints (ends overlapping, not meeting) -> clean corners
merge                                             # 7. straight lines as one piece
/c/Python312/python.exe "$L/teardrops.py" "$W"    # 8. V tapers where widths change
q "$L/route_quality.py" "$W"; q "$L/via_quality.py" "$W"
