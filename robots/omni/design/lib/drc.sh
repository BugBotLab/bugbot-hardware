# DRC of the main board, summarised (fill first: kicad-cli --refill-zones)
cd "$(dirname "$0")/../schematics/Main"
"/c/Program Files/KiCad/10.0/bin/kicad-cli.exe" pcb drc --refill-zones --save-board --format json --severity-error -o _route/drc_final.json BugBot_Main.kicad_pcb >/dev/null 2>&1
python -c "
import json,collections; d=json.load(open('_route/drc_final.json')); print(dict(collections.Counter(v['type'] for v in d['violations'])), 'unconnected', len(d['unconnected_items']))
skip=('courtyards_overlap','npth_inside_courtyard','pth_inside_courtyard','solder_mask_bridge')
for v in d['violations']:
  if v['type'] not in skip: print(' ',v['type'],'|',' / '.join(i['description'][:60]+' @%.1f,%.1f'%(i['pos']['x'],i['pos']['y']) for i in v['items']))
  elif v['type']!='solder_mask_bridge': print(' ',v['type'],'|',' / '.join(i['description'][:30] for i in v['items']))
for u in d['unconnected_items']: print('  open:', u['items'][0]['description'][:55], '@%.1f,%.1f'%(u['items'][0]['pos']['x'],u['items'][0]['pos']['y']), '<->', u['items'][1]['description'][:45])"
