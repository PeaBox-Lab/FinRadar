# FinRadar — Product & Site Knowledge Document

A comprehensive user guide and technical reference for the FinRadar static site: architecture, data pipeline, site structure, navigation, theme, and deployment.

---

## 1. Project Overview

**FinRadar** is a static, data-driven website that publishes derived macroeconomic KPIs, benchmarks, and reports built from public government data (World Bank, data.gov.in, RBI, NPCI, GST portal, MNRE, Census, IMF, FRED, etc.).

- **No server-side code** — fully static HTML/CSS/JS.
- **Daily automated updates** via GitHub Action at 02:30 UTC.
- **Deployment** via GitHub Pages from the `gh-pages` branch.
- **File:// compatible** — all CSS/JS/nav links use relative paths so the site can be opened directly from the filesystem.

---

## 2. Repository Structure (main branch)

```
FinRadar/
├── .github/
│   └── workflows/
│       └── daily-update.yml      # CI: fetch KPIs, regenerate site, deploy to gh-pages
├── data/
│   ├── latest_kpis.json          # Pipeline output: 45 KPIs + India + peers
│   └── snapshots/                # Demo fallbacks for India-specific figures
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
│   ├── app.js                    # Client-side rendering: KPI grid, benchmarks, tools, peers, reports
│   ├── charts.js                 # Sparkline SVG + canvas trend chart renderer
│   └── pipeline/
│       ├── fetch_kpis.py         # Daily pipeline: fetches data, computes KPIs, writes latest_kpis.json
│       ├── kpi_registry.py       # All KPI definitions: formulas, units, verdict ranges, insights
│       ├── analytics.py          # Plain-English insights per KPI
│       ├── site_data.py          # Source of truth: SECTORS, CATEGORY_GROUPS, FACTS, HISTORICAL_TRENDS
│       ├── page_generator.py     # Generates complete static site under site/ (97 pages)
│       └── api_catalog.py        # API catalog: 17 APIs across 11 categories with summary stats
├── styles/
│   ├── main.css                  # Base dark glassmorphic theme + components
│   └── european-theme.css        # European navy/slate/cream palette + nav/footer overrides
├── site/                         # BUILD OUTPUT (committed to main; deployed to gh-pages)
│   ├── index.html                # Dashboard / landing page
│   ├── search.html               # Full-text search across facts & KPIs
│   ├── sources.html              # Categorized API catalog with summary stats
│   ├── categories.html           # Top-level category index page (all 14 categories)
│   ├── category/*.html           # 14 sector pages (facts, KPIs, trends)
│   ├── facts/*.html              # 36 fact detail pages
│   ├── trend/*.html              # 8 historical trend chart pages
│   ├── kpi/*.html                # 45 KPI deep-dive pages
│   ├── styles/                   # Copied CSS
│   ├── scripts/                  # Copied client JS
│   ├── data/                     # latest_kpis.json + snapshots
│   └── sitemap.xml               # SEO sitemap with 97 URLs
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
- `data/latest_kpis.json`, `data/snapshots/`

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

Catalogs 17 public APIs/data portals across 11 categories with summary statistics:
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

Base dark glassmorphic theme:
- Background: radial gradient navy `#0b1120`
- Cards: `rgba(255,255,255,0.03)` with `rgba(255,255,255,0.09)` borders
- Accent teal: `#14b8a6`
- Accent violet: `#a855f7`
- Accent orange: `#f97316`
- Font: Inter (Google Fonts)

Includes styles for:
- Header / nav / dropdown / mobile overlay
- Footer (4-column grid)
- Cards, KPI cards, stat pills, verdict badges
- Benchmarks, tools, reports, peers table
- Category pages, fact detail, KPI detail, trend pages
- Search results, sources page
- Responsive breakpoints (980px, 860px, 780px)

### 5.2 `styles/european-theme.css`

Overrides with European palette:
- Background: `#0f172a` (slate navy)
- Nav: `rgba(15,23,42,0.88)` with backdrop blur
- Accent teal: `#2d6a4f`
- Accent orange: `#fbbf24`
- Accent violet: `#e879f2`
- Accent coral: `#ff6b6b`

Also contains:
- `.nav-primary` — inline primary nav styling
- `.nav-drop-menu` — scrollable dropdown (`max-height: 82vh`, `overflow-y: auto`, styled scrollbar)
- Footer navigation overrides
- Responsive mobile nav overlay

### 5.3 How themes load

Every page head includes:
```html
<link rel="stylesheet" href="styles/main.css" />
<link rel="stylesheet" href="styles/european-theme.css" />
```

`european-theme.css` overrides variables and component styles from `main.css`.

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

**Note:** The KPI grid and hero stats will appear empty when viewing `index.html` via `file://` because browsers block `fetch()` for local files. They work correctly on GitHub Pages (HTTPS).

---

## 7. GitHub Actions — Daily Update

File: `.github/workflows/daily-update.yml`

**Schedule:** Daily at 02:30 UTC (`cron: "30 2 * * *"`)

**Steps:**

1. `actions/checkout@v4` — check out `main`
2. `actions/setup-python@v5` — set up Python 3.x
3. Run `fetch_kpis.py` — fetches live data, computes KPIs, writes `data/latest_kpis.json`
   - Env: `DATA_GOV_IN_TOKEN` (secret; optional — demo snapshots used if missing)
4. Run `page_generator.py` — regenerates all 97 pages under `site/`
5. Commit `data/latest_kpis.json` and `site/` to `main`
6. `peaceiris/actions-gh-pages@v4` — deploy `site/` contents to `gh-pages` branch

**Permissions:** `contents: write` (required to commit and push)

**Manual trigger:** Available via `workflow_dispatch` in the Actions tab.

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
| `.github/workflows/daily-update.yml` | CI: pipeline + deploy |
| `site/index.html` | Dashboard landing page |
| `site/categories.html` | Category index page |
| `site/sitemap.xml` | SEO sitemap |

---

## 13. Branch Strategy

| Branch | Contents | Who touches it |
|--------|----------|----------------|
| `main` | Source code, pipeline, `site/` build output | You (via `git push origin main`) |
| `gh-pages` | Compiled static site only | GitHub Action (automatic) |

**Your daily workflow:** edit source → `git add` → `git commit` → `git push origin main`. The Action handles the rest.

---

*End of document.*