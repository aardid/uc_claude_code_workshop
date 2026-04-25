"""Generate a self-contained interactive bridge risk explorer HTML app."""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent
JSON_PATH = OUTPUT_DIR / "bridge_data.json"
HTML_PATH = OUTPUT_DIR / "bridge_risk_explorer.html"


def main():
    with open(JSON_PATH, "r") as f:
        bridge_json = f.read()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Texas Bridge Risk Explorer</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Calibri, sans-serif; background: #1a1a2e; color: #e0e0e0; display: flex; height: 100vh; overflow: hidden; }}

  #sidebar {{
    width: 340px; min-width: 340px; background: #16213e; padding: 20px;
    display: flex; flex-direction: column; gap: 16px; overflow-y: auto;
    border-right: 2px solid #0f3460;
  }}
  #sidebar h1 {{ font-size: 20px; color: #e94560; margin-bottom: 4px; }}
  #sidebar h2 {{ font-size: 14px; color: #8899aa; font-weight: 400; margin-bottom: 8px; }}

  .section {{ background: #1a1a3e; border-radius: 8px; padding: 14px; }}
  .section h3 {{ font-size: 13px; color: #e94560; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}

  .slider-group {{ margin-bottom: 12px; }}
  .slider-group label {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; color: #ccc; }}
  .slider-group label span {{ color: #e94560; font-weight: 700; }}
  input[type=range] {{
    width: 100%; height: 6px; -webkit-appearance: none; appearance: none;
    background: #0f3460; border-radius: 3px; outline: none;
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
    background: #e94560; cursor: pointer;
  }}

  .tier-filters {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .tier-btn {{
    padding: 8px; border: 2px solid; border-radius: 6px; cursor: pointer;
    font-size: 12px; font-weight: 700; text-align: center; transition: 0.2s;
    background: transparent;
  }}
  .tier-btn.active {{ color: #fff !important; }}
  .tier-btn.low {{ border-color: #2ecc71; color: #2ecc71; }}
  .tier-btn.low.active {{ background: #2ecc71; }}
  .tier-btn.moderate {{ border-color: #f1c40f; color: #f1c40f; }}
  .tier-btn.moderate.active {{ background: #f1c40f; color: #1a1a2e !important; }}
  .tier-btn.high {{ border-color: #e67e22; color: #e67e22; }}
  .tier-btn.high.active {{ background: #e67e22; }}
  .tier-btn.critical {{ border-color: #e74c3c; color: #e74c3c; }}
  .tier-btn.critical.active {{ background: #e74c3c; }}

  #update-btn {{
    width: 100%; padding: 12px; background: #e94560; color: #fff;
    border: none; border-radius: 8px; font-size: 15px; font-weight: 700;
    cursor: pointer; letter-spacing: 1px; transition: 0.2s;
  }}
  #update-btn:hover {{ background: #c73650; }}

  .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .stat-card {{
    background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
    padding: 10px; text-align: center;
  }}
  .stat-card .val {{ font-size: 22px; font-weight: 700; color: #e94560; }}
  .stat-card .lbl {{ font-size: 10px; color: #8899aa; text-transform: uppercase; letter-spacing: 0.5px; }}

  .tier-stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 4px; margin-top: 8px; }}
  .tier-stat {{ text-align: center; padding: 6px 2px; border-radius: 4px; }}
  .tier-stat .tval {{ font-size: 14px; font-weight: 700; }}
  .tier-stat .tlbl {{ font-size: 9px; }}
  .tier-stat.ts-low {{ background: rgba(46,204,113,0.15); color: #2ecc71; }}
  .tier-stat.ts-mod {{ background: rgba(241,196,15,0.15); color: #f1c40f; }}
  .tier-stat.ts-high {{ background: rgba(230,126,34,0.15); color: #e67e22; }}
  .tier-stat.ts-crit {{ background: rgba(231,76,60,0.15); color: #e74c3c; }}

  #map-container {{ flex: 1; position: relative; }}
  #map {{ width: 100%; height: 100%; }}

  .formula-box {{
    background: #0f3460; border-radius: 6px; padding: 10px;
    font-family: 'Consolas', monospace; font-size: 12px; color: #7fbbf0;
    line-height: 1.6; text-align: center;
  }}
</style>
</head>
<body>

<div id="sidebar">
  <div>
    <h1>Bridge Risk Explorer</h1>
    <h2>Texas NBI 2025 - Interactive Analysis</h2>
  </div>

  <div class="section">
    <h3>Risk Weights</h3>
    <div class="slider-group">
      <label>Condition <span id="w-cond-val">0.30</span></label>
      <input type="range" id="w-cond" min="0" max="100" value="30">
    </div>
    <div class="slider-group">
      <label>Age <span id="w-age-val">0.30</span></label>
      <input type="range" id="w-age" min="0" max="100" value="30">
    </div>
    <div class="slider-group">
      <label>Traffic <span id="w-traffic-val">0.40</span></label>
      <input type="range" id="w-traffic" min="0" max="100" value="40">
    </div>
    <div class="formula-box">
      risk = w<sub>c</sub> * condition + w<sub>a</sub> * age + w<sub>t</sub> * traffic
    </div>
  </div>

  <div class="section">
    <h3>Tier Filters</h3>
    <div class="tier-filters">
      <div class="tier-btn low active" data-tier="low" onclick="toggleTier(this)">Low &lt;0.25</div>
      <div class="tier-btn moderate active" data-tier="moderate" onclick="toggleTier(this)">Moderate</div>
      <div class="tier-btn high active" data-tier="high" onclick="toggleTier(this)">High</div>
      <div class="tier-btn critical active" data-tier="critical" onclick="toggleTier(this)">Critical</div>
    </div>
  </div>

  <button id="update-btn" onclick="updateMap()">Update Map</button>

  <div class="section">
    <h3>Live Statistics</h3>
    <div class="stats-grid">
      <div class="stat-card"><div class="val" id="stat-total">-</div><div class="lbl">Bridges Shown</div></div>
      <div class="stat-card"><div class="val" id="stat-mean">-</div><div class="lbl">Mean Risk</div></div>
      <div class="stat-card"><div class="val" id="stat-median">-</div><div class="lbl">Median Risk</div></div>
      <div class="stat-card"><div class="val" id="stat-critical">-</div><div class="lbl">Critical</div></div>
    </div>
    <div class="tier-stats">
      <div class="tier-stat ts-low"><div class="tval" id="ts-low">-</div><div class="tlbl">Low</div></div>
      <div class="tier-stat ts-mod"><div class="tval" id="ts-mod">-</div><div class="tlbl">Mod</div></div>
      <div class="tier-stat ts-high"><div class="tval" id="ts-high">-</div><div class="tlbl">High</div></div>
      <div class="tier-stat ts-crit"><div class="tval" id="ts-crit">-</div><div class="tlbl">Crit</div></div>
    </div>
  </div>
</div>

<div id="map-container">
  <div id="map"></div>
</div>

<script>
const RAW = {bridge_json};

const tiers = {{ low: true, moderate: true, high: true, critical: true }};

function getWeights() {{
  const wc = parseInt(document.getElementById('w-cond').value);
  const wa = parseInt(document.getElementById('w-age').value);
  const wt = parseInt(document.getElementById('w-traffic').value);
  const total = wc + wa + wt || 1;
  return {{ wc: wc / total, wa: wa / total, wt: wt / total }};
}}

function updateSliderLabels() {{
  const w = getWeights();
  document.getElementById('w-cond-val').textContent = w.wc.toFixed(2);
  document.getElementById('w-age-val').textContent = w.wa.toFixed(2);
  document.getElementById('w-traffic-val').textContent = w.wt.toFixed(2);
}}

document.querySelectorAll('input[type=range]').forEach(s => s.addEventListener('input', updateSliderLabels));

function toggleTier(el) {{
  el.classList.toggle('active');
  tiers[el.dataset.tier] = el.classList.contains('active');
}}

function getTier(score) {{
  if (score < 0.25) return 'low';
  if (score < 0.50) return 'moderate';
  if (score < 0.75) return 'high';
  return 'critical';
}}

function updateMap() {{
  const w = getWeights();
  const lons = [], lats = [], scores = [], texts = [];
  const tierCounts = {{ low: 0, moderate: 0, high: 0, critical: 0 }};
  const allScores = [];

  for (let i = 0; i < RAW.length; i++) {{
    const r = RAW[i];
    const score = w.wc * r[2] + w.wa * r[3] + w.wt * r[4];
    const tier = getTier(score);
    tierCounts[tier]++;
    if (!tiers[tier]) continue;

    lons.push(r[0]);
    lats.push(r[1]);
    scores.push(score);
    allScores.push(score);
    texts.push(
      'Loc: ' + r[1].toFixed(3) + ', ' + r[0].toFixed(3) +
      '<br>Condition: ' + r[2].toFixed(3) +
      '<br>Age: ' + r[3].toFixed(3) +
      '<br>Traffic: ' + r[4].toFixed(3) +
      '<br><b>Risk: ' + score.toFixed(3) + ' (' + tier.charAt(0).toUpperCase() + tier.slice(1) + ')</b>'
    );
  }}

  const trace = {{
    type: 'scattermapbox',
    lon: lons,
    lat: lats,
    mode: 'markers',
    marker: {{
      size: 4,
      color: scores,
      colorscale: [[0, '#2ecc71'], [0.25, '#a3e048'], [0.5, '#f1c40f'], [0.75, '#e67e22'], [1, '#e74c3c']],
      cmin: 0, cmax: 1,
      colorbar: {{
        title: {{ text: 'Risk Score', font: {{ color: '#ccc' }} }},
        tickfont: {{ color: '#ccc' }},
        bgcolor: 'rgba(22,33,62,0.8)',
        bordercolor: '#0f3460',
        len: 0.5, y: 0.3,
      }},
      opacity: 0.7,
    }},
    text: texts,
    hoverinfo: 'text',
  }};

  const layout = {{
    mapbox: {{
      style: 'carto-positron',
      center: {{ lat: 31.5, lon: -99.5 }},
      zoom: 5.2,
    }},
    margin: {{ l: 0, r: 0, t: 0, b: 0 }},
    paper_bgcolor: '#1a1a2e',
    showlegend: false,
  }};

  Plotly.react('map', [trace], layout, {{ responsive: true }});

  // Update stats
  allScores.sort((a, b) => a - b);
  const n = allScores.length;
  const mean = n > 0 ? allScores.reduce((a, b) => a + b, 0) / n : 0;
  const median = n > 0 ? (n % 2 === 0 ? (allScores[n/2-1] + allScores[n/2]) / 2 : allScores[Math.floor(n/2)]) : 0;

  document.getElementById('stat-total').textContent = n.toLocaleString();
  document.getElementById('stat-mean').textContent = mean.toFixed(3);
  document.getElementById('stat-median').textContent = median.toFixed(3);
  document.getElementById('stat-critical').textContent = tierCounts.critical.toLocaleString();

  document.getElementById('ts-low').textContent = tierCounts.low.toLocaleString();
  document.getElementById('ts-mod').textContent = tierCounts.moderate.toLocaleString();
  document.getElementById('ts-high').textContent = tierCounts.high.toLocaleString();
  document.getElementById('ts-crit').textContent = tierCounts.critical.toLocaleString();
}}

updateMap();
</script>
</body>
</html>"""

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = HTML_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved interactive explorer: {HTML_PATH}")
    print(f"File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
