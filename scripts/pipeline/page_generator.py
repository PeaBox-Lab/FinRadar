#!/usr/bin/env python3
"""
FinRadar — Static Page Generator
================================
Reads the KPI registry, site_data (facts, trends) and latest_kpis.json,
then writes a complete multi-page static site under `site/` ready for
GitHub Pages / Cloudflare Pages.

Pages generated:
  - index.html (dashboard / landing)
  - search.html (full-text lookup across facts & KPIs)
  - category/<sector>.html (one page per sector with facts, KPIs, trends)
  - facts/<fact-id>.html (detail page per fact)
  - trend/<kpi-id>.html (historical chart page)
  - kpi/<kpi-id>.html (deep-dive per KPI)
  - data/sources.json (catalog of all data.gov.in / API Setu sources used)
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kpi_registry import KPI_REGISTRY, interpret, kpis_by_sector
from site_data import (
    SECTORS, SECTOR_MAP, FACTS, FACTS_BY_CATEGORY,
    HISTORICAL_TRENDS, get_trend, search_index, trends_by_category,
)

ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "site"
DATA_FILE = ROOT / "data" / "latest_kpis.json"
SNAP_DIR = ROOT / "data" / "snapshots"


def load_latest():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def humanize(n, decimals=2):
    if n is None or not isinstance(n, (int, float)):
        return "—"
    return f"{n:,.{decimals}f}"


def get_latest_value(kpi_id, latest):
    """Extract the latest computed value for a KPI from latest_kpis.json."""
    for k in latest.get("kpis", []):
        if k.get("kpi_id") == kpi_id or k.get("id") == kpi_id:
            return k.get("value")
    return None


def render_base_head(title, description, current_url=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — FinRadar</title>
  <meta name="description" content="{description}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="styles/main.css" />
  <link rel="canonical" href="https://finradar.example{current_url}" />
</head>
<body>
  <!-- Navigation Component -->
  <nav class="site-nav">
    <div class="nav-container">
      <a class="nav-brand" href="index.html">FinRadar</a>
      <span class="nav-tagline">India & global macro, live from public data</span>
      
      <ul class="nav-primary">
        <li><a href="index.html">Dashboard</a></li>
        <li><a href="search.html">Search</a></li>
        <li><a href="sources.html">Sources</a></li>
        <li><a href="category/central.html">Central Govt</a></li>
        <li><a href="category/states.html">States</a></li>
        <li><a href="category/financials.html">Financials</a></li>
        <li><a href="category/geo.html">Geo</a></li>
        <li><a href="category/transport.html">Transport</a></li>
      </ul>
      
      <ul class="nav-secondary">
        <li><a href="category/economy.html">Economy</a></li>
        <li><a href="category/agriculture.html">Agriculture</a></li>
        <li><a href="category/health.html">Health</a></li>
        <li><a href="category/education.html">Education</a></li>
        <li><a href="category/welfare.html">Welfare</a></li>
      </ul>
      
      <div class="nav-dropdown">
        <a href="#">Categories ▾</a>
        <div class="nav-dropdown-content">
          <a href="category/central.html">Central Government</a>
          <a href="category/states.html">State Level</a>
          <a href="category/financials.html">Financials</a>
          <a href="category/geo.html">Geo Levels</a>
          <a href="category/transport.html">Transport</a>
          <a href="category/economy.html">Economy</a>
          <a href="category/agriculture.html">Agriculture</a>
          <a href="category/energy.html">Energy & Power</a>
          <a href="category/health.html">Health</a>
          <a href="category/education.html">Education</a>
          <a href="category/welfare.html">Welfare & Employment</a>
          <a href="category/environment.html">Environment & Climate</a>
          <a href="category/commerce.html">Trade & Commerce</a>
          <a href="category/housing.html">Housing & Urban</a>
        </div>
      </div>
    </div>
  </nav>
  <!-- End Navigation Component -->
  
  <main class="container">"""


def render_footer():
    return f"""  </main>
  <footer class="site-footer">
    <div class="footer-container">
      <div class="footer-brand">
        <a class="footer-logo" href="index.html">FinRadar</a>
        <p class="footer-tagline">India & global macro, live from public data</p>
      </div>
      
      <ul class="footer-links">
        <li><a href="index.html">Dashboard</a></li>
        <li><a href="search.html">Search</a></li>
        <li><a href="sources.html">Sources</a></li>
      </ul>
      
      <ul class="footer-category">
        <li><a href="category/central.html">Central Govt</a></li>
        <li><a href="category/states.html">States</a></li>
        <li><a href="category/financials.html">Financials</a></li>
        <li><a href="category/geo.html">Geo</a></li>
        <li><a href="category/transport.html">Transport</a></li>
      </ul>
      
      <div class="footer-bottom">
        <p class="footer-small">Data refreshed: <span id="footer-refresh">{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</span> | <a href="https://github.com/finradar/finradar">Source code</a></p>
      </div>
    </div>
  </footer>
  <script src="scripts/app.js"></script>
  <script src="scripts/charts.js"></script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Category page
# ---------------------------------------------------------------------------

def render_category_page(sector_id, latest):
    sector = SECTOR_MAP[sector_id]
    facts = FACTS_BY_CATEGORY.get(sector_id, [])
    kpis = kpis_by_sector(sector["title"])
    trends = trends_by_category().get(sector_id, [])

    # Attach latest values + verdicts to KPIs
    for kpi in kpis:
        val = get_latest_value(kpi["id"], latest)
        if val is not None:
            kpi["latest_value"] = val
            kpi["verdict"] = interpret(val, kpi).split(".")[0].lower()

    # Build facts HTML
    facts_html = ""
    for f in facts:
        facts_html += f"""
        <article class="fact-card">
          <h3>{f['fact'][:80]}…</h3>
          <p class="muted small">Source: {f['source']}</p>
          <p class="small">{f['why_it_matters']}</p>
          <a href="/facts/{f['id']}.html" class="btn">Read more</a>
        </article>"""

    # Build KPIs HTML
    kpis_html = ""
    for kpi in kpis:
        val = kpi.get("latest_value", None)
        val_str = humanize(val) + " " + kpi["unit"] if val is not None else "—"
        verdict = kpi.get("verdict", "")
        verdict_html = f'<span class="verdict-badge {verdict}">{verdict.upper()}</span>' if verdict else ""
        kpis_html += f"""
        <tr>
          <td><strong>{kpi['name']}</strong></td>
          <td class="num">{val_str}</td>
          <td>{verdict_html}</td>
          <td>{kpi.get('insight', '')}</td>
          <td class="muted small">{kpi.get('formula', '')}</td>
          <td><a href="/kpi/{kpi['id']}.html" class="btn small">Detail</a></td>
        </tr>"""

    # Build trends HTML
    trends_html = ""
    for kpi_id, trend in trends:
        pts = trend.get("points", [])
        if pts:
            latest_pt = pts[-1]
            trends_html += f"""
            <div class="trend-preview">
              <h4>{trend['label']}</h4>
              <p class="muted small">{trend['source']}</p>
              <div class="sparkline" data-points='{json.dumps([p["value"] for p in pts])}'></div>
              <p class="trend-value">{humanize(latest_pt["value"])} {trend["unit"]} <span class="muted">({latest_pt["year"]})</span></p>
              <a href="/trend/{kpi_id}.html" class="btn small">View history</a>
            </div>"""

    html = render_base_head(
        f"{sector['icon']} {sector['title']}",
        sector["description"],
        f"/category/{sector_id}.html"
    )
    html += f"""
    <section class="category-hero">
      <h1>{sector['icon']} {sector['title']}</h1>
      <p>{sector['description']}</p>
    </section>

    <section>
      <h2>Key Facts</h2>
      <div class="grid">{facts_html}</div>
    </section>

    <section>
      <h2>KPIs — {len(kpis)} metrics</h2>
      <table class="kpi-library-table">
        <thead><tr><th>KPI</th><th>Latest</th><th>Verdict</th><th>Insight</th><th>Formula</th><th></th></tr></thead>
        <tbody>{kpis_html}</tbody>
      </table>
    </section>

    <section>
      <h2>Historical Trends</h2>
      <div class="trend-grid">{trends_html}</div>
    </section>"""
    html += render_footer()
    return html


# ---------------------------------------------------------------------------
# Fact detail page
# ---------------------------------------------------------------------------

def render_fact_page(fact, latest):
    kpi_id = fact.get("kpi_id")
    trend = get_trend(kpi_id)
    val = get_latest_value(kpi_id, latest)

    html = render_base_head(
        fact["kpi_id"].replace("_", " ").title(),
        fact["fact"][:160],
        f"/facts/{fact['id']}.html"
    )
    html += f"""
    <section class="fact-detail">
      <h1>{fact['kpi_id'].replace('_', ' ').title()}</h1>
      <p class="fact-text">{fact['fact']}</p>
      <div class="fact-meta">
        <span><strong>Source:</strong> {fact['source']}</span>
        <span><strong>Scale:</strong> {fact['scale']}</span>
        <span><strong>Why it matters:</strong> {fact['why_it_matters']}</span>
      </div>
      {f'<p class="latest-value">Latest value: <strong>{humanize(val)}</strong></p>' if val is not None else ''}
      {f'<div class="trend-embed"><h3>{trend["label"]} (history)</h3><div class="sparkline" data-points=\'{json.dumps([p["value"] for p in trend["points"]])}\'></div><a href="/trend/{kpi_id}.html" class="btn">Full history</a></div>' if trend else ''}
      <a href="category/{fact['category']}.html" class="btn">← Back to {SECTOR_MAP[fact['category']]['title']}</a>
    </section>"""
    html += render_footer()
    return html


# ---------------------------------------------------------------------------
# Trend page (historical chart)
# ---------------------------------------------------------------------------

def render_trend_page(kpi_id, latest):
    trend = get_trend(kpi_id)
    if not trend:
        return None
    kpi_def = None
    for k in KPI_REGISTRY:
        if k["id"] == kpi_id:
            kpi_def = k
            break

    val = get_latest_value(kpi_id, latest)

    points = trend["points"]
    years = [p["year"] for p in points]
    values = [p["value"] for p in points]

    html = render_base_head(
        f"{trend['label']} — Historical Trend",
        f"Historical trend for {trend['label']} from {trend['source']}",
        f"/trend/{kpi_id}.html"
    )
    html += f"""
    <section class="trend-detail">
      <h1>{trend['label']}</h1>
      <p class="muted"><strong>Source:</strong> {trend['source']}</p>
      {f'<p class="latest-value">Latest ({years[-1]}): <strong>{humanize(values[-1])} {trend["unit"]}</strong></p>' if values else ''}

      <div class="chart-wrap">
        <canvas id="trend-chart"></canvas>
      </div>

      <table class="trend-table">
        <thead><tr><th>Year</th><th>Value ({trend['unit']})</th><th>YoY Δ</th></tr></thead>
        <tbody>
    """
    for i, p in enumerate(points):
        if i > 0:
            delta = p["value"] - points[i-1]["value"]
            delta_str = f"{delta:+.2f}"
        else:
            delta_str = "—"
        html += f"<tr><td>{p['year']}</td><td class='num'>{humanize(p['value'])}</td><td class='num'>{delta_str}</td></tr>"

    html += """</tbody></table>

      <h3>What this trend tells you</h3>
      <p>""" + (kpi_def.get("insight", "Trend data for this metric.") if kpi_def else "Trend data for this metric.") + """</p>
      <a href="category/""" + (next((c for c, facts in FACTS_BY_CATEGORY.items() if any(fi["kpi_id"]==kpi_id for fi in facts)), "economy")) + """.html" class="btn">← Back</a>
    </section>"""
    html += render_footer()
    # Inline the chart data for the simple JS chart
    html = html.replace("</body>", f"""
  <script>
    const chartData = {{
      labels: {json.dumps(years)},
      values: {json.dumps(values)},
      label: "{trend['label']}",
      unit: "{trend['unit']}"
    }};
  </script>
  </body>""")
    return html


# ---------------------------------------------------------------------------
# KPI deep-dive page
# ---------------------------------------------------------------------------

def render_kpi_page(kpi_id, latest):
    kpi_def = None
    for k in KPI_REGISTRY:
        if k["id"] == kpi_id:
            kpi_def = k
            break
    if not kpi_def:
        return None

    val = get_latest_value(kpi_id, latest)
    verdict = interpret(val, kpi_def) if val is not None else "No data"
    trend = get_trend(kpi_id)

    # Find category
    cat = None
    for f in FACTS:
        if f["kpi_id"] == kpi_id:
            cat = f["category"]
            break

    html = render_base_head(
        kpi_def["name"],
        kpi_def.get("insight", "")[:160],
        f"/kpi/{kpi_id}.html"
    )
    html += f"""
    <section class="kpi-detail">
      <header>
        <h1>{kpi_def['name']}</h1>
        <p class="muted"><strong>Sector:</strong> {kpi_def['sector']} | <strong>Frequency:</strong> {kpi_def.get('frequency', 'monthly')}</p>
      </header>

      <div class="kpi-headline">
        <div class="kpi-value-large">{humanize(val) + ' ' + kpi_def['unit'] if val is not None else '—'}</div>
        <div class="verdict-badge {verdict.split('.')[0].lower() if val is not None else 'weak'}">{verdict.split('.')[0].upper() if val is not None else 'NO DATA'}</div>
      </div>

      <div class="kpi-meta-grid">
        <div><strong>Formula</strong><p>{kpi_def.get('formula', '—')}</p></div>
        <div><strong>Source fields</strong><p>{', '.join(kpi_def.get('source_fields', []))}</p></div>
        <div><strong>Benchmark</strong><p>{kpi_def.get('benchmark', '—')}</p></div>
        <div><strong>Direction</strong><p>{kpi_def.get('direction', '—').replace('_', ' ').title()}</p></div>
      </div>

      <div class="kpi-insight">
        <h3>What this means</h3>
        <p>{kpi_def.get('insight', 'No insight available.')}</p>
        {f'<p class="muted small"><strong>Source:</strong> {kpi_def.get("source_resource_id", "")}</p>' if kpi_def.get("source_resource_id") else ''}
      </div>

      {f'<div class="trend-embed"><h3>Historical trend</h3><div class="sparkline" data-points=\'{json.dumps([p["value"] for p in trend["points"]])}\'></div><a href="/trend/{kpi_id}.html" class="btn">Full history</a></div>' if trend else ''}

      <a href="category/{cat}.html" class="btn">← Back to {SECTOR_MAP[cat]['title'] if cat else 'Dashboard'}</a>
    </section>"""
    html += render_footer()
    return html


# ---------------------------------------------------------------------------
# Search page
# ---------------------------------------------------------------------------

def render_search_page(latest):
    items = search_index()

    html = render_base_head(
        "Search — Find any data fact or KPI",
        "Search across 35+ KPIs, historical trends and plain-English facts from Indian government data.",
        "/search.html"
    )
    html += """
    <section class="search-page">
      <h1>Search FinRadar</h1>
      <div class="search-input-wrap">
        <input type="text" id="search-input" placeholder="Type a metric, sector, year or keyword…" autocomplete="off" />
      </div>
      <div id="search-results" class="search-results"></div>
    </section>
  <script>
    const INDEX = """ + json.dumps(items) + """;
    const input = document.getElementById('search-input');
    const results = document.getElementById('search-results');
    function render(resultsArr) {
      if (!resultsArr.length) { results.innerHTML = '<p class="muted">No matches.</p>'; return; }
      results.innerHTML = resultsArr.map(r => `
        <a href="${r.type==='fact' ? '/facts/'+r.id+'.html' : '/kpi/'+r.id+'.html'}" class="search-result">
          <strong>${r.title}</strong>
          <span class="badge">${r.category}</span>
          <p>${r.text.slice(0,120)}…</p>
          <small class="muted">Source: ${r.source}</small>
        </a>
      `).join('');
    }
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      if (!q) { results.innerHTML = ''; return; }
      const filtered = INDEX.filter(r =>
        r.title.toLowerCase().includes(q) ||
        r.text.toLowerCase().includes(q) ||
        r.category.toLowerCase().includes(q) ||
        r.source.toLowerCase().includes(q)
      );
      render(filtered);
    });
  </script>
""" + render_footer()
    return html


# ---------------------------------------------------------------------------
# Sources catalog page
# ---------------------------------------------------------------------------

def render_sources_page():
    html = render_base_head(
        "Data Sources — Catalog",
        "Every API, dataset and portal FinRadar draws from, with links and field notes.",
        "/sources.html"
    )
    html += """
    <section>
      <h1>Data Sources Catalog</h1>
      <p class="muted">FinRadar computes KPIs from these public government sources. Each row links to the live API or catalog page.</p>

      <h2>World Bank Open Data</h2>
      <ul class="source-list">
        <li><a href="https://api.worldbank.org/v2" target="_blank">api.worldbank.org/v2</a> — GDP, inflation, trade, PPP, demographics across 200+ countries.</li>
      </ul>

      <h2>data.gov.in (OGD Platform)</h2>
      <ul class="source-list">
        <li><a href="https://data.gov.in/apis?sector=Economy" target="_blank">Economy sector</a> — 500+ APIs: GDP, GST, inflation, fiscal, trade.</li>
        <li><a href="https://data.gov.in/apis?sector=Power%20and%20Energy" target="_blank">Power & Energy</a> — 300+ APIs: generation, renewables, consumption.</li>
        <li><a href="https://data.gov.in/apis?sector=Agriculture" target="_blank">Agriculture</a> — crops, fertilizer, irrigation, wages.</li>
        <li><a href="https://data.gov.in/apis?sector=Health%20and%20Family%20welfare" target="_blank">Health & Family Welfare</a> — hospital stats, immunization, NFHS.</li>
        <li><a href="https://data.gov.in/apis?sector=Transport" target="_blank">Transport</a> — Vahan, roads, vehicle registrations.</li>
        <li><a href="https://data.gov.in/apis?sector=Labour%20and%20Employment" target="_blank">Labour & Employment</a> — MGNREGA, wages, PLFS.</li>
        <li><a href="https://api.data.gov.in/resource/8b68ae56-84cf-4728-a0a6-1be11028dea7" target="_blank">MSME Udyam registrations</a> — unit-level state/district data.</li>
      </ul>

      <h2>API Setu (apisetu.gov.in)</h2>
      <ul class="source-list">
        <li><a href="https://directory.apisetu.gov.in" target="_blank">API Directory</a> — 4,200+ published APIs across 2,700+ organisations.</li>
        <li>Key APIs: DigiLocker, GSTN, MCA, Vahan, UIDAI, NPCI, PPAC, CBSE, IRCTC.</li>
      </ul>

      <h2>RBI & NPCI</h2>
      <ul class="source-list">
        <li><a href="https://dbie.rbi.org.in" target="_blank">RBI DBIE</a> — interest rates, reserves, sectoral credit, money supply.</li>
        <li><a href="https://www.npci.org.in" target="_blank">NPCI</a> — UPI/IMPS/FASTag volumes, ticket sizes.</li>
      </ul>

      <h2>IMF / FRED</h2>
      <ul class="source-list">
        <li><a href="https://data.imf.org" target="_blank">IMF DataMapper</a> — fiscal, debt, cross-country comparables.</li>
        <li><a href="https://fred.stlouisfed.org" target="_blank">FRED</a> — US rates, commodities, global indicators.</li>
      </ul>
    </section>""" + render_footer()
    return html


# ---------------------------------------------------------------------------
# Landing / Dashboard page
# ---------------------------------------------------------------------------

def render_index(latest):
    html = render_base_head(
        "FinRadar — India & Global Macro KPIs & Benchmarks",
        "Live macroeconomic KPIs, benchmarks and interactive tools built from public government data.",
        "/"
    )
    html += """
    <section class="hero">
      <div class="hero-inner">
        <h1>Real economy numbers, plain English.</h1>
        <p class="hero-sub">FinRadar turns public government data into living KPIs — real interest rates, digital velocity, fiscal health — and publishes benchmarks and reports you can cite. Every number is a derived metric, not a raw table.</p>
        <div class="hero-stats" id="hero-stats"></div>
      </div>
    </section>

    <section class="kpis">
      <h2>Live KPIs — what it actually costs</h2>
      <p class="section-intro">These are not raw tables. They are spreads, velocities and composite scores. Values update daily.</p>
      <div class="grid" id="kpi-grid"></div>
    </section>

    <section class="benchmarks">
      <h2>Original benchmarks we publish</h2>
      <div class="grid">
        <article class="card">
          <h3>1. India High-Frequency Macro Cycle Index</h3>
          <p>A 0–100 score blending GST, UPI, power demand, IIP, inflation, repo rate and GDP growth into one number that classifies the economy.</p>
          <div class="bench-stat" id="bench-macro-cycle-value"></div>
        </article>
        <article class="card">
          <h3>2. City Salary-Parity Benchmark</h3>
          <p>What salary in Jaipur gives the same purchasing power as ₹20 LPA in Mumbai? Interactive calculator below.</p>
        </article>
        <article class="card">
          <h3>3. State-Wise Fiscal Health Scorecard</h3>
          <p>Ranks all 28 states quarterly on GST growth, debt-to-GSDP, capex ratio.</p>
        </article>
        <article class="card">
          <h3>4. Global Emerging Market Resilience</h3>
          <p>India vs Vietnam, Indonesia, Brazil, Mexico on GDP growth, current account, FDI, digital infra.</p>
          <div class="bench-stat" id="bench-resilience-value"></div>
        </article>
      </div>
    </section>

    <section class="tools">
      <h2>Interactive tools</h2>
      <div class="tool-card">
        <h3>Your personal inflation rate</h3>
        <p class="sub">Enter your spending split — food, fuel, education, healthcare, housing — and see your personal inflation vs the headline.</p>
        <div id="personal-inflation-rows"></div>
        <button id="personal-inflation-btn" class="btn">Calculate</button>
        <div id="personal-inflation-result"></div>
      </div>
      <div class="tool-card">
        <h3>Salary parity between two cities</h3>
        <p class="sub">Enter a base salary and pick two cities. We tell you the equivalent purchasing-power salary.</p>
        <div class="tool-form">
          <input type="number" id="salary-parity-salary" value="200000" placeholder="INR" />
          <select id="salary-parity-from"></select>
          <select id="salary-parity-to"></select>
          <button id="salary-parity-btn" class="btn">Calculate</button>
        </div>
        <div id="salary-parity-result"></div>
      </div>
    </section>

    <section>
      <h2>Explore by category</h2>
      <div class="grid">
    """
    for s in SECTORS:
        facts_in_cat = FACTS_BY_CATEGORY.get(s["id"], [])
        kpis_in_cat = len(kpis_by_sector(s["title"]))
        html += f"""
        <article class="card category-card">
          <div class="card-header">
            <h3>{s['icon']} {s['title']}</h3>
            <span class="kpi-count small">{kpis_in_cat} KPIs</span>
          </div>
          <p class="card-desc">{s['description']}</p>
          <div class="card-footer">
            <span class="muted small">{len(facts_in_cat)} facts</span>
            <a href="category/{s['id']}.html" class="btn small">View</a>
          </div>
        </article>"""

    html += """
      </div>
    </section>
    <p style="text-align:center; margin-top:24px;"><a href="/search.html" class="btn">🔍 Search all facts & KPIs</a></p>"""
    html += render_footer()
    return html


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def main():
    latest = load_latest()

    # Clean and create site dir
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    (SITE_DIR / "category").mkdir()
    (SITE_DIR / "facts").mkdir()
    (SITE_DIR / "trend").mkdir()
    (SITE_DIR / "kpi").mkdir()
    (SITE_DIR / "styles").mkdir()
    (SITE_DIR / "scripts").mkdir()
    (SITE_DIR / "data").mkdir()

    # Copy static assets (styles + only the client JS, not the pipeline)
    shutil.copytree(ROOT / "styles", SITE_DIR / "styles", dirs_exist_ok=True)
    (SITE_DIR / "scripts").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "scripts" / "app.js", SITE_DIR / "scripts" / "app.js")
    shutil.copy2(ROOT / "scripts" / "charts.js", SITE_DIR / "scripts" / "charts.js")
    # Copy latest_kpis.json for the JS to consume
    shutil.copy2(DATA_FILE, SITE_DIR / "data" / "latest_kpis.json")
    # Copy snapshots for fallback
    shutil.copytree(SNAP_DIR, SITE_DIR / "data" / "snapshots", dirs_exist_ok=True)

    # Generate pages
    print("Generating index.html…")
    (SITE_DIR / "index.html").write_text(render_index(latest), encoding="utf-8")

    print("Generating search.html…")
    (SITE_DIR / "search.html").write_text(render_search_page(latest), encoding="utf-8")

    print("Generating sources.html…")
    (SITE_DIR / "sources.html").write_text(render_sources_page(), encoding="utf-8")

    print("Generating category pages…")
    for sector in SECTORS:
        html = render_category_page(sector["id"], latest)
        (SITE_DIR / "category" / f"{sector['id']}.html").write_text(html, encoding="utf-8")

    print("Generating fact pages…")
    for fact in FACTS:
        html = render_fact_page(fact, latest)
        (SITE_DIR / "facts" / f"{fact['id']}.html").write_text(html, encoding="utf-8")

    print("Generating trend pages…")
    for kpi_id, trend in HISTORICAL_TRENDS.items():
        html = render_trend_page(kpi_id, latest)
        if html:
            (SITE_DIR / "trend" / f"{kpi_id}.html").write_text(html, encoding="utf-8")

    print("Generating KPI detail pages…")
    for kpi in KPI_REGISTRY:
        html = render_kpi_page(kpi["id"], latest)
        if html:
            (SITE_DIR / "kpi" / f"{kpi['id']}.html").write_text(html, encoding="utf-8")

    print(f"[OK] Site generated at {SITE_DIR}")
    print(f"Pages: 1 index + 1 search + 1 sources + {len(SECTORS)} categories + {len(FACTS)} facts + {len(HISTORICAL_TRENDS)} trends + {len(KPI_REGISTRY)} KPIs")


if __name__ == "__main__":
    main()