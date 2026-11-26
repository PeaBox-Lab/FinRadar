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
import html


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


from tools_registry import (


    TOOL_CATEGORIES, TOOLS, ALL_TOOLS, tools_by_category, catalog_summary,


)





ROOT = Path(__file__).resolve().parents[2]


SITE_DIR = ROOT / "site"


DATA_FILE = ROOT / "data" / "latest_kpis.json"

EXTRA_FILE = ROOT / "data" / "extra_metrics.json"


SNAP_DIR = ROOT / "data" / "snapshots"








def load_latest():


    if DATA_FILE.exists():


        return json.loads(DATA_FILE.read_text(encoding="utf-8"))


    return {}








def load_extra():
    """Load the optional enrichment batch output without breaking older builds."""
    if EXTRA_FILE.exists():
        try:
            return json.loads(EXTRA_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
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








def verdict_class(verdict):
    """Map a verdict phrase to one of the three badge colour classes."""
    v = (verdict or "").lower()
    if v in ("strong", "on target", "good"):
        return "good"
    if v in ("moderate", "near target"):
        return "moderate"
    return "weak"


def section_head(title, eyebrow="", intro=""):
    """Consistent section heading with an optional kicker and description."""
    kicker = f'<span class="eyebrow dark">{eyebrow}</span>' if eyebrow else ""
    description = f'<p class="section-intro">{intro}</p>' if intro else ""
    return f'<div class="section-head"><div>{kicker}<h2>{title}</h2></div>{description}</div>'


def render_trend_embed(trend, kpi_id, heading=None):
    """Compact sparkline preview linking through to the full history page."""
    if not trend:
        return ""
    points = json.dumps([p["value"] for p in trend["points"]])
    label = heading or f'{trend["label"]} (history)'
    return f'''<div class="trend-embed">
      <h3>{label}</h3>
      <div class="sparkline" data-points='{points}'></div>
      <a href="../trend/{kpi_id}.html" class="btn">Full history</a>
    </div>'''


def render_source_tags(api):
    """Render an API's tags as small badges."""
    tags = api.get("tags", [])
    if not tags:
        return ""
    items = "".join(f'<span class="badge">{tag}</span>' for tag in tags)
    return f'<div class="source-tags">{items}</div>'


def render_base_head(title, description, current_url="", base=""):
    b = base  # '' for root pages, '../' for subfolder pages
    page_title = title if "FinRadar" in title else f"{title} — FinRadar"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{page_title}</title>
  <meta name="description" content="{description}" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230e7c70'/%3E%3Ccircle cx='16' cy='16' r='3' fill='white'/%3E%3Cpath d='M9 9a10 10 0 0 0 0 14M23 9a10 10 0 0 1 0 14' fill='none' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{b}styles/main.css" />
  <link rel="stylesheet" href="{b}styles/european-theme.css" />
  <link rel="canonical" href="https://finradar.example{current_url}" />
</head>
<body data-base="{b}">
  <a class="skip-link" href="#site-main">Skip to content</a>
  <header class="site-header">
    <div class="nav-inner container">
      <a class="brand" href="{b}index.html" aria-label="FinRadar home">
        <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/><path d="M6.2 6.2a8.2 8.2 0 0 0 0 11.6M17.8 6.2a8.2 8.2 0 0 1 0 11.6"/><path d="M3.3 3.3a12.3 12.3 0 0 0 0 17.4M20.7 3.3a12.3 12.3 0 0 1 0 17.4"/></svg></span>
        <span class="brand-name">FinRadar</span>
      </a>
      <span class="nav-status"><span class="status-dot"></span>Live data</span>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">
        <span></span><span></span><span></span>
      </button>
      <nav id="site-nav" class="site-nav" aria-label="Primary">
        <div class="nav-primary">
          <a href="{b}index.html" class="nav-link">Dashboard</a>
          <a href="{b}tools.html" class="nav-link">Tools</a>
          <a href="{b}search.html" class="nav-link">Search</a>
          <a href="{b}categories.html" class="nav-link">Categories</a>
          <a href="{b}sources.html" class="nav-link">Sources</a>
          <a href="{b}data-lab.html" class="nav-link">Data Lab</a>
        </div>
        <div class="nav-drop">
          <button class="nav-drop-btn" aria-expanded="false" aria-haspopup="true">Browse sectors <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg></button>
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

            <div class="nav-drop-heading">Calculators</div>


            <a href="{b}tools.html" role="menuitem">🧮 All Tools</a>


            <a href="{b}tools/emi-calculator.html" role="menuitem">💰 EMI &amp; Loans</a>


            <a href="{b}tools/sip-returns.html" role="menuitem">📈 SIP &amp; Returns</a>


            <a href="{b}tools/life-cover.html" role="menuitem">🛡️ Insurance</a>


            <a href="{b}tools/retirement-corpus.html" role="menuitem">🌴 Retirement</a>


          </div>


        </div>


      </nav>


    </div>


  </header>


  <main id="site-main" class="site-main container">"""








def render_footer(base=""):


    b = base


    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


    return f"""  </main>


  <footer class="site-footer">


    <div class="container footer-inner">


      <div class="footer-brand-col">


        <a class="brand" href="{b}index.html" aria-label="FinRadar home">
          <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/><path d="M6.2 6.2a8.2 8.2 0 0 0 0 11.6M17.8 6.2a8.2 8.2 0 0 1 0 11.6"/><path d="M3.3 3.3a12.3 12.3 0 0 0 0 17.4M20.7 3.3a12.3 12.3 0 0 1 0 17.4"/></svg></span>
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


      <p class="muted small">Developed by <a href="https://peabox.in" target="_blank">Peabox Labs (India)</a></p>


      <a href="https://github.com/rajeshceg3/FinRadar" class="footer-gh">GitHub</a>


    </div>


  </footer>


  <script src="{b}scripts/app.js"></script>


  <script src="{b}scripts/charts.js"></script>


  <script src="{b}scripts/tools.js"></script>


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


        verdict_html = f'<span class="verdict-badge {verdict_class(verdict)}">{verdict.upper()}</span>' if verdict else ""


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
    <section class="category-hero detail-hero">
      <a class="back-link" href="../categories.html">← All categories</a>
      <span class="eyebrow dark">{sector['icon']} Sector brief</span>
      <h1>{sector['title']}</h1>
      <p>{sector['description']}</p>
    </section>

    <section>
      <h2>Key Facts</h2>
      <div class="grid grid-3">{facts_html}</div>
    </section>

    <section>
      {section_head(f"KPIs — {len(kpis)} metrics", "Measured", "Latest value, plain-English read and the formula behind each metric.")}
      <div class="table-wrap">
        <table class="kpi-library-table">
          <thead><tr><th>KPI</th><th>Latest</th><th>Verdict</th><th>Insight</th><th>Formula</th><th></th></tr></thead>
          <tbody>{kpis_html}</tbody>
        </table>
      </div>
    </section>

    <section>
      {section_head("Historical Trends", "Time series", "Where each metric has been over the years.")}
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


    <section class="fact-detail detail-hero">
      <a class="back-link" href="../category/{fact['category']}.html">← Back to {SECTOR_MAP[fact['category']]['title']}</a>
      <span class="eyebrow dark">Fact file</span>
      <h1>{fact['kpi_id'].replace('_', ' ').title()}</h1>
      <p class="fact-text">{fact['fact']}</p>

      <div class="fact-meta">


        <span><strong>Source:</strong> {fact['source']}</span>


        <span><strong>Scale:</strong> {fact['scale']}</span>


        <span><strong>Why it matters:</strong> {fact['why_it_matters']}</span>


      </div>


      {f'<p class="latest-value">Latest value: <strong>{humanize(val)}</strong></p>' if val is not None else ''}


      {render_trend_embed(trend, kpi_id)}


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


    <section class="trend-detail detail-hero">
      <a class="back-link" href="../categories.html">← All categories</a>
      <span class="eyebrow dark">Historical series</span>
      <h1>{trend['label']}</h1>
      <p class="muted"><strong>Source:</strong> {trend['source']}</p>
      {f'<p class="latest-value">Latest ({years[-1]}): <strong>{humanize(values[-1])} {trend["unit"]}</strong></p>' if values else ''}

      <div class="chart-wrap">
        <canvas id="trend-chart" aria-label="Historical chart for {trend['label']}" role="img"></canvas>
      </div>

      <h3>Year-by-year values</h3>
      <div class="table-wrap">
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





    html += """</tbody></table></div>

      <h3>What this trend tells you</h3>

      <p>""" + (kpi_def.get("insight", "Trend data for this metric.") if kpi_def else "Trend data for this metric.") + """</p>


      <a href="../category/""" + (next((c for c, facts in FACTS_BY_CATEGORY.items() if any(fi["kpi_id"]==kpi_id for fi in facts)), "economy")) + """.html" class="btn">← Back</a>


    </section>"""


    html += render_footer("../")


    # Inline the chart data for the simple JS chart


    html = html.replace("</body>", f"""


  <script>


    window.__TREND_CHART_DATA__ = {{


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


    back_href = f"../category/{cat}.html" if cat else "../index.html"
    back_label = SECTOR_MAP[cat]["title"] if cat else "Dashboard"
    verdict_short = verdict.split(".")[0].strip() if val is not None else "No data"

    html += f"""
    <section class="kpi-detail detail-hero">
      <a class="back-link" href="{back_href}">← Back to {back_label}</a>
      <span class="eyebrow dark">{kpi_def['sector']} · KPI detail</span>
      <header>
        <h1>{kpi_def['name']}</h1>
        <p class="muted"><strong>Frequency:</strong> {kpi_def.get('frequency', 'monthly')} · <strong>Direction:</strong> {kpi_def.get('direction', '—').replace('_', ' ')}</p>
      </header>

      <div class="kpi-headline">
        <div class="kpi-value-large">{humanize(val) + ' ' + kpi_def['unit'] if val is not None else '—'}</div>
        <div class="verdict-badge {verdict_class(verdict_short)}">{verdict_short.upper()}</div>
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





      {render_trend_embed(trend, kpi_id, "Historical trend")}





      <a href="../category/{cat}.html" class="btn">← Back to {SECTOR_MAP[cat]['title'] if cat else 'Dashboard'}</a>


    </section>"""


    html += render_footer("../")


    return html








# ---------------------------------------------------------------------------


# Search page


# ---------------------------------------------------------------------------





def render_search_page(latest, extra=None):


    items = search_index()
    if extra:
        items.extend(build_extra_search_items(extra))
    items.extend(build_tool_search_items())





    html = render_base_head(


        "Search — Find any data fact or KPI",


        "Search across KPIs, expanded official data series, derived metrics, relationships and plain-English facts.",


        "/search.html",


        base=""


    )


    html += """


    <section class="search-page">
      <span class="eyebrow dark">Find anything</span>
      <h1>Search FinRadar</h1>
      <p class="hero-sub">Look up any fact, KPI or historical series across all 14 sectors.</p>
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


        <a href="${r.url || (r.type==='fact' ? 'facts/'+r.id+'.html' : 'kpi/'+r.id+'.html')}" class="search-result">


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

    stats = api.get("stats", {})
    series_used = stats.get("series_used", stats.get("indicators_used", 0))
    frequency = api.get("frequency") or stats.get("frequency", "N/A")
    access = (api.get("access", "") or "").split("·")[0].strip()

    return f"""


      <article class="card source-card">


        <div class="card-header">


          <h3><a href="{api.get('url', '#')}" target="_blank">{api['name']}</a></h3>


          <span class="badge">{cat_map.get(api.get('category', ''), {}).get('title', api.get('category', 'General'))}</span>


        </div>


        <p class="card-desc">{api.get('summary', '')}</p>


        <div class="source-stats">


          <div class="source-stat"><strong>{series_used}</strong><span>Series used</span></div>


          <div class="source-stat"><strong>{stats.get('history', 'N/A')}</strong><span>Coverage / era</span></div>


          <div class="source-stat"><strong>{frequency}</strong><span>Frequency</span></div>


          <div class="source-stat"><strong>{access}</strong><span>Access</span></div>


        </div>


        {render_source_tags(api)}


        <p class="muted small">Provider: {api.get('provider', '')} · Tags: {', '.join(api.get('tags', []))}</p>


      </article>"""








def render_sources_page():
    from api_catalog import API_CATALOG, API_CATEGORY_MAP, API_CATEGORIES, catalog_summary
    summ = catalog_summary()

    # Build these separately: Python 3.10 does not allow multiline expressions
    # (or escaped quotes) inside an f-string expression.
    category_sections = []
    for category in API_CATEGORIES:
        meta = API_CATEGORY_MAP.get(category["id"], {})
        cards = "".join(
            _source_card(api, API_CATEGORY_MAP)
            for api in API_CATALOG
            if api.get("category") == category["id"]
        )
        category_sections.append(f'''
      <h2>{meta.get("icon", "📁")} {meta.get("title", category["id"])}</h2>
      <p class="muted">{meta.get("description", "")}</p>
      <div class="grid grid-3">
        {cards}
      </div>''')
    categories_html = "".join(category_sections)

    source_items = []
    for api in API_CATALOG:
        url = api.get("url", "#")
        name = api.get("name", "")
        summary = api.get("summary", "")
        source_items.append(
            f'<li><a href="{url}" target="_blank" rel="noopener">{name}</a> — {summary}</li>'
        )
    source_list_html = "".join(source_items)

    html = render_base_head(
        "Data Sources — Catalog",
        f"Every API, dataset and portal FinRadar draws from — {summ['total_apis']} categorised sources with summary stats for each.",
        "/sources.html",
        base=""
    )
    html += f"""
    <section>
      <span class="eyebrow dark">Provenance</span>
      <h1>Data Sources Catalog</h1>
      <p class="muted">FinRadar computes KPIs from {summ['total_apis']} public government APIs across {summ['total_categories']} categories. Every source is categorised under a proper tag group and summarised with the key statistics we use.</p>

      <div class="grid grid-4 source-summary-grid">
        <div class="card source-summary-card"><strong>{summ['total_apis']}</strong><span>APIs catalogued</span></div>
        <div class="card source-summary-card"><strong>{summ['total_categories']}</strong><span>Categories</span></div>
        <div class="card source-summary-card"><strong>{summ['total_series']}</strong><span>Data series used</span></div>
        <div class="card source-summary-card"><strong>{summ['open_apis']}</strong><span>Open access</span></div>
      </div>

      {categories_html}

      <h2>All sources, flat list</h2>
      <ul class="source-list">
        {source_list_html}
      </ul>
    </section>""" + render_footer("")
    return html







# ---------------------------------------------------------------------------


# Landing / Dashboard page


# ---------------------------------------------------------------------------





def esc(value):
    """Escape untrusted/API-sourced text before embedding it in HTML."""
    return html.escape("" if value is None else str(value), quote=True)


def fmt_extra_value(value, unit=""):
    """Compact, human-readable formatting for enrichment values."""
    if value is None or not isinstance(value, (int, float)):
        return "—"
    if abs(value) >= 1000:
        text = f"{value:,.0f}"
    elif abs(value) >= 10:
        text = f"{value:,.1f}"
    else:
        text = f"{value:,.2f}"
    return esc(text + (" " + unit if unit else ""))


def fmt_coefficient(value):
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:+.3f}"


def build_extra_search_items(extra):
    """Make enrichment content searchable from the existing search page."""
    items = []

    def add(url, title, category, source, text, kind):
        items.append({
            "id": url,
            "type": kind,
            "url": url,
            "title": title,
            "category": category,
            "source": source,
            "text": text,
        })

    for series in extra.get("series", []):
        key = str(series.get("key", "")).replace(":", "-")
        add(
            "data-lab.html#series-" + key,
            series.get("label", "Series"),
            series.get("sector", "Data Lab"),
            series.get("source", "World Bank"),
            (series.get("definition", "") + " " + series.get("guide", "")).strip(),
            "series",
        )

    for kpi in extra.get("kpis", []):
        add(
            "data-lab.html#kpi-" + str(kpi.get("id", "")),
            kpi.get("name", "Derived KPI"),
            kpi.get("sector", "Data Lab"),
            ", ".join(kpi.get("sources", [])),
            (kpi.get("definition", "") + " " + kpi.get("guide", "")).strip(),
            "kpi",
        )

    for fact in extra.get("census", {}).get("facts", []):
        add(
            "data-lab.html#census",
            fact.get("name", "Census fact"),
            "Census",
            extra.get("census", {}).get("source", {}).get("name", "Census of India"),
            (fact.get("definition", "") + " " + fact.get("guide", "")).strip(),
            "census",
        )

    for rel in extra.get("relationships", []):
        add(
            "data-lab.html#relationships",
            rel.get("label", "Relationship"),
            rel.get("factor", "Relationships"),
            "World Bank",
            (rel.get("interpretation", "") + " Coefficients are correlations, not causation.").strip(),
            "relationship",
        )

    return items


def render_data_lab(extra):
    """Publish the curated raw series, derived KPIs, relationships and catalog."""
    title = "Data Lab — Expanded Official Data & Derived KPIs"
    description = "Curated World Bank, Census of India and data.gov.in data with definitions, guides, derived KPIs and correlations."
    hero = render_base_head(title, description, "/data-lab.html", base="")

    if not extra:
        hero += """
    <section>
      <span class="eyebrow dark">Data Lab</span>
      <h1>Expanded data is not published yet</h1>
      <p class="muted">Run <code>python scripts/pipeline/enrichment.py</code> to generate <code>data/extra_metrics.json</code>, then regenerate the site.</p>
    </section>"""
        return hero + render_footer("")

    generated = esc(extra.get("generated_at"))
    series = extra.get("series", [])
    derived = extra.get("kpis", [])
    relationships = extra.get("relationships", [])
    census = extra.get("census", {})
    datagov = extra.get("data_gov_resources", [])
    discovery = extra.get("discovery", {})
    live_count = sum(1 for item in series if item.get("status") == "live")

    hero += f"""
    <section class="lab-hero">
      <span class="eyebrow dark">Data Lab · updated {generated}</span>
      <h1>Expanded official data, explained</h1>
      <p class="hero-sub">Raw series are published with their source, unit, definition and a plain-English user guide. Derived KPIs show exactly how they are calculated, and relationships show how Indian metrics move with macro and global factors.</p>
      <div class="grid grid-4 source-summary-grid">
        <div class="card source-summary-card"><strong>{len(series)}</strong><span>Curated series</span></div>
        <div class="card source-summary-card"><strong>{live_count}</strong><span>Live this run</span></div>
        <div class="card source-summary-card"><strong>{len(derived)}</strong><span>Derived KPIs</span></div>
        <div class="card source-summary-card"><strong>{len(relationships)}</strong><span>Relationships</span></div>
      </div>
    </section>"""

    series_rows = []
    for item in series:
        key = str(item.get("key", "")).replace(":", "-")
        anchor = "series-" + key
        points = json.dumps([p.get("value") for p in item.get("points", []) if p.get("value") is not None])
        spark = f'<div class="sparkline" data-points=\'{points}\'></div>' if points else ""
        status = item.get("status", "unavailable")
        status_class = "good" if status == "live" else "moderate" if status == "cached" else "weak"
        series_rows.append(f"""
        <tr id="{esc(anchor)}">
          <td><strong>{esc(item.get('label'))}</strong><br><small class="muted">{esc(item.get('country'))} · {esc(item.get('category'))}</small></td>
          <td>{fmt_extra_value(item.get('latest_value'), item.get('unit'))}<br><small class="muted">{esc(item.get('latest_year'))}</small></td>
          <td>{spark}</td>
          <td><span class="badge {status_class}">{esc(status)}</span><br><small class="muted">{esc(item.get('frequency'))}</small></td>
          <td><details><summary>Definition</summary><p>{esc(item.get('definition'))}</p></details></td>
          <td><details><summary>User guide</summary><p>{esc(item.get('guide'))}</p></details><small class="muted"><a href="{esc(item.get('source_url'))}" target="_blank" rel="noopener">Source ↗</a></small></td>
        </tr>""")
    series_table = "".join(series_rows)

    hero += f"""
    <section id="series">
      {section_head('Published data series', 'Raw data', 'Every series below is fetched from an official public API. Open Definition or User guide for context before using a number.')}
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Series</th><th>Latest</th><th>History</th><th>Status</th><th>Definition</th><th>Guide</th></tr></thead>
          <tbody>{series_table}</tbody>
        </table>
      </div>
    </section>"""

    derived_cards = []
    for item in derived:
        anchor = "kpi-" + str(item.get("id", ""))
        sources = ", ".join(item.get("sources", []))
        derived_cards.append(f"""
        <article class="card data-kpi-card" id="{esc(anchor)}">
          <div class="card-header"><h3>{esc(item.get('name'))}</h3><span class="badge">{esc(item.get('status'))}</span></div>
          <div class="data-kpi-value">{fmt_extra_value(item.get('value'), item.get('unit'))}</div>
          <p><strong>Formula:</strong> {esc(item.get('formula'))}</p>
          <p><strong>Definition:</strong> {esc(item.get('definition'))}</p>
          <p><strong>User guide:</strong> {esc(item.get('guide'))}</p>
          <p class="muted small">Sources: {esc(sources)} · Latest year: {esc(item.get('latest_year'))} · {esc(item.get('frequency'))}</p>
        </article>""")
    derived_html = "".join(derived_cards)

    hero += f"""
    <section id="derived">
      {section_head('Innovative derived KPIs', 'Computed metrics', 'These are not published by any single authority. Each card shows the exact inputs and formula so you can reproduce or challenge the number.')}
      <div class="grid grid-2">{derived_html}</div>
    </section>"""

    rel_rows = []
    for item in relationships:
        coef = item.get("coefficient")
        width = int(abs(coef) * 100) if isinstance(coef, (int, float)) else 0
        direction = "positive" if isinstance(coef, (int, float)) and coef >= 0 else "negative"
        rel_rows.append(f"""
        <tr>
          <td><strong>{esc(item.get('label'))}</strong><br><small class="muted">{esc(item.get('factor'))}</small></td>
          <td>{esc(item.get('a'))}<br><small class="muted">vs</small><br>{esc(item.get('b'))}</td>
          <td><div class="relation-cell"><span class="relation-bar {direction}" style="width:{width}%"></span><strong>{fmt_coefficient(coef)}</strong></div></td>
          <td><small>{esc(item.get('interpretation'))}<br><span class="muted">{esc(item.get('period'))} · {esc(item.get('observations'))} observations</span></small></td>
        </tr>""")
    rel_table = "".join(rel_rows)

    hero += f"""
    <section id="relationships">
      {section_head('Macro and global relationships', 'Correlation lens', 'Pearson coefficients on overlapping annual observations. These show co-movement, not causation. Use them as prompts for deeper analysis.')}
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Relationship</th><th>Factors</th><th>Coefficient</th><th>Reading</th></tr></thead>
          <tbody>{rel_table}</tbody>
        </table>
      </div>
    </section>"""

    census_cards = []
    for fact in census.get("facts", []):
        census_cards.append(f"""
        <article class="card census-card">
          <h3>{esc(fact.get('name'))}</h3>
          <div class="data-kpi-value">{fmt_extra_value(fact.get('value'), fact.get('unit'))}</div>
          <p><strong>Definition:</strong> {esc(fact.get('definition'))}</p>
          <p><strong>User guide:</strong> {esc(fact.get('guide'))}</p>
        </article>""")
    census_html = "".join(census_cards)
    census_source = census.get("source", {})
    census_url = esc(census_source.get("url"))

    hero += f"""
    <section id="census">
      {section_head('Census of India benchmarks', 'Decadal data', 'Official 2011 enumeration figures. They are a benchmark, not a daily feed; annual estimates come from the World Bank population series above.')}
      <div class="grid grid-3">{census_html}</div>
      <p class="muted small"><a href="{census_url}" target="_blank" rel="noopener">{esc(census_source.get('name'))} ↗</a> · {esc(census_source.get('frequency'))}</p>
    </section>"""

    dg_cards = []
    for resource in datagov:
        stats = resource.get("stats", {})
        dg_cards.append(f"""
        <article class="card source-card">
          <div class="card-header"><h3><a href="{esc(resource.get('url'))}" target="_blank" rel="noopener">{esc(resource.get('name'))}</a></h3><span class="badge">{esc(resource.get('status'))}</span></div>
          <p>{esc(resource.get('definition'))}</p>
          <p><strong>User guide:</strong> {esc(resource.get('guide'))}</p>
          <div class="source-stats">
            <div class="source-stat"><strong>{esc(stats.get('total_records'))}</strong><span>Records</span></div>
            <div class="source-stat"><strong>{esc(stats.get('sample_period'))}</strong><span>Sample date</span></div>
            <div class="source-stat"><strong>{fmt_extra_value(stats.get('sample_modal_price_min'))} – {fmt_extra_value(stats.get('sample_modal_price_max'))}</strong><span>Sample modal price</span></div>
          </div>
          <p class="muted small">Provider: {esc(resource.get('provider'))} · Fields: {esc(', '.join(stats.get('fields_available', [])))}</p>
          {('<p class="muted small">' + esc(resource.get('note')) + '</p>') if resource.get('note') else ''}
        </article>""")
    dg_html = "".join(dg_cards) if dg_cards else '<p class="muted">No curated data.gov.in resource was reachable in this run.</p>'

    hero += f"""
    <section id="datagov">
      {section_head('Curated data.gov.in resources', 'Live official feed', 'A small, high-value subset of data.gov.in is fetched every night. Set DATA_GOV_IN_TOKEN to use a personal key instead of the rate-limited public sample key.')}
      <div class="grid grid-2">{dg_html}</div>
    </section>"""

    portal_items = []
    for portal in discovery.get("portals", []):
        portal_items.append(f"""
        <li><a href="{esc(portal.get('url'))}" target="_blank" rel="noopener">{esc(portal.get('name'))}</a> — <span class="badge">{esc(portal.get('category_label'))}</span> {esc(portal.get('summary'))} <small class="muted">{esc(portal.get('access'))}</small></li>""")
    portals_html = "".join(portal_items)
    apisetu = discovery.get("api_setu", {})

    hero += f"""
    <section id="discovery">
      {section_head('Discovery catalog', 'Source scan', 'Official portal metadata is catalogued here; the series actually fetched are published above. This is a curated scan, not an exhaustive crawl of every dataset.')}
      <ul class="source-list">{portals_html}</ul>
      <div class="callout">
        <h3>{esc(apisetu.get('name'))}</h3>
        <p>{esc(apisetu.get('status'))} · <a href="{esc(apisetu.get('url'))}" target="_blank" rel="noopener">Directory ↗</a></p>
        <p class="muted small">{esc(apisetu.get('access'))} · APISETU_TOKEN: {esc(apisetu.get('token'))}</p>
      </div>
      <p class="muted small">{esc(discovery.get('note'))}</p>
    </section>"""

    hero += """
    <section id="guide">
      <span class="eyebrow dark">User guide</span>
      <h2>How to use this data responsibly</h2>
      <ol class="guide-list">
        <li><strong>Read the unit and frequency.</strong> Annual World Bank figures are not monthly snapshots; Census figures are decadal.</li>
        <li><strong>Use the definition before comparing.</strong> Similar labels can use different age ranges or methodologies.</li>
        <li><strong>Check the formula on derived KPIs.</strong> They combine published inputs; they are interpretations, not official statistics.</li>
        <li><strong>Treat correlations as clues.</strong> A coefficient shows co-movement over the stated period, not cause and effect.</li>
        <li><strong>Refresh cadence.</strong> The separate enrichment workflow runs every night at 03:15 UTC and regenerates this page.</li>
        <li><strong>Access boundary.</strong> Public-key sources are limited; a personal data.gov.in key and APIsetu consumer credentials unlock larger volumes.</li>
      </ol>
    </section>"""

    return hero + render_footer("")


def render_index(latest):
    html = render_base_head(
        "FinRadar — India & Global Macro KPIs & Benchmarks",
        "Live macroeconomic KPIs, benchmarks and interactive tools built from public government data.",
        "/",
        base=""
    )
    html += f"""
    <section class="hero">
      <div class="hero-inner">
        <span class="eyebrow">Public data, refreshed daily</span>
        <h1>Real economy numbers, <span>plain English.</span></h1>
        <p class="hero-sub">FinRadar turns public government data into living KPIs — real interest rates, digital velocity, fiscal health — and publishes benchmarks and reports you can cite. Every number is a derived metric, not a raw table.</p>
        <div class="hero-actions">
          <a href="#kpis" class="btn btn-primary">Explore live KPIs <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
          <a href="tools.html" class="btn btn-ghost">Open calculators</a>
        </div>
        <div class="hero-stats" id="hero-stats"></div>
      </div>
      <div class="hero-visual" aria-hidden="true">
        <span class="orbit orbit-1"></span><span class="orbit orbit-2"></span><span class="orbit orbit-3"></span>
        <div class="signal-card">
          <span class="signal-label">Macro cycle</span>
          <strong id="hero-signal-value">—</strong>
          <span class="signal-foot">Composite · 0–100</span>
        </div>
      </div>
    </section>

    <section class="kpis" id="kpis">
      {section_head("Live KPIs — what the numbers mean", "Dashboard", "Derived spreads, velocities and composite scores — never raw tables. Values refresh daily.")}
      <div class="grid" id="kpi-grid"></div>
    </section>

    <section class="benchmarks">
      {section_head("Original benchmarks we publish", "Indexes", "Four composites built entirely from public data, designed to make the economy legible.")}
      <div class="grid benchmark-grid">
        <article class="card benchmark-card">
          <span class="bench-index">01 / MACRO</span>
          <h3>India High-Frequency Macro Cycle Index</h3>
          <p>A 0–100 score blending GST, UPI, power demand, IIP, inflation, repo rate and GDP growth into one number that classifies the economy.</p>
          <div class="bench-stat" id="bench-macro-cycle-value">—</div>
          <span class="bench-tag">Composite score · 0–100</span>
        </article>
        <article class="card benchmark-card">
          <span class="bench-index">02 / CITIES</span>
          <h3>City Salary-Parity Benchmark</h3>
          <p>What salary in Jaipur gives the same purchasing power as ₹20 LPA in Mumbai? Try the calculator below.</p>
          <div class="bench-stat">₹ → ₹</div>
          <span class="bench-tag">Cost-of-living adjusted</span>
        </article>
        <article class="card benchmark-card">
          <span class="bench-index">03 / STATES</span>
          <h3>State-Wise Fiscal Health Scorecard</h3>
          <p>Ranks all 28 states quarterly on GST growth, debt-to-GSDP and capex ratio.</p>
          <div class="bench-stat">28</div>
          <span class="bench-tag">States ranked quarterly</span>
        </article>
        <article class="card benchmark-card">
          <span class="bench-index">04 / GLOBAL</span>
          <h3>Global Emerging Market Resilience</h3>
          <p>India vs Vietnam, Indonesia, Brazil and Mexico on GDP growth, current account, FDI and digital infrastructure.</p>
          <div class="bench-stat" id="bench-resilience-value">—</div>
          <span class="bench-tag">Peer ranking</span>
        </article>
      </div>
    </section>

    <section class="tools">
      {section_head("Interactive tools", "Calculators", "Put the data to work on your own numbers — no sign-up, no tracking.")}
      <div class="tool-card">
        <div class="tool-card-head">
          <span class="tool-icon-wrap" aria-hidden="true">📊</span>
          <div>
            <h3>Your personal inflation rate</h3>
            <p class="sub">Enter your spending split — food, fuel, education, healthcare, housing — and see how it compares with the headline.</p>
          </div>
        </div>
        <div class="inflation-table-wrap">
          <table class="data-table inflation-table">
            <thead><tr><th>Category</th><th>Weight %</th><th>Sub-index</th><th>Extra %</th><th>Adjusted</th></tr></thead>
            <tbody id="personal-inflation-rows"></tbody>
          </table>
        </div>
        <div class="tool-actions">
          <button id="personal-inflation-btn" class="btn btn-primary">Calculate</button>
          <button id="personal-inflation-reset" class="btn btn-quiet small">Reset</button>
        </div>
        <div id="personal-inflation-result" class="tool-result"></div>
      </div>
      <div class="tool-card">
        <div class="tool-card-head">
          <span class="tool-icon-wrap" aria-hidden="true">💼</span>
          <div>
            <h3>Salary parity between two cities</h3>
            <p class="sub">Enter a base salary and pick two cities. We tell you the equivalent purchasing-power salary.</p>
          </div>
        </div>
        <div class="tool-form">
          <label class="field"><span>Annual salary (₹)</span><input type="number" id="salary-parity-salary" value="200000" placeholder="INR" /></label>
          <label class="field"><span>From city</span><select id="salary-parity-from"></select></label>
          <label class="field"><span>To city</span><select id="salary-parity-to"></select></label>
          <button id="salary-parity-btn" class="btn btn-primary">Calculate</button>
        </div>
        <div id="salary-parity-result" class="tool-result"></div>
      </div>
    </section>

    <section>
      {section_head("Explore by category", "Browse", "14 sectors, each with facts, KPIs and historical trends.")}
      <div class="grid grid-3">
    """
    for s in SECTORS:
        facts_in_cat = FACTS_BY_CATEGORY.get(s["id"], [])
        kpis_in_cat = len(kpis_by_sector(s["title"]))
        html += f"""
        <article class="card category-card">
          <span class="category-icon" aria-hidden="true">{s['icon']}</span>
          <div class="card-header">
            <h3>{s['title']}</h3>
            <span class="kpi-count small">{kpis_in_cat} KPIs</span>
          </div>
          <p class="card-desc">{s['description']}</p>
          <div class="card-footer">
            <span class="muted small">{len(facts_in_cat)} facts</span>
            <a href="category/{s['id']}.html" class="btn small">View <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
          </div>
        </article>"""

    html += f"""
      </div>
    </section>

    <section class="cta-band">
      <div>
        <h2>Can't find the number you need?</h2>
        <p>Search every fact, KPI and trend published on FinRadar.</p>
      </div>
      <a href="search.html" class="btn btn-ghost">Search all data <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
    </section>"""
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
      <span class="eyebrow dark">Complete taxonomy</span>
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





def build_tool_search_items():
    """Make every calculator discoverable from the global search page."""
    cat_map = {category["id"]: category["title"] for category in TOOL_CATEGORIES}
    items = []
    for item in ALL_TOOLS:
        category = cat_map.get(item["category"], item["category"])
        haystack = " ".join([
            item.get("description", ""),
            item.get("formula", ""),
            item.get("guide", ""),
            " ".join(item.get("outcomes", [])),
        ])
        items.append({
            "id": item["id"],
            "title": item["title"],
            "category": category,
            "text": haystack,
            "source": "FinRadar calculator",
            "url": "tools/" + item["href"],
            "type": "tool",
        })
    return items


def render_tools_index():
    """Render the categorized calculator hub."""
    summary = catalog_summary()
    html = render_base_head(
        "Tools — FinRadar",
        "Interactive banking, insurance, loan, investment and personal-finance calculators with formulas and guides.",
        "/tools.html",
        base="",
    )

    html += """
    <section class="tools-hero">
      <span class="eyebrow dark">Calculator hub</span>
      <h1>Money decisions, <span>made legible.</span></h1>
      <p class="hero-sub">From EMIs and amortization schedules to term cover, SIPs and retirement planning — every calculator shows its inputs, formula and interpretation. No sign-up, no data leaving your browser.</p>
      <div class="hero-actions">
        <a href="#loans" class="btn btn-primary">Start with loans</a>
        <a href="#guide" class="btn btn-ghost">How to use these tools</a>
      </div>
      <div class="tools-hero-stats">
        <div><strong>{total}</strong><span>Calculators</span></div>
        <div><strong>{categories}</strong><span>Practical categories</span></div>
        <div><strong>100%</strong><span>Runs in your browser</span></div>
      </div>
    </section>
    """.format(total=summary["total_tools"], categories=summary["categories"])

    for category in TOOL_CATEGORIES:
        items = tools_by_category(category["id"])
        html += section_head(
            category["title"],
            "Calculator suite",
            category["description"],
        )
        html += '<div class="grid grid-3 tools-grid" id="' + category["id"] + '">'
        for item in items:
            href = "tools/" + item["href"]
            outputs = " · ".join(item["outcomes"][:3])
            html += f'''
      <article class="card tool-card index tool-hub-card">
        <span class="tool-icon-wrap" aria-hidden="true">{item['icon']}</span>
        <span class="badge">{esc(item['eyebrow'])}</span>
        <h3>{esc(item['title'])}</h3>
        <p>{esc(item['description'])}</p>
        <p class="tool-output-line"><strong>Outputs:</strong> {esc(outputs)}</p>
        <div class="card-footer"><a href="{href}" class="tool-link">Open calculator →</a></div>
      </article>'''
        html += "</div>"

    html += section_head(
        "How to use the calculator hub",
        "User guide",
        "Pick a tool, adjust the inputs and read the result alongside the formula and notes.",
    )
    html += """
    <div class="grid grid-3 calc-guide-grid" id="guide">
      <article class="card calc-guide-card">
        <span class="guide-step">01</span>
        <h3>Enter realistic inputs</h3>
        <p>Defaults are illustrative Indian-market values. Replace them with your actual numbers, rates and tenure.</p>
      </article>
      <article class="card calc-guide-card">
        <span class="guide-step">02</span>
        <h3>Read the formula</h3>
        <p>Every page states the exact calculation. This makes it easy to audit a result or compare two offers.</p>
      </article>
      <article class="card calc-guide-card">
        <span class="guide-step">03</span>
        <h3>Stress-test the answer</h3>
        <p>Change the rate, inflation or return by a few points. The range matters more than one exact figure.</p>
      </article>
    </div>
    <div class="callout">
      <strong>Important:</strong> These calculators are decision aids, not financial advice. Lender tariffs, insurer underwriting and tax rules can change the final number.
    </div>
    """

    html += render_footer("")
    return html


def render_tool_page(tool):
    """Render a dedicated page for one registry-driven calculator."""
    config_json = json.dumps(tool, ensure_ascii=False).replace("</", "<\\/")
    cat_map = {category["id"]: category for category in TOOL_CATEGORIES}
    category = cat_map.get(tool["category"], TOOL_CATEGORIES[0])
    related = [item for item in tools_by_category(tool["category"]) if item["id"] != tool["id"]][:4]

    html = render_base_head(
        tool["title"] + " — FinRadar",
        tool["description"],
        "/tools/" + tool["id"] + ".html",
        base="../",
    )

    html += f'''
    <section class="calc-hero">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../index.html">Dashboard</a><span>/</span>
        <a href="tools.html">Tools</a><span>/</span>
        <span>{esc(category['title'])}</span>
      </nav>
      <span class="eyebrow dark">{esc(tool['eyebrow'])}</span>
      <h1><span class="calc-hero-icon" aria-hidden="true">{tool['icon']}</span> {esc(tool['title'])}</h1>
      <p class="hero-sub">{esc(tool['description'])}</p>
    </section>

    <section class="calc-layout">
      <article class="card calc-card">
        <div class="calc-card-head">
          <div><h2>Calculate</h2><p class="muted">Change any input and press calculate.</p></div>
          <span class="badge">Inputs: {len(tool['fields'])}</span>
        </div>
        <form id="calc-form" class="calc-form"></form>
        <div class="calc-actions">
          <button type="button" id="calc-run" class="btn btn-primary">Calculate</button>
          <button type="button" id="calc-reset" class="btn btn-quiet">Reset defaults</button>
        </div>
        <div id="calc-result" class="calc-results" aria-live="polite"></div>
      </article>

      <aside class="calc-sidebar">
        <article class="card calc-info-card">
          <span class="calc-info-label">Formula</span>
          <p>{esc(tool['formula'])}</p>
        </article>
        <article class="card calc-info-card">
          <span class="calc-info-label">User guide</span>
          <p>{esc(tool['guide'])}</p>
          <ul class="guide-list">
            {''.join('<li>' + esc(outcome) + '</li>' for outcome in tool['outcomes'])}
          </ul>
        </article>
        <article class="card calc-info-card note-card">
          <span class="calc-info-label">Notes</span>
          {''.join('<p>' + esc(note) + '</p>' for note in tool['notes'])}
        </article>
      </aside>
    </section>

    <section class="related-tools">
      <div class="section-head"><div><span class="eyebrow dark">Keep exploring</span><h2>Related calculators</h2></div></div>
      <div class="grid grid-4">
        {''.join('<a class="card related-tool" href="' + item['href'] + '"><span aria-hidden="true">' + item['icon'] + '</span><strong>' + esc(item['title']) + '</strong><small>Open calculator →</small></a>' for item in related)}
      </div>
    </section>

    <script type="application/json" id="calc-config">{config_json}</script>
    '''
    html += render_footer("../")
    return html


def render_personal_inflation_page():


    """Render the personal inflation calculator page."""


    data = load_latest()


    html = render_base_head(


        "Personal Inflation Calculator — FinRadar",


        "Calculate your personal inflation rate based on your spending split across categories.",


        "/tools/personal-inflation.html",


        base="../"


    )


    html += render_personal_inflation_form(data)
    html += render_footer("../")

    return html








def render_salary_parity_page():


    """Render the salary parity calculator page."""


    data = load_latest()


    html = render_base_head(


        "Salary Parity Calculator — FinRadar",


        "Find the equivalent salary in another Indian city that maintains the same purchasing power.",


        "/tools/salary-parity.html",


        base="../"


    )


    html += render_salary_parity_form(data)
    html += render_footer("../")

    return html








def render_personal_inflation_form(data):
    """Render the personal inflation calculator form.

    The markup matches the shared app.js tool initialiser so the same logic
    runs on both the dashboard and this dedicated page.
    """
    subindices = data.get("subindices") or {
        "food": 36, "fuel & light": 7, "clothing": 5, "education": 3,
        "healthcare": 3, "housing": 25, "other stuff": 17
    }
    categories = [(name, value) for name, value in subindices.items()
                  if isinstance(value, (int, float))]
    n = max(len(categories), 1)
    base_weight = 100 // n
    weights = [base_weight + (1 if i < (100 - base_weight * n) else 0) for i in range(n)]

    rows = []
    for i, (name, subindex) in enumerate(categories):
        rows.append(f"""
          <tr>
            <td>{name}</td>
            <td class="num"><input type="number" id="w-{i}" min="0" max="100" value="{weights[i]}" aria-label="Weight % for {name}"></td>
            <td class="num"><span class="muted" id="s-{i}">{subindex}</span></td>
            <td class="num"><input type="number" id="e-{i}" step="0.25" min="0" value="0" aria-label="Extra % for {name}"></td>
            <td class="num"><strong class="adj" id="a-{i}"></strong></td>
          </tr>""")

    html = f"""
    <section class="tool-card">
      <span class="eyebrow dark">Personal finance</span>
      <h1>Personal Inflation Calculator</h1>
      <p class="sub">Your spending mix is not the average household's. Adjust the weights and see what inflation actually feels like for you.</p>
      <h3>Spending weights</h3>
      <p class="tool-note">Distribute 100% across the categories below, then add any category-specific shock.</p>
      <div class="inflation-table-wrap">
        <table class="data-table inflation-table">
          <thead><tr><th>Category</th><th>Weight %</th><th>Sub-index</th><th>Extra %</th><th>Adjusted</th></tr></thead>
          <tbody id="personal-inflation-rows">{''.join(rows)}</tbody>
        </table>
      </div>
      <div class="tool-actions">
        <button id="personal-inflation-btn" class="btn btn-primary">Calculate personal inflation</button>
        <button id="personal-inflation-reset" class="btn btn-quiet small">Reset</button>
      </div>
      <div id="personal-inflation-result" class="tool-result"></div>
    </section>"""
    return html


def render_salary_parity_form(data):
    """Render the salary parity calculator form."""
    city_indices = data.get("city_indices") or {
        "Pune": 120, "Mumbai": 130, "Delhi": 118, "Jaipur": 90,
        "Bengaluru": 115, "Hyderabad": 105
    }
    names = [k for k, v in city_indices.items() if isinstance(v, (int, float))]
    options = "".join(f"<option>{name}</option>" for name in names)

    html = f"""
    <section class="tool-card">
      <span class="eyebrow dark">Personal finance</span>
      <h1>Salary Parity Calculator</h1>
      <p class="sub">Find the salary in another city that buys exactly the same lifestyle as your current one.</p>
      <div class="tool-form">
        <label class="field"><span>Annual salary (₹)</span><input type="number" id="salary-parity-salary" value="200000" placeholder="INR" aria-label="Base salary in INR" /></label>
        <label class="field"><span>From city</span><select id="salary-parity-from">{options}</select></label>
        <label class="field"><span>To city</span><select id="salary-parity-to">{options}</select></label>
        <button id="salary-parity-btn" class="btn btn-primary">Calculate</button>
      </div>
      <div id="salary-parity-result" class="tool-result"></div>
    </section>"""
    return html







# ---------------------------------------------------------------------------


# Main generator


# ---------------------------------------------------------------------------





def main():


    latest = load_latest()
    extra = load_extra()





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


    shutil.copy2(ROOT / "scripts" / "tools.js", SITE_DIR / "scripts" / "tools.js")


    # Copy latest_kpis.json for the JS to consume


    shutil.copy2(DATA_FILE, SITE_DIR / "data" / "latest_kpis.json")

    if EXTRA_FILE.exists():
        shutil.copy2(EXTRA_FILE, SITE_DIR / "data" / "extra_metrics.json")


    # Copy snapshots for fallback


    shutil.copytree(SNAP_DIR, SITE_DIR / "data" / "snapshots", dirs_exist_ok=True)





    # Generate pages


    print("Generating index.html…")


    (SITE_DIR / "index.html").write_text(render_index(latest), encoding="utf-8")





    print("Generating search.html…")


    (SITE_DIR / "search.html").write_text(render_search_page(latest, extra), encoding="utf-8")





    print("Generating sources.html…")


    (SITE_DIR / "sources.html").write_text(render_sources_page(), encoding="utf-8")

    print("Generating data-lab.html…")

    (SITE_DIR / "data-lab.html").write_text(render_data_lab(extra), encoding="utf-8")





    print("Generating tools index.html…")


    (SITE_DIR / "tools.html").write_text(render_tools_index(), encoding="utf-8")





    print("Generating personal inflation page…")


    (SITE_DIR / "tools" / "personal-inflation.html").write_text(render_personal_inflation_page(), encoding="utf-8")





    print("Generating salary parity page…")


    (SITE_DIR / "tools" / "salary-parity.html").write_text(render_salary_parity_page(), encoding="utf-8")





    print(f"Generating {len(TOOLS)} registry calculators…")

    for item in TOOLS:

        (SITE_DIR / "tools" / (item["id"] + ".html")).write_text(render_tool_page(item), encoding="utf-8")



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


    tool_pages = len(ALL_TOOLS)

    print(f"Pages: 1 index + 1 search + 1 sources + 1 data lab + 1 tools hub + {tool_pages} calculator pages + "
          f"{len(SECTORS)} categories + {len(FACTS)} facts + {len(HISTORICAL_TRENDS)} trends + {len(KPI_REGISTRY)} KPIs")








if __name__ == "__main__":


    main()