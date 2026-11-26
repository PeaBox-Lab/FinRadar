# FinRadar — Product & Site Knowledge Document

A comprehensive user guide and technical reference for the FinRadar static site: architecture, data pipeline, site structure, navigation, theme, and deployment.

---

## 1. Project Overview

**FinRadar** is a static, data-driven website that publishes derived macroeconomic KPIs, benchmarks, reports, and a Data Lab of curated official series built from public government data (World Bank, data.gov.in, RBI, NPCI, GST portal, MNRE, Census of India, IMF, FRED, etc.).

- **No server-side code** — fully static HTML/CSS/JS.
- **Two daily automated updates** — core KPIs at 02:30 UTC, expanded Data Lab at 03:15 UTC.
- **Deployment** via GitHub Pages from the `gh-pages` branch.
- **Relative paths** — all CSS/JS/nav links work on GitHub Pages and subfolder pages; dynamic KPI data requires HTTP rather than `file://`.

---

## 2. Repository Structure (main branch)

```
FinRadar/
├── .github/
│   └── workflows/
│       ├── daily-update.yml      # CI: core KPIs, regenerate site, deploy to gh-pages
│       └── enrichment-update.yml # CI: Data Lab enrichment, regenerate site, deploy
├── data/
│   ├── latest_kpis.json          # Core pipeline output: 45 KPIs + India + peers
│   ├── extra_metrics.json        # Data Lab output: series, census, KPIs, relationships, catalog
│   └── snapshots/                # Demo fallbacks + enrichment last-known-good cache
│       ├── city_indices.json
│       ├── debt_service.json
│       ├── gst_growth.json
│       ├── iip.json
│       ├── india_gsec_yields.json
│       ├── power_demand.json
│       ├── reserves.json
│       ├── state_cpi_spread.json
│       ├── subindices.json
│       └── upi_stats.json
├── docs/
│   └── product-guide.md          # This document
├── scripts/
│   ├── app.js                    # Client-side rendering: KPI grid, benchmarks, peers, legacy tools
│   ├── charts.js                 # Sparkline SVG + canvas trend chart renderer
│   ├── tools.js                  # Shared engine for all registry calculators
│   └── pipeline/
│       ├── fetch_kpis.py         # Core daily pipeline: writes latest_kpis.json
│       ├── enrichment.py         # Data Lab batch: curated series, census, derived KPIs, correlations
│       ├── datagovin_client.py   # data.gov.in client with token fallback
│       ├── kpi_registry.py       # Core KPI definitions: formulas, units, verdict ranges, insights
│       ├── analytics.py          # Plain-English insights per KPI
│       ├── site_data.py          # Source of truth: SECTORS, CATEGORY_GROUPS, FACTS, HISTORICAL_TRENDS
│       ├── page_generator.py     # Generates complete static site under site/ (132 pages)
│       ├── tools_registry.py     # 21 calculator definitions, formulas, fields and guides
│       └── api_catalog.py        # API catalog: 20 APIs across 10 categories with summary stats
├── styles/
│   ├── main.css                  # UI foundation: tokens, layout, nav, cards, tables, footer
│   └── european-theme.css        # FinRadar theme layer: hero, KPIs, tools, detail pages
├── site/                         # BUILD OUTPUT (committed to main; deployed to gh-pages)
│   ├── index.html                # Dashboard / landing page
│   ├── search.html               # Full-text search across facts, KPIs and Data Lab content
│   ├── sources.html              # Categorized API catalog with summary stats
│   ├── data-lab.html             # Expanded official data with definitions, guides and correlations
│   ├── tools.html                # Categorized calculator hub (4 groups, 23 calculators)
│   ├── tools/*.html              # 21 registry calculator pages + 2 live-data legacy tools
│   ├── categories.html           # Top-level category index page (all 14 categories)
│   ├── category/*.html           # 14 sector pages (facts, KPIs, trends)
│   ├── facts/*.html              # 36 fact detail pages
│   ├── trend/*.html              # 8 historical trend chart pages
│   ├── kpi/*.html                # 45 KPI deep-dive pages
│   ├── styles/                   # Copied CSS
│   ├── scripts/                  # Copied client JS
│   └── data/                     # latest_kpis.json, extra_metrics.json + snapshots
└── README.md                     # Brief project README
```

**Important:** `site/` is build output. It is committed to `main` so the GitHub Action can deploy it to `gh-pages`. You should not hand-edit files inside `site/` — regenerate via `scripts/pipeline/page_generator.py`.

---

## 3. Data Pipeline

### 3.1 `scripts/pipeline/fetch_kpis.py`

The daily data pipeline. Steps:

1. **Fetch live World Bank data** for India and peer countries (Vietnam, Indonesia, etc.) using indicators:
   - `FP.CPI.TOTL.ZG` — Inflation, consumer prices
   - `NY.GDP.PCAP.CD` — GDP per capita (nominal)
   - `NY.GDP.PCAP.PP.CD` — GDP per capita (PPP)
   - `NY.GDP.MKTP.KD.ZG` — GDP growth (real)
   - `NE.CAB.TOTL.PT` — Current account balance
   - `BX.KD.FDI.DT.GP` — FDI inflows
2. **Load local snapshots** from `data/snapshots/` as demo fallbacks:
   - India G-Sec yields, UPI stats, GST growth, forex reserves, state CPI spread, IIP, power demand, debt service
3. **Compute derived KPI values** via `kpi_registry.py` formulas.
4. **Build plain-English insights** via `analytics.py`.
5. **Write `data/latest_kpis.json`** — 45 KPIs across sectors, plus India summary and peer list.

### 3.2 `scripts/pipeline/page_generator.py`

Reads `latest_kpis.json`, `kpi_registry.py`, and `site_data.py`, then generates the complete static site under `site/`.

Pages generated:
- `index.html` — dashboard with hero stats, live KPI grid, benchmarks, tools, category cards
- `search.html` — full-text lookup across all facts and KPIs
- `sources.html` — categorized API catalog
- `categories.html` — top-level category index (all 14 categories grouped into 6 groups)
- `category/<sector>.html` — 14 sector pages
- `facts/<id>.html` — 36 fact detail pages
- `trend/<id>.html` — 8 historical trend pages
- `kpi/<id>.html` — 45 KPI deep-dive pages

Static assets copied into `site/`:
- `styles/main.css`, `styles/european-theme.css`
- `scripts/app.js`, `scripts/charts.js`
- `data/latest_kpis.json`, `data/extra_metrics.json`, `data/snapshots/`

### 3.2.1 `scripts/pipeline/enrichment.py`

The separate Data Lab batch publishes the expanded data layer without touching the core KPI output:

1. **Curated World Bank series** — 28 keyless series for India, the world and four emerging-market peers, covering GDP, demographics, savings/credit, external balances, digital adoption, environment and exchange rates. Each has a definition and user guide.
2. **Official Census of India benchmarks** — 2011 population, literacy, urbanisation, sex ratio and density, with a note that these are decadal figures rather than daily observations.
3. **Curated data.gov.in resource** — a daily mandi price feed fetched with `DATA_GOV_IN_TOKEN` when present, otherwise the rate-limited public sample key. Responses are cached in `data/snapshots/enrichment_cache.json`.
4. **Innovative derived KPIs** — 12 reproducible metrics such as per-capita growth spread, demographic dividend index, credit–savings gap, external resilience score, peer growth spread, global inflation gap and growth tailwind ratio.
5. **Relationships** — Pearson coefficients between Indian metrics and macro/demographic/global factors, with observation windows and a causation caveat.
6. **Discovery catalog** — official portal metadata, access mode and APIsetu's credential boundary, published under `data-lab.html#discovery`.

It writes `data/extra_metrics.json`. The generator consumes that file to build `site/data-lab.html` and enrich the search index. If the batch has never run, the page degrades to an instruction rather than breaking the build.

### 3.3 `scripts/pipeline/kpi_registry.py`

Defines all 45 KPIs. Each KPI has:
- `id` — unique key (e.g., `real_inflation_rate`)
- `name` — display name
- `sector` — sector name for grouping
- `unit` — display unit (% , months, USD, etc.)
- `formula` — how the value is computed
- `verdict_ranges` — good/moderate/weak thresholds
- `insight` — plain-English explanation
- `source` — data source reference

### 3.4 `scripts/pipeline/site_data.py`

Single source of truth for site content:

- **`SECTORS`** — 14 sectors with id, title, icon, description
- **`SECTOR_MAP`** — lookup by sector id
- **`CATEGORY_GROUPS`** — 6 logical groups used for the nav dropdown and categories index page:
  1. Macro & National Accounts (central, economy, financials)
  2. Sector Categories (agriculture, energy, transport, commerce)
  3. Geographic & Sub-national (geo, states)
  4. Social Services (health, education, welfare)
  5. Environment & Urban (environment, housing)
- **`FACTS` / `EXTENDED_FACTS`** — 36 defensible facts with source, scale, why-it-matters
- **`HISTORICAL_TRENDS`** — 8 historical series with yearly points
- **`FACTS_BY_CATEGORY`** — facts grouped by sector

### 3.5 `scripts/pipeline/api_catalog.py`

Catalogs 20 public APIs/data portals across 10 categories with summary statistics:
- Indicators used
- Coverage era
- Update frequency
- Access level (open / demo / key required)
- Provider

---

## 4. Site Navigation

### 4.1 Primary Navigation Bar (all pages)

```
[Brand: FinRadar]  [Dashboard] [Search] [Categories] [Sources]  [Browse Sectors ▼]  [nav-toggle ☰]
```

- **Dashboard** — `index.html` (root pages) or `../index.html` (subfolder pages)
- **Search** — `search.html`
- **Categories** — `categories.html`
- **Sources** — `sources.html`
- **Browse Sectors** — dropdown menu with all 14 sectors grouped into 6 category groups
- **nav-toggle** — mobile hamburger; opens full nav overlay

### 4.2 Dropdown Menu Groups

| Group | Sectors |
|-------|---------|
| Macro & National Accounts | Central Government, Economy, Financials |
| Sector Categories | Agriculture, Energy & Power, Transport, Trade & Commerce |
| Geographic & Sub-national | Geo Levels, State Level |
| Social Services | Health, Education, Welfare & Employment |
| Environment & Urban | Environment & Climate, Housing & Urban |
| More | View All Categories |

### 4.3 Footer Navigation (4 columns)

- **Brand / Tagline / Metadata** — FinRadar branding, tagline, last refreshed timestamp
- **Explore** — Dashboard, Search, Data Sources
- **Key Sectors** — Central Government, State Level, Finance & Banking, Geo Levels, Transport
- **More Sectors** — Economy, Agriculture, Health, Education, Welfare & Employment

### 4.4 Relative Paths

All internal links use relative paths:
- Root pages (`index.html`, `search.html`, etc.): `styles/main.css`, `scripts/app.js`, `category/x.html`
- Subfolder pages (`category/`, `facts/`, `trend/`, `kpi/`): `../styles/main.css`, `../scripts/app.js`, `../index.html`

This makes the site work both on GitHub Pages and when opened via `file://`.

---

## 5. Theme & Styling

### 5.1 `styles/main.css`

Modern, light-first design foundation:
- Canvas: warm paper `#f5f7f8` with soft teal/indigo radial washes
- Surfaces: white cards with `#dfe7ec` borders and layered shadows
- Ink: deep navy `#0c1c2e`, text `#31485a`, muted `#6b7d8b`
- Brand teal `#0e7c70`, indigo `#4f46e5`, green/amber/red verdicts
- Type: Inter for UI, Plus Jakarta Sans for headings

Includes styles for:
- Sticky blurred header, primary nav, sector dropdown, mobile overlay
- Four-column dark footer
- Buttons, badges, cards, grids, tables
- Skip link, focus rings, reduced-motion support
- Responsive breakpoints (1050px, 900px, 760px, 480px)

### 5.2 `styles/european-theme.css`

FinRadar-specific component layer:
- Dark gradient hero with grid texture, radar visual and live signal card
- KPI cards with sector chip, live badge, verdict and insight
- Benchmark cards, tool forms, result panels and data tables
- Category tiles, fact cards, trend previews and canvas chart panel
- KPI/fact/trend detail pages, search results, sources catalogue
- Closing CTA band and mobile adaptations

### 5.3 How themes load

Every page head includes:
```html
<link rel="stylesheet" href="styles/main.css" />
<link rel="stylesheet" href="styles/european-theme.css" />
```

`european-theme.css` builds on the tokens and primitives in `main.css` with FinRadar-specific components.

---

## 6. Client-Side JavaScript (`scripts/app.js`)

Runs on pages that need dynamic data (primarily `index.html`):

- `loadKPIs()` — fetches `data/latest_kpis.json`, falls back to `data/snapshots/indicators.json`
- `renderKPIs(data)` — renders live KPI grid
- `renderHeroStats(data)` — renders stat pills (GDP/capita, macro cycle score, KPI verdicts, peer rank)
- `renderBenchmarks(data)` — renders benchmark values (macro cycle score, global resilience rank)
- `renderPeers(data)` — renders country comparison table (India vs Vietnam, Indonesia, etc.)
- `initPersonalInflationTool(data)` — personal inflation calculator
- `initSalaryParityTool(data)` — city salary parity calculator
- `renderFooter(data)` — updates last-refresh timestamp
- `initNav()` — mobile nav toggle + dropdown menu handlers

`scripts/tools.js` is a second, independent client script loaded on every page. It activates only when a page contains `#calc-config`, parses the embedded registry JSON, renders the form and runs the matching function in `CALCULATORS`. Results are calculated entirely in the browser; inputs are never sent to a server. Schedule tools also expose a CSV download.

**Note:** The KPI grid and hero stats will appear empty when viewing `index.html` via `file://` because browsers block `fetch()` for local files. They work correctly on GitHub Pages (HTTPS). The calculators do not need `fetch()` and work even from `file://`.

### 6.1 Calculator registry (`scripts/pipeline/tools_registry.py`)

The tools hub is registry-driven. Each entry defines its category, title, description, formula, user guide, inputs, outputs and notes. The generator creates one dedicated page per registry tool and embeds the definition as JSON; `tools.js` supplies the calculation function keyed by tool id.

**Loans & EMI (6):** EMI, affordability, interest/principal split, amortization schedule, prepayment impact, loan comparison.
**Deposits & Returns (6):** FD maturity, RD maturity, SIP returns, CAGR, compound interest, simple interest.
**Insurance (4):** life cover need, term premium estimator, health cover gap, emergency fund.
**Personal Finance (5):** retirement corpus, goal savings, 50/30/20 budget, inflation adjuster, net worth.

The two original live-data tools (personal inflation and salary parity) remain bespoke but are listed in the hub and global search.

---

## 7. GitHub Actions — Daily Updates

Two workflows run on separate schedules so a slow official API cannot block the core dashboard.

### 7.1 Core KPI update

File: `.github/workflows/daily-update.yml` · **Schedule:** 02:30 UTC (`cron: "30 2 * * *"`)

1. Check out `main`, set up Python 3.x
2. Run `fetch_kpis.py` — writes `data/latest_kpis.json`
   - Env: `DATA_GOV_IN_TOKEN` (secret; optional — snapshots used if missing)
3. Run `page_generator.py` — regenerates all 132 pages under `site/`
4. Commit `data/latest_kpis.json` and `site/` to `main`
5. `peaceiris/actions-gh-pages@v4` — deploy `site/` to the `gh-pages` branch

### 7.2 Data Lab enrichment

File: `.github/workflows/enrichment-update.yml` · **Schedule:** 03:15 UTC (`cron: "15 3 * * *"`)

1. Check out `main`, set up Python 3.x
2. Run `enrichment.py` — writes `data/extra_metrics.json` and refreshes the last-known-good cache
   - Env: `DATA_GOV_IN_TOKEN`, `APISETU_TOKEN` (secrets; optional — APIsetu token only reports credential readiness; gated data endpoints are not called)
3. Run `page_generator.py` — regenerates the site with the refreshed Data Lab
4. Commit `data/extra_metrics.json`, `data/snapshots/enrichment_cache.json` and `site/` to `main`
5. Deploy `site/` to the `gh-pages` branch

**Permissions:** `contents: write` for both workflows.

**Manual trigger:** Both workflows support `workflow_dispatch` in the Actions tab.

---

## 8. GitHub Pages Configuration

**Required one-time setup** (in GitHub repo Settings → Pages):

| Setting | Value |
|---------|-------|
| Source | Deploy from a branch |
| Branch | `gh-pages` |
| Folder | `/` (root) |

**How deployment works:**

- The GitHub Action pushes compiled `site/` contents to the `gh-pages` branch.
- GitHub Pages serves `gh-pages` directly.
- Your live site URL: `https://<username>.github.io/FinRadar/` (or custom domain `finradar.peabox.in`)

**You never push to `gh-pages` manually.** The Action handles it.

---

## 9. Local Development

### 9.1 Regenerate the site

```bash
python scripts/pipeline/page_generator.py
```

This cleans `site/`, regenerates all pages, copies static assets, and prints a summary.

### 9.2 View locally

Open `site/index.html` in a browser. Note:
- The UI, nav, and footer will render correctly.
- The KPI grid / hero stats will be empty (fetch blocked by `file://` protocol).
- For full local testing with live data, serve via a local HTTP server:

```bash
# Python 3
python -m http.server 5000 --directory site

# Then open http://127.0.0.1:5000
```

### 9.3 Run the data pipeline

```bash
python scripts/pipeline/fetch_kpis.py
```

Requires internet access for World Bank API. Uses demo snapshots if `DATA_GOV_IN_TOKEN` is not set.

---

## 10. Adding New Content

### 10.1 Add a new KPI

1. Edit `scripts/pipeline/kpi_registry.py` — add KPI definition (id, name, sector, unit, formula, verdict ranges, insight, source).
2. Edit `scripts/pipeline/fetch_kpis.py` — add computed value in `compute_values()` if needed.
3. Edit `scripts/pipeline/site_data.py` — optionally add a fact in `EXTENDED_FACTS`.
4. Regenerate: `python scripts/pipeline/page_generator.py`

### 10.2 Add a new sector/category

1. Edit `scripts/pipeline/site_data.py` — add to `SECTORS` and `CATEGORY_GROUPS`.
2. Regenerate pages.

### 10.3 Add a new historical trend

1. Edit `scripts/pipeline/site_data.py` — add to `HISTORICAL_TRENDS`.
2. Regenerate pages.

---

## 11. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Live site shows old content | GitHub Pages not pointing at `gh-pages` | Settings → Pages → Source: `gh-pages` / root |
| KPI grid empty locally | `file://` blocks `fetch()` | Serve via `python -m http.server` instead |
| GitHub Action fails to commit | No write permissions | Ensure `permissions: contents: write` in workflow |
| Nav dropdown overflows screen | Dropdown too tall | Already fixed: `max-height: 82vh`, `overflow-y: auto` |
| Styles not loading | Wrong relative path | Verify `styles/main.css` and `styles/european-theme.css` are linked |
| `site/` not updating | Pipeline not re-run | Run `python scripts/pipeline/page_generator.py` |

---

## 12. Key Files Cheat Sheet

| File | Purpose |
|------|---------|
| `scripts/pipeline/fetch_kpis.py` | Daily data pipeline |
| `scripts/pipeline/page_generator.py` | Static site generator |
| `scripts/pipeline/kpi_registry.py` | KPI definitions |
| `scripts/pipeline/site_data.py` | Sectors, facts, trends, category groups |
| `scripts/pipeline/api_catalog.py` | API catalog with summary stats |
| `scripts/app.js` | Client-side rendering |
| `scripts/charts.js` | Sparkline + trend charts |
| `styles/main.css` | Base theme |
| `styles/european-theme.css` | European palette + nav/footer |
| `.github/workflows/daily-update.yml` | CI: core KPI pipeline + deploy |
| `.github/workflows/enrichment-update.yml` | CI: Data Lab enrichment + deploy |
| `scripts/pipeline/enrichment.py` | Daily Data Lab batch |
| `site/index.html` | Dashboard landing page |
| `site/categories.html` | Category index page |
| `site/data-lab.html` | Expanded official data, definitions, guides, derived KPIs and relationships |

---

## 13. Branch Strategy

| Branch | Contents | Who touches it |
|--------|----------|----------------|
| `main` | Source code, pipeline, `site/` build output | You (via `git push origin main`) |
| `gh-pages` | Compiled static site only | GitHub Action (automatic) |

**Your daily workflow:** edit source → `git add` → `git commit` → `git push origin main`. The Action handles the rest.

---

*End of document.*