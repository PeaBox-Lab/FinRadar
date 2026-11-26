# Radar — Product & Site Knowledge Document

A concise reference for the Radar static site: pages, data pipeline, snapshot layer, SEO output and deployment.

---

## 1. Product overview

Radar is the completed sitewide rebrand; the canonical domain is **https://radar.peabox.in/**. It publishes derived macro KPIs, benchmarks, sector facts, trends, calculators and a Data Lab from public data.

- **Hybrid live API + curated monthly snapshot pipeline:** live official feeds supply current series; curated, dated publications supply figures without a stable keyless API.
- **Official-first sourcing:** World Bank, ECB, BIS, WTO, IMF/WEO, RBI, NPCI, GST portal, MNRE, Census of India and data.gov.in are preferred; named industry bodies (for example SIAM or WFE) are used only where they are the publisher and are labelled as such.
- **Null-with-reason:** no demo, random, mock, simulated or indicative numbers. If an official metric is unavailable, Radar publishes `null` with a reason (`source_type: "unavailable"` and a "no data available yet" verdict) instead of estimating.
- **Mandatory snapshot disclosure:** every snapshot-powered card, chart and table displays exactly `Static Snapshot • Updated Monthly (Not Live)` together with `Last Updated: Month YYYY` (for example, `Last Updated: November 2026`). Delayed market quotes are secondary context, never official statistics.

---

## 2. Site structure

`site/` is generated output. Do not hand-edit it; regenerate with `python scripts/pipeline/page_generator.py`.

### 2.1 Home and dashboards

`index.html` is deliberately concise: a short introduction and navigation into the detail routes. The five categorised dashboards come from `DASHBOARD_PAGES` in `scripts/pipeline/page_generator.py`; the IDs are authoritative:

| Route | ID | Coverage |
|-------|----|----------|
| `global.html` | `global` | World GDP, inflation, policy rates, FX, debt, trade |
| `markets.html` | `markets` | Exchange fundamentals and labelled delayed market context |
| `insurance.html` | `insurance` | IRDAI insurance penetration, density and premiums |
| `india.html` | `india` | India growth, prices, fiscal position and benchmarks |
| `mobility-housing.html` | `mobility-housing` | SIAM auto sales, housing sales and home loans |

Other generated routes: `search.html`, `sources.html`, `data-lab.html`, `tools.html`, `categories.html`, `monthly-snapshots.html`, plus `kpi/`, `category/`, `facts/`, `trend/`, `tools/` and `data/`.

### 2.2 Categories

`scripts/pipeline/site_data.py` defines 14 sectors grouped into 5 navigation groups: Macro & National Accounts, Sector Categories, Geographic & Sub-national, Social Services, and Environment & Urban.

All internal links are relative, so the static output works on the canonical domain and from a local HTTP server. Dynamic KPI data is fetched over HTTP and will be empty under `file://`.

---

## 3. Generated inventory

| Item | Count |
|------|-------:|
| KPIs | 45 |
| Calculator pages | 23 (21 registry + 2 legacy) |
| Categories | 14 |
| Facts | 36 |
| Trends | 8 |
| Dashboards | 5 |
| Monthly snapshot datasets | 6 |

The generator also emits the home page, search, sources, Data Lab, tools hub, categories index, snapshot catalogue, `sitemap.xml` and `robots.txt`.

---

## 4. Monthly snapshot layer

- **Files:** `data/monthly-snapshots/*.json` (6 datasets) plus `data/monthly-snapshots/schema.json`.
- **Datasets:** `global-macro`, `global-exchanges`, `irdai-insurance`, `india-auto-sales`, `india-housing-sales`, `india-home-loans`.
- **Schema fields:** `dataset_id`, `title`, `category`, `page`, `last_updated`, `coverage`, `source` (organisation, title, URL, retrieved date), `methodology`, `metrics` (id, name, unit, definition, dated values that may be numeric or `null`), `notes`, plus stamped `schema_version` and `badge`.
- **Catalogue:** `monthly-snapshots.html` lists every dataset with its source, coverage and disclosure badge and links to the relevant dashboard section.
- **Update rule:** read the linked publication, transcribe only published figures, set `last_updated`, run `update_monthly_snapshots.py`, then regenerate the site. The updater rejects mock/demo/placeholder/random/indicative language and validates required fields. Derived latest values and YoY changes are stamped by the same script.

The shared badge string is defined in `scripts/pipeline/monthly_snapshots.py` and reused by the generator for cards, tables, catalogue entries and curated KPI disclosures.

---

## 5. Data pipeline

| Command | Output / role |
|---------|---------------|
| `python scripts/pipeline/update_monthly_snapshots.py` | Validates and normalises `data/monthly-snapshots/*.json`; stamps schema version and badge |
| `python scripts/pipeline/fetch_kpis.py` | Live World Bank/official inputs plus curated `data/snapshots/` → `data/latest_kpis.json` (45 KPIs); unavailable metrics are `null` with `source_type: "unavailable"` |
| `python scripts/pipeline/enrichment.py` | Curated India/global Data Lab feeds, derived KPIs, commodities, market context and relationships → `data/extra_metrics.json` |
| `python scripts/pipeline/page_generator.py` | Builds all routes under `site/`, copies JSON assets, and writes `sitemap.xml` and `robots.txt` |

Enrichment keeps last-known-good official responses where a feed is rate-limited and labels their status; it does not replace missing official values with synthetic ones. Nightly GitHub Actions run `fetch_kpis.py` at 02:30 UTC and `enrichment.py` at 03:15 UTC, each followed by the generator. Snapshot transcription and validation remain an explicit manual step.

---

## 6. SEO files

The generator writes these files to the root of `site/`:

- `sitemap.xml` — `urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"`, with every URL on `https://radar.peabox.in/` and change frequencies reflecting live versus monthly content.
- `robots.txt` — allows all crawlers and includes `Sitemap: https://radar.peabox.in/sitemap.xml`.
- `_headers` — Cloudflare Pages rule serving `/sitemap.xml` as `application/xml` with `X-Content-Type-Options: nosniff`.

---

## 7. Deployment

The deployment decision is unchanged: **Cloudflare Pages + Cloudflare Worker** for the generated static site at the canonical domain. The existing GitHub Actions continue to regenerate `site/` and publish it to the `gh-pages` branch; the Radar rebrand and documentation update do not change deployment wiring.

---

## 8. Local workflow

```bash
python scripts/pipeline/update_monthly_snapshots.py
python scripts/pipeline/fetch_kpis.py
python scripts/pipeline/enrichment.py
python scripts/pipeline/page_generator.py
python -m http.server 5000 --directory site   # open http://127.0.0.1:5000
```

Calendars/calculators run entirely in the browser. To add content, edit the relevant registry or `site_data.py`, then regenerate. Never edit `site/` directly.

---

## 9. Key files

| File | Purpose |
|------|---------|
| `scripts/pipeline/page_generator.py` | `DASHBOARD_PAGES`, all static routes, sitemap and robots |
| `scripts/pipeline/monthly_snapshots.py` | Badge text, schema reader and render helpers |
| `scripts/pipeline/update_monthly_snapshots.py` | Snapshot validation and stamping |
| `scripts/pipeline/fetch_kpis.py` / `kpi_registry.py` | 45 KPI computation and definitions |
| `scripts/pipeline/enrichment.py` / `global_feeds.py` | Curated Data Lab feeds |
| `scripts/pipeline/site_data.py` | 14 sectors, 5 groups, 36 facts, 8 trends |
| `scripts/pipeline/tools_registry.py` | 21 registry calculators (+2 legacy pages) |
| `data/monthly-snapshots/schema.json` | Snapshot contract |
| `site/sitemap.xml`, `site/robots.txt` | Generated SEO output |
