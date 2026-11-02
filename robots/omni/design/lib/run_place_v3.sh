# Floor plan v3 pipeline (connectors already chosen: _place/connector_choice_full.json): anneal, then refine twice from the
# legal result (slide-past then no-overlap), then a last nearest-spot fix and the 2D plan.
#   bash design/lib/run_place_v3.sh
set -e
cd "$(dirname "$0")"
P=../schematics/Main/_place
python -u place_v3.py 300000 > $P/place_v3.log 2>&1;            grep -E "cost" $P/place_v3.log | tail -1
cp $P/placement_v3.json $P/placement_v3_legal1.json
W_OV=20 REFINE=1 python -u place_v3.py 400000 > $P/place_v3r.log 2>&1; grep -E "cost" $P/place_v3r.log | tail -1
cp $P/placement_v3.json $P/placement_v3_legal1.json
REFINE=1 python -u place_v3.py 200000 > $P/place_v3r2.log 2>&1;  grep -E "cost" $P/place_v3r2.log | tail -1
python place_v3_fixlast.py 2>&1 | tail -4
cd ../BugBot_Main && python draw_floorplan_v3.py
