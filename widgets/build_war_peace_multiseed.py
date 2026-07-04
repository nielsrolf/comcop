"""Build an interactive widget for the multi-seed War vs Peace experiment.

Reads assets/war_peace_multiseed.json (produced by
`python3 war_peace_multiseed_experiment.py --json`) and inlines it into a
self-contained Plotly HTML page. The reader toggles which quantity to view
(population, welfare, aggression, weapon budget) and sees the mean +/-1 SD
band across seeds for three contrasting environments (peaceful / arms race /
collapse), making the average dynamics -- not a single noisy seed -- explicit.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "assets", "war_peace_multiseed.json")
OUT_PATH = os.path.join(ROOT, "assets", "war_peace_multiseed.html")

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
  button.active { background:#1f77b4; color:#fff; border-color:#1f77b4; }
  #note { font-size:12px; color:#555; margin:6px 2px; }
  #chart { width:100%; height:430px; }
</style></head>
<body>
<div class="controls">
  <button id="b-pop" class="active" onclick="show('pop')">Population</button>
  <button id="b-welfare" onclick="show('welfare')">Total welfare</button>
  <button id="b-aggr" onclick="show('aggr')">Mean aggression</button>
  <button id="b-weap" onclick="show('weap')">Weapon budget</button>
</div>
<div id="chart"></div>
<div id="note"></div>
<script>
const DATA = __DATA_JSON__;
const C = DATA.conditions;
const NAMES = Object.keys(C);
const COL = {'peaceful':'#2ca02c', 'arms race':'#d62728', 'collapse':'#7f7f7f'};
const RGB = {'peaceful':'44,160,44', 'arms race':'214,39,40', 'collapse':'127,127,127'};
const STEPS = DATA.n_steps, N = DATA.n_seeds;
const xs = Array.from({length: STEPS}, (_, i) => i);
const YLAB = {pop:'agents', welfare:'sum of resources', aggr:'P(attack)', weap:'weapon fraction'};
const TITLE = {pop:'Population', welfare:'Total welfare',
               aggr:'Mean evolved aggression', weap:'Mean weapon budget'};

function traces(stat) {
  const out = [];
  for (const name of NAMES) {
    const m = C[name][stat + '_mean'], s = C[name][stat + '_sd'];
    const up = m.map((v,i) => v + s[i]), lo = m.map((v,i) => v - s[i]);
    out.push({x: xs.concat([...xs].reverse()), y: up.concat([...lo].reverse()),
      fill:'toself', fillcolor:'rgba(' + RGB[name] + ',0.15)', line:{color:'transparent'},
      hoverinfo:'skip', showlegend:false});
    const cfg = C[name];
    out.push({x: xs, y: m, mode:'lines', line:{color:COL[name], width:2.2},
      name: name + ' (det=' + cfg.determinism + ', RoI=' + cfg.roi + ')'});
  }
  return out;
}

function show(stat) {
  ['pop','welfare','aggr','weap'].forEach(v =>
    document.getElementById('b-'+v).classList.toggle('active', v===stat));
  const layout = {title: TITLE[stat] + ' (mean \\u00b1 1 SD over ' + N + ' seeds)',
    xaxis:{title:'step'}, yaxis:{title: YLAB[stat]}, margin:{t:44}, legend:{orientation:'h'}};
  if (stat === 'aggr' || stat === 'weap') layout.yaxis.range = [0, 1];
  Plotly.newPlot('chart', traces(stat), layout, {displayModeBar:false, responsive:true});
  const notes = {
    pop: 'Collapse (low RoI) dies out; peaceful and arms-race environments sustain a population.',
    welfare: 'Peace compounds: the disarming population accumulates far more total resources.',
    aggr: 'Deterministic wars select for high aggression; low determinism + high RoI select for peace.',
    weap: 'When strength reliably decides fights, budgets flow into weapons instead of production.'
  };
  document.getElementById('note').textContent = notes[stat];
}
show('pop');
</script>
</body></html>
"""

html = HTML.replace("__DATA_JSON__", json.dumps(DATA))
with open(OUT_PATH, "w") as f:
    f.write(html)
print("Wrote", OUT_PATH)
