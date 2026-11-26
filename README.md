# Radar

**India & Global Macro KPIs, Benchmarks & Reports — public data, clearly labelled.**

Radar is the completed sitewide rebrand. Canonical site: **https://radar.peabox.in/**

[![Website](https://img.shields.io/badge/Website-radar.peabox.in-brightgreen)](https://radar.peabox.in/)
[![Static Site](https://img.shields.io/badge/Type-Static%20HTML%2FCSS%2FJS-green)](site/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Radar is a fully static site built from a **hybrid live API + curated monthly snapshot pipeline**. It publishes derived macro KPIs, benchmarks, sector pages, 23 calculators, a Data Lab and a searchable snapshot catalogue.

- **Official-first sourcing:** primary values come from public government and international APIs; curated published figures are transcribed from official publications or named industry bodies.
- **No invented data (null-with-reason):** no demo, random, mock, simulated or indicative numbers. If an official series is unavailable, the metric is published as `null` with a reason (`source_type: "unavailable"` and an explicit "no data available yet" disclosure) — never estimated.
- **Transparent snapshots:** every card, chart and table powered by a monthly snapshot carries exactly `Static Snapshot • Updated Monthly (Not Live)` plus `Last Updated: Month YYYY` (for example, `Last Updated: November 2026`).
- **Concise home page:** `index.html` is a short entry point, not a wall of numbers. Detail is split across five categorised dashboards generated from `DASHBOARD_PAGES` in `scripts/pipeline/page_generator.py`:
  - `global.html` — global macro (`global`)
  - `markets.html` — exchanges and secondary market context (`markets`)
  - `insurance.html` — IRDAI insurance snapshots (`insurance`)
  - `india.html` — India national accounts (`india`)
  - `mobility-housing.html` — auto, housing and home-loan trends (`mobility-housing`)

---

## Current generated inventory

| Item | Count |
|------|-------:|
| KPI deep-dive pages | 45 |
| Calculator pages | 23 (21 registry tools + 2 legacy live-data tools) |
| Category pages | 14 |
| Fact detail pages | 36 |
| Historical trend pages | 8 |
| Categorised dashboards | 5 |
| Monthly snapshot datasets | 6 |

The generator also writes the home page, search, sources, Data Lab, tools hub, categories index, `monthly-snapshots.html`, `sitemap.xml` and `robots.txt`.

### Monthly snapshots

`monthly-snapshots.html` is the catalogue for the curated datasets in `data/monthly-snapshots/*.json`. `data/monthly-snapshots/schema.json` defines the format: dataset id, title, category, `last_updated`, coverage, source organisation/title/URL/retrieval date, methodology, metrics with periods and values (numbers or `null`), notes, and the stamped badge/schema version.

Current datasets: `global-macro`, `global-exchanges`, `irdai-insurance`, `india-auto-sales`, `india-housing-sales`, `india-home-loans`. Each links back to its dashboard section.

---

## Pipeline and commands

Typical local order: refresh snapshots, refresh live data, regenerate the site.

```bash
python scripts/pipeline/update_monthly_snapshots.py  # validate and stamp curated snapshots
python scripts/pipeline/fetch_kpis.py                # live API + curated inputs → data/latest_kpis.json
python scripts/pipeline/enrichment.py                # curated Data Lab feeds → data/extra_metrics.json
python scripts/pipeline/page_generator.py            # regenerate site/, sitemap.xml, robots.txt
```

`update_monthly_snapshots.py` refuses files containing mock/demo/placeholder/random/indicative language, validates required source and period fields, and stamps `schema_version` and the mandatory badge. `fetch_kpis.py` emits `null` plus `source_type: "unavailable"` when a source cannot supply a value. Enrichment keeps last-known-good official responses where allowed and labels their status, rather than substituting fabricated data.

Nightly GitHub Actions run `fetch_kpis.py` (02:30 UTC) and `enrichment.py` (03:15 UTC), each followed by `page_generator.py`. Snapshot transcription is a deliberate manual step before regeneration.

---

## SEO output

The generator writes root `sitemap.xml`, `robots.txt` and `_headers` into `site/`.

- Sitemap namespace: `http://www.sitemaps.org/schemas/sitemap/0.9`
- All sitemap URLs use the canonical domain `https://radar.peabox.in/`
- `robots.txt` contains the directive `Sitemap: https://radar.peabox.in/sitemap.xml`
- Cloudflare Pages `_headers` serves `/sitemap.xml` as `application/xml` with `X-Content-Type-Options: nosniff`

---

## Deployment

The deployment decision is unchanged: **Cloudflare Pages + Cloudflare Worker** serve the generated static output at `https://radar.peabox.in/`. The repository's existing GitHub Actions still regenerate `site/` and publish it to the `gh-pages` branch; this rebrand does not alter that wiring.

---

## Repository layout

```text
data/
  latest_kpis.json          # computed KPI output
  extra_metrics.json        # Data Lab output
  snapshots/                # curated published inputs and cache
  monthly-snapshots/        # 6 curated datasets + schema.json
scripts/
  app.js, charts.js, tools.js
  pipeline/                 # four commands above, registries and feed adapters
site/                       # generated static output; do not hand-edit
  index.html + 5 dashboards + monthly-snapshots.html
  kpi/, category/, facts/, trend/, tools/, data/
  sitemap.xml, robots.txt
docs/product-guide.md        # detailed product and architecture reference
```

Regenerate with `python scripts/pipeline/page_generator.py`; never edit files under `site/` by hand.

For full detail, see [docs/product-guide.md](docs/product-guide.md).

---

## License

MIT — see [LICENSE](LICENSE).
