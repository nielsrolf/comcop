"""Build an interactive widget for the multi-seed War vs Peace experiment.

Reads assets/war_peace_multiseed.json (produced by
`python3 war_peace_multiseed_experiment.py --json`) and inlines it into a
self-contained Plotly HTML page. The reader toggles

  * which quantity to view (population, welfare, aggression, weapon budget), and
  * which pairing regime (location/proximity vs well-mixed/random),

and sees the mean +/-1 SD band across seeds for three contrasting environments
(peaceful / arms race / collapse), making the average dynamics -- not a single
noisy seed -- explicit, and the effect of spatial structure directly comparable.
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
  .sep { width:1px; height:22px; background:#ddd; margin:0 4px; }
  button { border:1px solid #ccc; background:#f6f6f6; border-radius:6px; padding:6px 12px;
            cursor:pointer; font-size:13px; }
  button.active { background:#1f77b4; color:#fff; border-color:#1f77b4; }
  button.pair.active { background:#6a3d9a; border-color:#6a3d9a; }
  #note { font-size:12px; color:#555; margin:6px 2px; }
  #chart { width:100%; height:430px; }
</style></head>
<body>
<div class="controls">
  <button id="b-pop" class="active" onclick="setStat('pop')">Population</button>
  <button id="b-welfare" onclick="setStat('welfare')">Total welfare</button>
  <button id="b-aggr" onclick="setStat('aggr')">Mean aggression</button>
  <button id="b-weap" onclick="setStat('weap')">Weapon budget</button>
  <span class="sep"></span>
  <button id="p-proximity" class="pair active" onclick="setPair('proximity')">Location (proximity)</button>
  <button id="p-random" class="pair" onclick="setPair('random')">Well-mixed (random)</button>
</div>
<div id="chart"></div>
<div id="note"></div>
<script>
const DATA = __DATA_JSON__;
const PAIR = DATA.pairings;
const COL = {'peaceful':'#2ca02c', 'arms race':'#d62728', 'collapse':'#7f7f7f'};
const RGB = {'peaceful':'44,160,44', 'arms race':'214,39,40', 'collapse':'127,127,127'};
const STEPS = DATA.n_steps, N = DATA.n_seeds;
const xs = Array.from({length: STEPS}, (_, i) => i);
const YLAB = {pop:'agents', welfare:'sum of resources', aggr:'P(attack)', weap:'weapon fraction'};
const TITLE = {pop:'Population', welfare:'Total welfare',
               aggr:'Mean evolved aggression', weap:'Mean weapon budget'};
let stat='pop', pairing='proximity';

function traces() {
  const C = PAIR[pairing].conditions;
  const out = [];
  for (const name of Object.keys(C)) {
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

function draw() {
  ['pop','welfare','aggr','weap'].forEach(v =>
    document.getElementById('b-'+v).classList.toggle('active', v===stat));
  ['proximity','random'].forEach(v =>
    document.getElementById('p-'+v).classList.toggle('active', v===pairing));
  const tag = pairing==='proximity' ? 'location / proximity pairing' : 'well-mixed / random pairing';
  const layout = {title: TITLE[stat] + ' — ' + tag + ' (mean \\u00b1 1 SD over ' + N + ' seeds)',
    xaxis:{title:'step'}, yaxis:{title: YLAB[stat]}, margin:{t:44}, legend:{orientation:'h'}};
  if (stat === 'aggr' || stat === 'weap') layout.yaxis.range = [0, 1];
  Plotly.newPlot('chart', traces(), layout, {displayModeBar:false, responsive:true});
  const notes = {
    pop: 'Collapse (low RoI) dies out under both pairings; the arms-race world survives far better with location, where armed lineages cluster.',
    welfare: 'Peace compounds. Location lets a deterministic arms race sustain more agents but at lower per-capita welfare than the well-mixed peace.',
    aggr: 'Aggression stays modest everywhere; the decisive adaptation is weapon investment, not the attack rate.',
    weap: 'The key contrast: under location the arms-race world ratchets weapon budget up to ~0.37, vs ~0.11 well-mixed — repeatedly meeting the same neighbours makes out-arming them reliably pay.'
  };
  document.getElementById('note').textContent = notes[stat];
}
function setStat(s){ stat=s; draw(); }
function setPair(p){ pairing=p; draw(); }
draw();
</script>
</body></html>
"""

html = HTML.replace("__DATA_JSON__", json.dumps(DATA))
with open(OUT_PATH, "w") as f:
    f.write(html)
print("Wrote", OUT_PATH)
