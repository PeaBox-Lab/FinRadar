# FinRadar

**India & Global Macro KPIs, Benchmarks & Reports — live from public government data.**

FinRadar turns public government data into derived macroeconomic KPIs, benchmarks, and plain-English decision tools. Every published number is a computed metric (ratios, velocities, composites) — never raw tables republished as-is.

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-brightgreen)](https://finradar.peabox.in/)
[![Daily Pipeline](https://img.shields.io/badge/Pipeline-Daily%2002%3A30%20UTC-blue)](.github/workflows/daily-update.yml)
[![Static Site](https://img.shields.io/badge/Type-Static%20HTML%2FCSS%2FJS-green)](site/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Overview

FinRadar is a fully static, data-driven website that publishes derived macroeconomic KPIs across 12 sectors (Central Government, States, Financials, Geo, Transport, Economy, Agriculture, Energy, Health, Education, Welfare, Environment, Commerce, Housing).

A daily GitHub Action at **02:30 UTC** fetches live public data, computes KPIs, regenerates the complete 97-page static site, and deploys it via GitHub Pages.

**Live site:** https://finradar.peabox.in/

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **45 Live KPIs** | Derived metrics across 14 sectors with verdict badges (Good / Moderate / Weak) |
| **Benchmarks** | India High-Frequency Macro Cycle Index (0–100), State-Wise Fiscal Health Scorecard, Global Emerging Market Resilience |
| **Interactive Tools** | Personal inflation calculator, city salary-parity tool |
| **Category Pages** | 14 sector pages with facts, KPIs, and historical trends |
| **Categories Index** | Top-level landing page grouping all categories into 6 logical groups |
| **Search Index** | Full-text lookup across all facts and KPIs |
| **Sources Catalog** | 17 public APIs across 11 categories with summary statistics |
| **Historical Trends** | 8 trend series with sparkline SVG and canvas chart rendering |
| **Modern Dashboard UI** | Light paper canvas, deep-navy dark hero/footer, teal + indigo accents, responsive cards and charts |
| **Mobile Responsive** | Hamburger nav, scrollable sector dropdown, touch-friendly cards |
| **SEO Ready** | Sitemap with 97 URLs, canonical links, meta descriptions |
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
| World Bank (api.worldbank.org/v2) | Live API | GDP growth, GDP per capita (nominal & PPP), inflation, current account, FDI, peer comparisons |
| data.gov.in | Live API (token-gated) | India-specific figures (GST, UPI, state data) |
| RBI DBIE | Live / Snapshot | Interest rates, credit-deposit ratio, GNPAs, forex reserves |
| NPCI | Snapshot | UPI transaction volume, FASTag toll data |
| GST Portal | Snapshot | GST collections growth |
| MNRE | Snapshot | Renewable capacity share |
| Census / MoSPI | Snapshot | Population density, urbanisation, literacy |
| IMF / FRED | Live / Snapshot | Global macro benchmarks |

> **Note:** `DATA_GOV_IN_TOKEN` is optional. If not set, the pipeline falls back to committed demo snapshots in `data/snapshots/`.

---

## 📁 Repository Structure

```
FinRadar/
├── .github/
│   └── workflows/
│       └── daily-update.yml      # CI: daily 02:30 UTC pipeline + deploy
├── data/
│   ├── latest_kpis.json          # Computed KPIs + benchmarks (pipeline output)
│   └── snapshots/                # Demo fallbacks for India-specific figures
├── docs/
│   └── product-guide.md          # Detailed product & site knowledge document
├── scripts/
│   ├── app.js                    # Client-side rendering (KPI grid, tools, peers, benchmarks)
│   ├── charts.js                 # Sparkline SVG + canvas trend charts
│   └── pipeline/
│       ├── fetch_kpis.py         # Daily data pipeline
│       ├── kpi_registry.py       # KPI definitions: formulas, units, verdicts, insights
│       ├── analytics.py          # Plain-English insights per KPI
│       ├── site_data.py          # Sectors, facts, trends, category groups
│       ├── page_generator.py     # Static site generator (97 pages)
│       └── api_catalog.py        # API catalog with summary stats
├── styles/
│   ├── main.css                  # UI foundation: tokens, layout, nav, cards, tables, footer
│   └── european-theme.css        # European palette + nav/footer overrides
├── site/                         # Build output (committed to main, deployed to gh-pages)
│   ├── index.html                # Dashboard / landing page
│   ├── categories.html           # Category index page
│   ├── search.html               # Search across facts & KPIs
│   ├── sources.html              # API catalog page
│   ├── category/                 # 14 sector pages
│   ├── facts/                    # 36 fact detail pages
│   ├── trend/                    # 8 historical trend pages
│   ├── kpi/                      # 45 KPI deep-dive pages
│   ├── styles/, scripts/, data/  # Copied static assets
│   └── sitemap.xml               # SEO sitemap (97 URLs)
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

A GitHub Action runs every day at **02:30 UTC**:

1. Checks out `main`
2. Runs `fetch_kpis.py` — fetches live data, computes 45 KPIs
3. Runs `page_generator.py` — regenerates all 97 pages under `site/`
4. Commits `data/latest_kpis.json` and `site/` to `main`
5. Deploys `site/` contents to the `gh-pages` branch
6. GitHub Pages serves `gh-pages` automatically

**You only push to `main`.** The Action handles everything else.

**Manual trigger:** Available via the Actions tab → `workflow_dispatch`.

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