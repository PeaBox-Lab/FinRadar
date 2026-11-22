# FinRadar — daily pipeline

Runs every day (locally or via the GitHub Action) and writes `data/latest_kpis.json`,
which the static site (`scripts/app.js`) renders into live KPIs, benchmarks and tools.

## Sources

- **World Bank Open Data API (verified live, `api.worldbank.org/v2`)** — values fetched per run:
  - India: `FP.CPI.TOTL.ZG` (Inflation), `NY.GDP.PCAP.CD` (GDP per capita), `NY.GDP.PCAP.PP.CD`
    (GDP per capita, PPP), `NY.GDP.MKTP.KD.ZG` (GDP growth), `NE.CAB.TOTL.PT` (Current account).
  - Peers: **VNM** (Vietnam), **IDN** (Indonesia), **BRA** (Brazil), **MEX** (Mexico) — real GDP
    growth, current account, FDI inflows.
- **Snapshots (`data/snapshots/`)** — India-specific figures (G-Sec yields, UPI volumes, GST
  growth, forex reserves, state-level CPI spread, IIP/power demand growth, debt-service share)
  with labeled "DEMO SNAPSHOT" fallbacks when live sources aren't available.
- **data.gov.in (optional, `DATA_GOV_IN_TOKEN` env var)** — can be wired for live India data.

## KPI computation rule

Every published number is a **derived metric**: a spread (real vs headline, nominal vs PPP),
a velocity (UPI ticket = value ÷ volume), or a composite (Macro Cycle Score). Raw tables are
never republished as-is.

## Quick start

```sh
python3 scripts/pipeline/fetch_kpis.py   # refresh data/latest_kpis.json (then `git add` it)
```

To preview the site locally: `python -m http.server` in the repo root and open `index.html`.
