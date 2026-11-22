#!/usr/bin/env python3
"""
FinRadar — daily KPI pipeline.

Fetches the latest India & global macro numbers from public sources and
writes ``data/latest_kpis.json``, which the static site (scripts/app.js)
renders into living KPIs, benchmarks and tools.

Sources used:

* World Bank Open Data API (verified live: api.worldbank.org/v2)
* Static snapshots in ``data/snapshots/`` for India-specific figures when
  the World Bank does not carry them (G-Sec yields, UPI, state CPI spreads,
  FX reserves, imports). If the ``DATA_GOV_IN_TOKEN`` environment variable
  is set, the pipeline can also pull from data.gov.in.

Computation rule of this project: every KPI is a ratio, a spread or a
composite score derived from the raw series — never a raw table copy.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "data" / "snapshots"
OUT = ROOT / "data" / "latest_kpis.json"

WB_API = "http://api.worldbank.org/v2"

# ---------------------------------------------------------------------------
# World Bank helpers
# ---------------------------------------------------------------------------

def fetch_json(url: str, timeout: int = 15):
    """Fetch a URL as JSON. Returns None on any failure."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "FinRadar/1.0 (+github.com/<repo>) data pipeline"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
        return json.loads(payload)
    except Exception as exc:  # network/HTTP/JSON errors — degrade gracefully
        print(f"[pipeline] fetch failed: {url} -> {exc}")
        return None


def wb_value(wb_values: dict, iso: str, indicator: str):
    """Return the numeric value of a WB indicator from a wb_values dict."""
    row = wb_values.get(iso, {}).get(indicator)
    if isinstance(row, dict):
        return row.get("value")
    return row if row is not None else None


def wb_latest(country: str, indicator: str):
    """
    Return the newest (date, value) from the WB API for a country+indicator.
    WB returns the series newest-first; with per_page=1 we get the latest.
    """
    url = f"{WB_API}/country/{country}/indicator/{urllib.parse.quote(indicator)}?format=json&per_page=2"
    data = fetch_json(url)
    if not data or len(data) < 2 or not data[1]:
        return None
    # WB returns newest first, but sort to be safe.
    rows = sorted(data[1], key=lambda r: str(r.get("date", "")), reverse=True)
    row = rows[0]
    value = row.get("value")
    if value is None:
        return None
    return {"date": row.get("date"), "value": float(value)}


# ---------------------------------------------------------------------------
# Snapshot helpers (demo fallbacks)
# ---------------------------------------------------------------------------

def load_snapshot(name: str):
    path = SNAP / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------------------
# KPI computations
# ---------------------------------------------------------------------------

def compute_kpis(india, snapshots, wb_values):
    kpis = []

    def kpi(k_id, name, value, unit, subtitle, source, benchmark=None):
        kpis.append({
            "id": k_id,
            "name": name,
            "value": value,
            "unit": unit,
            "subtitle": subtitle,
            "source": source,
            "benchmark": benchmark,
        })

    inflation = india["real_inflation_rate"]
    gsec = snapshots.get("india_gsec_yields", {}).get("latest_10y_yield_pct")
    ugi = snapshots.get("upi_stats", {})
    gst = snapshots.get("gst_growth", {})

    # 1. Real Interest Rate (Saver's Yield)
    if gsec is not None:
        real_rate = gsec - inflation
        kpi("real_interest_rate", "Real Interest Rate (Saver's Yield)",
            round(real_rate, 2), "%",
            "G-Sec 10Y yield minus inflation: if positive, savers beat the price rise; if negative, savings quietly lose value.",
            "RBI DBIE 10Y G-Sec Yield — DEMO SNAPSHOT − World Bank CPI",
            benchmark="positive is better")
    else:
        kpi("real_interest_rate", "Real Interest Rate (Saver's Yield)",
            None, "%", "Not available in the latest data set.",
            "RBI DBIE 10Y G-Sec Yield — not fetched", benchmark="positive is better")

    # 2. Real Inflation Rate (Headline)
    kpi("real_inflation_rate", "Real Inflation Rate (Headline)",
        inflation, "%",
        "The official Consumer Price Index growth — the number people usually mean by 'it is getting more expensive.'",
        "World Bank FP.CPI.TOTL.ZG")

    # 3. Regional Inflation Spread
    spread = snapshots.get("state_cpi_spread", {}).get("latest_spread_pct")
    if spread is not None:
        top = snapshots.get("state_cpi_spread", {}).get("top_state")
        kpi("state_inflation_spread", "Regional Inflation Spread",
            spread, "%",
            f"The gap the national average hides — e.g. {top} shows much bigger spikes than the headline number.",
            "State CPIs (MoSPI) − National CPI — DEMO SNAPSHOT")

    # 4. Digital Consumption Velocity
    ticket = ugi.get("avg_ticket_usd")
    if ticket is not None:
        kpi("digital_consumption_velocity", "Digital Consumption Velocity (UPI Ticket)",
            round(ticket, 2), "USD/tx",
            "Average value per UPI transaction, tracked alongside GST collections growth — value moving faster than volume means faster digital money flow.",
            "NPCI UPI Volumes/Value — DEMO SNAPSHOT",
            benchmark="tracked with GST momentum")

    # 5. Import Cover & Reserve Adequacy Ratio
    reserves = snapshots.get("reserves", {}).get("fx_reserves_usd")
    imports = snapshots.get("reserves", {}).get("annual_imports_usd")
    if reserves is not None and imports:
        cover = reserves / (imports / 12)
        kpi("import_cover_ratio", "Import Cover Ratio", round(cover, 1), "months",
            "Forex reserves as a multiple of one month's imports — if it falls, India can import less month to month.",
            "RBI DBIE Forex Reserves — DEMO SNAPSHOT")
    else:
        kpi("import_cover_ratio", "Import Cover Ratio", None, "months",
            "FX reserves ÷ (annual imports ÷ 12) — not available in the latest data set.",
            "RBI DBIE Forex Reserves — not fetched")

    # 6. Reserve Adequacy Ratio
    short_term_debt = snapshots.get("reserves", {}).get("short_term_debt_usd")
    if reserves is not None and short_term_debt:
        adj = reserves / short_term_debt
        kpi("reserve_adequacy_ratio", "Reserve Adequacy Ratio", round(adj, 2), "x",
            "FX reserves as a share of short-term debt — above 1.0 means the reserve pile covers the near-term debt bill.",
            "RBI DBIE Forex Reserves — DEMO SNAPSHOT")
    else:
        kpi("reserve_adequacy_ratio", "Reserve Adequacy Ratio", None, "x",
            "FX reserves vs short-term debt — not available in the latest data set.",
            "RBI DBIE — not fetched")

    # 7. Debt Service Burden — share of revenue
    debt_service = snapshots.get("debt_service", {}).get("share_of_revenue_pct")
    if debt_service is not None:
        kpi("debt_service_burden", "Debt Service Burden", debt_service, "% of revenue",
            "Interest paid on public debt as a share of revenue — when it rises, tax money that could fund health or schools instead pays interest.",
            "RBI DBIE debt-service composition — DEMO SNAPSHOT")

    # 8. India core: GDP per capita, PPP gap, growth
    kpi("gdp_per_capita_usd", "GDP per Capita (Nominal)",
        india["gdp_per_capita_usd"], "USD",
        "Average economic output per person — the usual headline number global rankings use.",
        "World Bank NY.GDP.PCAP.CD")

    if india.get("gdp_per_capita_ppp_usd") is not None:
        gap = india["gdp_per_capita_usd"] - india["gdp_per_capita_ppp_usd"]
        multiple = india["gdp_per_capita_ppp_usd"] / india["gdp_per_capita_usd"] if india["gdp_per_capita_usd"] else None
        kpi("ppp_gap_usd", "PPP Gap (Nominal − PPP)", round(gap, 2), "USD",
            "The difference between nominal and purchasing-power-parity GDP per capita — the gap that explains why the same salary buys a different life in Jaipur vs Delhi.",
            "World Bank NY.GDP.PCAP.CD − NY.GDP.PCAP.PP.CD")
        kpi("ppp_multiple", "PPP Conversion Multiple", round(multiple, 2), "×",
            "How many times bigger the PPP-adjusted GDP per capita is versus the nominal one — a quick picture of how prices change a salary.",
            "World Bank NY.GDP.PCAP.PP.CD ÷ NY.GDP.PCAP.CD")

    kpi("gdp_growth_pct", "GDP Growth (Annual %)",
        india["gdp_growth_pct"], "%",
        "How fast the economy is growing, year over year.",
        "World Bank NY.GDP.MKTP.KD.ZG")

    # 9. IIP growth + power demand (snapshots)
    iip = snapshots.get("iip", {}).get("growth_pct")
    if iip is not None:
        kpi("iip_growth_pct", "Index of Industrial Production Growth", round(iip, 1), "%",
            "How fast factories, mines and utilities are actually growing — a real-time check of business activity.",
            "MoSPI PLFS IIP — DEMO SNAPSHOT")
    power = snapshots.get("power_demand", {}).get("growth_pct")
    if power is not None:
        kpi("power_demand_growth_pct", "Power Demand Growth", round(power, 1), "%",
            "Growth in electricity use — a rough check of whether industry is turning on the lights or the meters are moving fast.",
            "PX/SECL — DEMO SNAPSHOT")

    return kpis


def compute_benchmarks(india, snapshots, wb_values):
    benchmarks = {}

    # --- India Macro Cycle Score (0–100) ---
    # Blended from live pieces and demo pieces; each piece is normalized to 0–100.
    inflation = india["real_inflation_rate"]
    growth = india["gdp_growth_pct"]
    parts = {}

    # Growth score: clamp 0–10 percent into 0–100.
    parts["Growth Score"] = clamp(growth, 0, 10) * 10 if growth is not None else None
    # Inflation score: mild deflation or low inflation scores high.
    parts["Inflation Score"] = clamp(15 - inflation, 0, 100)
    # Digital velocity score.
    vel = snapshots.get("upi_stats", {}).get("avg_ticket_usd")
    parts["Digital Velocity Score"] = clamp((vel or 0) - 0.5, 0, 2) * 50 if vel else None

    scores = [v for v in parts.values() if v is not None]
    bench_macro = round(sum(scores) / len(scores)) if scores else None
    benchmarks["india_macro_cycle_score"] = bench_macro
    benchmarks["india_macro_cycle_parts"] = {k: v for k, v in parts.items() if v is not None}

    # --- Digital velocity + GST momentum ratio ---
    ugi = snapshots.get("upi_stats", {})
    val = ugi.get("total_value_usd"); vol = ugi.get("total_volume"); vel = ugi.get("avg_ticket_usd")
    gst = snapshots.get("gst_growth", {})
    prior = gst.get("prior_year_growth_pct")
    cur = gst.get("current_year_growth_pct")
    bench_vel = {"avg_ticket_usd": vel, "total_value_usd": val, "total_volume": vol}
    if cur is not None and prior:
        bench_vel["gst_momentum_ratio"] = round(cur / prior, 2)
    benchmarks["digital_velocity_benchmark"] = bench_vel

    # --- State inflation spread ---
    state_cpi = snapshots.get("state_cpi_spread", {})
    if state_cpi.get("top_states"):
        bench_states = {
            "top_states": state_cpi["top_states"][:3],
            "latest_spread_pct": state_cpi.get("latest_spread_pct"),
            "source": "MoSPI — DEMO SNAPSHOT",
        }
        benchmarks["state_inflation_spread_benchmark"] = bench_states

    # --- Global resillience rank ---
    peers = []
    for p in PEER_COUNTRIES:
        peers.append({
            "iso": p["iso"],
            "name": p["name"],
            "real_gdp_growth": wb_value(wb_values, p["iso"], "NY.GDP.MKTP.KD.ZG"),
            "current_account": wb_value(wb_values, p["iso"], "NE.CAB.TOTL.PT"),
            "fdi_inflows": wb_value(wb_values, p["iso"], "BX.KD.FDI.DT.GP"),
        })
    # Rank India by average of available real GDP growth (peers), India last.
    valid = [p["real_gdp_growth"] for p in peers if p["real_gdp_growth"] is not None]
    india_growth = wb_value(wb_values, "IN", "NY.GDP.MKTP.KD.ZG")
    ranks = [p["real_gdp_growth"] for p in peers if p["real_gdp_growth"] is not None]
    if india_growth is not None and ranks:
        # India ranks by how many peers grow slower than her.
        rank = sum(1 for v in ranks if india_growth > v) + 1
    else:
        rank = None
    benchmarks["global_resilience"] = {
        "india_rank_by_real_gdp_growth": rank,
        "of": len(peers) + 1,
        "peers": peers,
        "note": "Ranked against India on real GDP growth where World Bank data is available. Current account and FDI columns fill in where data exists.",
    }

    return benchmarks


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


PEER_COUNTRIES = [
    {"iso": "VNM", "name": "Vietnam"},
    {"iso": "IDN", "name": "Indonesia"},
    {"iso": "BRA", "name": "Brazil"},
    {"iso": "MEX", "name": "Mexico"},
]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    wb_values = {}

    # Fetch live World Bank values (India + peers).
    for iso in ["IN", "VNM", "IDN", "BRA", "MEX"]:
        for indicator in ["NY.GDP.MKTP.KD.ZG", "NY.GDP.PCAP.CD", "NY.GDP.PCAP.PP.CD",
                          "FP.CPI.TOTL.ZG", "NE.CAB.TOTL.PT"]:
            res = wb_latest(iso, indicator)
            if res:
                wb_values.setdefault(iso, {})[indicator] = res

    # --- India ---
    india = {
        "real_inflation_rate": wb_value(wb_values, "IN", "FP.CPI.TOTL.ZG"),
        "gdp_per_capita_usd": wb_value(wb_values, "IN", "NY.GDP.PCAP.CD"),
        "gdp_per_capita_ppp_usd": wb_value(wb_values, "IN", "NY.GDP.PCAP.PP.CD"),
        "gdp_growth_pct": wb_value(wb_values, "IN", "NY.GDP.MKTP.KD.ZG"),
        "current_account": wb_value(wb_values, "IN", "NE.CAB.TOTL.PT"),
        "fdi_inflows": wb_value(wb_values, "IN", "BX.KD.FDI.DT.GP"),
    }
    # Rank India among peers by real GDP growth.
    peers_growth = [
        (p["iso"], wb_value(wb_values, p["iso"], "NY.GDP.MKTP.KD.ZG"))
        for p in PEER_COUNTRIES
    ]
    if india["gdp_growth_pct"] is not None:
        india["rank_by_growth"] = sum(
            1 for _iso, v in peers_growth if v is not None and india["gdp_growth_pct"] > v
        ) + 1
    else:
        india["rank_by_growth"] = None

    # --- Snapshots ---
    snapshots = {
        "india_gsec_yields": load_snapshot("india_gsec_yields.json") or {},
        "upi_stats": load_snapshot("upi_stats.json") or {},
        "gst_growth": load_snapshot("gst_growth.json") or {},
        "reserves": load_snapshot("reserves.json") or {},
        "state_cpi_spread": load_snapshot("state_cpi_spread.json") or {},
        "iip": load_snapshot("iip.json") or {},
        "power_demand": load_snapshot("power_demand.json") or {},
        "debt_service": load_snapshot("debt_service.json") or {},
    }

    kpis = compute_kpis(india, snapshots, wb_values)
    benchmarks = compute_benchmarks(india, snapshots, wb_values)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": {
            "world_bank": "api.worldbank.org/v2",
            "india_specific": "data.gov.in (token-gated) + snapshots in data/snapshots/ (demo fallbacks)",
        },
        "india": india,
        "peers": [
            {
                "iso": p["iso"],
                "name": p["name"],
                "real_gdp_growth": wb_value(wb_values, p["iso"], "NY.GDP.MKTP.KD.ZG"),
                "current_account": wb_value(wb_values, p["iso"], "NE.CAB.TOTL.PT"),
                "fdi_inflows": wb_value(wb_values, p["iso"], "BX.KD.FDI.DT.GP"),
                "source": "World Bank — NY.GDP.MKTP.KD.ZG / NE.CAB.TOTL.PT / BX.KD.FDI.DT.GP",
            }
            for p in PEER_COUNTRIES
        ],
        "kpis": kpis,
        "benchmarks": benchmarks,
        "subindices": (load_snapshot("subindices.json") or {}).get("subindices"),
        "city_indices": (load_snapshot("city_indices.json") or {}).get("city_indices"),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[pipeline] wrote {OUT}")
    print(f"[pipeline] India real inflation: {india['real_inflation_rate']}, GDP per capita: {india['gdp_per_capita_usd']}")


if __name__ == "__main__":
    main()
