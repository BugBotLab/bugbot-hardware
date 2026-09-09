"""Falstad-style animated view of the BugBot stack, playing back the mission
transients from sim_mission.py. One self-contained HTML file: the block
diagram of both boards with current shown as moving dots (speed and
direction follow the simulated current, wire brightness follows voltage),
the four motors spinning at their simulated rpm, the scripted MCU's
register writes on a timeline, the fault line, and strip charts with a
cursor. It plays back what ngspice computed - it is not a live solver.
"""
import json


def build(results, path, M, V):
    data = json.dumps(results)
    html = TEMPLATE.replace("/*__DATA__*/", "const MISSIONS = " + data + ";")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


TEMPLATE = r'''<title>BugBot Stack Bench</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root { --ink:#e8e4da; --dim:#8d8a82; --bg:#101418; --panel:#171c22; --line:#2a313a;
          --amber:#f2b33d; --cyan:#5fd3e6; --green:#7bd88f; --red:#ff6b57; --violet:#b48cff; }
  body { background:var(--bg); color:var(--ink); font-family:"IBM Plex Sans",system-ui,sans-serif; margin:0; }
  header { display:flex; flex-wrap:wrap; align-items:center; gap:14px 22px; padding:14px 20px; border-bottom:1px solid var(--line); background:var(--panel); }
  h1 { font-size:17px; font-weight:600; margin:0; letter-spacing:.2px; }
  h1 small { color:var(--dim); font-weight:400; margin-left:10px; }
  label { color:var(--dim); font-size:12px; text-transform:uppercase; letter-spacing:.08em; margin-right:6px; }
  select, button { background:#0d1114; color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:6px 10px; font:inherit; font-size:13px; }
  button:hover, select:hover { border-color:var(--amber); }
  button:focus-visible, select:focus-visible, input:focus-visible { outline:2px solid var(--cyan); outline-offset:2px; }
  .mono { font-family:"IBM Plex Mono",ui-monospace,monospace; font-variant-numeric:tabular-nums; }
  .scrub { display:flex; align-items:center; gap:10px; flex:1 1 320px; }
  input[type=range] { flex:1; accent-color:var(--amber); }
  main { display:grid; grid-template-columns: minmax(0,1fr) 300px; gap:16px; padding:16px 20px; }
  @media (max-width:1100px) { main { grid-template-columns:1fr; } }
  canvas { display:block; width:100%; background:var(--panel); border:1px solid var(--line); border-radius:8px; }
  .side { display:flex; flex-direction:column; gap:14px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px 14px; }
  .card h2 { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:var(--dim); margin:0 0 8px; font-weight:500; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td { padding:3px 0; border-bottom:1px solid var(--line); }
  td:last-child { text-align:right; }
  .ok { color:var(--green); } .bad { color:var(--red); }
  .writes div { padding:2px 0; color:var(--dim); font-size:12px; }
  .writes div.now { color:var(--amber); }
  .charts { padding:0 20px 20px; }
  .charts canvas { margin-top:12px; }
  .legend { display:flex; gap:14px; flex-wrap:wrap; font-size:12px; color:var(--dim); margin-top:6px; }
  .legend i { display:inline-block; width:18px; height:3px; margin-right:6px; vertical-align:middle; border-radius:2px; }
  p.note { color:var(--dim); font-size:12px; margin:6px 0 0; line-height:1.5; }
  @media (prefers-reduced-motion: reduce) { .dot { display:none } }
</style>
<header>
  <h1>BugBot Stack Bench <small>Motion + Vision, ngspice mission playback</small></h1>
  <div><label for="mission">Mission</label><select id="mission"></select></div>
  <div><label for="speed">Speed</label><select id="speed"><option value="0.02">1/50</option><option value="0.05" selected>1/20</option><option value="0.1">1/10</option><option value="0.25">1/4</option><option value="1">real time</option></select></div>
  <button id="play">Pause</button>
  <div class="scrub"><input id="t" type="range" min="0" max="1000" value="0"><span class="mono" id="tlabel">0.0 ms</span></div>
</header>
<main>
  <div><canvas id="bench" width="1120" height="640"></canvas>
    <p class="note">Dots move with the simulated current (speed and direction), wire brightness follows voltage, motors spin at their simulated rpm. Everything shown was computed by ngspice from the two boards' netlists; this page only plays it back.</p></div>
  <div class="side">
    <div class="card"><h2>MCU register writes</h2><div class="writes" id="writes"></div></div>
    <div class="card"><h2>Drivers</h2><table id="drv"></table></div>
    <div class="card"><h2>Checks</h2><table id="checks"></table></div>
  </div>
</main>
<div class="charts">
  <canvas id="c1" width="1440" height="150"></canvas>
  <div class="legend"><span><i style="background:var(--amber)"></i>cell current</span><span><i style="background:var(--violet)"></i>USB current</span><span><i style="background:var(--cyan)"></i>VMOT</span><span><i style="background:var(--green)"></i>3V3</span><span><i style="background:#ccc"></i>VSYS_SW</span></div>
  <canvas id="c2" width="1440" height="150"></canvas>
  <div class="legend"><span>motor currents U6 U7 U8 U9 (dashed: current limit)</span></div>
  <canvas id="c3" width="1440" height="150"></canvas>
  <div class="legend"><span>motor speed, rpm (U6 U7 U8 U9)</span><span style="margin-left:auto"><i style="background:var(--red)"></i>MOT_INT (fault line, right axis)</span></div>
</div>
<script>
/*__DATA__*/
const names = Object.keys(MISSIONS);
const sel = document.getElementById('mission');
names.forEach(n => { const o = document.createElement('option'); o.value = n; o.textContent = n; sel.appendChild(o); });
let cur = MISSIONS[names[0]], tIdx = 0, playing = true, last = performance.now(), simT = 0;
const speedSel = document.getElementById('speed'), playBtn = document.getElementById('play'), scrub = document.getElementById('t'), tlabel = document.getElementById('tlabel');
sel.onchange = () => { cur = MISSIONS[sel.value]; simT = 0; renderStatic(); };
playBtn.onclick = () => { playing = !playing; playBtn.textContent = playing ? 'Pause' : 'Play'; };
scrub.oninput = () => { simT = scrub.value / 1000 * cur.t[cur.t.length - 1]; };

function idxAt(t) { const T = cur.t; let lo = 0, hi = T.length - 1; while (lo < hi) { const m = (lo + hi) >> 1; if (T[m] < t) lo = m + 1; else hi = m; } return lo; }
function val(name, t) { const s = cur.series[name]; if (!s) return 0; return s[idxAt(t)]; }
function regsAt(t) { const r = { U6: [0, 3], U7: [0, 3], U8: [0, 3], U9: [0, 3] }; for (const [tw, w] of cur.mcu) { if (tw <= t) for (const k in w) r[k] = w[k]; } return r; }

// ---- the bench diagram --------------------------------------------------
const C = document.getElementById('bench'), g = C.getContext('2d');
const N = {  // boxes: id -> [x, y, w, h, label, sub]
  cell: [30, 300, 90, 60, 'LiPo cell', '1S'], usb: [30, 90, 90, 60, 'USB-C', 'J1'],
  chg: [190, 170, 120, 70, 'ETA6003', 'charger + power path'], q1: [150, 300, 60, 40, 'Q1/F1', 'reverse + PTC'],
  vsys: [360, 200, 24, 24, 'VSYS', ''], sw: [400, 90, 90, 50, 'SW1', 'slide switch'],
  q2: [420, 190, 60, 40, 'Q2', ''], q3: [420, 320, 60, 40, 'Q3', ''],
  tps: [520, 170, 120, 70, 'TPS63020', 'buck-boost 3V3'], v33: [690, 200, 24, 24, '3V3', ''],
  j8: [760, 150, 40, 130, 'J8/J9', 'stack'], mod: [850, 60, 130, 70, 'ESP32-P4', 'module'],
  cam: [850, 150, 60, 40, 'camera', ''], tof: [920, 150, 60, 40, 'ToF', ''], led: [850, 210, 60, 40, 'LED', ''], servo: [920, 210, 60, 40, 'servos', 'VMOT'],
  vmot: [520, 335, 24, 24, 'VMOT', ''],
  U6: [600, 430, 70, 46, 'DRV8830', 'U6 0x60'], U7: [600, 500, 70, 46, 'DRV8830', 'U7 0x61'], U8: [600, 570, 70, 46, 'DRV8830', 'U8 0x62'], U9: [600, 360, 70, 46, 'DRV8830', 'U9 0x64'],
  M6: [730, 453, 0, 0, 'M', 'A'], M7: [730, 523, 0, 0, 'M', 'B'], M8: [730, 593, 0, 0, 'M', 'C'], M9: [730, 383, 0, 0, 'M', 'D'],
};
function cx(b) { return b[0] + b[2] / 2; } function cy(b) { return b[1] + b[3] / 2; }
// wires: [points], current fn (A, + along the path), voltage fn
const W = [
  { p: [[120, 330], [150, 330]], i: t => val('VBAT', t), v: t => 3.7 },
  { p: [[210, 320], [250, 320], [250, 240]], i: t => val('VBAT', t), v: t => val('VSYS', t) },
  { p: [[120, 120], [250, 120], [250, 170]], i: t => val('I_USB', t), v: t => (cur.series.I_USB ? 5 : 0) },
  { p: [[310, 205], [372, 205]], i: t => val('VBAT', t) + val('I_USB', t), v: t => val('VSYS', t) },
  { p: [[372, 212], [372, 340], [420, 340]], i: t => motSum(t) + 0.1, v: t => val('VSYS', t) },
  { p: [[384, 205], [420, 205]], i: t => tpsIn(t), v: t => val('VSYS', t) },
  { p: [[445, 140], [445, 190]], i: t => 0.00005, v: t => val('GATE', t), thin: true },
  { p: [[445, 230], [445, 320]], i: t => 0.00005, v: t => val('GATE', t), thin: true },
  { p: [[480, 210], [520, 210]], i: t => tpsIn(t), v: t => val('VSYS_SW', t) },
  { p: [[640, 205], [690, 205]], i: t => 0.82, v: t => val('3V3', t) },
  { p: [[714, 212], [760, 212]], i: t => 0.77, v: t => val('3V3', t) },
  { p: [[800, 180], [830, 180], [830, 95], [850, 95]], i: t => 0.55, v: t => val('MOD_3V3', t) },
  { p: [[800, 190], [850, 170]], i: t => 0.15, v: t => val('3V3', t) },
  { p: [[800, 200], [920, 170]], i: t => 0.05, v: t => val('3V3', t) },
  { p: [[800, 240], [850, 230]], i: t => 0.02, v: t => val('3V3', t) },
  { p: [[480, 340], [520, 340]], i: t => motSum(t) + 0.1, v: t => val('VMOT', t) },
  { p: [[544, 347], [780, 347], [780, 270], [920, 270], [920, 250]], i: t => 0.1, v: t => val('VMOT', t) },
  { p: [[532, 359], [532, 615], [600, 615]], i: t => motSum(t), v: t => val('VMOT', t) },
  { p: [[532, 383], [600, 383]], i: t => Math.abs(val('I_U9', t)), v: t => val('VMOT', t) },
  { p: [[532, 453], [600, 453]], i: t => Math.abs(val('I_U6', t)), v: t => val('VMOT', t) },
  { p: [[532, 523], [600, 523]], i: t => Math.abs(val('I_U7', t)), v: t => val('VMOT', t) },
  { p: [[670, 453], [716, 453]], i: t => val('I_U6', t), v: t => 3 },
  { p: [[670, 523], [716, 523]], i: t => val('I_U7', t), v: t => 3 },
  { p: [[670, 593], [716, 593]], i: t => val('I_U8', t), v: t => 3 },
  { p: [[670, 383], [716, 383]], i: t => val('I_U9', t), v: t => 3 },
  { p: [[635, 360], [635, 300], [990, 300], [990, 130]], i: t => 0.0003 * (val('MOT_INT', t) < 1 ? 1 : 0), v: t => val('MOT_INT', t), thin: true, tag: 'MOT_INT' },
];
function motSum(t) { return ['U6', 'U7', 'U8', 'U9'].reduce((a, k) => a + Math.abs(val('I_' + k, t)), 0); }
function tpsIn(t) { const vin = Math.max(val('VSYS_SW', t), 1.8); return 0.82 * 3.3 / (vin * 0.9); }
function vcol(v, vmax = 5) { const k = Math.max(0, Math.min(1, v / vmax)); const r = Math.round(60 + 182 * k), gg = Math.round(60 + 119 * k), b = Math.round(60 + 1 * k); return `rgb(${r},${gg},${b})`; }
function drawBox(b, hot) { g.fillStyle = '#0d1114'; g.strokeStyle = hot ? '#f2b33d' : '#3a434e'; g.lineWidth = 1.5; roundRect(b[0], b[1], b[2], b[3], 6); g.fill(); g.stroke(); g.fillStyle = '#e8e4da'; g.font = '600 12px "IBM Plex Sans"'; g.textAlign = 'center'; g.fillText(b[4], cx(b), cy(b) + (b[5] ? -2 : 4)); if (b[5]) { g.fillStyle = '#8d8a82'; g.font = '11px "IBM Plex Sans"'; g.fillText(b[5], cx(b), cy(b) + 12); } }
function roundRect(x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function pathLen(p) { let L = 0; for (let i = 1; i < p.length; i++) L += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); return L; }
function pointAt(p, d) { for (let i = 1; i < p.length; i++) { const l = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); if (d <= l) { const k = d / l; return [p[i - 1][0] + (p[i][0] - p[i - 1][0]) * k, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k]; } d -= l; } return p[p.length - 1]; }
let phase = 0;
function drawBench(t, dt) {
  g.clearRect(0, 0, C.width, C.height);
  g.fillStyle = '#8d8a82'; g.font = '11px "IBM Plex Mono"'; g.textAlign = 'left';
  g.fillText('MOTION BOARD', 30, 40); g.fillText('VISION BOARD', 850, 40);
  g.strokeStyle = '#2a313a'; g.setLineDash([4, 6]); g.beginPath(); g.moveTo(830, 30); g.lineTo(830, 290); g.stroke(); g.setLineDash([]);
  phase += dt;
  for (const w of W) {
    const I = w.i(t), Vv = w.v(t);
    g.strokeStyle = vcol(Vv); g.lineWidth = w.thin ? 1.2 : 2.5 + Math.min(3, Math.abs(I));
    g.beginPath(); g.moveTo(w.p[0][0], w.p[0][1]); for (let i = 1; i < w.p.length; i++) g.lineTo(w.p[i][0], w.p[i][1]); g.stroke();
    const L = pathLen(w.p), sp = Math.min(220, 160 * Math.abs(I)) * Math.sign(I || 0);
    if (Math.abs(I) > 0.0002) { const spacing = 18; const off = ((phase * sp) % spacing + spacing) % spacing; g.fillStyle = w.tag === 'MOT_INT' ? '#ff6b57' : '#f2b33d'; for (let d = off; d < L; d += spacing) { const q = pointAt(w.p, d); g.beginPath(); g.arc(q[0], q[1], w.thin ? 1.6 : 2.4, 0, 6.283); g.fill(); } }
  }
  const regs = regsAt(t);
  for (const k in N) { const b = N[k]; if (b[2] === 0) continue; drawBox(b, k.startsWith('U') && regs[k] && regs[k][0] !== 0); }
  // node voltage readouts
  g.font = '11px "IBM Plex Mono"'; g.textAlign = 'left';
  const readouts = [['VSYS', val('VSYS', t), 360, 195], ['VSYS_SW', val('VSYS_SW', t), 485, 195], ['3V3', val('3V3', t), 690, 195], ['VMOT', val('VMOT', t), 520, 330], ['module', val('MOD_3V3', t), 850, 145], ['MOT_INT', val('MOT_INT', t), 900, 292], ['cell', val('VBAT', t), 30, 372, 'A'], ['GATE', val('GATE', t), 455, 165]];
  for (const r of readouts) { g.fillStyle = '#e8e4da'; g.fillText(r[0] + ' ' + r[1].toFixed(2) + (r[4] || 'V'), r[2], r[3]); }
  // motors
  for (const [mk, dk] of [['M6', 'U6'], ['M7', 'U7'], ['M8', 'U8'], ['M9', 'U9']]) {
    const b = N[mk], rpm = val('RPM_' + dk, t), I = val('I_' + dk, t);
    const ang = (phase * rpm / 60 * 2 * Math.PI * 0.02) % 6.283;   // shown at 1/50 speed
    g.strokeStyle = Math.abs(I) > cur.ilim * 0.9 ? '#ff6b57' : '#5fd3e6'; g.lineWidth = 2;
    g.beginPath(); g.arc(b[0], b[1], 16, 0, 6.283); g.stroke();
    g.beginPath(); g.moveTo(b[0], b[1]); g.lineTo(b[0] + 14 * Math.cos(ang), b[1] + 14 * Math.sin(ang)); g.stroke();
    g.fillStyle = '#e8e4da'; g.textAlign = 'left'; g.fillText(b[5] + ' ' + Math.round(Math.abs(rpm)) + ' rpm  ' + (I * 1000).toFixed(0) + ' mA', b[0] + 24, b[1] + 4);
  }
  if (cur.stall && t > cur.stall[1] && t < cur.stall[2]) { const b = N['M' + cur.stall[0].slice(1)]; g.fillStyle = '#ff6b57'; g.font = '600 11px "IBM Plex Sans"'; g.fillText('BLOCKED', b[0] + 24, b[1] + 18); }
}
// ---- charts -------------------------------------------------------------
function chart(id, lines, t, yl, yr) {
  const c = document.getElementById(id), x = c.getContext('2d'); x.clearRect(0, 0, c.width, c.height);
  const T = cur.t, tmax = T[T.length - 1], L = 46, R = c.width - 46, H = c.height - 22;
  x.strokeStyle = '#2a313a'; x.lineWidth = 1; x.strokeRect(L, 6, R - L, H);
  x.fillStyle = '#8d8a82'; x.font = '10px "IBM Plex Mono"'; x.textAlign = 'right';
  const [lo, hi] = yl; x.fillText(hi.toFixed(1), L - 4, 12); x.fillText(lo.toFixed(1), L - 4, H + 6);
  if (yr) { x.textAlign = 'left'; x.fillText(yr[1].toFixed(1), R + 4, 12); x.fillText(yr[0].toFixed(1), R + 4, H + 6); }
  for (const ln of lines) {
    const s = cur.series[ln.k]; if (!s) continue; const [a, b] = ln.right ? yr : yl;
    x.strokeStyle = ln.c; x.lineWidth = 1.4; if (ln.dash) x.setLineDash([4, 4]); else x.setLineDash([]);
    x.beginPath(); for (let i = 0; i < T.length; i++) { const px = L + (T[i] / tmax) * (R - L), py = 6 + H - ((ln.f ? ln.f(s[i]) : s[i]) - a) / (b - a) * H; if (i === 0) x.moveTo(px, py); else x.lineTo(px, py); } x.stroke();
  }
  x.setLineDash([]);
  if (lines.some(l => l.hline !== undefined)) { const l = lines.find(l => l.hline !== undefined); const py = 6 + H - (l.hline - yl[0]) / (yl[1] - yl[0]) * H; x.strokeStyle = '#ff6b57'; x.setLineDash([3, 5]); x.beginPath(); x.moveTo(L, py); x.lineTo(R, py); x.stroke(); x.setLineDash([]); }
  const px = L + (t / tmax) * (R - L); x.strokeStyle = '#f2b33d'; x.lineWidth = 1; x.beginPath(); x.moveTo(px, 6); x.lineTo(px, H + 6); x.stroke();
  x.fillStyle = '#8d8a82'; x.textAlign = 'center'; x.fillText('0 ms', L, c.height - 4); x.fillText((tmax * 1000).toFixed(0) + ' ms', R, c.height - 4);
}
function drawCharts(t) {
  chart('c1', [{ k: 'VBAT', c: '#f2b33d' }, { k: 'I_USB', c: '#b48cff' }, { k: 'VMOT', c: '#5fd3e6' }, { k: '3V3', c: '#7bd88f' }, { k: 'VSYS_SW', c: '#cccccc' }], t, [-1, 5]);
  chart('c2', [{ k: 'I_U6', c: '#f2b33d', f: v => v * 1000 }, { k: 'I_U7', c: '#5fd3e6', f: v => v * 1000 }, { k: 'I_U8', c: '#7bd88f', f: v => v * 1000 }, { k: 'I_U9', c: '#b48cff', f: v => v * 1000, hline: cur.ilim * 1000 }], t, [-500, 500]);
  chart('c3', [{ k: 'RPM_U6', c: '#f2b33d' }, { k: 'RPM_U7', c: '#5fd3e6' }, { k: 'RPM_U8', c: '#7bd88f' }, { k: 'RPM_U9', c: '#b48cff' }, { k: 'MOT_INT', c: '#ff6b57', right: true }], t, [-25000, 25000], [0, 4]);
}
function renderStatic() {
  const wr = document.getElementById('writes'); wr.innerHTML = '';
  for (const [tw, w] of cur.mcu) { const d = document.createElement('div'); d.dataset.t = tw; d.textContent = (tw * 1000).toFixed(0) + ' ms  ' + Object.entries(w).map(([k, v]) => k + '=' + (v[0] > 0 ? 'FWD' : v[0] < 0 ? 'REV' : 'OFF') + '@' + v[1] + 'V').join(' '); wr.appendChild(d); }
  const ck = document.getElementById('checks'); ck.innerHTML = '';
  for (const [desc, ok] of cur.checks) { const tr = document.createElement('tr'); tr.innerHTML = '<td>' + desc + '</td><td class="' + (ok ? 'ok' : 'bad') + '">' + (ok ? 'PASS' : 'FAIL') + '</td>'; ck.appendChild(tr); }
}
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  const tmax = cur.t[cur.t.length - 1];
  if (playing) { simT += dt * parseFloat(speedSel.value); if (simT > tmax) simT = 0; }
  scrub.value = Math.round(simT / tmax * 1000); tlabel.textContent = (simT * 1000).toFixed(1) + ' ms';
  drawBench(simT, dt); drawCharts(simT);
  const regs = regsAt(simT), tb = document.getElementById('drv'); tb.innerHTML = '';
  for (const k of ['U6', 'U7', 'U8', 'U9']) { const tr = document.createElement('tr'); const r = regs[k]; tr.innerHTML = '<td>' + k + ' ' + (r[0] > 0 ? 'FWD' : r[0] < 0 ? 'REV' : 'off') + ' ' + r[1] + ' V</td><td class="mono">' + (val('I_' + k, simT) * 1000).toFixed(0) + ' mA · ' + Math.round(Math.abs(val('RPM_' + k, simT))) + ' rpm</td>'; tb.appendChild(tr); }
  for (const d of document.querySelectorAll('.writes div')) d.classList.toggle('now', Math.abs(parseFloat(d.dataset.t) - simT) < 0.004);
  requestAnimationFrame(frame);
}
renderStatic(); requestAnimationFrame(frame);
</script>
'''
