#!/usr/bin/env python3
"""
FinRadar — daily KPI pipeline (v2).

Pulls fresh data from public sources, computes derived KPIs using the
KPI registry (kpi_registry.py), builds plain-English insights (analytics.py),
and writes data/latest_kpis.json for the static site to render.

Data sources
------------
* World Bank Open Data (api.worldbank.org/v2) — verified live.
* data.gov.in (api.data.gov.in) — optional; the sample key works for
  schema discovery and demos. With your own token (env DATA_GOV_IN_TOKEN),
  the pipeline can pull real numbers for registered resource IDs.
* Snapshots (data/snapshots/) — labeled fallbacks for India-specific
  figures (G-Sec yields, UPI, state CPI, reserves, etc.).

The pipeline never fails hard: if one source is unreachable, it falls back
to the snapshot and marks the KPI "demo" in the output.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from kpi_registry import KPI_REGISTRY, interpret
from datagovin_client import fetch_resource
from analytics import build_insights_for_value

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "data" / "snapshots"
OUT = ROOT / "data" / "latest_kpis.json"
WB_API = "http://api.worldbank.org/v2"

PEER_COUNTRIES = [
    {"iso": "VNM", "name": "Vietnam"},
    {"iso": "IDN", "name": "Indonesia"},
    {"iso": "BRA", "name": "Brazil"},
    {"iso": "MEX", "name": "Mexico"},
]

WB_INDICATORS = {
    "IN": ["NY.GDP.PCAP.CD", "NY.GDP.PCAP.PP.CD", "NY.GDP.MKTP.KD.ZG",
           "FP.CPI.TOTL.ZG", "NE.CAB.TOTL.PT", "BX.KD.FDI.DT.GP", "GC.DOD.TOTL.GD.ZG"],
    "VNM": ["NY.GDP.MKTP.KD.ZG", "NE.CAB.TOTL.PT", "BX.KD.FDI.DT.GP"],
    "IDN": ["NY.GDP.MKTP.KD.ZG", "NE.CAB.TOTL.PT", "BX.KD.FDI.DT.GP"],
    "BRA": ["NY.GDP.MKTP.KD.ZG", "NE.CAB.TOTL.PT", "BX.KD.FDI.DT.GP"],
    "MEX": ["NY.GDP.MKTP.KD.ZG", "NE.CAB.TOTL.PT", "BX.KD.FDI.DT.GP"],
}


def wb_latest(country: str, indicator: str) -> dict | None:
    url = f"{WB_API}/country/{country}/indicator/{urllib.parse.quote(indicator)}?format=json&per_page=2"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "FinRadar/2.0 pipeline"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if len(data) < 2 or not data[1]:
            return None
        row = sorted(data[1], key=lambda r: str(r.get("date", "")), reverse=True)[0]
        val = row.get("value")
        if val is None:
            return None
        return {"date": row.get("date"), "value": float(val)}
    except Exception as exc:
        print(f"[pipeline] WB fetch failed {country}/{indicator}: {exc}")
        return None


def load_snapshot(name: str) -> dict | None:
    path = SNAP / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def dg_resource(kpi_def: dict) -> dict | None:
    """
    Try to fetch a small page from the resource referenced by a KPI.
    Returns the raw data.gov.in response or None on failure.

    Only used for schema discovery / sample data; production numbers come
    from the snapshots (which you can replace with live data.gov.in feeds).
    """
    rid = kpi_def.get("source_resource_id", "")
    if not rid or rid.startswith(("wb:", "rbi:", "npci:", "gst:", "agri:", "mspi:", "mospi:", "health:", "edu:", "morth:", "mnre:", "mgnrega:", "food:", "census:")):
        return None
    # Pure UUIDs only.
    if not rid.replace("-", "").isalnum():
        return None
    return fetch_resource(rid, limit=5)


# ---------------------------------------------------------------------------
# Compute all values → insights
# ---------------------------------------------------------------------------

def compute_values(snapshots: dict, india: dict) -> dict:
    """Return {kpi_id: value} using snapshots, India data and demo fallbacks."""
    v: dict = {}

    # Economy
    v["real_inflation_rate"] = india.get("real_inflation_rate")
    v["gdp_growth_pct"] = india.get("gdp_growth_pct")
    v["gdp_per_capita_usd"] = india.get("gdp_per_capita_usd")
    v["gdp_per_capita_ppp_usd"] = india.get("gdp_per_capita_ppp_usd")
    if v["gdp_per_capita_usd"] is not None and v["gdp_per_capita_ppp_usd"] is not None:
        v["ppp_gap_usd"] = v["gdp_per_capita_usd"] - v["gdp_per_capita_ppp_usd"]
    v["current_account_pct_gdp"] = india.get("current_account")
    v["fdi_inflows_pct_gdp"] = india.get("fdi_inflows")

    # Snapshots
    gsec = snapshots.get("india_gsec_yields", {}).get("latest_10y_yield_pct")
    if gsec is not None and v["real_inflation_rate"] is not None:
        v["real_interest_rate"] = gsec - v["real_inflation_rate"]

    reserves = snapshots.get("reserves", {})
    fx = reserves.get("fx_reserves_usd")
    imports = reserves.get("annual_imports_usd")
    std = reserves.get("short_term_debt_usd")
    if fx is not None and imports:
        v["import_cover_ratio"] = fx / (imports / 12)
    if fx is not None and std:
        v["reserve_adequacy_ratio"] = fx / std

    v["debt_service_burden"] = snapshots.get("debt_service", {}).get("share_of_revenue_pct")
    v["iip_growth_pct"] = snapshots.get("iip", {}).get("growth_pct")
    v["power_demand_growth_pct"] = snapshots.get("power_demand", {}).get("growth_pct")
    v["gst_growth_pct"] = snapshots.get("gst_growth", {}).get("current_year_growth_pct")
    ugi = snapshots.get("upi_stats", {})
    v["digital_consumption_velocity"] = ugi.get("avg_ticket_usd")

    # A few indicative demo values for sectors with no live source yet.
    demo = {
        "bank_credit_deposit_ratio": 82.4,
        "priority_sector_lending_pct": 42.1,
        "gnpa_ratio_pct": 2.8,
        "msme_credit_penetration_pct": 12.6,
        "hospital_bed_density": 1.3,
        "immunization_coverage_pct": 76.0,
        "oope_share_pct": 47.1,
        "pupil_teacher_ratio": 26.0,
        "literacy_rate_pct": 73.0,
        "road_density": 192.0,
        "vehicle_density": 22.0,
        "mgnrega_person_days": 235.0,
        "pds_coverage_pct": 88.0,
        "renewable_capacity_share_pct": 42.5,
        "per_capita_co2_emissions": 2.0,
        "foodgrain_growth_pct": 1.4,
        "fertilizer_intensity": 145.0,
        "irrigation_coverage_pct": 55.0,
        "crop_insurance_penetration_pct": 37.0,
        "fiscal_deficit_pct_gdp": 5.1,
    }
    v.update(demo)

    return v


def compute_benchmarks(india: dict, snapshots: dict, values: dict) -> dict:
    benchmarks = {}

    # Macro cycle score (0-100): blend growth, inflation, digital velocity.
    growth = values.get("gdp_growth_pct")
    infl = values.get("real_inflation_rate")
    vel = values.get("digital_consumption_velocity")
    parts = {}
    if growth is not None:
        parts["Growth Score"] = max(0, min(10, growth)) * 10
    if infl is not None:
        parts["Inflation Score"] = max(0, min(100, 15 - infl))
    if vel is not None:
        parts["Digital Velocity Score"] = max(0, min(100, (vel - 0.5) * 50))
    parts_vals = [v for v in parts.values() if v is not None]
    benchmarks["india_macro_cycle_score"] = round(sum(parts_vals) / len(parts_vals)) if parts_vals else None
    benchmarks["india_macro_cycle_parts"] = parts

    # Digital velocity benchmark.
    ugi = snapshots.get("upi_stats", {})
    benchmarks["digital_velocity_benchmark"] = {
        "avg_ticket_usd": ugi.get("avg_ticket_usd"),
        "total_value_usd": ugi.get("total_value_usd"),
        "total_volume": ugi.get("total_volume"),
        "gst_momentum_ratio": (
            round(
                snapshots.get("gst_growth", {}).get("current_year_growth_pct", 0)
                / max(snapshots.get("gst_growth", {}).get("prior_year_growth_pct", 1), 0.01),
                2,
            )
            if snapshots.get("gst_growth", {}).get("current_year_growth_pct")
            else None
        ),
    }

    # State inflation spread benchmark.
    state_cpi = snapshots.get("state_cpi_spread", {})
    if state_cpi.get("top_states"):
        benchmarks["state_inflation_spread_benchmark"] = {
            "top_states": state_cpi["top_states"][:3],
            "latest_spread_pct": state_cpi.get("latest_spread_pct"),
            "source": "MoSPI — DEMO SNAPSHOT",
        }

    # Global resilience rank by real GDP growth.
    peers = []
    for p in PEER_COUNTRIES:
        row = snapshots.get("_wb_peers", {}).get(p["iso"], {})
        peers.append({
            "iso": p["iso"],
            "name": p["name"],
            "real_gdp_growth": row.get("NY.GDP.MKTP.KD.ZG"),
            "current_account": row.get("NE.CAB.TOTL.PT"),
            "fdi_inflows": row.get("BX.KD.FDI.DT.GP"),
        })
    india_growth = values.get("gdp_growth_pct")
    ranks = [p["real_gdp_growth"] for p in peers if p["real_gdp_growth"] is not None]
    rank = sum(1 for v in ranks if india_growth > v) + 1 if india_growth is not None else None
    benchmarks["global_resilience"] = {
        "india_rank_by_real_gdp_growth": rank,
        "of": len(peers) + 1,
        "peers": peers,
        "note": "Ranked against India on real GDP growth where World Bank data is available. Current account and FDI columns fill in where data exists.",
    }

    return benchmarks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 1. Fetch live World Bank data.
    wb_values: dict = {}
    for iso, indicators in WB_INDICATORS.items():
        wb_values[iso] = {}
        for indicator in indicators:
            res = wb_latest(iso, indicator)
            if res:
                wb_values[iso][indicator] = res["value"]
                wb_values.setdefault("_raw", {}).setdefault(iso, {})[indicator] = res

    india = {
        "real_inflation_rate": wb_values.get("IN", {}).get("FP.CPI.TOTL.ZG"),
        "gdp_per_capita_usd": wb_values.get("IN", {}).get("NY.GDP.PCAP.CD"),
        "gdp_per_capita_ppp_usd": wb_values.get("IN", {}).get("NY.GDP.PCAP.PP.CD"),
        "gdp_growth_pct": wb_values.get("IN", {}).get("NY.GDP.MKTP.KD.ZG"),
        "current_account": wb_values.get("IN", {}).get("NE.CAB.TOTL.PT"),
        "fdi_inflows": wb_values.get("IN", {}).get("BX.KD.FDI.DT.GP"),
    }
    # Rank India among peers by real GDP growth.
    peers_growth = [wb_values.get(p["iso"], {}).get("NY.GDP.MKTP.KD.ZG") for p in PEER_COUNTRIES]
    if india["gdp_growth_pct"] is not None:
        india["rank_by_growth"] = sum(1 for v in peers_growth if v is not None and india["gdp_growth_pct"] > v) + 1
    else:
        india["rank_by_growth"] = None

    # 2. Load snapshots.
    snapshots = {
        "india_gsec_yields": load_snapshot("india_gsec_yields.json") or {},
        "upi_stats": load_snapshot("upi_stats.json") or {},
        "gst_growth": load_snapshot("gst_growth.json") or {},
        "reserves": load_snapshot("reserves.json") or {},
        "state_cpi_spread": load_snapshot("state_cpi_spread.json") or {},
        "iip": load_snapshot("iip.json") or {},
        "power_demand": load_snapshot("power_demand.json") or {},
        "debt_service": load_snapshot("debt_service.json") or {},
        "_wb_peers": {p["iso"]: wb_values.get(p["iso"], {}) for p in PEER_COUNTRIES},
    }

    # 3. Compute values and insights.
    values = compute_values(snapshots, india)
    insights = []
    for kpi_def in KPI_REGISTRY:
        val = values.get(kpi_def["id"])
        # Mark data as demo when the source is a snapshot.
        is_demo = not (
            kpi_def.get("source_resource_id", "").startswith("wb:")
            or val is not None
            and kpi_def["id"] in {
                "real_inflation_rate", "gdp_growth_pct", "gdp_per_capita_usd",
                "gdp_per_capita_ppp_usd", "ppp_gap_usd",
            }
        )
        insight = build_insights_for_value(kpi_def["id"], val)
        if insight is not None:
            insight["source_live"] = not is_demo
            insights.append(insight)

    # 4. Benchmarks.
    benchmarks = compute_benchmarks(india, snapshots, values)

    # 5. Write output.
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": {
            "world_bank": "api.worldbank.org/v2",
            "data_gov_in": "api.data.gov.in (sample key by default; DATA_GOV_IN_TOKEN to enable live feeds)",
            "snapshots": "data/snapshots/ (demo fallbacks for India-specific figures)",
        },
        "india": india,
        "peers": [
            {
                "iso": p["iso"],
                "name": p["name"],
                "real_gdp_growth": wb_values.get(p["iso"], {}).get("NY.GDP.MKTP.KD.ZG"),
                "current_account": wb_values.get(p["iso"], {}).get("NE.CAB.TOTL.PT"),
                "fdi_inflows": wb_values.get(p["iso"], {}).get("BX.KD.FDI.DT.GP"),
                "source": "World Bank — NY.GDP.MKTP.KD.ZG / NE.CAB.TOTL.PT / BX.KD.FDI.DT.GP",
            }
            for p in PEER_COUNTRIES
        ],
        "kpis": insights,
        "benchmarks": benchmarks,
        "subindices": (load_snapshot("subindices.json") or {}).get("subindices"),
        "city_indices": (load_snapshot("city_indices.json") or {}).get("city_indices"),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[pipeline] wrote {OUT}")
    print(f"[pipeline] KPIs computed: {len(insights)}; India inflation={india['real_inflation_rate']}; GDP/cap={india['gdp_per_capita_usd']}")


if __name__ == "__main__":
    main()