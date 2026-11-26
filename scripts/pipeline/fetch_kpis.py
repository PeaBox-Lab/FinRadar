#!/usr/bin/env python3
"""
Radar — daily KPI pipeline (v3).

Pulls fresh data from keyless public APIs, computes derived KPIs from the
registry, builds plain-English insights, and writes ``data/latest_kpis.json``.

Sources
-------
* World Bank Open Data (api.worldbank.org/v2) — live primary source for macro,
  financial-sector, health, education, environment and trade series.
* Curated snapshots (data/snapshots/) — authentic published figures for
  India-specific series without keyless APIs (G-Sec yields, UPI, GST, reserves).
* data.gov.in — optional; a public sample key supports schema discovery. Set
  DATA_GOV_IN_TOKEN for registered resources.

No value is generated, simulated, randomised or copied from an indicative
table. If a source is unavailable, the KPI is emitted with a null value and
``source_type: "unavailable"``.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from analytics import build_insights_for_value
from datagovin_client import fetch_resource
from kpi_registry import KPI_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "data" / "snapshots"
OUT = ROOT / "data" / "latest_kpis.json"
SNAP_OUT = SNAP / "indicators.json"
WB_API = "https://api.worldbank.org/v2"

PEER_COUNTRIES = [
    {"iso": "VNM", "name": "Vietnam"},
    {"iso": "IDN", "name": "Indonesia"},
    {"iso": "BRA", "name": "Brazil"},
    {"iso": "MEX", "name": "Mexico"},
]

WB_INDICATORS = {
    "IN": [
        "NY.GDP.PCAP.CD", "NY.GDP.PCAP.PP.CD", "NY.GDP.MKTP.KD.ZG",
        "FP.CPI.TOTL.ZG", "BN.CAB.XOKA.GD.ZS", "BX.KLT.DINV.WD.GD.ZS",
        "GC.DOD.TOTL.GD.ZS", "NY.GDP.MKTP.CD",
        "NE.EXP.GNFS.ZS", "NE.IMP.GNFS.ZS",
        "EN.ATM.CO2E.PC", "SH.MED.BEDS.ZS", "SH.IMM.MEAS",
        "SH.UHC.OOPE.ZS", "SE.ADT.LIT.ZS", "SE.PRM.TCHR",
        "AG.LND.IRIG.AG.ZS", "FS.AST.PRVT.GD.ZS",
        "FB.BNK.CAPA.ZS", "SM.VAR.MANKD.ZS",
    ],
    **{
        peer["iso"]: ["NY.GDP.MKTP.KD.ZG", "BN.CAB.XOKA.GD.ZS", "BX.KLT.DINV.WD.GD.ZS"]
        for peer in PEER_COUNTRIES
    },
}

LIVE_KPI_IDS = {
    "real_inflation_rate", "gdp_growth_pct", "gdp_per_capita_usd",
    "gdp_per_capita_ppp_usd", "ppp_gap_usd", "current_account_pct_gdp",
    "fdi_inflows_pct_gdp", "debt_service_burden", "exports_pct_gdp",
    "imports_pct_gdp", "trade_balance_pct_gdp", "per_capita_co2_emissions",
    "hospital_bed_density", "immunization_coverage_pct", "oope_share_pct",
    "literacy_rate_pct", "pupil_teacher_ratio", "irrigation_coverage_pct",
    "bank_credit_deposit_ratio", "gnpa_ratio_pct",
}


def wb_latest(country: str, indicator: str) -> dict | None:
    """Fetch the most recent non-null World Bank observation for an indicator."""
    url = (
        f"{WB_API}/country/{country}/indicator/{urllib.parse.quote(indicator)}"
        "?format=json&per_page=5"
    )
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Radar/3.0 pipeline"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read())
            if len(data) < 2 or not data[1]:
                return None
            rows = sorted(data[1], key=lambda row: str(row.get("date", "")), reverse=True)
            for row in rows:
                if row.get("value") is not None:
                    return {"date": row.get("date"), "value": float(row["value"])}
            return None
        except Exception as exc:
            last_error = exc
    print(f"[pipeline] World Bank fetch failed {country}/{indicator}: {last_error}")
    return None


def load_snapshot(name: str) -> dict:
    path = SNAP / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def dg_resource(kpi_def: dict) -> dict | None:
    """Schema-discovery helper for genuine data.gov.in UUID resources."""
    rid = kpi_def.get("source_resource_id", "")
    prefixes = (
        "wb:", "rbi:", "npci:", "gst:", "agri:", "mspi:", "mospi:", "health:",
        "edu:", "morth:", "mnre:", "mgnrega:", "food:", "census:", "msme:",
        "shipping:", "mo_env:", "moef:", "nhb:", "indian_rails:",
    )
    if not rid or rid.startswith(prefixes):
        return None
    if not rid.replace("-", "").isalnum():
        return None
    return fetch_resource(rid, limit=5)


def compute_values(wb: dict, snapshots: dict) -> tuple[dict, set[str]]:
    """Return {kpi_id: value} and the set of KPI IDs backed by live API data."""
    india = wb.get("IN", {})
    v: dict = {}
    live: set[str] = set()

    def live_value(kpi_id: str, code: str):
        value = india.get(code)
        if value is not None:
            v[kpi_id] = value
            live.add(kpi_id)
        return value

    # National accounts and prices.
    inflation = live_value("real_inflation_rate", "FP.CPI.TOTL.ZG")
    growth = live_value("gdp_growth_pct", "NY.GDP.MKTP.KD.ZG")
    gdp_pc = live_value("gdp_per_capita_usd", "NY.GDP.PCAP.CD")
    gdp_ppp = live_value("gdp_per_capita_ppp_usd", "NY.GDP.PCAP.PP.CD")
    if gdp_pc is not None and gdp_ppp is not None:
        v["ppp_gap_usd"] = gdp_pc - gdp_ppp  # published values, derived difference
        live.add("ppp_gap_usd")
    live_value("current_account_pct_gdp", "BN.CAB.XOKA.GD.ZS")
    live_value("fdi_inflows_pct_gdp", "BX.KLT.DINV.WD.GD.ZS")

    # Trade balance as a share of GDP, from two official World Bank series.
    exports = live_value("exports_pct_gdp", "NE.EXP.GNFS.ZS")
    imports = live_value("imports_pct_gdp", "NE.IMP.GNFS.ZS")
    if exports is not None and imports is not None:
        v["trade_balance_pct_gdp"] = exports - imports
        live.add("trade_balance_pct_gdp")

    # Environment, health, education and agriculture.
    for kpi_id, code in {
        "per_capita_co2_emissions": "EN.ATM.CO2E.PC",
        "hospital_bed_density": "SH.MED.BEDS.ZS",
        "immunization_coverage_pct": "SH.IMM.MEAS",
        "oope_share_pct": "SH.UHC.OOPE.ZS",
        "literacy_rate_pct": "SE.ADT.LIT.ZS",
        "pupil_teacher_ratio": "SE.PRM.TCHR",
        "irrigation_coverage_pct": "AG.LND.IRIG.AG.ZS",
    }.items():
        live_value(kpi_id, code)

    # Financial sector ratios with direct World Bank equivalents.
    private_credit = india.get("FS.AST.PRVT.GD.ZS")
    deposits = india.get("SM.VAR.MANKD.ZS")
    if private_credit is not None and deposits is not None and deposits != 0:
        v["bank_credit_deposit_ratio"] = private_credit / deposits * 100
        live.add("bank_credit_deposit_ratio")
    capital = india.get("FB.BNK.CAPA.ZS")
    if capital is not None:
        # Bank capital to assets is the published official ratio; the registry
        # labels this KPI as a gross NPA ratio, so do not substitute it.
        pass

    # Curated, non-live official snapshots. These are authentic published
    # figures, clearly disclosed in the UI as static snapshots.
    gsec = snapshots.get("india_gsec_yields", {}).get("latest_10y_yield_pct")
    if gsec is not None and inflation is not None:
        v["real_interest_rate"] = gsec - inflation
    reserves = snapshots.get("reserves", {})
    fx = reserves.get("fx_reserves_usd")
    annual_imports = reserves.get("annual_imports_usd")
    short_term_debt = reserves.get("short_term_debt_usd")
    if fx is not None and annual_imports:
        v["import_cover_ratio"] = fx / (annual_imports / 12)
    if fx is not None and short_term_debt:
        v["reserve_adequacy_ratio"] = fx / short_term_debt
    for kpi_id, snapshot_name, field in (
        ("debt_service_burden", "debt_service", "share_of_revenue_pct"),
        ("iip_growth_pct", "iip", "growth_pct"),
        ("power_demand_growth_pct", "power_demand", "growth_pct"),
        ("gst_growth_pct", "gst_growth", "current_year_growth_pct"),
        ("digital_consumption_velocity", "upi_stats", "avg_ticket_usd"),
    ):
        value = snapshots.get(snapshot_name, {}).get(field)
        if value is not None:
            v[kpi_id] = value

    # The registry's fiscal-deficit field maps to a World Bank government-debt
    # series, which is not the same statistic. It is intentionally left null
    # rather than publishing a mislabelled value.
    return v, live


def compute_benchmarks(wb: dict, snapshots: dict, values: dict) -> dict:
    growth = values.get("gdp_growth_pct")
    inflation = values.get("real_inflation_rate")
    velocity = values.get("digital_consumption_velocity")
    parts = {}
    if growth is not None:
        parts["Growth Score"] = max(0, min(10, growth)) * 10
    if inflation is not None:
        parts["Inflation Score"] = max(0, min(100, 15 - inflation))
    if velocity is not None:
        parts["Digital Velocity Score"] = max(0, min(100, min(velocity, 25) * 4))
    part_values = list(parts.values())
    macro_score = round(sum(part_values) / len(part_values)) if part_values else None

    upi = snapshots.get("upi_stats", {})
    gst = snapshots.get("gst_growth", {})
    current_gst = gst.get("current_year_growth_pct")
    prior_gst = gst.get("prior_year_growth_pct")
    gst_ratio = round(current_gst / prior_gst, 2) if current_gst and prior_gst else None

    state_cpi = snapshots.get("state_cpi_spread", {})
    state_benchmark = None
    if state_cpi.get("top_states"):
        state_benchmark = {
            "top_states": state_cpi["top_states"][:3],
            "latest_spread_pct": state_cpi.get("latest_spread_pct"),
            "source": "MoSPI state CPI publication (curated snapshot)",
        }

    peers = []
    for country in PEER_COUNTRIES:
        row = wb.get(country["iso"], {})
        peers.append({
            "iso": country["iso"],
            "name": country["name"],
            "real_gdp_growth": row.get("NY.GDP.MKTP.KD.ZG"),
            "current_account": row.get("BN.CAB.XOKA.GD.ZS"),
            "fdi_inflows": row.get("BX.KLT.DINV.WD.GD.ZS"),
            "source": "World Bank (live)",
        })
    peer_growth = [p["real_gdp_growth"] for p in peers if p["real_gdp_growth"] is not None]
    rank = sum(1 for value in peer_growth if growth is not None and growth > value) + 1 if growth is not None else None

    return {
        "india_macro_cycle_score": macro_score,
        "india_macro_cycle_parts": parts,
        "digital_velocity_benchmark": {
            "avg_ticket_usd": upi.get("avg_ticket_usd"),
            "total_value_usd": upi.get("total_value_usd"),
            "total_volume": upi.get("total_volume"),
            "gst_momentum_ratio": gst_ratio,
        },
        "state_inflation_spread_benchmark": state_benchmark,
        "global_resilience": {
            "india_rank_by_real_gdp_growth": rank,
            "of": len(peers) + 1,
            "peers": peers,
            "note": "Ranked against India on real GDP growth where World Bank data is available.",
        },
    }


def main():
    wb: dict = {}
    raw_dates: dict = {}
    for iso, indicators in WB_INDICATORS.items():
        wb[iso] = {}
        for indicator in indicators:
            result = wb_latest(iso, indicator)
            if result:
                wb[iso][indicator] = result["value"]
                raw_dates.setdefault(iso, {})[indicator] = result["date"]

    snapshots = {
        "india_gsec_yields": load_snapshot("india_gsec_yields.json"),
        "upi_stats": load_snapshot("upi_stats.json"),
        "gst_growth": load_snapshot("gst_growth.json"),
        "reserves": load_snapshot("reserves.json"),
        "state_cpi_spread": load_snapshot("state_cpi_spread.json"),
        "iip": load_snapshot("iip.json"),
        "power_demand": load_snapshot("power_demand.json"),
        "debt_service": load_snapshot("debt_service.json"),
    }

    values, live_ids = compute_values(wb, snapshots)
    insights = []
    for definition in KPI_REGISTRY:
        kpi_id = definition["id"]
        insight = build_insights_for_value(kpi_id, values.get(kpi_id))
        if insight is None:
            continue
        if values.get(kpi_id) is None:
            source_type = "unavailable"
        elif kpi_id in live_ids:
            source_type = "live_api"
        else:
            source_type = "curated_snapshot"
        insight["source_type"] = source_type
        insight["source_live"] = source_type == "live_api"
        insights.append(insight)

    india = {
        "real_inflation_rate": values.get("real_inflation_rate"),
        "gdp_per_capita_usd": values.get("gdp_per_capita_usd"),
        "gdp_per_capita_ppp_usd": values.get("gdp_per_capita_ppp_usd"),
        "gdp_growth_pct": values.get("gdp_growth_pct"),
        "current_account": values.get("current_account_pct_gdp"),
        "fdi_inflows": values.get("fdi_inflows_pct_gdp"),
        "rank_by_growth": None,
    }
    if india["gdp_growth_pct"] is not None:
        peers_growth = [
            wb.get(country["iso"], {}).get("NY.GDP.MKTP.KD.ZG")
            for country in PEER_COUNTRIES
        ]
        india["rank_by_growth"] = sum(
            1 for value in peers_growth if value is not None and india["gdp_growth_pct"] > value
        ) + 1

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    out = {
        "generated_at": generated_at,
        "last_updated_month": generated_at[:7],
        "sources": {
            "world_bank": "api.worldbank.org/v2 (live)",
            "data_gov_in": "api.data.gov.in (public sample key; DATA_GOV_IN_TOKEN for registered feeds)",
            "snapshots": "data/snapshots/ (transcribed published figures, non-live; no demo fallbacks)",
        },
        "observation_dates": raw_dates,
        "india": india,
        "peers": [
            {
                "iso": country["iso"],
                "name": country["name"],
                "real_gdp_growth": wb.get(country["iso"], {}).get("NY.GDP.MKTP.KD.ZG"),
                "current_account": wb.get(country["iso"], {}).get("BN.CAB.XOKA.GD.ZS"),
                "fdi_inflows": wb.get(country["iso"], {}).get("BX.KLT.DINV.WD.GD.ZS"),
                "source": "World Bank — NY.GDP.MKTP.KD.ZG / BN.CAB.XOKA.GD.ZS / BX.KLT.DINV.WD.GD.ZS",
            }
            for country in PEER_COUNTRIES
        ],
        "kpis": insights,
        "benchmarks": compute_benchmarks(wb, snapshots, values),
        "subindices": load_snapshot("subindices.json").get("subindices"),
        "subindex_weights": load_snapshot("subindices.json").get("subindex_weights"),
        "subindex_metadata": {
            "source": load_snapshot("subindices.json").get("source"),
            "source_url": load_snapshot("subindices.json").get("source_url"),
            "month": load_snapshot("subindices.json").get("month"),
            "base": load_snapshot("subindices.json").get("base"),
        },
        "city_indices": load_snapshot("city_indices.json").get("city_indices"),
        "city_indices_metadata": {
            "source": load_snapshot("city_indices.json").get("source"),
            "source_url": load_snapshot("city_indices.json").get("source_url"),
            "month": load_snapshot("city_indices.json").get("month"),
            "base": load_snapshot("city_indices.json").get("base"),
        },
    }
    payload = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    OUT.write_text(payload, encoding="utf-8")
    SNAP_OUT.write_text(payload, encoding="utf-8")
    print(f"[pipeline] wrote {OUT} and fallback {SNAP_OUT}")
    print(
        f"[pipeline] KPIs: {len(insights)} | live: {sum(1 for i in insights if i['source_live'])} "
        f"| snapshot: {sum(1 for i in insights if i['source_type'] == 'curated_snapshot')} "
        f"| unavailable: {sum(1 for i in insights if i['source_type'] == 'unavailable')}"
    )


if __name__ == "__main__":
    main()
