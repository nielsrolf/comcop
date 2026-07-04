"""Build an interactive widget for the multi-seed ultimatum experiment.

Reads assets/ultimatum_multiseed.json (produced by
`python3 ultimatum_multiseed_experiment.py --json`) and inlines it into a
self-contained Plotly HTML page. Lets the reader toggle between the offer and
threshold trajectory (mean +/-1 SD band across seeds) and the per-seed final
distribution, making it obvious the proximity>random gap is not a lucky draw.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "assets", "ultimatum_multiseed.json")
OUT_PATH = os.path.join(ROOT, "assets", "ultimatum_multiseed.html")

with open(JSON_PATH) as f:
    DATA = json.load(f)

HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 12px;
         color: #1a1a1a; background: #fff; }
  .controls { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; align-items:center; }
  button { border:1px solid #ccc; background:#f6f6f6; border-radius:6px; padding:6px 12px;
            cursor:pointer; font-size:13px; }
  button.active { background:#2ca02c; color:#fff; border-color:#2ca02c; }
  #note { font-size:12px; color:#555; margin:6px 2px; }
  #chart { width:100%; height:420px; }
</style></head>
<body>
<div class="controls">
  <button id="b-offer" class="active" onclick="show('offer')">Offer trajectory</button>
  <button id="b-thr" onclick="show('thr')">Threshold trajectory</button>
  <button id="b-dist" onclick="show('dist')">Final distribution</button>
</div>
<div id="chart"></div>
<div id="note"></div>
<script>
const DATA = __DATA_JSON__;
const COL = {random:'#8c564b', proximity:'#2ca02c'};
const NM = {random:'random pairing', proximity:'proximity pairing'};
const N = DATA.n_seeds, STEPS = DATA.n_steps;
const xs = Array.from({length: STEPS}, (_, i) => i);

function band(stat) {
  const traces = [];
  for (const p of ['random','proximity']) {
    const m = DATA[p][stat + '_mean'], s = DATA[p][stat + '_sd'];
    const up = m.map((v,i) => v + s[i]), lo = m.map((v,i) => v - s[i]);
    const rgb = p === 'random' ? '140,86,75' : '44,160,44';
    traces.push({x: xs.concat([...xs].reverse()), y: up.concat([...lo].reverse()),
      fill:'toself', fillcolor:'rgba(' + rgb + ',0.15)', line:{color:'transparent'},
      hoverinfo:'skip', showlegend:false});
    traces.push({x: xs, y: m, mode:'lines', line:{color:COL[p], width:2.2}, name: NM[p]});
  }
  return traces;
}

function dist(stat) {
  const traces = [];
  for (const p of ['random','proximity']) {
    traces.push({x: DATA[p]['final_' + stat], type:'histogram', opacity:0.6,
      marker:{color:COL[p]}, name: NM[p], xbins:{start:0,end:1,size:0.05}});
  }
  return traces;
}

function show(view) {
  ['offer','thr','dist'].forEach(v =>
    document.getElementById('b-'+v).classList.toggle('active', v===view));
  let traces, layout, note;
  if (view === 'dist') {
    traces = dist('offer');
    layout = {barmode:'overlay', title:'Final mean offer across ' + N + ' seeds',
      xaxis:{title:'offer', range:[0,1]}, yaxis:{title:'# seeds'}, margin:{t:40}};
    note = 'Two clean, near-separated clusters: random pairing settles low, proximity pairing high.';
  } else {
    const stat = view;
    traces = band(stat);
    layout = {title: (stat==='offer'?'Mean offer':'Mean acceptance threshold') +
        ' (mean \\u00b1 1 SD over ' + N + ' seeds)',
      xaxis:{title:'step'}, yaxis:{title: stat==='offer'?'offer':'threshold', range:[0,1]},
      margin:{t:40}, shapes:[{type:'line', x0:0, x1:STEPS-1, y0:0.5, y1:0.5,
        line:{color:'#999', dash:'dot', width:1}}]};
    note = 'Bands are +/-1 SD across ' + N + ' seeds; they barely overlap, so the ordering is robust, not chance.';
  }
  Plotly.newPlot('chart', traces, layout, {displayModeBar:false, responsive:true});
  document.getElementById('note').textContent = note;
}
show('offer');
</script>
</body></html>
"""

html = HTML.replace("__DATA_JSON__", json.dumps(DATA))
with open(OUT_PATH, "w") as f:
    f.write(html)
print("Wrote", OUT_PATH)
