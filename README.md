# FinRadar

**India & Global Macro KPIs, Benchmarks & Reports — live from public government data.**

FinRadar turns public government and international data into derived macroeconomic KPIs, benchmarks, plain-English decision tools, and a curated Data Lab of raw official series with definitions and user guides. Derived numbers always show their formulas. The Data Lab now spans India and the world: FX and policy rates, debt and credit, trade, PPP cost-of-living proxies, pay parity, banking, insurance, equity-market depth, official commodity prices and clearly labelled delayed market snapshots.

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-brightgreen)](https://finradar.peabox.in/)
[![Daily Pipeline](https://img.shields.io/badge/Pipeline-Daily%2002%3A30%20UTC-blue)](.github/workflows/daily-update.yml)
[![Data Lab](https://img.shields.io/badge/Data%20Lab-Daily%2003%3A15%20UTC-teal)](.github/workflows/enrichment-update.yml)
[![Static Site](https://img.shields.io/badge/Type-Static%20HTML%2FCSS%2FJS-green)](site/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Overview

FinRadar is a fully static, data-driven website that publishes macroeconomic KPIs and an expanded data catalog across 14 sectors (Central Government, States, Financials, Geo, Transport, Economy, Agriculture, Energy, Health, Education, Welfare, Environment, Commerce, Housing).

Two nightly GitHub Actions fetch live public data, compute KPIs, refresh the Data Lab, regenerate the complete 132-page static site, and deploy it via GitHub Pages.

**Live site:** https://finradar.peabox.in/

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **45 Live KPIs** | Derived metrics across 14 sectors with verdict badges (Good / Moderate / Weak) |
| **Data Lab** | 28 India series plus 368 global series, 12 India + 13 global derived KPIs, 14 macro correlations, 71 official commodity prices, 34 delayed market quotes, Census benchmarks and a source-discovery catalog |
| **Benchmarks** | India High-Frequency Macro Cycle Index (0–100), State-Wise Fiscal Health Scorecard, Global Emerging Market Resilience |
| **Interactive Tools** | 23 calculators across loans, deposits/returns, insurance and personal finance — including EMI, amortization schedules, interest/principal split, SIP, FD/RD, CAGR, term cover and retirement planning |
| **Category Pages** | 14 sector pages with facts, KPIs, and historical trends |
| **Categories Index** | Top-level landing page grouping all categories into 6 logical groups |
| **Search Index** | Full-text lookup across facts, KPIs, India and global series, commodity prices, market quotes, derived metrics, relationships and guides |
| **Sources Catalog** | 25 public APIs across 9 categories with summary statistics, including ECB, BIS, WTO, the World Bank Pink Sheet and clearly labelled Yahoo Finance quotes |
| **Historical Trends** | 8 trend series with sparkline SVG and canvas chart rendering |
| **Modern Dashboard UI** | Light paper canvas, deep-navy dark hero/footer, teal + indigo accents, responsive cards and charts |
| **Mobile Responsive** | Hamburger nav, scrollable sector dropdown, touch-friendly cards |
| **SEO Ready** | Canonical links, meta descriptions and structured page headings |
| **File:// Compatible** | All links use relative paths — works on GitHub Pages and local filesystem |

---

## 🏗️ Tech Stack

- **Frontend:** HTML5, CSS3 (modern light dashboard theme), vanilla JavaScript
- **Charts:** Canvas trend charts + SVG sparklines
- **Data Pipeline:** Python 3, World Bank API, public government snapshots
- **Static Site Generation:** Custom Python generator (`scripts/pipeline/page_generator.py`)
- **Deployment:** GitHub Actions → `gh-pages` branch → GitHub Pages
- **Fonts:** Inter + Plus Jakarta Sans (Google Fonts)

---

## 📊 Data Sources

| Source | Type | Used For |
|--------|------|----------|
| World Bank (api.worldbank.org/v2) | Live API | Core KPI history, 28 curated India/world series, plus global PPP, pay parity, banking, insurance, treasury debt and equity-market indicators |
| World Bank Pink Sheet | Live monthly workbook | 71 official nominal commodity prices (oil, gas, metals, gold, silver, grains, softs) with per-commodity units |
| ECB Data Portal | Live API | Daily euro reference rates for 13 currencies plus a derived INR/USD cross rate |
| BIS Statistics API v2 | Live API | Policy rates, debt-service ratios, credit-to-GDP gaps and effective exchange rates |
| IMF DataMapper / WEO | Live API with World Bank fallback | GDP growth, inflation, government debt and current-account balances for major economies |
| WTO Timeseries | Live API | Annual merchandise exports and imports for eight major trading economies |
| Yahoo Finance | Live API — delayed, secondary | Index, futures and FX reference quotes, clearly labelled as non-official context |
| data.gov.in | Live API (sample key / personal token) | Curated mandi price feed; token unlocks higher record limits. A discovery catalog documents the broader portal |
| Census of India | Decadal benchmark | 2011 population, literacy, urbanisation and sex-ratio benchmarks with definitions |
| RBI DBIE | Live / Snapshot | Interest rates, credit-deposit ratio, GNPAs, forex reserves |
| NPCI | Snapshot | UPI transaction volume, FASTag toll data |
| GST Portal | Snapshot | GST collections growth |
| MNRE | Snapshot | Renewable capacity share |
| Census / MoSPI | Snapshot | Population density, urbanisation, literacy |
| IMF / FRED | Live / Snapshot | Global macro benchmarks |

> **Note:** `DATA_GOV_IN_TOKEN` is optional. Without it, the enrichment batch uses data.gov.in's rate-limited public sample key and keeps the last known good response in `data/snapshots/enrichment_cache.json`. `APISETU_TOKEN` is read to report credential readiness in the discovery catalog; APIsetu remains metadata-only because its data endpoints require consumer registration. IMF DataMapper can be blocked in some networks (`403`); the global feed then falls back to equivalent World Bank series and labels the source accordingly. Every global feed keeps a last-known-good copy in the shared cache, and status badges show whether a table came from the live call or the cache.

---

## 📁 Repository Structure

```
FinRadar/
├── .github/
│   └── workflows/
│       ├── daily-update.yml      # CI: daily 02:30 UTC core KPI pipeline + deploy
│       └── enrichment-update.yml # CI: daily 03:15 UTC Data Lab enrichment + deploy
├── data/
│   ├── latest_kpis.json          # Computed KPIs + benchmarks (pipeline output)
│   ├── extra_metrics.json        # India + global curated series, derived KPIs, commodities, markets, census, relationships, catalog
│   └── snapshots/                # Demo fallbacks and last-known-good enrichment cache
├── docs/
│   └── product-guide.md          # Detailed product & site knowledge document
├── scripts/
│   ├── app.js                    # Client-side rendering (KPI grid, peers, benchmarks, legacy tools)
│   ├── charts.js                 # Sparkline SVG + canvas trend charts
│   ├── tools.js                  # Shared calculator engine for all registry tools
│   └── pipeline/
│       ├── fetch_kpis.py         # Daily core KPI pipeline
│       ├── enrichment.py         # Daily Data Lab batch (India + global feeds + derived KPIs)
│       ├── global_feeds.py       # Global adapters: ECB, BIS, IMF, WTO, World Bank, Pink Sheet, markets
│       ├── datagovin_client.py   # data.gov.in request client with token fallback
│       ├── kpi_registry.py       # Core KPI definitions: formulas, units, verdicts, insights
│       ├── analytics.py          # Plain-English insights per KPI
│       ├── site_data.py          # Sectors, facts, trends, category groups
│       ├── page_generator.py     # Static site generator (132 pages)
│       ├── tools_registry.py     # 21 calculator definitions, fields, formulas and guides
│       └── api_catalog.py        # API catalog with summary stats
├── styles/
│   ├── main.css                  # UI foundation: tokens, layout, nav, cards, tables, footer
│   └── european-theme.css        # European palette + nav/footer overrides
├── site/                         # Build output (committed to main, deployed to gh-pages)
│   ├── index.html                # Dashboard / landing page
│   ├── categories.html           # Category index page
│   ├── search.html               # Search across facts, KPIs, global series, commodities, markets & guides
│   ├── sources.html              # API catalog page
│   ├── data-lab.html             # India + global data, definitions, guides, charts and relationships
│   ├── tools.html                # Categorized calculator hub
│   ├── tools/                    # 23 dedicated calculator pages (21 registry + 2 legacy)
│   ├── category/                 # 14 sector pages
│   ├── facts/                    # 36 fact detail pages
│   ├── trend/                    # 8 historical trend pages
│   ├── kpi/                      # 45 KPI deep-dive pages
│   └── styles/, scripts/, data/  # Copied static assets and JSON feeds
├── README.md                     # This file
└── LICENSE                       # MIT License
```

> `site/` is build output. It is committed to `main` so the GitHub Action can deploy it to `gh-pages`. Do not hand-edit files in `site/` — regenerate via `scripts/pipeline/page_generator.py`.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.x
- Git

### Run locally

```bash
# Clone the repo
git clone https://github.com/PeaBox-Lab/FinRadar.git
cd FinRadar

# Refresh the expanded Data Lab feed (optional — output is already committed)
python scripts/pipeline/enrichment.py

# Regenerate the static site (optional — site/ is already committed)
python scripts/pipeline/page_generator.py

# Serve locally
python -m http.server 5000 --directory site

# Open http://127.0.0.1:5000
```

> The KPI grid populates via `fetch()` over HTTP. Opening `index.html` directly via `file://` will show an empty KPI grid (browsers block local fetch). Use a local server for full functionality.

### Run the data pipeline

```bash
python scripts/pipeline/fetch_kpis.py
```

Requires internet access for World Bank API. Falls back to `data/snapshots/` if `DATA_GOV_IN_TOKEN` is not set.

---

## 🔄 Daily Automation

Two GitHub Actions run every day:

| Time (UTC) | Workflow | Work |
|------------|----------|------|
| 02:30 | `daily-update.yml` | Runs `fetch_kpis.py`, computes the 45 core KPIs, regenerates the site, commits `data/latest_kpis.json` and `site/`, and deploys to `gh-pages` |
| 03:15 | `enrichment-update.yml` | Runs `enrichment.py`, refreshes the 28 India series plus 368 global series, 12 India + 13 global derived KPIs, 14 relationships, 71 commodity prices, 34 market quotes, Census benchmarks and discovery catalog, regenerates the site, commits `data/extra_metrics.json`, the last-known-good cache and `site/`, then deploys to `gh-pages` |

Both workflows support manual triggers from the Actions tab (`workflow_dispatch`). The separation means a slow official API cannot delay the core dashboard update.

---

## 🌐 Deployment

### GitHub Pages (current)

1. Go to **Settings → Pages** in your GitHub repo
2. **Source:** Deploy from a branch
3. **Branch:** `gh-pages`
4. **Folder:** `/` (root)
5. Click **Save**

The live site will be at: `https://<username>.github.io/FinRadar/`

### Cloudflare Pages

1. Import the repo in Cloudflare Pages
2. Framework preset: **None**
3. Build command: (none)
4. Build output directory: `site/`
5. No build step required — fully static

---

## 🛠️ Adding New Content

### Add a new KPI

1. Edit `scripts/pipeline/kpi_registry.py` — add KPI definition (id, name, sector, unit, formula, verdict ranges, insight, source)
2. Edit `scripts/pipeline/fetch_kpis.py` — add computed value if needed
3. Edit `scripts/pipeline/site_data.py` — optionally add a fact in `EXTENDED_FACTS`
4. Regenerate: `python scripts/pipeline/page_generator.py`

### Add a new sector

1. Edit `scripts/pipeline/site_data.py` — add to `SECTORS` and `CATEGORY_GROUPS`
2. Regenerate pages

### Add a new historical trend

1. Edit `scripts/pipeline/site_data.py` — add to `HISTORICAL_TRENDS`
2. Regenerate pages

---

## 📄 Product Documentation

For detailed architecture, navigation structure, theme variables, and troubleshooting, see:

📖 **[docs/product-guide.md](docs/product-guide.md)**

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make changes and test locally
4. Commit (`git commit -m "feat: your feature"`)
5. Push to your branch (`git push origin feature/your-feature`)
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

- **Website:** https://finradar.peabox.in/
- **Repo:** https://github.com/PeaBox-Lab/FinRadar
- **Issues:** [GitHub Issues](https://github.com/PeaBox-Lab/FinRadar/issues)

---

*FinRadar — Real economy numbers, plain English.*