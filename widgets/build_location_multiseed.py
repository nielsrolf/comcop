"""Build an interactive widget for the location experiment averaged over seeds.

Reads assets/location_cooperation_multiseed.json (produced by
baseline_location_experiment.py) and emits a self-contained HTML page that
plots every per-seed rollout as a faint line plus the mean +/- 1 SD band, for
both pairing rules. A control lets the viewer toggle individual rollouts vs the
averaged band, and switch between CooperateBot and DefectBot counts.
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "assets", "location_cooperation_multiseed.json")
OUT = os.path.join(HERE, "assets", "location_multiseed.html")

with open(DATA) as f:
    data = json.load(f)

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body{font-family:system-ui,sans-serif;margin:0;padding:12px;color:#222}
  .controls{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:8px;font-size:14px}
  select,label{font-size:14px}
  #plot{width:100%;height:460px}
</style></head>
<body>
<div class="controls">
  <label>Strategy:
    <select id="strat"><option value="coop">CooperateBot</option><option value="defect">DefectBot</option></select>
  </label>
  <label><input type="checkbox" id="showruns" checked> Show individual rollouts</label>
  <label><input type="checkbox" id="showband" checked> Show mean &plusmn; 1 SD</label>
  <span id="caption" style="color:#555"></span>
</div>
<div id="plot"></div>
<script>
const DATA = __DATA__;
const NSEEDS = DATA.seeds.length;
const COLORS = {coop:"#2ca02c", defect:"#d62728"};

function mean(cols){return cols.map(c=>c.reduce((a,b)=>a+b,0)/c.length);}
function std(cols,m){return cols.map((c,i)=>Math.sqrt(c.reduce((a,b)=>a+(b-m[i])**2,0)/c.length));}
// transpose runs (nseeds x nsteps) -> per-step columns
function cols(runs){const T=runs[0].length;const out=[];for(let t=0;t<T;t++){out.push(runs.map(r=>r[t]));}return out;}

function panelTraces(runs,color,xshift,showruns,showband){
  const T=runs[0].length; const x=[...Array(T).keys()];
  const c=cols(runs); const m=mean(c); const s=std(c,m);
  const tr=[];
  if(showruns){
    runs.forEach((r,i)=>tr.push({x,y:r,mode:"lines",line:{color:color,width:1},opacity:0.18,
      hoverinfo:"skip",showlegend:false,xaxis:xshift,yaxis:xshift.replace("x","y")}));
  }
  if(showband){
    tr.push({x:x.concat([...x].reverse()),
      y:m.map((v,i)=>v+s[i]).concat(m.map((v,i)=>v-s[i]).reverse()),
      fill:"toself",fillcolor:color,opacity:0.2,line:{width:0},hoverinfo:"skip",
      showlegend:false,xaxis:xshift,yaxis:xshift.replace("x","y")});
  }
  tr.push({x,y:m,mode:"lines",line:{color:color,width:3},name:"mean",
    hovertemplate:"step %{x}: %{y:.1f}<extra></extra>",showlegend:false,
    xaxis:xshift,yaxis:xshift.replace("x","y")});
  return tr;
}

function draw(){
  const strat=document.getElementById("strat").value;
  const showruns=document.getElementById("showruns").checked;
  const showband=document.getElementById("showband").checked;
  const color=COLORS[strat];
  let traces=[];
  traces=traces.concat(panelTraces(DATA.spatial[strat],color,"x",showruns,showband));
  traces=traces.concat(panelTraces(DATA.mixed[strat],color,"x2",showruns,showband));
  const layout={
    grid:{rows:1,columns:2,pattern:"independent"},
    margin:{t:40,r:10,b:45,l:45},
    annotations:[
      {text:"Spatial pairing (location matters)",x:0.22,y:1.08,xref:"paper",yref:"paper",showarrow:false,font:{size:13}},
      {text:"Well-mixed pairing (no location)",x:0.80,y:1.08,xref:"paper",yref:"paper",showarrow:false,font:{size:13}},
    ],
    xaxis:{title:"Step"}, xaxis2:{title:"Step"},
    yaxis:{title:strat==="coop"?"CooperateBot count":"DefectBot count"}, yaxis2:{matches:"y"},
  };
  Plotly.react("plot",traces,layout,{responsive:true,displayModeBar:false});
  document.getElementById("caption").textContent=`mean of ${NSEEDS} seeds`;
}
["strat","showruns","showband"].forEach(id=>document.getElementById(id).addEventListener("change",draw));
draw();
</script>
</body></html>
"""

html = HTML.replace("__DATA__", json.dumps(data))
with open(OUT, "w") as f:
    f.write(html)
print("Wrote", OUT, os.path.getsize(OUT), "bytes")
