#!/usr/bin/env python3


"""


Radar — Static Page Generator


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
import html as html_lib


import os


import shutil


import sys


from datetime import datetime, timezone


from pathlib import Path





sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))





from kpi_registry import KPI_REGISTRY, interpret, kpis_by_sector


from site_data import (


    SECTORS, SECTOR_MAP, FACTS, FACTS_BY_CATEGORY,


    HISTORICAL_TRENDS, fact_text, get_trend, search_index, trends_by_category,


    CATEGORY_GROUPS,


)


from tools_registry import (


    TOOL_CATEGORIES, TOOLS, ALL_TOOLS, tools_by_category, catalog_summary,
)

from monthly_snapshots import (
    BADGE_TEXT, SNAPSHOT_DIR, load_all, render_metric_card,
    render_dataset_table, search_items as snapshot_search_items, snapshot_badge,


)





ROOT = Path(__file__).resolve().parents[2]


SITE_DIR = ROOT / "site"


DATA_FILE = ROOT / "data" / "latest_kpis.json"

EXTRA_FILE = ROOT / "data" / "extra_metrics.json"


SNAP_DIR = ROOT / "data" / "snapshots"

SITE_URL = "https://radar.peabox.in"

DASHBOARD_PAGES = [
    {
        "id": "india",
        "title": "India dashboard",
        "eyebrow": "National accounts",
        "description": "India's growth, prices, fiscal position, external balance and high-frequency activity in one view.",
        "intro": "Live World Bank and government-derived KPIs, with original benchmarks. No randomised or placeholder values.",
        "kpis": [
            "gdp_growth_pct", "real_inflation_rate", "gdp_per_capita_usd",
            "gdp_per_capita_ppp_usd", "current_account_pct_gdp",
            "fdi_inflows_pct_gdp", "fiscal_deficit_pct_gdp", "gst_growth_pct",
        ],
        "snapshots": [],
        "benchmarks": True,
    },
    {
        "id": "global",
        "title": "Global macro dashboard",
        "eyebrow": "World economy",
        "description": "GDP, GDP per capita, inflation, policy rates, debt and exchange rates across major economies.",
        "intro": "Official World Bank, BIS, ECB, IMF-fallback and WTO series. Country coverage is curated for comparability.",
        "kpis": [],
        "snapshots": ["global-macro"],
        "snapshot_filters": {
            "global-macro": [
                "gdp_current_usd_wld", "gdp_current_usd_ind", "gdp_current_usd_usa",
                "gdp_per_capita_current_usd_wld", "gdp_per_capita_current_usd_ind",
                "gdp_per_capita_current_usd_usa", "cpi_inflation_pct_wld",
                "cpi_inflation_pct_ind", "cpi_inflation_pct_usa",
            ],
        },
        "global_sections": [
            "imf-ngdp_rpch", "imf-pcpipch", "imf-ggxwdg_ngdp", "imf-bca",
            "policy-rates", "fx-rates", "wb-cm-mkt-lcap-gd-zs", "wto-its-mtv-ax",
        ],
    },
    {
        "id": "markets",
        "title": "Global markets dashboard",
        "eyebrow": "Exchanges & assets",
        "description": "Exchange-level fundamentals and secondary market context for the world's major equity venues.",
        "intro": "Official exchange statistics are labelled as monthly snapshots; delayed market quotes are context only, never official statistics.",
        "kpis": [],
        "snapshots": ["global-exchanges"],
        "global_sections": ["wb-cm-mkt-lcap-gd-zs", "wb-cm-mkt-trnr"],
        "market": True,
    },
    {
        "id": "insurance",
        "title": "Insurance dashboard",
        "eyebrow": "IRDAI snapshots",
        "description": "India's insurance penetration, density, premiums and policies from IRDAI annual reports.",
        "intro": "Annual regulatory publications are transcribed monthly and clearly marked as non-live snapshots.",
        "kpis": [],
        "snapshots": ["irdai-insurance"],
        "global_sections": ["wb-gfdd-di-09", "wb-gfdd-di-10"],
    },
    {
        "id": "mobility-housing",
        "title": "Mobility & housing dashboard",
        "eyebrow": "Real economy",
        "description": "Indian auto sales, housing sales and bank home-loan trends from SIAM, JLL and RBI publications.",
        "intro": "Official and industry-body figures are published as dated monthly snapshots with their original source links.",
        "kpis": ["housing_affordability_ratio", "vehicle_density", "urban_household_deficit_pct"],
        "snapshots": ["india-auto-sales", "india-housing-sales", "india-home-loans"],
    },
]








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


def month_label(value) -> str:
    """Format a YYYY-MM stamp as 'Month YYYY' for snapshot disclosures."""
    raw = str(value or "")
    try:
        return datetime.strptime(raw[:7], "%Y-%m").strftime("%B %Y")
    except ValueError:
        return raw or "Unknown"


def curated_badge(latest: dict) -> str:
    """Mandatory disclosure for any non-live, curated published figure."""
    return (f'<span class="snapshot-badge">{html_lib.escape(BADGE_TEXT)}'
            f'<span class="snapshot-updated">Last Updated: {html_lib.escape(month_label(latest.get("last_updated_month", "")))}</span>'
            '</span>')


def kpi_disclosure(kpi_id: str, latest: dict) -> str:
    """Source badge for a KPI detail/card driven by latest_kpis.json."""
    item = next((k for k in latest.get("kpis", [])
                 if k.get("kpi_id") == kpi_id or k.get("id") == kpi_id), None)
    if not item:
        return ""
    source_type = item.get("source_type", "live_api" if item.get("source_live") else "curated_snapshot")
    if source_type == "curated_snapshot":
        return curated_badge(latest)
    if source_type == "unavailable":
        return '<span class="snapshot-badge unavailable">Official series unavailable — no value published</span>'
    return '<span class="live-badge">Live API</span>'


def section_head(title, eyebrow="", intro=""):
    """Consistent section heading with an optional kicker and description."""
    kicker = f'<span class="eyebrow dark">{eyebrow}</span>' if eyebrow else ""
    description = f'<p class="section-intro">{intro}</p>' if intro else ""
    return f'<div class="section-head"><div>{kicker}<h2>{title}</h2></div>{description}</div>'


def build_dashboard_search_items() -> list[dict]:
    """Make the split dashboard routes discoverable from site search."""
    return [
        {
            "id": page["id"],
            "title": page["title"],
            "category": "Dashboard",
            "text": f"{page['description']} {page['intro']}",
            "source": "Radar dashboard",
            "url": page["id"] + ".html",
            "type": "dashboard",
        }
        for page in DASHBOARD_PAGES
    ]


def render_live_kpi_card(kpi_id: str, latest: dict) -> str:
    """Render a live KPI highlight; disclose non-live curated values."""
    item = next((k for k in latest.get("kpis", []) if k.get("kpi_id") == kpi_id), None)
    if not item:
        return ""
    value = item.get("value")
    disclosure = kpi_disclosure(kpi_id, latest)
    trend = item.get("trend") or {}
    change = trend.get("change") if isinstance(trend, dict) else None
    change_text = f'{change:+.2f}' if isinstance(change, (int, float)) else "—"
    return f"""<article class="card live-kpi-card">
      <div class="live-kpi-top"><span class="eyebrow dark">{html_lib.escape(item.get('sector', 'KPI'))}</span>{disclosure}</div>
      <h3>{html_lib.escape(item.get('name', kpi_id))}</h3>
      <div class="snapshot-value">{humanize(value) if isinstance(value, (int, float)) else '—'} <small>{html_lib.escape(item.get('unit', ''))}</small></div>
      <div class="snapshot-period">Latest change {change_text} · <span class="badge {verdict_class(item.get('verdict'))}">{html_lib.escape(item.get('verdict', 'unknown'))}</span></div>
      <p class="small muted">{html_lib.escape(item.get('insight_text', ''))}</p>
      <a class="btn small" href="kpi/{html_lib.escape(kpi_id)}.html">Read the KPI</a>
    </article>"""


def render_global_section(section: dict, limit: int = 12) -> str:
    """Render one official global feed section as compact data cards."""
    if not section:
        return ""
    rows = section.get("series") or section.get("items") or []
    if not rows:
        return ""
    cards = []
    for row in rows[:limit]:
        points = row.get("points") or []
        values = [p.get("value") for p in points if p.get("value") is not None]
        spark = ""
        if len(values) >= 2:
            spark = (f'<div class="sparkline" data-points=\''
                     f'{html_lib.escape(json.dumps(values), quote=True)}\'></div>')
        latest_value = row.get("latest_value", row.get("value"))
        latest_period = row.get("latest_period", row.get("as_of", ""))
        change = row.get("change_pct")
        change_text = f'{change:+.2f}%' if isinstance(change, (int, float)) else ""
        source_url = row.get("source_url", "")
        source_name = html_lib.escape(row.get("source", "Official feed"))
        source_html = (f'<a href="{html_lib.escape(source_url, quote=True)}" target="_blank" rel="noopener">{source_name}</a>'
                       if source_url else source_name)
        cards.append(f"""<article class="card global-feed-card">
          <h3>{html_lib.escape(row.get('label', row.get('name', 'Series')))}</h3>
          <div class="snapshot-value">{humanize(latest_value) if isinstance(latest_value, (int, float)) else html_lib.escape(str(latest_value or '—'))} <small>{html_lib.escape(row.get('unit', ''))}</small></div>
          <div class="snapshot-period">{html_lib.escape(str(latest_period))} {change_text}</div>
          {spark}
          <p class="small muted">{html_lib.escape(row.get('definition', ''))}</p>
          <div class="snapshot-card-foot"><span>Source: {source_html}</span></div>
        </article>""")
    note = section.get("status_note") or section.get("definition") or ""
    return (section_head(section.get("title", "Official series"), "Live feed", note)
            + f'<div class="grid global-feed-grid">{"".join(cards)}</div>')


def render_market_context(extra: dict, limit: int = 12) -> str:
    """Render delayed market quotes with an explicit secondary-data warning."""
    market = (extra.get("global") or {}).get("market") or {}
    groups = market.get("groups") or []
    rows = []
    for group in groups:
        rows.extend(group.get("items") or [])
    if not rows:
        return ""
    cards = []
    for row in rows[:limit]:
        values = [p.get("value") for p in row.get("points", []) if p.get("value") is not None]
        spark = ""
        if len(values) >= 2:
            spark = f'<div class="sparkline" data-points=\'{html_lib.escape(json.dumps(values), quote=True)}\'></div>'
        change = row.get("change_pct")
        change_text = f'{change:+.2f}%' if isinstance(change, (int, float)) else ""
        cards.append(f"""<article class="card market-card">
          <span class="eyebrow dark">{html_lib.escape(row.get('exchange', 'Market'))}</span>
          <h3>{html_lib.escape(row.get('label', 'Index'))}</h3>
          <div class="snapshot-value">{humanize(row.get('value'))} <small>{html_lib.escape(row.get('unit', 'index pts'))}</small></div>
          <div class="snapshot-period">{html_lib.escape(str(row.get('as_of', '')))} {change_text}</div>
          {spark}
        </article>""")
    return (section_head("Delayed market context", "Secondary data", market.get("status_note") or market.get("definition") or "Delayed quotes for context only; not official statistics.")
            + f'<div class="grid global-feed-grid">{"".join(cards)}</div>')


def render_snapshot_sections(snapshots: dict, dataset_ids: list[str], filters: dict | None = None) -> str:
    """Render curated snapshot KPI cards and tables with the mandatory badge."""
    blocks = []
    filters = filters or {}
    for dataset_id in dataset_ids:
        snapshot = snapshots.get(dataset_id)
        if not snapshot:
            continue
        wanted = filters.get(dataset_id)
        metrics = snapshot.get("metrics", [])
        if wanted:
            metrics = [m for m in metrics if m.get("id") in set(wanted)]
        cards = "".join(render_metric_card(snapshot, metric) for metric in metrics)
        blocks.append(f"""<section id="{html_lib.escape(dataset_id)}" class="snapshot-section">
          {section_head(snapshot.get('title', dataset_id), 'Static snapshot', snapshot.get('methodology', ''))}
          <div class="grid snapshot-grid">{cards}</div>
          {render_dataset_table(snapshot, metrics)}
          <p class="small muted">{html_lib.escape(' · '.join(snapshot.get('notes', [])))}</p>
          <p class="small"><a href="monthly-snapshots.html#{html_lib.escape(dataset_id)}">Open the full {html_lib.escape(snapshot.get('title', dataset_id))} catalogue entry →</a></p>
        </section>""")
    return "".join(blocks)


def render_benchmark_section() -> str:
    return """<section class="benchmarks" id="benchmarks">
      <div class="section-head"><div><span class="eyebrow dark">Indexes</span><h2>Original benchmarks</h2></div><p class="section-intro">Four composites built entirely from published public data.</p></div>
      <div class="grid benchmark-grid">
        <article class="card benchmark-card"><span class="bench-index">01 / MACRO</span><h3>India High-Frequency Macro Cycle Index</h3><p>A 0–100 score blending GST, UPI, power demand, IIP, inflation, repo rate and GDP growth.</p><div class="bench-stat" id="bench-macro-cycle-value">—</div><span class="bench-tag">Composite score · 0–100</span></article>
        <article class="card benchmark-card"><span class="bench-index">02 / CITIES</span><h3>City Salary-Parity Benchmark</h3><p>Purchasing-power adjusted salaries across six major Indian cities.</p><div class="bench-stat">₹ → ₹</div><span class="bench-tag">Cost-of-living adjusted</span></article>
        <article class="card benchmark-card"><span class="bench-index">03 / STATES</span><h3>State-Wise Fiscal Health Scorecard</h3><p>Ranks all 28 states on GST growth, debt-to-GSDP and capex ratio.</p><div class="bench-stat">28</div><span class="bench-tag">States ranked quarterly</span></article>
        <article class="card benchmark-card"><span class="bench-index">04 / GLOBAL</span><h3>Global Emerging Market Resilience</h3><p>India vs Vietnam, Indonesia, Brazil and Mexico on official macro indicators.</p><div class="bench-stat" id="bench-resilience-value">—</div><span class="bench-tag">Peer ranking</span></article>
      </div>
    </section>"""


def render_dashboard_page(page: dict, latest: dict, extra: dict, snapshots: dict) -> str:
    """Render one of the split, categorised dashboard routes."""
    html = render_base_head(
        page["title"],
        page["description"],
        "/" + page["id"] + ".html",
        base="",
    )
    html += f"""<section class="category-index-hero">
      <span class="eyebrow dark">{html_lib.escape(page['eyebrow'])}</span>
      <h1>{html_lib.escape(page['title'])}</h1>
      <p class="hero-sub">{html_lib.escape(page['description'])}</p>
      <p class="muted">{html_lib.escape(page['intro'])}</p>
      <div class="hero-actions"><a href="search.html" class="btn btn-ghost">Search all data</a><a href="monthly-snapshots.html" class="btn btn-ghost">Snapshot catalogue</a></div>
    </section>"""

    kpi_cards = "".join(render_live_kpi_card(kpi_id, latest) for kpi_id in page.get("kpis", []))
    if kpi_cards:
        html += section_head("Key indicators", "Dashboard", "Live API values and clearly disclosed non-live published figures.")
        html += f'<div class="grid snapshot-grid">{kpi_cards}</div>'

    if page.get("benchmarks"):
        html += render_benchmark_section()

    html += render_snapshot_sections(snapshots, page.get("snapshots", []), page.get("snapshot_filters"))

    global_data = extra.get("global") or {}
    section_map = {section.get("id"): section for section in global_data.get("sections", [])}
    for section_id in page.get("global_sections", []):
        section = section_map.get(section_id)
        if section_id.startswith("commodities") and global_data.get("commodities"):
            section = global_data["commodities"]
        html += render_global_section(section)

    if page.get("market"):
        html += render_market_context(extra)

    html += """<section class="cta-band"><div><h2>Need another cut of the data?</h2><p>Search every fact, KPI, trend and monthly snapshot published on Radar.</p></div><a href="search.html" class="btn btn-ghost">Search all data</a></section>"""
    return html + render_footer("")


def render_monthly_snapshots_index(snapshots: dict) -> str:
    """Catalogue page for every curated monthly snapshot dataset."""
    html = render_base_head(
        "Monthly snapshots — Radar",
        "Catalogue of curated non-live datasets with transparency badges and official source links.",
        "/monthly-snapshots.html",
        base="",
    )
    cards = []
    for snapshot in snapshots.values():
        source = snapshot.get("source", {})
        source_link = ""
        if source.get("url"):
            source_link = (f'<a href="{html_lib.escape(source["url"], quote=True)}" target="_blank" rel="noopener">'
                           f'{html_lib.escape(source.get("organization", "Source"))}</a>')
        cards.append(f"""<article class="card snapshot-card" id="{html_lib.escape(snapshot['dataset_id'])}">
          <span class="eyebrow dark">{html_lib.escape(snapshot.get('category', 'Snapshot'))}</span>
          {snapshot_badge(snapshot)}
          <h3>{html_lib.escape(snapshot.get('title', snapshot['dataset_id']))}</h3>
          <p>{html_lib.escape(snapshot.get('methodology', ''))}</p>
          <p class="small muted">Coverage: {html_lib.escape(snapshot.get('coverage', ''))} · {len(snapshot.get('metrics', []))} metrics · Source: {source_link}</p>
          <a class="btn small" href="{html_lib.escape(snapshot.get('page', 'index.html'), quote=True)}">Open dashboard</a>
        </article>""")
    html += """<section class="category-index-hero"><span class="eyebrow dark">Transparency first</span><h1>Monthly snapshots</h1><p class="hero-sub">Curated datasets transcribed from official publications. Every figure on these pages carries a static-snapshot badge and a visible Last Updated month.</p></section>"""
    html += f'<div class="grid snapshot-grid">{"".join(cards)}</div>'
    html += """<section class="cta-band"><div><h2>How updates work</h2><p>Read each linked source, transcribe published figures, set last_updated, then run update_monthly_snapshots.py and regenerate the site. No simulated values are accepted.</p></div><a href="sources.html" class="btn btn-ghost">All sources</a></section>"""
    return html + render_footer("")


def render_sitemap(latest: dict, snapshots: dict) -> str:
    """Generate a sitemap covering every public route emitted by main()."""
    today = (latest.get("generated_at") or datetime.now(timezone.utc).isoformat())[:10]

    def snap_date(value: str) -> str:
        return value if len(value) == 10 else value + "-01"

    routes: list[tuple[str, str, str, str]] = [
        ("/", today, "daily", "1.0"),
        ("/index.html", today, "daily", "0.9"),
        ("/search.html", today, "weekly", "0.7"),
        ("/sources.html", today, "weekly", "0.7"),
        ("/data-lab.html", today, "daily", "0.8"),
        ("/tools.html", today, "weekly", "0.8"),
        ("/categories.html", today, "weekly", "0.8"),
        ("/monthly-snapshots.html", snap_date(max((s.get("last_updated", "") for s in snapshots.values()), default=today)), "monthly", "0.8"),
    ]
    for page in DASHBOARD_PAGES:
        snapshot_dates = [
            snap_date(snapshots[d]["last_updated"])
            for d in page.get("snapshots", []) if d in snapshots
        ]
        modified = max(snapshot_dates + [today])
        changefreq = "monthly" if snapshot_dates else "daily"
        routes.append(("/" + page["id"] + ".html", modified, changefreq, "0.9"))

    for item in TOOLS:
        routes.append(("/tools/" + item["id"] + ".html", today, "monthly", "0.6"))
    routes.extend([
        ("/tools/personal-inflation.html", today, "monthly", "0.6"),
        ("/tools/salary-parity.html", today, "monthly", "0.6"),
    ])
    for sector in SECTORS:
        routes.append(("/category/" + sector["id"] + ".html", today, "weekly", "0.7"))
    for fact in FACTS:
        routes.append(("/facts/" + fact["id"] + ".html", today, "weekly", "0.6"))
    for kpi_id in HISTORICAL_TRENDS:
        routes.append(("/trend/" + kpi_id + ".html", today, "weekly", "0.6"))
    for kpi in KPI_REGISTRY:
        routes.append(("/kpi/" + kpi["id"] + ".html", today, "weekly", "0.7"))

    seen = set()
    entries = []
    for path, modified, frequency, priority in routes:
        if path in seen:
            continue
        seen.add(path)
        entries.append(f"""  <url>
    <loc>{html_lib.escape(SITE_URL + path, quote=True)}</loc>
    <lastmod>{html_lib.escape(modified, quote=True)}</lastmod>
    <changefreq>{frequency}</changefreq>
    <priority>{priority}</priority>
  </url>""")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entries)
            + '\n</urlset>\n')


def render_robots() -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""


def render_trend_embed(trend, kpi_id, heading=None, latest=None):
    """Compact sparkline preview linking through to the full history page."""
    if not trend:
        return ""
    points = json.dumps([p["value"] for p in trend["points"]])
    label = heading or f'{trend["label"]} (history)'
    badge = curated_badge(latest) if latest else ""
    return f'''<div class="trend-embed">
      <h3>{label}</h3>
      {f'<div class="disclosure-row">{badge}</div>' if badge else ''}
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
    page_title = title if "Radar" in title else f"{title} — Radar"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{page_title}</title>
  <meta name="description" content="{html_lib.escape(description, quote=True)}" />
  <meta property="og:site_name" content="Radar" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{html_lib.escape(page_title, quote=True)}" />
  <meta property="og:description" content="{html_lib.escape(description, quote=True)}" />
  <meta property="og:url" content="{SITE_URL}{current_url}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{html_lib.escape(page_title, quote=True)}" />
  <meta name="twitter:description" content="{html_lib.escape(description, quote=True)}" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230e7c70'/%3E%3Ccircle cx='16' cy='16' r='3' fill='white'/%3E%3Cpath d='M9 9a10 10 0 0 0 0 14M23 9a10 10 0 0 1 0 14' fill='none' stroke='white' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{b}styles/main.css" />
  <link rel="stylesheet" href="{b}styles/european-theme.css" />
  <link rel="canonical" href="{SITE_URL}{current_url}" />
</head>
<body data-base="{b}">
  <a class="skip-link" href="#site-main">Skip to content</a>
  <header class="site-header">
    <div class="nav-inner container">
      <a class="brand" href="{b}index.html" aria-label="Radar home">
        <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/><path d="M6.2 6.2a8.2 8.2 0 0 0 0 11.6M17.8 6.2a8.2 8.2 0 0 1 0 11.6"/><path d="M3.3 3.3a12.3 12.3 0 0 0 0 17.4M20.7 3.3a12.3 12.3 0 0 1 0 17.4"/></svg></span>
        <span class="brand-name">Radar</span>
      </a>
      <span class="nav-status"><span class="status-dot"></span>Live data</span>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">
        <span></span><span></span><span></span>
      </button>
      <nav id="site-nav" class="site-nav" aria-label="Primary">
        <div class="nav-primary">
          <a href="{b}index.html" class="nav-link">Overview</a>
          <a href="{b}india.html" class="nav-link">India</a>
          <a href="{b}global.html" class="nav-link">Global</a>
          <a href="{b}markets.html" class="nav-link">Markets</a>
          <a href="{b}insurance.html" class="nav-link">Insurance</a>
          <a href="{b}mobility-housing.html" class="nav-link">Mobility</a>
          <a href="{b}data-lab.html" class="nav-link">Data Lab</a>
          <a href="{b}tools.html" class="nav-link">Tools</a>
          <a href="{b}search.html" class="nav-link">Search</a>
        </div>
        <div class="nav-drop">
          <button class="nav-drop-btn" aria-expanded="false" aria-haspopup="true">Browse sectors <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg></button>
          <div class="nav-drop-menu" role="menu">
            <div class="nav-drop-heading">Dashboards</div>
            <a href="{b}india.html" role="menuitem">📊 India macro</a>
            <a href="{b}global.html" role="menuitem">🌐 Global macro</a>
            <a href="{b}markets.html" role="menuitem">🏦 Global markets</a>
            <a href="{b}insurance.html" role="menuitem">🛡️ Insurance</a>
            <a href="{b}mobility-housing.html" role="menuitem">🚗 Mobility &amp; housing</a>
            <a href="{b}monthly-snapshots.html" role="menuitem">🗓️ Monthly snapshots</a>

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


        <a class="brand" href="{b}index.html" aria-label="Radar home">
          <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/><path d="M6.2 6.2a8.2 8.2 0 0 0 0 11.6M17.8 6.2a8.2 8.2 0 0 1 0 11.6"/><path d="M3.3 3.3a12.3 12.3 0 0 0 0 17.4M20.7 3.3a12.3 12.3 0 0 1 0 17.4"/></svg></span>
          <span class="brand-name">Radar</span>
        </a>
        <p class="footer-tagline">Original macro KPIs, benchmarks, and facts derived from public government data.</p>

        <p class="footer-meta">Data refreshed: <span id="footer-refresh">{ts}</span></p>


      </div>


      <div class="footer-col">


        <h4 class="footer-heading">Explore</h4>


        <a href="{b}index.html">Overview</a>


        <a href="{b}india.html">India dashboard</a>


        <a href="{b}global.html">Global macro</a>


        <a href="{b}markets.html">Global markets</a>


        <a href="{b}insurance.html">Insurance</a>


        <a href="{b}mobility-housing.html">Mobility &amp; housing</a>


        <a href="{b}monthly-snapshots.html">Monthly snapshots</a>


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


      <p>© {datetime.now(timezone.utc).year} Radar. Built on public data from World Bank, RBI, MoSPI, NPCI, and data.gov.in.</p>


      <p class="muted small">Developed by <a href="https://peabox.in" target="_blank">Peabox Labs (India)</a></p>


      <a href="https://github.com/PeaBox-Lab/Radar" class="footer-gh">GitHub</a>


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


          <h3>{html_lib.escape(fact_text(f, latest)[:120])}{'…' if len(fact_text(f, latest)) > 120 else ''}</h3>


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


          <td><strong>{kpi['name']}</strong><div class="disclosure-row">{kpi_disclosure(kpi['id'], latest)}</div></td>


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
              <div class="disclosure-row">{curated_badge(latest)}</div>

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


        fact_text(fact, latest)[:160],


        f"/facts/{fact['id']}.html",


        base="../"


    )


    html += f"""


    <section class="fact-detail detail-hero">
      <a class="back-link" href="../category/{fact['category']}.html">← Back to {SECTOR_MAP[fact['category']]['title']}</a>
      <span class="eyebrow dark">Fact file</span>
      <h1>{fact['kpi_id'].replace('_', ' ').title()}</h1>
      <p class="fact-text">{html_lib.escape(fact_text(fact, latest))}</p>

      <div class="fact-meta">


        <span><strong>Source:</strong> {fact['source']}</span>


        <span><strong>Scale:</strong> {fact['scale']}</span>


        <span><strong>Why it matters:</strong> {fact['why_it_matters']}</span>


      </div>


      <div class="disclosure-row">{kpi_disclosure(kpi_id, latest)}</div>

      {f'<p class="latest-value">Latest value: <strong>{humanize(val)}</strong></p>' if val is not None else ''}


      {render_trend_embed(trend, kpi_id, latest=latest)}


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
      <div class="disclosure-row">{curated_badge(latest)}</div>
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
        <div class="disclosure-row">{kpi_disclosure(kpi_id, latest)}</div>
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





      {render_trend_embed(trend, kpi_id, "Historical trend", latest=latest)}





      <a href="{back_href}" class="btn">← Back to {back_label}</a>


    </section>"""


    html += render_footer("../")


    return html








# ---------------------------------------------------------------------------


# Search page


# ---------------------------------------------------------------------------





def render_search_page(latest, extra=None, snapshots=None):


    items = search_index(latest)
    if extra:
        items.extend(build_extra_search_items(extra))
    items.extend(snapshot_search_items(snapshots or {}))
    items.extend(build_dashboard_search_items())
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
      <h1>Search Radar</h1>
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
        f"Every API, dataset and portal Radar draws from — {summ['total_apis']} categorised sources with summary stats for each.",
        "/sources.html",
        base=""
    )
    html += f"""
    <section>
      <span class="eyebrow dark">Provenance</span>
      <h1>Data Sources Catalog</h1>
      <p class="muted">Radar computes KPIs from {summ['total_apis']} public government APIs across {summ['total_categories']} categories. Every source is categorised under a proper tag group and summarised with the key statistics we use.</p>

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
    return html_lib.escape("" if value is None else str(value), quote=True)


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


def fmt_change(value):
    """Signed percentage change with a directional colour class."""
    if not isinstance(value, (int, float)):
        return '<span class="muted">—</span>'
    direction = "up" if value >= 0 else "down"
    return f'<span class="change {direction}">{value:+.2f}%</span>'


def status_badge(value):
    status = str(value or "unavailable")
    kind = "good" if status == "live" else "moderate" if status == "cached" else "weak"
    return f'<span class="badge {kind}">{esc(status)}</span>'


def _sparkline(points):
    values = [p.get("value") for p in points if isinstance(p.get("value"), (int, float))]
    if len(values) < 2:
        return ""
    payload = json.dumps(values).replace("'", "\\u0027")
    return f'<div class="sparkline" data-points=\'{payload}\'></div>'


def render_global_series_section(section):
    """One filterable table for a curated global feed section."""
    section_id = str(section.get("id", "global"))
    anchor = "global-" + section_id
    target = "rows-" + section_id
    rows = []
    for item in section.get("items", []):
        key = esc(item.get("key", ""))
        rows.append(f"""
        <tr id="{key}">
          <td><strong>{esc(item.get('label'))}</strong><br><small class="muted">{esc(item.get('country'))} · {esc(item.get('frequency'))}</small></td>
          <td>{fmt_extra_value(item.get('latest_value'), item.get('unit'))}<br><small class="muted">{esc(item.get('latest_period'))}</small></td>
          <td>{fmt_change(item.get('change_pct'))}</td>
          <td>{_sparkline(item.get('points', []))}</td>
          <td>{status_badge(item.get('status'))}</td>
          <td><details><summary>Definition</summary><p>{esc(item.get('definition'))}</p></details></td>
          <td><details><summary>Guide</summary><p>{esc(item.get('guide'))}</p></details><small class="muted"><a href="{esc(item.get('source_url'))}" target="_blank" rel="noopener">Source ↗</a></small></td>
        </tr>""")
    if not rows:
        note = section.get("status_note") or "No observations were available in this run."
        rows.append(f'<tr><td colspan="7" class="muted">{esc(note)}</td></tr>')
    note = section.get("status_note")
    note_html = f'<p class="muted small">{esc(note)}</p>' if note else ""
    return f"""
    <section id="{esc(anchor)}" class="global-section">
      {section_head(esc(section.get('title', 'Global data')), 'Global data', esc(section.get('description', '')))}
      <p class="muted small">Source: <a href="{esc(section.get('source_url'))}" target="_blank" rel="noopener">{esc(section.get('source'))} ↗</a></p>
      {note_html}
      <div class="filter-bar">
        <label class="filter-input-wrap"><span>Filter rows</span><input type="search" class="filter-input" data-filter-input data-filter-target="{esc(target)}" placeholder="Country, series or keyword"></label>
      </div>
      <div class="table-wrap">
        <table class="data-table filter-table">
          <thead><tr><th>Series</th><th>Latest</th><th>Change</th><th>History</th><th>Status</th><th>Definition</th><th>Guide</th></tr></thead>
          <tbody id="{esc(target)}">{"".join(rows)}</tbody>
        </table>
      </div>
      <p class="muted small">{esc(section.get('guide'))}</p>
    </section>"""


def render_commodity_section(commodities):
    """Publish the full Pink Sheet commodity price board."""
    target = "rows-commodities"
    headline_ids = set(commodities.get("headline_ids", []))
    cards = []
    for item in commodities.get("items", []):
        if item.get("key") in headline_ids:
            cards.append(f"""
            <article class="card market-card" id="{esc(item.get('key'))}">
              <div class="card-header"><h3>{esc(item.get('label'))}</h3>{status_badge(item.get('status'))}</div>
              <div class="data-kpi-value">{fmt_extra_value(item.get('latest_value'), item.get('unit'))}</div>
              <p class="muted small">{esc(item.get('latest_period'))} · {fmt_change(item.get('change_pct'))} month-on-month</p>
              {_sparkline(item.get('points', []))}
            </article>""")
    rows = []
    for item in commodities.get("items", []):
        rows.append(f"""
        <tr id="{esc(item.get('key'))}">
          <td><strong>{esc(item.get('label'))}</strong></td>
          <td>{fmt_extra_value(item.get('latest_value'), item.get('unit'))}<br><small class="muted">{esc(item.get('latest_period'))}</small></td>
          <td>{fmt_change(item.get('change_pct'))}</td>
          <td>{_sparkline(item.get('points', []))}</td>
          <td><details><summary>Definition</summary><p>{esc(item.get('definition'))}</p></details></td>
          <td><a href="{esc(commodities.get('source_url'))}" target="_blank" rel="noopener">Source ↗</a></td>
        </tr>""")
    if not rows:
        rows.append('<tr><td colspan="6" class="muted">No commodity prices were available in this run.</td></tr>')
    note = commodities.get("status_note")
    note_html = f'<p class="muted small">{esc(note)}</p>' if note else ""
    return f"""
    <section id="commodities" class="global-section">
      {section_head('Official monthly commodity prices', 'World Bank Pink Sheet', f"All {len(commodities.get('items', []))} published commodity series with their own units. These are monthly benchmarks, not live quotes.")}
      <p class="muted small">Source: <a href="{esc(commodities.get('source_url'))}" target="_blank" rel="noopener">{esc(commodities.get('source'))} ↗</a></p>
      {note_html}
      <div class="grid grid-4">{"".join(cards)}</div>
      <div class="filter-bar">
        <label class="filter-input-wrap"><span>Filter commodities</span><input type="search" class="filter-input" data-filter-input data-filter-target="{target}" placeholder="Gold, copper, wheat…"></label>
      </div>
      <div class="table-wrap">
        <table class="data-table filter-table">
          <thead><tr><th>Commodity</th><th>Latest price</th><th>Monthly change</th><th>History</th><th>Definition</th><th>Source</th></tr></thead>
          <tbody id="{target}">{"".join(rows)}</tbody>
        </table>
      </div>
      <p class="muted small">{esc(commodities.get('guide'))}</p>
    </section>"""


def render_market_section(market):
    """Publish delayed market-reference snapshots with an explicit caveat."""
    groups = []
    for group in market.get("groups", []):
        cards = []
        for item in group.get("items", []):
            cards.append(f"""
            <article class="card market-card" id="{esc(item.get('key'))}">
              <div class="card-header"><h3>{esc(item.get('label'))}</h3>{status_badge(item.get('status'))}</div>
              <div class="market-value">{fmt_extra_value(item.get('value'), item.get('unit'))}</div>
              <p>{fmt_change(item.get('change_pct'))} <span class="muted small">{esc(item.get('as_of'))} · {esc(item.get('exchange'))}</span></p>
              {_sparkline(item.get('points', []))}
              <p class="muted small">{esc(item.get('symbol'))}</p>
            </article>""")
        if cards:
            groups.append(f"""
            <div class="market-group">
              <h3>{esc(group.get('title'))}</h3>
              <div class="grid grid-4">{"".join(cards)}</div>
            </div>""")
    note = market.get("status_note")
    note_html = f'<p class="muted small">{esc(note)}</p>' if note else ""
    return f"""
    <section id="markets" class="global-section">
      {section_head('Market reference snapshots', 'Delayed · secondary source', 'Index, futures and FX quotes for context. They are not official statistics and may be delayed.')}
      <div class="callout">
        <h3>Read this before using market quotes</h3>
        <p>{esc(market.get('definition'))} {esc(market.get('guide'))}</p>
        <p class="muted small"><a href="{esc(market.get('source_url'))}" target="_blank" rel="noopener">{esc(market.get('source'))} ↗</a></p>
      </div>
      {note_html}
      {''.join(groups)}
    </section>"""


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

    glob = extra.get("global", {})
    for section in glob.get("sections", []):
        for item in section.get("items", []):
            add(
                "data-lab.html#global-" + str(section.get("id", "global")),
                item.get("label", "Global series"),
                section.get("title", "Global data"),
                item.get("source", ""),
                (item.get("definition", "") + " " + item.get("guide", "")).strip(),
                "global-series",
            )

    for item in glob.get("commodities", {}).get("items", []):
        add(
            "data-lab.html#commodities",
            item.get("label", "Commodity price"),
            "Commodity prices",
            item.get("source", "World Bank Pink Sheet"),
            (item.get("definition", "") + " " + item.get("guide", "")).strip(),
            "commodity",
        )

    for group in glob.get("market", {}).get("groups", []):
        for item in group.get("items", []):
            add(
                "data-lab.html#markets",
                item.get("label", "Market quote"),
                group.get("title", "Market snapshots"),
                item.get("source", "Yahoo Finance (secondary market data)"),
                (item.get("definition", "") + " " + item.get("guide", "")).strip(),
                "market",
            )

    for kpi in glob.get("kpis", []):
        add(
            "data-lab.html#global-kpis",
            kpi.get("name", "Global derived KPI"),
            kpi.get("sector", "Global"),
            ", ".join(kpi.get("sources", [])),
            (kpi.get("formula", "") + " " + kpi.get("definition", "") + " " + kpi.get("guide", "")).strip(),
            "global-kpi",
        )

    for guide in glob.get("guides", []):
        add(
            "data-lab.html#global-guides",
            guide.get("title", "Global data guide"),
            "Global data guide",
            guide.get("source", ""),
            (guide.get("definition", "") + " " + guide.get("guide", "")).strip(),
            "guide",
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
    glob = extra.get("global", {})
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
      <div class="grid grid-4 source-summary-grid">
        <div class="card source-summary-card"><strong>{glob.get('counts', {}).get('sections', 0)}</strong><span>Global feeds</span></div>
        <div class="card source-summary-card"><strong>{glob.get('counts', {}).get('series', 0)}</strong><span>Global series</span></div>
        <div class="card source-summary-card"><strong>{len(glob.get('commodities', {}).get('items', []))}</strong><span>Commodity prices</span></div>
        <div class="card source-summary-card"><strong>{glob.get('counts', {}).get('derived_kpis', 0)}</strong><span>Global KPIs</span></div>
      </div>
      <div class="lab-jump">
        <a href="#series">India series</a><a href="#derived">Derived KPIs</a><a href="#relationships">Relationships</a>
        <a href="#global-fx-rates">FX &amp; rates</a><a href="#global-policy-rates">Policy rates</a><a href="#commodities">Commodities</a>
        <a href="#markets">Markets</a><a href="#global-kpis">Global KPIs</a><a href="#global-guides">Guides</a>
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

    # ---- Global feed sections ----
    hero += f"""
    <section id="global" class="global-section">
      {section_head('Global data feeds', 'Worldwide coverage', 'Curated official feeds for exchange rates, interest rates, debt, trade, banking, insurance, pay parity and markets. Every table carries its source, unit, definition and guide.')}
      <div class="callout">
        <h3>Official first, clearly labelled</h3>
        <p>{esc(glob.get('methodology', 'Official sources are used wherever possible.'))}</p>
        <p class="muted small">Last known good values are reused when a feed is rate-limited or unavailable; the status badge tells you which run supplied each series.</p>
      </div>
    </section>"""

    for global_section in glob.get("sections", []):
        hero += render_global_series_section(global_section)

    hero += render_commodity_section(glob.get("commodities", {}))
    hero += render_market_section(glob.get("market", {}))

    global_kpi_cards = []
    for item in glob.get("kpis", []):
        anchor = "global-kpi-" + str(item.get("id", ""))
        sources = ", ".join(item.get("sources", []))
        global_kpi_cards.append(f"""
        <article class="card data-kpi-card" id="{esc(anchor)}">
          <div class="card-header"><h3>{esc(item.get('name'))}</h3><span class="badge">{esc(item.get('status'))}</span></div>
          <div class="data-kpi-value">{fmt_extra_value(item.get('value'), item.get('unit'))}</div>
          <p><strong>Formula:</strong> {esc(item.get('formula'))}</p>
          <p><strong>Definition:</strong> {esc(item.get('definition'))}</p>
          <p><strong>User guide:</strong> {esc(item.get('guide'))}</p>
          <p class="muted small">Sources: {esc(sources)} · Latest: {esc(item.get('latest_period'))}</p>
        </article>""")
    hero += f"""
    <section id="global-kpis" class="global-section">
      {section_head('Global derived KPIs', 'Computed from global feeds', 'Cross-country metrics calculated from the published feeds above. Each card states the exact inputs and formula.')}
      <div class="grid grid-2">{"".join(global_kpi_cards)}</div>
    </section>"""

    guide_cards = []
    for guide in glob.get("guides", []):
        guide_cards.append(f"""
        <details class="card guide-card" id="guide-{esc(guide.get('id'))}">
          <summary>{esc(guide.get('title'))}</summary>
          <p><strong>Definition:</strong> {esc(guide.get('definition'))}</p>
          <p><strong>User guide:</strong> {esc(guide.get('guide'))}</p>
          <p class="muted small">Source: <a href="{esc(guide.get('source_url'))}" target="_blank" rel="noopener">{esc(guide.get('source'))} ↗</a></p>
        </details>""")
    hero += f"""
    <section id="global-guides" class="global-section">
      {section_head('Global definitions & guides', 'Read before comparing', 'Plain-English explanations of the indicators, units and caveats used in the global sections.')}
      <div class="guide-grid">{"".join(guide_cards)}</div>
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


def render_index(latest, snapshots):
    """Concise landing page that routes readers to the categorised dashboards."""
    html = render_base_head(
        "Radar — India & Global Macro Dashboards",
        "Live economic indicators, curated monthly snapshots and calculators built from published public data.",
        "/",
        base=""
    )
    html += """<section class="hero hero-compact">
      <div class="hero-inner">
        <span class="eyebrow">Public data, clearly labelled</span>
        <h1>Real economy numbers, <span>plain English.</span></h1>
        <p class="hero-sub">Radar separates live API feeds from curated monthly snapshots. Every figure is published by an official or authoritative source, with its own date, badge and source link.</p>
        <div class="hero-actions">
          <a href="#dashboards" class="btn btn-primary">Choose a dashboard <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
          <a href="search.html" class="btn btn-ghost">Search all data</a>
        </div>
      </div>
      <div class="hero-visual" aria-hidden="true">
        <span class="orbit orbit-1"></span><span class="orbit orbit-2"></span><span class="orbit orbit-3"></span>
        <div class="signal-card"><span class="signal-label">Data layers</span><strong>2</strong><span class="signal-foot">Live + snapshot</span></div>
      </div>
    </section>

    <section class="dashboards" id="dashboards">"""
    html += section_head("Explore by dashboard", "Categorised views", "The full data set is split into focused pages so each section stays readable and source-transparent.")
    html += '<div class="grid dashboard-grid">'
    for page in DASHBOARD_PAGES:
        meta = []
        if page.get("kpis"):
            meta.append(f"{len(page['kpis'])} live KPIs")
        if page.get("snapshots"):
            meta.append(f"{len(page['snapshots'])} snapshot datasets")
        if page.get("global_sections"):
            meta.append(f"{len(page['global_sections'])} official series")
        html += f"""<article class="card dashboard-card">
          <span class="eyebrow dark">{html_lib.escape(page['eyebrow'])}</span>
          <h3>{html_lib.escape(page['title'])}</h3>
          <p class="card-desc">{html_lib.escape(page['description'])}</p>
          <p class="small muted">{' · '.join(html_lib.escape(m) for m in meta)}</p>
          <a href="{page['id']}.html" class="btn small">Open dashboard <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></a>
        </article>"""
    html += """<article class="card dashboard-card">
          <span class="eyebrow dark">Transparency</span>
          <h3>Monthly snapshots</h3>
          <p class="card-desc">Every curated dataset, its last-updated month, its source publication and the shared static-snapshot badge.</p>
          <a href="monthly-snapshots.html" class="btn small">Open catalogue →</a>
        </article>
      </div>
    </section>"""

    highlights = []
    for dataset_id in ("india-auto-sales", "irdai-insurance", "global-macro"):
        snapshot = snapshots.get(dataset_id)
        if snapshot and snapshot.get("metrics"):
            highlights.append(render_metric_card(snapshot, snapshot["metrics"][0]))
    if highlights:
        html += section_head("Latest published figures", "Snapshot examples", "These cards are not live. Each shows its published period and Last Updated month.")
        html += f'<div class="grid snapshot-grid">{"".join(highlights)}</div>'

    html += """<section class="cta-band">
      <div><h2>Prefer the full sector view?</h2><p>Browse 14 sectors with facts, KPIs, historical trends and the tools built on them.</p></div>
      <a href="categories.html" class="btn btn-ghost">Browse sectors</a>
    </section>"""
    html += render_footer("")
    return html







# ---------------------------------------------------------------------------


# Categories Index page (top-level category landing page)


# ---------------------------------------------------------------------------





def render_categories_index():


    html = render_base_head(


        "Categories — All Radar Data",


        "Browse all 14 categories of macro and sector data on Radar — government, economy, agriculture, energy, transport, geo, health, education, welfare, environment, commerce, housing.",


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
            "source": "Radar calculator",
            "url": "tools/" + item["href"],
            "type": "tool",
        })
    return items


def render_tools_index():
    """Render the categorized calculator hub."""
    summary = catalog_summary()
    html = render_base_head(
        "Tools — Radar",
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
        <p>Default inputs are provided for convenience only. Replace them with your actual numbers, rates and tenure.</p>
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
        tool["title"] + " — Radar",
        tool["description"],
        "/tools/" + tool["id"] + ".html",
        base="../",
    )

    html += f'''
    <section class="calc-hero">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../index.html">Dashboard</a><span>/</span>
        <a href="../tools.html">Tools</a><span>/</span>
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


        "Personal Inflation Calculator — Radar",


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


        "Salary Parity Calculator — Radar",


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
    snapshots = load_all()





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

    if SNAPSHOT_DIR.exists():
        shutil.copytree(SNAPSHOT_DIR, SITE_DIR / "data" / "monthly-snapshots", dirs_exist_ok=True)

    if (ROOT / "CNAME").exists():
        shutil.copy2(ROOT / "CNAME", SITE_DIR / "CNAME")





    # Generate pages


    print("Generating index.html…")


    (SITE_DIR / "index.html").write_text(render_index(latest, snapshots), encoding="utf-8")

    print(f"Generating {len(DASHBOARD_PAGES)} categorised dashboards…")
    for page in DASHBOARD_PAGES:
        (SITE_DIR / (page["id"] + ".html")).write_text(
            render_dashboard_page(page, latest, extra, snapshots), encoding="utf-8"
        )

    print("Generating monthly-snapshots.html…")
    (SITE_DIR / "monthly-snapshots.html").write_text(
        render_monthly_snapshots_index(snapshots), encoding="utf-8"
    )





    print("Generating search.html…")


    (SITE_DIR / "search.html").write_text(render_search_page(latest, extra, snapshots), encoding="utf-8")





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





    print("Generating sitemap.xml, robots.txt and Cloudflare headers…")
    (SITE_DIR / "sitemap.xml").write_text(render_sitemap(latest, snapshots), encoding="utf-8")
    (SITE_DIR / "robots.txt").write_text(render_robots(), encoding="utf-8")
    (SITE_DIR / "_headers").write_text(
        "/sitemap.xml\n"
        "  Content-Type: application/xml\n"
        "  X-Content-Type-Options: nosniff\n",
        encoding="utf-8",
    )

    print(f"[OK] Site generated at {SITE_DIR}")


    tool_pages = len(ALL_TOOLS)

    print(f"Pages: 1 index + 1 search + 1 sources + 1 data lab + 1 tools hub + {len(DASHBOARD_PAGES)} dashboards + "
          f"1 snapshot catalogue + {len(snapshots)} snapshot datasets + {tool_pages} calculator pages + "
          f"{len(SECTORS)} categories + {len(FACTS)} facts + {len(HISTORICAL_TRENDS)} trends + "
          f"{len(KPI_REGISTRY)} KPIs + sitemap.xml + robots.txt + _headers")








if __name__ == "__main__":


    main()