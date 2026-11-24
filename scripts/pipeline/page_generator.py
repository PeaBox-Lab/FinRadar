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
    CATEGORY_GROUPS,
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


def render_base_head(title, description, current_url="", base=""):
    b = base  # '' for root pages, '../' for subfolder pages
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
  <link rel="stylesheet" href="{b}styles/main.css" />
  <link rel="stylesheet" href="{b}styles/european-theme.css" />
  <link rel="canonical" href="https://finradar.example{current_url}" />
</head>
<body>
  <header class="site-header">
    <div class="nav-inner container">
      <a class="brand" href="{b}index.html">
        <span class="brand-mark">F</span>
        <span class="brand-name">FinRadar</span>
      </a>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">
        <span></span><span></span><span></span>
      </button>
      <nav id="site-nav" class="site-nav" aria-label="Primary">
        <div class="nav-primary">
          <a href="{b}index.html" class="nav-link">Dashboard</a>
          <a href="{b}search.html" class="nav-link">Search</a>
          <a href="{b}categories.html" class="nav-link">Categories</a>
          <a href="{b}sources.html" class="nav-link">Sources</a>
        </div>
        <div class="nav-drop">
          <button class="nav-link nav-drop-btn" aria-expanded="false" aria-haspopup="true">Browse Sectors <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg></button>
          <div class="nav-drop-menu" role="menu">
            <div class="nav-drop-heading">Macro &amp; National Accounts</div>
            <a href="{b}category/central.html" role="menuitem">🏛️ Central Government</a>
            <a href="{b}category/economy.html" role="menuitem">💰 Economy</a>
            <a href="{b}category/financials.html" role="menuitem">🏦 Financials</a>
            <div class="nav-drop-heading">Sector Categories</div>
            <a href="{b}category/agriculture.html" role="menuitem">🌾 Agriculture</a>
            <a href="{b}category/energy.html" role="menuitem">⚡ Energy &amp; Power</a>
            <a href="{b}category/transport.html" role="menuitem">🚗 Transport</a>
            <a href="{b}category/commerce.html" role="menuitem">🛒 Trade &amp; Commerce</a>
            <div class="nav-drop-heading">Geographic &amp; Sub-national</div>
            <a href="{b}category/geo.html" role="menuitem">📍 Geo Levels</a>
            <a href="{b}category/states.html" role="menuitem">🗺️ State Level</a>
            <div class="nav-drop-heading">Social Services</div>
            <a href="{b}category/health.html" role="menuitem">🏥 Health</a>
            <a href="{b}category/education.html" role="menuitem">📚 Education</a>
            <a href="{b}category/welfare.html" role="menuitem">🤝 Welfare &amp; Employment</a>
            <div class="nav-drop-heading">Environment &amp; Urban</div>
            <a href="{b}category/environment.html" role="menuitem">🌍 Environment &amp; Climate</a>
            <a href="{b}category/housing.html" role="menuitem">🏠 Housing &amp; Urban</a>
            <div class="nav-drop-heading">More</div>
            <a href="{b}categories.html" role="menuitem">📂 View All Categories</a>
          </div>
        </div>
      </nav>
    </div>
  </header>
  <main class="site-main container">"""


def render_footer(base=""):
    b = base
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""  </main>
  <footer class="site-footer">
    <div class="container footer-inner">
      <div class="footer-brand-col">
        <a class="brand" href="{b}index.html">
          <span class="brand-mark">F</span>
          <span class="brand-name">FinRadar</span>
        </a>
        <p class="footer-tagline">Original macro KPIs, benchmarks, and facts derived from public government data.</p>
        <p class="footer-meta">Data refreshed: <span id="footer-refresh">{ts}</span></p>
      </div>
      <div class="footer-col">
        <h4 class="footer-heading">Explore</h4>
        <a href="{b}index.html">Dashboard</a>
        <a href="{b}search.html">Search</a>
        <a href="{b}sources.html">Data Sources</a>
      </div>
      <div class="footer-col">
        <h4 class="footer-heading">Key Sectors</h4>
        <a href="{b}category/central.html">Central Government</a>
        <a href="{b}category/states.html">State Level</a>
        <a href="{b}category/financials.html">Finance &amp; Banking</a>
        <a href="{b}category/geo.html">Geo Levels</a>
        <a href="{b}category/transport.html">Transport</a>
      </div>
      <div class="footer-col">
        <h4 class="footer-heading">More Sectors</h4>
        <a href="{b}category/economy.html">Economy</a>
        <a href="{b}category/agriculture.html">Agriculture</a>
        <a href="{b}category/health.html">Health</a>
        <a href="{b}category/education.html">Education</a>
        <a href="{b}category/welfare.html">Welfare &amp; Employment</a>
      </div>
    </div>
    <div class="container footer-bottom">
      <p>© {datetime.now(timezone.utc).year} FinRadar. Built on public data from World Bank, RBI, MoSPI, NPCI, and data.gov.in.</p>
      <a href="https://github.com/rajeshceg3/FinRadar" class="footer-gh">GitHub</a>
    </div>
  </footer>
  <script src="{b}scripts/app.js"></script>
  <script src="{b}scripts/charts.js"></script>
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
          <a href="../facts/{f['id']}.html" class="btn">Read more</a>
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
          <td><a href="../kpi/{kpi['id']}.html" class="btn small">Detail</a></td>
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
              <a href="../trend/{kpi_id}.html" class="btn small">View history</a>
            </div>"""

    html = render_base_head(
        f"{sector['icon']} {sector['title']}",
        sector["description"],
        f"/category/{sector_id}.html",
        base="../"
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
    html += render_footer("../")
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
        f"/facts/{fact['id']}.html",
        base="../"
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
      {f'<div class="trend-embed"><h3>{trend["label"]} (history)</h3><div class="sparkline" data-points=\'{json.dumps([p["value"] for p in trend["points"]])}\'></div><a href="../trend/{kpi_id}.html" class="btn">Full history</a></div>' if trend else ''}
      <a href="../category/{fact['category']}.html" class="btn">← Back to {SECTOR_MAP[fact['category']]['title']}</a>
    </section>"""
    html += render_footer("../")
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
        f"/trend/{kpi_id}.html",
        base="../"
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
      <a href="../category/""" + (next((c for c, facts in FACTS_BY_CATEGORY.items() if any(fi["kpi_id"]==kpi_id for fi in facts)), "economy")) + """.html" class="btn">← Back</a>
    </section>"""
    html += render_footer("../")
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
        f"/kpi/{kpi_id}.html",
        base="../"
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

      {f'<div class="trend-embed"><h3>Historical trend</h3><div class="sparkline" data-points=\'{json.dumps([p["value"] for p in trend["points"]])}\'></div><a href="../trend/{kpi_id}.html" class="btn">Full history</a></div>' if trend else ''}

      <a href="../category/{cat}.html" class="btn">← Back to {SECTOR_MAP[cat]['title'] if cat else 'Dashboard'}</a>
    </section>"""
    html += render_footer("../")
    return html


# ---------------------------------------------------------------------------
# Search page
# ---------------------------------------------------------------------------

def render_search_page(latest):
    items = search_index()

    html = render_base_head(
        "Search — Find any data fact or KPI",
        "Search across 35+ KPIs, historical trends and plain-English facts from Indian government data.",
        "/search.html",
        base=""
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
        <a href="${r.type==='fact' ? 'facts/'+r.id+'.html' : 'kpi/'+r.id+'.html'}" class="search-result">
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
""" + render_footer("")
    return html


# ---------------------------------------------------------------------------
# Sources catalog page
# ---------------------------------------------------------------------------

def _source_card(api, cat_map):
    return f"""
      <article class="card source-card">
        <div class="card-header">
          <h3><a href="{api.get('url', '#')}" target="_blank">{api['name']}</a></h3>
          <span class="badge">{cat_map.get(api.get('category', ''), {}).get('title', api.get('category', 'General'))}</span>
        </div>
        <p class="card-desc">{api.get('summary', '')}</p>
        <div class="source-stats">
          <div class="source-stat"><strong>{api['stats'].get('indicators_used', 0)}</strong><span>Series used</span></div>
          <div class="source-stat"><strong>{api['stats'].get('history', 'N/A')}</strong><span>Coverage / era</span></div>
          <div class="source-stat"><strong>{api['stats'].get('frequency', 'N/A')}</strong><span>Frequency</span></div>
          <div class="source-stat"><strong>{api['access'].split('·')[0].strip()}</strong><span>Access</span></div>
        </div>
        {f"<div class=\"source-tags\">{''.join(f'<span class=\"badge\">{t}</span>' for t in api.get('tags', []))}</div>" if api.get("tags") else ""}
        <p class="muted small">Provider: {api.get('provider', '')} · Tags: {', '.join(api.get('tags', []))}</p>
      </article>"""


def render_sources_page():
    from api_catalog import API_CATALOG, API_CATEGORY_MAP, API_CATEGORIES, catalog_summary
    summ = catalog_summary()
    html = render_base_head(
        "Data Sources — Catalog",
        f"Every API, dataset and portal FinRadar draws from — {summ['total_apis']} categorised sources with summary stats for each.",
        "/sources.html",
        base=""
    )
    html += f"""
    <section>
      <h1>Data Sources Catalog</h1>
      <p class="muted">FinRadar computes KPIs from {summ['total_apis']} public government APIs across {summ['total_categories']} categories. Every source is categorised under a proper tag group and summarised with the key statistics we use.</p>

      <div class="grid grid-4 source-summary-grid">
        <div class="card source-summary-card"><strong>{summ['total_apis']}</strong><span>APIs catalogued</span></div>
        <div class="card source-summary-card"><strong>{summ['total_categories']}</strong><span>Categories</span></div>
        <div class="card source-summary-card"><strong>{summ['total_series']}</strong><span>Data series used</span></div>
        <div class="card source-summary-card"><strong>{summ['open_apis']}</strong><span>Open access</span></div>
      </div>

      {''.join(f"""
      <h2>{API_CATEGORY_MAP.get(c['id'], {}).get('icon', '📁')} {API_CATEGORY_MAP.get(c['id'], {}).get('title', c['id'])}</h2>
      <p class="muted">{API_CATEGORY_MAP.get(c['id'], {}).get('description', '')}</p>
      <div class="grid grid-3">
        {''.join(_source_card(a, API_CATEGORY_MAP) for a in API_CATALOG if a.get('category') == c['id'])}
      </div>""" for c in API_CATEGORIES)}

      <h2>All sources, flat list</h2>
      <ul class="source-list">
        {''.join(f'<li><a href="{a.get("url", "#")}" target="_blank">{a["name"]}</a> — {a.get("summary", "")}</li>' for a in API_CATALOG)}
      </ul>
    </section>""" + render_footer("")
    return html


# ---------------------------------------------------------------------------
# Landing / Dashboard page
# ---------------------------------------------------------------------------

def render_index(latest):
    html = render_base_head(
        "FinRadar — India & Global Macro KPIs & Benchmarks",
        "Live macroeconomic KPIs, benchmarks and interactive tools built from public government data.",
        "/",
        base=""
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
    <p style="text-align:center; margin-top:24px;"><a href="search.html" class="btn">🔍 Search all facts &amp; KPIs</a></p>"""
    html += render_footer("")
    return html


# ---------------------------------------------------------------------------
# Categories Index page (top-level category landing page)
# ---------------------------------------------------------------------------

def render_categories_index():
    html = render_base_head(
        "Categories — All FinRadar Data",
        "Browse all 14 categories of macro and sector data on FinRadar — government, economy, agriculture, energy, transport, geo, health, education, welfare, environment, commerce, housing.",
        "/categories.html",
        base=""
    )
    html += """
    <section class="category-index-hero">
      <h1>All Categories</h1>
      <p class="hero-sub">Browse our 14 categories spanning macro-economics, sectors, geography, social services and environment — each with KPIs, facts and historical trends built from public government data.</p>
    </section>
    """

    for grp in CATEGORY_GROUPS:
        html += f"""
    <section class="category-group">
      <div class="category-group-header">
        <h2>{grp['icon']} {grp['group']}</h2>
        <p>{grp['description']}</p>
      </div>
      <div class="category-group-grid">
    """
        for cid in grp["categories"]:
            sector = SECTOR_MAP.get(cid)
            if not sector:
                continue
            facts_in_cat = FACTS_BY_CATEGORY.get(cid, [])
            kpis_in_cat = len(kpis_by_sector(sector["title"]))
            html += f"""
        <a class="category-tile" href="category/{cid}.html">
          <div class="cat-tile-header">
            <span class="cat-tile-icon">{sector['icon']}</span>
            <h3>{sector['title']}</h3>
          </div>
          <p class="cat-tile-desc">{sector['description'][:120]}…</p>
          <div class="cat-tile-footer">
            <span>{kpis_in_cat} KPIs</span>
            <span>{len(facts_in_cat)} facts</span>
          </div>
        </a>"""
        html += """
      </div>
    </section>"""

    html += render_footer("")
    return html


# ---------------------------------------------------------------------------
# Tools pages
# ---------------------------------------------------------------------------

def render_tools_index():
    """Render the tools index page listing all available calculators."""
    html = render_base_head(
        "Tools — FinRadar",
        "Interactive calculators and utilities for macroeconomic analysis — personal inflation, salary parity, and more.",
        "/tools.html",
        base=""
    )
    html += """
    <section class="tool-index-hero">
      <h1>Interactive Tools</h1>
      <p class="hero-sub">Use our calculators and utilities to explore macroeconomic data in practical ways. Each tool gets its own dedicated page for a focused experience.</p>
    </section>
    """

    tools = [
        {
            "id": "personal-inflation",
            "title": "Personal Inflation Rate",
            "icon": "📊",
            "description": "Enter your spending split across categories and see how your personal inflation compares to the official headline rate.",
            "href": "personal-inflation.html",
            "category": "Personal Finance"
        },
        {
            "id": "salary-parity",
            "title": "Salary Parity",
            "icon": "💼",
            "description": "Find the equivalent salary in another Indian city that maintains the same purchasing power.",
            "href": "salary-parity.html",
            "category": "Personal Finance"
        },
        {
            "id": "investment-growth",
            "title": "Investment Growth",
            "icon": "𓂀",
            "description": "Calculate the future value of your investments with compound interest.",
            "href": "#",
            "category": "Finance"
        },
        {
            "id": "emi-calculator",
            "title": "EMI Calculator",
            "icon": "💰",
            "description": "Estimate your Equated Monthly Installment for home, car, or personal loans.",
            "href": "#",
            "category": "Finance"
        },
        {
            "id": "cagr-calculator",
            "title": "CAGR Calculator",
            "icon": "𓂀",
            "description": "Compute the Compound Annual Growth Rate for your investments.",
            "href": "#",
            "category": "Finance"
        },
        {
            "id": "inflation-adjuster",
            "title": "Inflation Adjuster",
            "icon": "📈",
            "description": "Calculate the inflation-adjusted value of money across years.",
            "href": "#",
            "category": "Personal Finance"
        },
    ]

    for tool in tools:
        html += f"""
    <article class="tool-card">
      <div class="tool-icon">{tool['icon']}</div>
      <div>
        <h3>{tool['title']}</h3>
        <p>{tool['description']}</p>
      </div>
      <a href="{tool['href']}" class="tool-link">Open tool</a>
    </article>"""

    html += render_footer("")
    return html


def render_personal_inflation_page():
    """Render the personal inflation calculator page."""
    data = load_latest()
    html = render_base_head(
        "Personal Inflation Calculator — FinRadar",
        "Calculate your personal inflation rate based on your spending split across categories.",
        "/tools/personal-inflation.html",
        base=""
    )
    html += render_personal_inflation_form(data)
    html += render_footer("")
    return html


def render_salary_parity_page():
    """Render the salary parity calculator page."""
    data = load_latest()
    html = render_base_head(
        "Salary Parity Calculator — FinRadar",
        "Find the equivalent salary in another Indian city that maintains the same purchasing power.",
        "/tools/salary-parity.html",
        base=""
    )
    html += render_salary_parity_form(data)
    html += render_footer("")
    return html


def render_personal_inflation_form(data):
    """Render the personal inflation calculator form."""
    # Use data for headline if available
    headline = data.get("india", {}).get("real_inflation_rate", 2.4)
    
    subindices = {
        "food": 36, "fuel & light": 7, "clothing": 5, "education": 3,
        "healthcare": 3, "housing": 25, "other stuff": 17
    }
    n = len(subindices)
    base_weight = 100 // n
    default_weights = [base_weight + (1 if i < (100 - base_weight * n) else 0) for i in range(n)]
    default_weight_at = lambda i: default_weights[i]
    
    categories = list(subindices.keys())
    
    rows = []
    for i, c in enumerate(categories):
        rows.append(f"""
      <tr>
        <td>{c}</td>
        <td class="num"><input type="number" id="w-{i}" min="0" max="100" value="{default_weight_at(i)}" aria-label="Weight % for {c}"></td>
        <td class="muted" id="s-{i}">{subindices[c]}</td>
        <td class="num"><input type="number" id="e-{i}" step="0.25" min="0" value="0" aria-label="Extra % for {c}"></td>
        <td class="muted" id="a-{i}"></td>
      </tr>""")
    
    table_html = "<table>" + "".join(rows) + "</table>"
    
    html = f"""
    <section class="tool-card">
      <div class="tool-section">
        <h3>Spending Weights</h3>
        <p class="tool-note">Distribute 100% total weight across the categories below.</p>
        {table_html}
      </div>

      <div class="tool-actions">
        <button id="personal-inflation-btn" class="btn">Calculate Personal Inflation</button>
        <button id="personal-inflation-reset" class="btn small" style="margin-left: 10px;">Reset</button>
      </div>

      <div id="personal-inflation-result" class="tool-result" style="margin-top: 20px; padding: 16px; background: rgba(255,255,255,0.04); border: 1px solid var(--card-border); border-radius: 12px; min-height: 80px; display: none;">
        <h3>Your personal inflation rate: <span id="personal-inflation-result-rate">—</span>%</h3>
        <p id="personal-inflation-result-comment">Give the weights a total above 0.</p>
        <p class="muted" id="personal-inflation-result-headline">The official headline is <span id="personal-inflation-result-headline-val">{headline:.2f}</span>%.</p>
        <p class="muted small" id="personal-inflation-result-comparison"></p>
      </div>
    </section>"""

    return html


def render_salary_parity_form(data):
    """Render the salary parity calculator form."""
    city_indices = data.get("city_indices", {
        "Pune": 120, "Mumbai": 130, "Delhi": 118, "Jaipur": 90, 
        "Bengaluru": 115, "Hyderabad": 105
    })
    names = [k for k in city_indices.keys() if isinstance(city_indices[k], (int, float))]
    
    html = f"""
    <section class="tool-card">
      <div class="tool-section">
        <h3>Enter Your Salary</h3>
        <div class="tool-form">
          <input type="number" id="salary-parity-salary" value="200000" placeholder="INR" aria-label="Base salary in INR" />
          <select id="salary-parity-from">
{''.join([f'<option>{name}</option>' for name in names])}
          </select>
          <span>₹ Base in</span>
          <select id="salary-parity-to">
{''.join([f'<option>{name}</option>' for name in names])}
          </select>
          <button id="salary-parity-btn" class="btn">Calculate</button>
        </div>
      </div>

      <section class="tool-section" style="margin-top: 24px;">
        <h3>Result</h3>
        <div id="salary-parity-result" class="tool-result" style="margin-top: 16px; padding: 16px; background: rgba(255,255,255,0.04); border: 1px solid var(--card-border); border-radius: 12px; min-height: 80px; display: none;">
          <p id="salary-parity-result-text">Enter a salary and pick two cities above.</p>
        </div>
      </section>
    </section>"""

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
    (SITE_DIR / "tools").mkdir()  # NEW: tools directory

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

    print("Generating tools index.html…")
    (SITE_DIR / "tools.html").write_text(render_tools_index(), encoding="utf-8")

    print("Generating personal inflation page…")
    (SITE_DIR / "tools" / "personal-inflation.html").write_text(render_personal_inflation_page(), encoding="utf-8")

    print("Generating salary parity page…")
    (SITE_DIR / "tools" / "salary-parity.html").write_text(render_salary_parity_page(), encoding="utf-8")

    print("Generating categories index.html…")
    (SITE_DIR / "categories.html").write_text(render_categories_index(), encoding="utf-8")

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