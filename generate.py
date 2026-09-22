#!/usr/bin/env python3
"""Generate index.html from data/wvs-synthetic.csv — self-contained WVS analysis."""

import csv
import json
import math
import os
import random
from string import Template

SEED = 42
CSV_PATH = os.path.join(os.path.dirname(__file__) or ".", "data", "wvs-synthetic.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__) or ".", "index.html")

NUMERIC_COLS = [
    "age",
    "life_satisfaction",
    "freedom_of_choice",
    "emancipative_values",
    "importance_of_god",
    "financial_satisfaction",
    "secular_values",
]
CATEGORICAL_COLS = [
    "country",
    "urban_rural",
    "income_level",
    "sex",
    "marital_status",
    "education",
    "trust_people",
]
ALL_COLS = CATEGORICAL_COLS + NUMERIC_COLS  # display order (excludes respondent_id)

COUNTRIES = ["China", "India", "Kazakhstan", "Singapore", "Turkey"]
COLORS = {
    "China": "#E69F00",
    "Singapore": "#D55E00",
    "Turkey": "#CC79A7",
    "India": "#0072B2",
    "Kazakhstan": "#009E73",
}
MARKERS = {
    "China": "circle",
    "Singapore": "rectRot",
    "Turkey": "triangle",
    "India": "rect",
    "Kazakhstan": "star",
}

# ---------------------------------------------------------------------------
# 1. Read & clean
# ---------------------------------------------------------------------------

def read_csv():
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def column_metadata(rows):
    meta = []
    for col in ALL_COLS:
        non_empty = sum(1 for r in rows if r.get(col, "").strip() != "")
        dtype = "Numeric" if col in NUMERIC_COLS else "Categorical"
        meta.append({"name": col, "type": dtype, "non_empty": non_empty})
    return meta


def check_duplicates(rows):
    ids = [r["respondent_id"] for r in rows]
    return len(ids) - len(set(ids))


def clean(rows):
    all_fields = CATEGORICAL_COLS + NUMERIC_COLS + ["respondent_id"]
    clean_rows = []
    for r in rows:
        if any(r.get(c, "").strip() == "" for c in all_fields):
            continue
        row = dict(r)
        for c in NUMERIC_COLS:
            row[c] = float(row[c])
        clean_rows.append(row)
    return clean_rows

# ---------------------------------------------------------------------------
# 2. Compute statistics
# ---------------------------------------------------------------------------

def mean(vals):
    return sum(vals) / len(vals) if vals else 0


def country_groups(rows):
    groups = {c: [] for c in COUNTRIES}
    for r in rows:
        if r["country"] in groups:
            groups[r["country"]].append(r)
    return groups


def cultural_map(groups):
    data = []
    for c in COUNTRIES:
        rs = groups[c]
        data.append({
            "country": c,
            "x": round(mean([r["secular_values"] for r in rs]), 4),
            "y": round(mean([r["emancipative_values"] for r in rs]), 4),
        })
    return data


def radar_data(groups):
    labels = [
        "Life Satisfaction",
        "Trust (share)",
        "Importance of God",
        "Emancipative Values",
        "Secular Values",
        "Financial Satisfaction",
    ]
    datasets = {}
    for c in COUNTRIES:
        rs = groups[c]
        n = len(rs)
        life = round(mean([r["life_satisfaction"] for r in rs]) / 10, 4)
        trust = round(sum(1 for r in rs if r["trust_people"] == "Trusted") / n, 4)
        god = round(mean([r["importance_of_god"] for r in rs]) / 10, 4)
        eman = round(mean([r["emancipative_values"] for r in rs]), 4)
        sec = round(mean([r["secular_values"] for r in rs]), 4)
        fin = round(mean([r["financial_satisfaction"] for r in rs]) / 10, 4)
        datasets[c] = [life, trust, god, eman, sec, fin]
    return labels, datasets


def individual_scatter(groups):
    random.seed(SEED)
    china = groups["China"]
    india = groups["India"]
    china_sample = random.sample(china, min(300, len(china)))
    india_sample = random.sample(india, min(300, len(india)))
    to_pts = lambda rs: [
        {"x": round(r["secular_values"], 4), "y": round(r["emancipative_values"], 4)}
        for r in rs
    ]
    china_avg = {
        "x": round(mean([r["secular_values"] for r in china]), 4),
        "y": round(mean([r["emancipative_values"] for r in china]), 4),
    }
    india_avg = {
        "x": round(mean([r["secular_values"] for r in india]), 4),
        "y": round(mean([r["emancipative_values"] for r in india]), 4),
    }
    return to_pts(china_sample), to_pts(india_sample), china_avg, india_avg


def heatmap_data(groups):
    sg = groups["Singapore"]
    grid = [[0] * 10 for _ in range(10)]  # grid[life-1][fin-1]
    for r in sg:
        li = int(r["life_satisfaction"])
        fi = int(r["financial_satisfaction"])
        if 1 <= li <= 10 and 1 <= fi <= 10:
            grid[li - 1][fi - 1] += 1
    max_count = max(max(row) for row in grid)
    return grid, max_count


def heatmap_html(grid, max_count):
    parts = []
    parts.append('<div class="heatmap-wrap">')
    parts.append('<div class="heatmap-ylabel">Life Satisfaction &rarr;</div>')
    parts.append('<div class="heatmap-grid">')
    # corner
    parts.append('<div class="hm-corner"></div>')
    # column headers
    for fi in range(1, 11):
        parts.append(f'<div class="hm-col-hdr">{fi}</div>')
    # rows from 10 down to 1
    for li in range(10, 0, -1):
        parts.append(f'<div class="hm-row-hdr">{li}</div>')
        for fi in range(1, 11):
            count = grid[li - 1][fi - 1]
            if max_count > 0:
                intensity = count / max_count
            else:
                intensity = 0
            # teal scale: hsl(174, 62%, 95%) to hsl(174, 62%, 25%)
            lightness = 95 - intensity * 70
            bg = f"hsl(174, 62%, {lightness:.0f}%)"
            text_color = "#fff" if lightness < 50 else "#1a1a1a"
            title = f"Life Sat: {li}, Financial Sat: {fi}, Count: {count}"
            parts.append(
                f'<div class="hm-cell" style="background:{bg};color:{text_color}" title="{title}">'
                f'{count if count > 0 else ""}</div>'
            )
    parts.append("</div>")  # grid
    parts.append('<div class="heatmap-xlabel">Financial Satisfaction &rarr;</div>')
    parts.append("</div>")  # wrap
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# 3. Build HTML
# ---------------------------------------------------------------------------

def build_summary_table(col_meta, total_rows, dup_count, removed_count, clean_count):
    rows_html = ""
    for m in col_meta:
        rows_html += (
            f"<tr><td><code>{m['name']}</code></td>"
            f"<td>{m['type']}</td>"
            f"<td>{m['non_empty']:,}</td></tr>\n"
        )
    return f"""
<h2>Dataset Overview</h2>
<p>Total rows (before cleaning): <strong>{total_rows:,}</strong>. Columns shown below exclude
<code>respondent_id</code> (identifier only).</p>
<div class="table-wrap">
<table>
  <thead><tr><th>Column</th><th>Data Type</th><th>Non-Empty Observations</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
<p><strong>Duplicate check:</strong> {dup_count} duplicate respondent IDs found.</p>
<p><strong>Missing values:</strong> {removed_count:,} rows contained at least one blank cell and were
removed. Analysis uses the remaining <strong>{clean_count:,}</strong> complete rows.</p>
"""


HTML_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exploratory Analysis — Simulated World Values Survey Data</title>
<style>
:root {
  --china: #E69F00; --sg: #D55E00; --turkey: #CC79A7;
  --india: #0072B2; --kz: #009E73;
  --bg: #ffffff; --fg: #1a1a1a; --muted: #555;
  --card-bg: #f7f7f7; --border: #ddd;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#1a1a1a; --fg:#e8e8e8; --muted:#aaa; --card-bg:#262626; --border:#444; }
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0; padding: 1rem; font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.6;
}
.container { max-width: 900px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
h2 { font-size: 1.25rem; margin-top: 2.5rem; border-bottom: 2px solid var(--border); padding-bottom: 0.3rem; }
p { max-width: 72ch; }
a { color: var(--india); }
.intro-countries { display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; padding: 0; margin: 0.5rem 0; }
.intro-countries li {
  padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.9rem; font-weight: 600; color: #fff;
}
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border); }
th { background: var(--card-bg); }
code { font-size: 0.85em; background: var(--card-bg); padding: 0.1em 0.3em; border-radius: 3px; }
.chart-section { margin-top: 2rem; }
.chart-wrap { position: relative; width: 100%; max-width: 700px; margin: 0 auto; }
.takeaway {
  background: var(--card-bg); border-left: 4px solid var(--india);
  padding: 0.75rem 1rem; margin-top: 0.75rem; border-radius: 0 4px 4px 0; font-size: 0.95rem;
}
/* Heatmap */
.heatmap-wrap { max-width: 560px; margin: 0 auto; text-align: center; }
.heatmap-ylabel {
  writing-mode: vertical-lr; transform: rotate(180deg);
  font-weight: 600; font-size: 0.85rem; position: absolute; left: -1.8rem; top: 50%;
  transform: rotate(180deg) translateY(50%);
}
.heatmap-wrap { position: relative; padding-left: 2.2rem; }
.heatmap-grid {
  display: grid; grid-template-columns: 2rem repeat(10, 1fr); gap: 2px;
}
.hm-corner { }
.hm-col-hdr, .hm-row-hdr { font-weight: 600; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; }
.hm-cell {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; border-radius: 2px; cursor: default;
}
.heatmap-xlabel { font-weight: 600; font-size: 0.85rem; margin-top: 0.3rem; }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--muted); }
@media (max-width: 600px) {
  body { padding: 0.5rem; }
  h1 { font-size: 1.3rem; }
  h2 { font-size: 1.1rem; }
  .chart-wrap { max-width: 100%; }
  .heatmap-grid { gap: 1px; }
  .hm-cell { font-size: 0.6rem; }
}
</style>
</head>
<body>
<div class="container">

<h1>Exploratory Analysis of Simulated World Values Survey Data</h1>
<p>This page presents an exploratory analysis of <strong>synthetic (simulated) data</strong>
fabricated to resemble distributions and relationships found in the
<a href="https://www.worldvaluessurvey.org/" target="_blank" rel="noopener">World Values Survey, Wave 7</a>
(Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano, J.,
Lagos, M., Norris, P., Ponarin, E., &amp; Puranen, B. (Eds.), 2022).
<strong>No real respondent data is used.</strong> Any patterns or findings shown here are
<em>illustrative only</em> and should not be cited as real-world results.</p>
<p>Respondents are drawn from five countries spanning different parts of Asia:</p>
<ul class="intro-countries">
  <li style="background:var(--china)">China</li>
  <li style="background:var(--india)">India</li>
  <li style="background:var(--kz)">Kazakhstan</li>
  <li style="background:var(--sg)">Singapore</li>
  <li style="background:var(--turkey)">Turkey</li>
</ul>

$summary_table

<!-- Chart 1 -->
<div class="chart-section">
<h2>Cultural Map — Emancipative vs Secular Values</h2>
<p>Average position of each country on the classic Inglehart–Welzel cultural map.</p>
<div class="chart-wrap"><canvas id="culturalMap"></canvas></div>
<div class="takeaway">$takeaway1</div>
</div>

<!-- Chart 2 -->
<div class="chart-section">
<h2>Value Fingerprints — Radar Chart</h2>
<p>Six normalised measures (0–1 scale) compared across all five countries.</p>
<div class="chart-wrap"><canvas id="radarChart"></canvas></div>
<div class="takeaway">$takeaway2</div>
</div>

<!-- Chart 3 -->
<div class="chart-section">
<h2>Individual Values — China vs India</h2>
<p>A random sample of ~300 respondents per country plotted on secular vs emancipative values.
Larger outlined markers show each country's overall average.</p>
<div class="chart-wrap"><canvas id="indivScatter"></canvas></div>
<div class="takeaway">$takeaway3</div>
</div>

<!-- Chart 4 -->
<div class="chart-section">
<h2>Life vs Financial Satisfaction — Singapore</h2>
<p>Heatmap of Singapore respondents: each cell shows the count of people reporting
that combination of life satisfaction (rows) and financial satisfaction (columns).
Darker shading indicates more respondents.</p>
$heatmap_html
<div class="takeaway">$takeaway4</div>
</div>

<footer>
Generated from synthetic data by <code>generate.py</code>.
Modelled on the World Values Survey, Wave 7
(<a href="https://www.worldvaluessurvey.org/" target="_blank" rel="noopener">worldvaluessurvey.org</a>).
</footer>
</div>

<!-- Data -->
<script>
const CULTURAL_MAP = $cultural_map_json;
const RADAR_LABELS = $radar_labels_json;
const RADAR_DATASETS = $radar_datasets_json;
const CHINA_PTS = $china_pts_json;
const INDIA_PTS = $india_pts_json;
const CHINA_AVG = $china_avg_json;
const INDIA_AVG = $india_avg_json;
const COLORS = $colors_json;
const MARKERS = $markers_json;
const COUNTRIES = $countries_json;
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script>
(function() {
  "use strict";

  function hexToRgba(hex, a) {
    var r = parseInt(hex.slice(1,3),16),
        g = parseInt(hex.slice(3,5),16),
        b = parseInt(hex.slice(5,7),16);
    return "rgba("+r+","+g+","+b+","+a+")";
  }

  /* ---- Chart 1: Cultural Map ---- */
  var cmDatasets = COUNTRIES.map(function(c) {
    var pt = CULTURAL_MAP.find(function(d){ return d.country === c; });
    return {
      label: c,
      data: [{x: pt.x, y: pt.y}],
      backgroundColor: COLORS[c],
      borderColor: COLORS[c],
      pointStyle: MARKERS[c],
      pointRadius: 12,
      pointHoverRadius: 14,
      borderWidth: 2
    };
  });
  new Chart(document.getElementById("culturalMap"), {
    type: "scatter",
    data: {datasets: cmDatasets},
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return ctx.dataset.label + ": secular " + ctx.parsed.x.toFixed(2) +
                     ", emancipative " + ctx.parsed.y.toFixed(2);
            }
          }
        },
        legend: {display: true, position: "bottom",
          labels: {usePointStyle: true, padding: 16, font:{size:13}}
        }
      },
      scales: {
        x: {title:{display:true, text:"Secular Values (avg)", font:{size:13}},
            ticks:{callback: function(v){return v.toFixed(2);}}},
        y: {title:{display:true, text:"Emancipative Values (avg)", font:{size:13}},
            ticks:{callback: function(v){return v.toFixed(2);}}}
      }
    },
    plugins: [{
      afterDraw: function(chart) {
        var ctx = chart.ctx;
        ctx.save();
        ctx.font = "bold 12px system-ui, sans-serif";
        ctx.textBaseline = "bottom";
        chart.data.datasets.forEach(function(ds, i) {
          var meta = chart.getDatasetMeta(i);
          if (meta.data.length) {
            var pt = meta.data[0];
            ctx.fillStyle = ds.borderColor;
            ctx.fillText(ds.label, pt.x + 14, pt.y - 6);
          }
        });
        ctx.restore();
      }
    }]
  });

  /* ---- Chart 2: Radar ---- */
  var radarDS = COUNTRIES.map(function(c) {
    return {
      label: c,
      data: RADAR_DATASETS[c],
      borderColor: COLORS[c],
      backgroundColor: hexToRgba(COLORS[c], 0.08),
      pointBackgroundColor: COLORS[c],
      pointStyle: MARKERS[c],
      pointRadius: 5,
      borderWidth: 2,
      fill: true
    };
  });
  new Chart(document.getElementById("radarChart"), {
    type: "radar",
    data: {labels: RADAR_LABELS, datasets: radarDS},
    options: {
      responsive: true,
      scales: {
        r: {min:0, max:1, ticks:{stepSize:0.2, backdropColor:"transparent",
            callback: function(v){return v.toFixed(1);}},
            pointLabels:{font:{size:12}}}
      },
      plugins: {
        legend: {position:"bottom", labels:{usePointStyle:true, padding:16, font:{size:13}}},
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return ctx.dataset.label + ": " + ctx.parsed.r.toFixed(2);
            }
          }
        }
      }
    }
  });

  /* ---- Chart 3: Individual Scatter ---- */
  new Chart(document.getElementById("indivScatter"), {
    type: "scatter",
    data: {
      datasets: [
        {label:"China (individuals)", data:CHINA_PTS,
         backgroundColor: hexToRgba(COLORS["China"], 0.35),
         borderColor: "transparent",
         pointStyle: MARKERS["China"], pointRadius:3, pointHoverRadius:5, borderWidth:0},
        {label:"India (individuals)", data:INDIA_PTS,
         backgroundColor: hexToRgba(COLORS["India"], 0.35),
         borderColor: "transparent",
         pointStyle: MARKERS["India"], pointRadius:3, pointHoverRadius:5, borderWidth:0},
        {label:"China (average)", data:[CHINA_AVG],
         backgroundColor: COLORS["China"],
         borderColor: "#000", borderWidth:3,
         pointStyle: MARKERS["China"], pointRadius:12, pointHoverRadius:14},
        {label:"India (average)", data:[INDIA_AVG],
         backgroundColor: COLORS["India"],
         borderColor: "#000", borderWidth:3,
         pointStyle: MARKERS["India"], pointRadius:12, pointHoverRadius:14}
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {position:"bottom", labels:{usePointStyle:true, padding:16, font:{size:13}}},
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return ctx.dataset.label + ": secular " + ctx.parsed.x.toFixed(2) +
                     ", emancipative " + ctx.parsed.y.toFixed(2);
            }
          }
        }
      },
      scales: {
        x: {title:{display:true, text:"Secular Values", font:{size:13}},
            ticks:{callback: function(v){return v.toFixed(1);}}},
        y: {title:{display:true, text:"Emancipative Values", font:{size:13}},
            ticks:{callback: function(v){return v.toFixed(1);}}}
      }
    }
  });

})();
</script>
</body>
</html>
""")


def generate_takeaways(cm_data, radar_labels, radar_ds, china_avg, india_avg, grid, max_count):
    # Chart 1
    sorted_sec = sorted(cm_data, key=lambda d: d["x"])
    sorted_eman = sorted(cm_data, key=lambda d: d["y"])
    t1 = (
        f"{sorted_sec[-1]['country']} scores highest on secular values ({sorted_sec[-1]['x']:.2f}) "
        f"while {sorted_sec[0]['country']} scores lowest ({sorted_sec[0]['x']:.2f}). "
        f"{sorted_eman[-1]['country']} leads on emancipative values ({sorted_eman[-1]['y']:.2f}), "
        f"illustrating distinct cultural orientations across these five Asian societies."
    )
    # Chart 2
    god_idx = radar_labels.index("Importance of God")
    trust_idx = radar_labels.index("Trust (share)")
    high_god = max(COUNTRIES, key=lambda c: radar_ds[c][god_idx])
    low_god = min(COUNTRIES, key=lambda c: radar_ds[c][god_idx])
    high_trust = max(COUNTRIES, key=lambda c: radar_ds[c][trust_idx])
    t2 = (
        f"The radar reveals sharply different value profiles: {high_god} scores highest on "
        f"importance of god ({radar_ds[high_god][god_idx]:.2f}) while {low_god} scores "
        f"lowest ({radar_ds[low_god][god_idx]:.2f}). "
        f"{high_trust} shows the highest share of interpersonal trust ({radar_ds[high_trust][trust_idx]:.2f})."
    )
    # Chart 3
    t3 = (
        f"Despite different country averages (China: secular {china_avg['x']:.2f}, "
        f"emancipative {china_avg['y']:.2f}; India: secular {india_avg['x']:.2f}, "
        f"emancipative {india_avg['y']:.2f}), the individual-level clouds overlap substantially, "
        f"showing that within-country variation is large relative to between-country differences."
    )
    # Chart 4
    # find mode cell
    mode_li, mode_fi, mode_count = 0, 0, 0
    for li in range(10):
        for fi in range(10):
            if grid[li][fi] > mode_count:
                mode_li, mode_fi, mode_count = li + 1, fi + 1, grid[li][fi]
    t4 = (
        f"The most common combination among Singapore respondents is life satisfaction = {mode_li} "
        f"and financial satisfaction = {mode_fi} ({mode_count} respondents). "
        f"The concentration along the diagonal suggests a positive association between life and financial satisfaction."
    )
    return t1, t2, t3, t4


def main():
    raw = read_csv()
    total = len(raw)
    col_meta = column_metadata(raw)
    dup_count = check_duplicates(raw)
    rows = clean(raw)
    removed = total - len(rows)

    groups = country_groups(rows)

    cm = cultural_map(groups)
    r_labels, r_ds = radar_data(groups)
    china_pts, india_pts, china_avg, india_avg = individual_scatter(groups)
    grid, max_count = heatmap_data(groups)
    hm_html = heatmap_html(grid, max_count)

    t1, t2, t3, t4 = generate_takeaways(cm, r_labels, r_ds, china_avg, india_avg, grid, max_count)

    summary = build_summary_table(col_meta, total, dup_count, removed, len(rows))

    html = HTML_TEMPLATE.substitute(
        summary_table=summary,
        takeaway1=t1,
        takeaway2=t2,
        takeaway3=t3,
        takeaway4=t4,
        heatmap_html=hm_html,
        cultural_map_json=json.dumps(cm),
        radar_labels_json=json.dumps(r_labels),
        radar_datasets_json=json.dumps(r_ds),
        china_pts_json=json.dumps(china_pts),
        india_pts_json=json.dumps(india_pts),
        china_avg_json=json.dumps(china_avg),
        india_avg_json=json.dumps(india_avg),
        colors_json=json.dumps(COLORS),
        markers_json=json.dumps(MARKERS),
        countries_json=json.dumps(COUNTRIES),
    )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {OUT_PATH}")
    print(f"  Total rows: {total:,}")
    print(f"  Duplicates: {dup_count}")
    print(f"  Rows removed (blanks): {removed:,}")
    print(f"  Clean rows used: {len(rows):,}")


if __name__ == "__main__":
    main()
