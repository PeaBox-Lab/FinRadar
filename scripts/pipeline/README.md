# Radar — data pipeline

Radar (sitewide rebrand complete; canonical domain **https://radar.peabox.in/**) is built from a **hybrid live API + curated monthly snapshot pipeline**. All generated output is static; no server-side code runs on the site.

## Commands

Run from the repository root, in this order when refreshing everything:

```bash
python scripts/pipeline/update_monthly_snapshots.py  # validate/stamp curated snapshot JSON
python scripts/pipeline/fetch_kpis.py                # live + curated inputs → data/latest_kpis.json
python scripts/pipeline/enrichment.py                # Data Lab feeds → data/extra_metrics.json
python scripts/pipeline/page_generator.py            # regenerate site/, sitemap.xml, robots.txt
```

`fetch_kpis.py` pulls World Bank and other keyless official series and combines them with curated published figures in `data/snapshots/`. `enrichment.py` builds the India/global Data Lab, commodity prices, derived KPIs and labelled market context. `page_generator.py` writes the concise home page, five dashboards, snapshot catalogue, detail pages and SEO files.

## Sourcing rules

- **Official-first:** prefer government, central-bank and international-organisation publications; name industry bodies explicitly when they are the publisher.
- **No demo, random, mock, simulated or indicative numbers.**
- **Null-with-reason:** when an official metric is unavailable, emit `null` with `source_type: "unavailable"` and a visible no-data verdict. Never fabricate or interpolate a substitute.
- Cached official responses used by enrichment are labelled by status; delayed Yahoo Finance quotes are secondary context, never official statistics.

## Monthly snapshots

Curated datasets live in `data/monthly-snapshots/*.json` (6 datasets) with `data/monthly-snapshots/schema.json` as the contract: source URL and retrieval date, methodology, coverage, `last_updated`, and metric values that are published numbers or `null` plus a reason in notes.

`update_monthly_snapshots.py` validates required fields, stamps `schema_version` and the badge, and rejects mock/demo/placeholder/random/indicative language. Every snapshot-powered card, chart and table must show exactly:

`Static Snapshot • Updated Monthly (Not Live)` · `Last Updated: Month YYYY`

Examples: `global-macro`, `global-exchanges`, `irdai-insurance`, `india-auto-sales`, `india-housing-sales`, `india-home-loans`. The catalogue is `site/monthly-snapshots.html`.

## Generated output

`page_generator.py` reads the registries and JSON feeds and writes: 45 KPIs, 23 calculator pages, 14 categories, 36 facts, 8 trends, 5 dashboards (`india`, `global`, `markets`, `insurance`, `mobility-housing`) and 6 snapshot datasets, plus `sitemap.xml`, `robots.txt` and Cloudflare Pages `_headers`. The sitemap uses `http://www.sitemaps.org/schemas/sitemap/0.9`; robots contains `Sitemap: https://radar.peabox.in/sitemap.xml`; `_headers` serves the sitemap as `application/xml`.

## Deployment

Deployment decision unchanged: **Cloudflare Pages + Cloudflare Worker** at `https://radar.peabox.in/`. The existing GitHub Actions still regenerate `site/` and publish it to `gh-pages`; do not hand-edit generated files.
