# FinRadar — India & Global Macro KPIs, Benchmarks & Reports

FinRadar publishes **original benchmarks and automated reports built from public government data**. Instead of republishing raw tables, it combines multiple datasets into derived KPIs, composite indices and plain-English decision tools — that is the fintech-media / programmatic-SEO / B2B-research playbook, done with zero compliance risk.

## Use case

A central dashboard that turns public data into living numbers:

- **Personal finance & rates:** real interest rates (10-Y G-Sec yield vs. CPI), the gap between nominal and PPP GDP per capita, real inflation rate.
- **Economic momentum:** digital consumption velocity (UPI ticket size tracked with GST growth), IIP and power-demand growth.
- **External stability:** import cover ratio, reserve adequacy, debt service burden.
- **Interactive tools:** "Your personal inflation rate" (per-user spending split), "Salary parity between two cities" — "What salary in Jaipur gives you the same purchasing power as ₹20 LPA in Mumbai?"
- **Original benchmarks:** India High-Frequency Macro Cycle Index (0–100), State-Wise Economic & Fiscal Health Scorecard (28 states), Global Emerging Market Resilience Benchmark.

## Site layout

```
FinRadar/
  index.html                     # one-page site: hero, KPI dashboard, benchmarks, glossary, tools, reports, peers, sources
  styles/main.css                # modern dark theme, glassmorphic cards, teal/violet/orange accents
  scripts/app.js                 # client renderer — reads data/latest_kpis.json, renders KPIs/tools/peers
  data/
    latest_kpis.json             # computed KPIs + benchmarks (regenerated daily by the pipeline)
    snapshots/                   # labeled fallback data (India-specific figures are marked DEMO)
    subindices.json              # MoSPI-style sub-indices for the personal inflation calculator
    snapshots/city_indices.json  # illustrative city indices for the salary-parity tool
  scripts/pipeline/fetch_kpis.py # daily pipeline: fetch → compute → write data/latest_kpis.json
  .github/workflows/daily-update.yml   # GitHub Action: daily cron → run pipeline → commit to main
  README.md (this file)
```

## Data sources

**Verified live (api.worldbank.org/v2):**

- `NY.GDP.PCAP.CD` — GDP per capita (current US$) — *India (2025): ₹2,702.48*
- `NY.GDP.PCAP.PP.CD` — GDP per capita, PPP (current international $)
- `NY.GDP.MKTP.KD.ZG` — GDP growth (annual %) — *India (2025): 7.57%*
- `FP.CPI.TOTL.ZG` — Inflation, consumer prices (annual %) — *India (2025): 2.40%*
- Peers: Vietnam, Indonesia, Brazil, Mexico (same indicators).

**Optional (env token `DATA_GOV_IN_TOKEN`, data.gov.in):** live India-specific figures — G-Sec yields, UPI volumes, GST collections, state-level CPI spreads.

**Static fallbacks (data/snapshots/):** illustrative values for India-specific figures that are clearly marked "DEMO SNAPSHOT" in the UI until live sources are wired in.

## KPI computation principle

Every published number is a **derived metric**: a ratio (real rate = G-Sec yield − CPI), a velocity (UPI ticket = UPI value ÷ volume), or a composite (Macro Cycle Score). Raw tables are never republished as-is.

## Deploy

1. Push to GitHub → **Settings > Pages** → Source: `main` branch (or any branch; the repo is fully static).
2. Or on **Cloudflare Pages**: import the repo, framework "None", root dir `FinRadar`. Static — no build step.
3. Optional: set the `DATA_GOV_IN_TOKEN` secret for token-gated live India data.

## Daily automation

`python3 scripts/pipeline/fetch_kpis.py` — fetches fresh data, computes KPIs, writes `data/latest_kpis.json`. The GitHub Action runs it on a daily cron (02:30 UTC) and commits changes to `main` automatically. Site users always see fresh numbers; if sources are unreachable, the app falls back to the committed snapshot.

## Development

```sh
python3 scripts/pipeline/fetch_kpis.py   # refresh data/latest_kpis.json
```

To preview locally: `python -m http.server` (or any static server) and open `index.html`.
