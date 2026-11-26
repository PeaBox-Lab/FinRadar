"""FinRadar — Enrichment batch
================================

Publishes an expanded, sourced data layer on top of the core KPI pipeline:

* curated World Bank series (GDP, census/demographics, finance, markets,
  environment, digital) fetched live without an API key;
* official Census of India 2011 benchmark figures (decadal, not daily);
* curated data.gov.in resources fetched with DATA_GOV_IN_TOKEN when set and
  the portal's sample key otherwise, with a last-known-good cache;
* APISETU_TOKEN is read only to report APIsetu credential readiness — the
  curated batch does not call gated APIsetu endpoints;
* innovative derived KPIs with explicit formulas and user guidance;
* Pearson relationships between Indian metrics and macro/global factors;
* curated global feeds (ECB FX, BIS rates/debt/credit, IMF/WEO, WTO trade,
  World Bank PPP/pay/insurance/banking/debt/equity, Pink Sheet commodities)
  and clearly labelled delayed market snapshots;
* a discovery catalog of official sources and their access status.

Output: data/extra_metrics.json (consumed by page_generator.py).
Nothing in this module mutates data/latest_kpis.json or the core pipeline.

Usage:
    python scripts/pipeline/enrichment.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SNAP_DIR = DATA_DIR / "snapshots"
OUTPUT = DATA_DIR / "extra_metrics.json"
CACHE_FILE = SNAP_DIR / "enrichment_cache.json"

WB_BASE = "https://api.worldbank.org/v2"
START_YEAR = 2000
USER_AGENT = "FinRadar enrichment batch/1.0"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datagovin_client import fetch_resource  # noqa: E402
from global_feeds import build_global_data  # noqa: E402


# ---------------------------------------------------------------------------
# Curated series definitions
# ---------------------------------------------------------------------------

def series(code, label, sector, unit, definition, guide, *, country="IND",
           category="macro", frequency="Annual", source="World Bank Open Data"):
    return {
        "code": code,
        "label": label,
        "country": country,
        "sector": sector,
        "category": category,
        "unit": unit,
        "frequency": frequency,
        "definition": definition,
        "guide": guide,
        "source": source,
        "source_url": f"https://data.worldbank.org/indicator/{code}",
    }


SERIES_DEFS = [
    series("NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)", "economy", "%",
           "Annual percentage change of real Gross Domestic Product at constant prices.",
           "Use it as the headline speed of the economy. Compare with inflation to see whether growth is real or price-driven."),
    series("NY.GDP.PCAP.CD", "GDP per capita (current US$)", "economy", "USD",
           "GDP divided by mid-year population, converted to current US dollars.",
           "A rough measure of average material output per person. It is not a measure of household income or welfare."),
    series("NY.GDP.PCAP.KD.ZG", "GDP per capita growth (annual %)", "economy", "%",
           "Annual growth of real GDP divided by population growth.",
           "Prefer this over headline GDP growth when assessing whether average living standards are improving."),
    series("FP.CPI.TOTL.ZG", "Consumer price inflation", "economy", "%",
           "Annual percentage change in the Consumer Price Index.",
           "The rate at which a representative basket of consumer goods becomes more expensive. Compare with your own spending mix using the inflation tool."),
    series("SP.POP.TOTL", "Total population", "central", "people",
           "Mid-year estimate of the resident population.",
           "Denominator for per-capita metrics. Census 2011 below is the official decadal benchmark; this series is an annual estimate."),
    series("SP.POP.GROW", "Population growth (annual %)", "central", "%",
           "Annual percentage change in population.",
           "Subtract this from GDP growth to approximate per-capita growth."),
    series("SP.URB.TOTL.IN.ZS", "Urban population (% of total)", "housing", "%",
           "Share of the population living in urban areas as defined by national statistical offices.",
           "A rising share usually signals structural change; pair it with productivity and housing data before drawing conclusions."),
    series("SP.POP.1564.TO.ZS", "Working-age population (15–64, %)", "welfare", "%",
           "Share of the population aged 15 to 64 years.",
           "A demographic dividend exists only when this large cohort is employed and productive."),
    series("SP.DYN.LE00.IN", "Life expectancy at birth", "health", "years",
           "Number of years a newborn would live if prevailing mortality patterns remained constant.",
           "A broad outcome measure for health, sanitation and nutrition. Moves slowly, so read multi-year trends."),
    series("SE.ADT.LITR.ZS", "Literacy rate (ages 15+)", "education", "%",
           "Percentage of people aged 15 and above who can read and write.",
           "Compare with the Census 2011 literacy benchmark below to gauge long-run educational progress."),
    series("NY.GDS.TOTL.ZS", "Gross domestic savings (% of GDP)", "financials", "% GDP",
           " GDP minus final consumption expenditure, as a share of GDP.",
           "Higher savings give an economy more internally funded investment capacity."),
    series("FS.AST.PRVT.GD.ZS", "Domestic credit to private sector (% of GDP)", "financials", "% GDP",
           "Financial resources provided to the private sector by banks and other financial corporations.",
           "A proxy for financial depth. Very rapid growth can also signal credit stress, so read it alongside savings."),
    series("FR.INR.RINR", "Real interest rate", "financials", "%",
           "Lending interest rate adjusted for inflation.",
           "Positive rates reward savers; deeply negative rates erode deposits. It is a market-wide rate, not your FD rate."),
    series("BX.KLT.DINV.WD.GD.ZS", "FDI inflows (% of GDP)", "economy", "% GDP",
           "Net inflows of foreign direct investment as a share of GDP.",
           "Reflects long-term foreign confidence, but a single large deal can distort one year."),
    series("BN.CAB.XOKA.GD.ZS", "Current account balance (% of GDP)", "economy", "% GDP",
           "Current account balance (goods, services, income and transfers) as a share of GDP.",
           "Persistent deficits need stable external financing; persistent surpluses may signal weak domestic demand."),
    series("FI.RES.TOTL.MO", "Foreign exchange reserves (months of imports)", "financials", "months",
           "International reserves expressed as the number of months of goods and services imports they could cover.",
           "A standard resilience buffer. Compare with short-term external debt before judging adequacy."),
    series("EN.ATM.PM25.MC.M3", "Fine particulate matter (PM2.5)", "environment", "µg/m³",
           "Annual mean concentration of fine particulate matter with a diameter of 2.5 micrometres or less.",
           "Lower is better. Compare the trend with GDP growth to see whether expansion is improving or worsening air quality."),
    series("EG.ELC.ACCS.ZS", "Access to electricity (% of population)", "energy", "%",
           "Share of the population with access to an electricity supply.",
           "Near-universal access shifts the policy focus from connection to reliability and affordability."),
    series("IT.NET.USER.ZS", "Internet users (% of population)", "commerce", "%",
           "Share of the population using the internet (the past 12 months).",
           "A foundation for digital commerce; combine with payment data for digital velocity."),
    series("PA.NUS.FCRF", "Official exchange rate (INR per US$)", "financials", "INR/USD",
           "Official exchange rate used to convert national currency to US dollars.",
           "Rapid depreciation raises imported inflation and the rupee cost of foreign debt."),
    series("SL.UEM.TOTL.ZS", "Unemployment (% of labour force)", "welfare", "%",
           "Share of the labour force without work but available and seeking employment.",
           "India's estimate is modelled by ILO; use it for direction rather than exact levels."),
    series("SI.POV.DDAY", "Extreme poverty (% below $2.15/day)", "welfare", "%",
           "Share of the population living below the World Bank's extreme poverty line (2017 PPP).",
           "Useful for long-run comparison, not for measuring relative deprivation within India."),
    series("NY.GDP.MKTP.KD.ZG", "World GDP growth (annual %)", "economy", "%",
           "Annual growth of global real GDP.", country="WLD", category="global",
           guide="An external demand benchmark: if India grows faster than the world, it is gaining share."),
    series("FP.CPI.TOTL.ZG", "World inflation (annual %)", "economy", "%",
           "Annual change in the global consumer price aggregate.", country="WLD", category="global",
           guide="Helps separate domestic inflation from imported, global price pressure."),
]

PEERS = [
    ("VNM", "Vietnam"),
    ("IDN", "Indonesia"),
    ("BRA", "Brazil"),
    ("MEX", "Mexico"),
]

for _iso, _name in PEERS:
    SERIES_DEFS.append(series(
        "NY.GDP.MKTP.KD.ZG", f"{_name} GDP growth (annual %)", "economy", "%",
        f"Annual growth of real GDP in {_name}.",
        "Peer benchmark for India's relative growth performance.",
        country=_iso, category="global",
    ))


# ---------------------------------------------------------------------------
# Official Census of India benchmark (decadal — refreshed when a new census is published)
# ---------------------------------------------------------------------------

CENSUS_FACTS = [
    {"name": "Population (2011 Census)", "value": 1210854977, "unit": "people",
     "definition": "Final population totals of the 2011 decennial Census of India.",
     "guide": "The last completed enumeration. Use the annual World Bank population series for in-between estimates."},
    {"name": "Decennial population growth (2001–2011)", "value": 17.7, "unit": "%",
     "definition": "Percentage increase in population between the 2001 and 2011 Censuses.",
     "guide": "Decadal growth is slowing; compare it with GDP growth for per-capita gains."},
    {"name": "Literacy rate (2011)", "value": 73.0, "unit": "%",
     "definition": "Percentage of the population aged seven and above who were literate in 2011.",
     "guide": "Census definition differs from the World Bank's age-15+ literacy rate; do not mix them in one chart."},
    {"name": "Urban population (2011)", "value": 31.16, "unit": "%",
     "definition": "Share of the population living in urban areas in the 2011 Census.",
     "guide": "Baseline for measuring urbanisation since 2011."},
    {"name": "Sex ratio (2011)", "value": 943, "unit": "females per 1,000 males",
     "definition": "Number of females per 1,000 males recorded in the 2011 Census.",
     "guide": "A social outcome indicator; compare with the 0–6 child sex ratio (919) to see recent change."},
    {"name": "Population density (2011)", "value": 382, "unit": "people per km²",
     "definition": "Average number of people per square kilometre in 2011.",
     "guide": "Highly uneven across states; use state tables for local analysis."},
    {"name": "Child sex ratio, age 0–6 (2011)", "value": 919, "unit": "females per 1,000 males",
     "definition": "Females per 1,000 males in the 0–6 age group in the 2011 Census.",
     "guide": "A sensitive indicator of recent demographic behaviour."},
]

CENSUS_SOURCE = {
    "name": "Census of India — Office of the Registrar General & Census Commissioner",
    "url": "https://censusindia.gov.in/census.website/data/census-tables",
    "frequency": "Decadal (last enumeration 2011; next scheduled 2027)",
}


# ---------------------------------------------------------------------------
# Curated data.gov.in resources
# ---------------------------------------------------------------------------

DATAGOV_RESOURCES = [
    {
        "id": "9ef84268-d588-465a-a308-a864a43d0070",
        "name": "Daily commodity prices in major mandis",
        "provider": "Ministry of Agriculture & Farmers Welfare, Government of India",
        "category": "agriculture",
        "definition": "Daily minimum, maximum and modal prices of agricultural commodities across reporting markets.",
        "guide": "Use the modal price for a representative transaction price; the spread between min and max shows market fragmentation.",
        "url": "https://data.gov.in/resource/daily-price-various-commodities-various-markets-mandi",
        "fields": ["State", "District", "Market", "Commodity", "Variety", "Min Price", "Max Price", "Modal Price", "Arrival Date"],
    },
]


# ---------------------------------------------------------------------------
# Network helpers with a last-known-good cache
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_cache() -> dict[str, Any]:
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def get_json(url: str, timeout: int = 25, attempts: int = 3) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1 + attempt)
    raise last_error


def wb_series(country: str, code: str) -> list[dict[str, Any]]:
    """Fetch annual observations for one country/indicator from the World Bank."""
    params = urllib.parse.urlencode({
        "format": "json",
        "per_page": "200",
        "date": f"{START_YEAR}:{datetime.now(timezone.utc).year}",
    })
    url = f"{WB_BASE}/country/{country}/indicator/{urllib.parse.quote(code)}?{params}"
    payload = get_json(url)
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        return []
    rows = []
    for row in payload[1]:
        if row.get("value") is None:
            continue
        try:
            rows.append({"year": int(row["date"]), "value": float(row["value"])})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(rows, key=lambda r: r["year"])


def key_for(code: str, country: str) -> str:
    return f"wb:{country}:{code}"


def build_series() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    cache = load_cache()
    fresh: dict[str, list[dict[str, Any]]] = {}
    published = []
    used_cache = 0

    for definition in SERIES_DEFS:
        key = key_for(definition["code"], definition["country"])
        points: list[dict[str, Any]] = []
        fetch_error = None
        try:
            points = wb_series(definition["country"], definition["code"])
            if not points:
                raise ValueError("no observations returned")
            cache[key] = {"fetched_at": now_iso(), "points": points}
        except Exception as exc:  # keep the last good series when the API is down
            fetch_error = str(exc)
            cached = cache.get(key) or {}
            points = cached.get("points", [])
            if points:
                used_cache += 1

        item = dict(definition)
        item["key"] = key
        item["points"] = points
        item["latest_year"] = points[-1]["year"] if points else None
        item["latest_value"] = points[-1]["value"] if points else None
        item["status"] = "live" if not fetch_error and points else ("cached" if points else "unavailable")
        if fetch_error:
            item["fetch_error"] = fetch_error[:200]
        published.append(item)
        fresh[key] = points

    save_cache(cache)
    print(f"[series] {len(published)} definitions, {used_cache} served from cache")
    return published, fresh


def build_datagov_stats() -> list[dict[str, Any]]:
    """Try the curated resources; keep the previous result if rate-limited."""
    cache = load_cache()
    results = []
    for resource in DATAGOV_RESOURCES:
        item = dict(resource)
        page = fetch_resource(resource["id"], limit=5)
        if page.get("status") == "error" or "error" in page:
            cached = cache.get(f"dg:{resource['id']}") or {}
            item.update({
                "status": "cached" if cached.get("stats") else "rate_limited",
                "stats": cached.get("stats", {}),
                "note": "The portal's public key is rate-limited; set DATA_GOV_IN_TOKEN for full access.",
            })
        else:
            records = page.get("records", [])
            fields = resource["fields"]
            prices = []
            for record in records:
                try:
                    prices.append(float(record.get("modal_price", record.get("Modal Price", ""))))
                except (TypeError, ValueError):
                    continue
            stat = {
                "records_in_page": len(records),
                "total_records": page.get("total"),
                "sample_modal_price_min": min(prices) if prices else None,
                "sample_modal_price_max": max(prices) if prices else None,
                "sample_period": records[0].get("arrival_date", records[0].get("Arrival_Date")) if records else None,
                "fields_available": [f["name"] for f in page.get("field", [])][: len(fields)],
            }
            item.update({"status": "live", "stats": stat})
            cache[f"dg:{resource['id']}"] = {"fetched_at": now_iso(), "stats": stat}
        results.append(item)
    save_cache(cache)
    return results


# ---------------------------------------------------------------------------
# Derived KPIs
# ---------------------------------------------------------------------------

def value_of(fresh: dict[str, list[dict[str, Any]]], country: str, code: str) -> tuple[float | None, int | None, list[dict[str, Any]]]:
    points = fresh.get(key_for(code, country), [])
    if not points:
        return None, None, []
    return points[-1]["value"], points[-1]["year"], points


def delta(points: list[dict[str, Any]], years: int = 1) -> float | None:
    if len(points) <= years:
        return None
    return points[-1]["value"] - points[-1 - years]["value"]


def growth(points: list[dict[str, Any]]) -> float | None:
    if len(points) < 2 or not points[-2]["value"]:
        return None
    return (points[-1]["value"] / points[-2]["value"] - 1) * 100


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 6:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def alert(value: float | None, good: float, watch: float) -> str:
    if value is None:
        return "No data"
    if value >= good:
        return "Favourable"
    if value >= watch:
        return "Watch"
    return "Under pressure"


def derive_kpis(fresh: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    gdp_growth, gdp_year, gdp_pts = value_of(fresh, "IND", "NY.GDP.MKTP.KD.ZG")
    pop_growth, _, _ = value_of(fresh, "IND", "SP.POP.GROW")
    gdp_pc_growth, _, gdp_pc_pts = value_of(fresh, "IND", "NY.GDP.PCAP.KD.ZG")
    gdp_pc, _, gdp_pc_level = value_of(fresh, "IND", "NY.GDP.PCAP.CD")
    urban, _, urban_pts = value_of(fresh, "IND", "SP.URB.TOTL.IN.ZS")
    working_age, _, _ = value_of(fresh, "IND", "SP.POP.1564.TO.ZS")
    literacy, _, _ = value_of(fresh, "IND", "SE.ADT.LITR.ZS")
    savings, _, _ = value_of(fresh, "IND", "NY.GDS.TOTL.ZS")
    credit, _, _ = value_of(fresh, "IND", "FS.AST.PRVT.GD.ZS")
    real_rate, _, _ = value_of(fresh, "IND", "FR.INR.RINR")
    fdi, _, fdi_pts = value_of(fresh, "IND", "BX.KLT.DINV.WD.GD.ZS")
    current_account, _, ca_pts = value_of(fresh, "IND", "BN.CAB.XOKA.GD.ZS")
    reserves, _, reserves_pts = value_of(fresh, "IND", "FI.RES.TOTL.MO")
    inflation, _, _ = value_of(fresh, "IND", "FP.CPI.TOTL.ZG")
    pm25, _, pm25_pts = value_of(fresh, "IND", "EN.ATM.PM25.MC.M3")
    internet, _, internet_pts = value_of(fresh, "IND", "IT.NET.USER.ZS")
    fx, _, fx_pts = value_of(fresh, "IND", "PA.NUS.FCRF")

    peer_growths = [value_of(fresh, iso, "NY.GDP.MKTP.KD.ZG")[0] for iso, _ in PEERS]
    peer_growths = [v for v in peer_growths if v is not None]
    peer_growth = mean(peer_growths) if peer_growths else None
    world_growth, _, _ = value_of(fresh, "WLD", "NY.GDP.MKTP.KD.ZG")
    world_inflation, _, _ = value_of(fresh, "WLD", "FP.CPI.TOTL.ZG")

    kpis: list[dict[str, Any]] = []

    def add(kpi_id, name, sector, value, unit, formula, definition, guide, sources, status="Favourable"):
        kpis.append({
            "id": kpi_id, "name": name, "sector": sector,
            "value": round(value, 2) if isinstance(value, (int, float)) and math.isfinite(value) else None,
            "unit": unit, "formula": formula, "definition": definition,
            "guide": guide, "sources": sources, "latest_year": gdp_year,
            "status": status, "frequency": "Annual",
        })

    # 1. Per-capita growth spread
    if gdp_growth is not None and pop_growth is not None:
        v = gdp_growth - pop_growth
        add("per_capita_growth_spread", "Per-capita growth spread", "economy", v, "pp",
            "Real GDP growth − population growth",
            "How much of headline growth remains after accounting for a growing population.",
            "A wider spread means average output per person is rising faster. It is an approximation of GDP-per-capita growth.",
            ["World Bank NY.GDP.MKTP.KD.ZG", "World Bank SP.POP.GROW"], alert(v, 5, 2))

    # 2. Demographic dividend index
    if working_age is not None and literacy is not None:
        v = working_age * literacy / 100
        add("demographic_dividend_index", "Demographic dividend index", "welfare", v, "index",
            "Working-age share (%) × literacy rate (%) ÷ 100",
            "Potential productive capacity from the size and education of the working-age population.",
            "This is potential, not realised, capacity. Read it with employment and job-quality data before calling it a dividend.",
            ["World Bank SP.POP.1564.TO.ZS", "World Bank SE.ADT.LITR.ZS"], alert(v, 60, 50))

    # 3. Urbanisation productivity ratio
    urban_change = delta(urban_pts)
    if gdp_pc_growth is not None and urban_change not in (None, 0):
        v = gdp_pc_growth / urban_change
        add("urbanisation_productivity_ratio", "Urbanisation productivity ratio", "housing", v, "×",
            "GDP per capita growth (%) ÷ change in urban share (pp)",
            "Output growth generated for each percentage-point shift of population into towns and cities.",
            "A high ratio can mean productive cities — or that urbanisation is simply too slow. Always inspect both inputs.",
            ["World Bank NY.GDP.PCAP.KD.ZG", "World Bank SP.URB.TOTL.IN.ZS"], "Interpret with care")

    # 4. Credit–savings gap
    if credit is not None and savings is not None:
        v = credit - savings
        add("credit_savings_gap", "Credit–savings gap", "financials", v, "pp of GDP",
            "Domestic credit to private sector (% GDP) − gross domestic savings (% GDP)",
            "How far private credit extends beyond the nation's own savings, indicating reliance on other funding sources.",
            "A widening gap can support investment but may signal leverage. Compare across a full cycle, not a single year.",
            ["World Bank FS.AST.PRVT.GD.ZS", "World Bank NY.GDS.TOTL.ZS"], "Interpret with care")

    # 5. Credit per person
    if credit is not None and gdp_pc is not None:
        v = credit / 100 * gdp_pc
        add("credit_per_person", "Private credit per person", "financials", v, "USD",
            "Domestic credit (% GDP) × GDP per capita (current US$) ÷ 100",
            "Approximate financial depth available per resident.",
            "Use it to compare financial access across countries; it does not show how credit is distributed.",
            ["World Bank FS.AST.PRVT.GD.ZS", "World Bank NY.GDP.PCAP.CD"], "Context")

    # 6. External resilience composite
    components = [(fdi_pts, 1), (ca_pts, 1), (reserves_pts, 1)]
    if all(len(pts) >= 3 for pts, _ in components):
        scores = []
        for pts, direction in components:
            vals = [p["value"] for p in pts]
            avg, sd = mean(vals), (math.sqrt(sum((v - mean(vals)) ** 2 for v in vals) / len(vals)) or 1)
            scores.append(direction * (vals[-1] - avg) / sd)
        v = 50 + 10 * mean(scores)
        v = max(0, min(100, v))
        add("external_resilience_score", "External resilience score", "economy", v, "0–100",
            "Average z-score of FDI (% GDP), current account (% GDP) and reserve cover (months), scaled to 0–100",
            "Composite of the three external buffers that help an economy absorb a sudden stop in capital flows.",
            "A score above 50 means the three buffers are above their own long-run averages; it is a relative, not absolute, measure.",
            ["World Bank BX.KLT.DINV.WD.GD.ZS", "BN.CAB.XOKA.GD.ZS", "FI.RES.TOTL.MO"], alert(v, 55, 45))

    # 7. Peer growth spread
    if gdp_growth is not None and peer_growth is not None:
        v = gdp_growth - peer_growth
        add("peer_growth_spread", "Peer growth spread", "economy", v, "pp",
            "India GDP growth − average GDP growth of Vietnam, Indonesia, Brazil and Mexico",
            "How much faster or slower India is growing than a basket of large emerging economies.",
            "A positive spread suggests India is gaining relative ground; check the exchange rate and FDI before extrapolating.",
            ["World Bank India + 4 peer GDP series"], alert(v, 0, -1))

    # 8. Global inflation gap
    if inflation is not None and world_inflation is not None:
        v = inflation - world_inflation
        add("global_inflation_gap", "Global inflation gap", "economy", v, "pp",
            "India CPI inflation − world inflation",
            "The part of domestic inflation that is above the global price trend.",
            "A positive gap points to domestic cost or demand pressure; a negative gap suggests imported disinflation.",
            ["World Bank FP.CPI.TOTL.ZG (IND and WLD)"], "Interpret with care")

    # 9. Pollution intensity of growth
    pm25_growth = growth(pm25_pts)
    if pm25_growth is not None and gdp_growth not in (None, 0):
        v = pm25_growth / gdp_growth
        add("pollution_intensity_of_growth", "Pollution intensity of growth", "environment", v, "×",
            "Growth in PM2.5 (%) ÷ real GDP growth (%)",
            "Change in air pollution associated with each unit of economic growth.",
            "Below zero means air quality improved while the economy grew — a sign of decoupling. Values above one mean growth remains pollution-heavy.",
            ["World Bank EN.ATM.PM25.MC.M3", "NY.GDP.MKTP.KD.ZG"], alert(-v if v is not None else None, 0, 0.5))

    # 10. Digital adoption per unit of growth
    internet_change = delta(internet_pts)
    if internet_change not in (None, 0) and gdp_pc_growth is not None:
        v = gdp_pc_growth / internet_change
        add("digital_growth_elasticity", "Digital growth elasticity", "commerce", v, "×",
            "GDP per capita growth (%) ÷ change in internet users (% of population, pp)",
            "Output growth associated with each percentage-point increase in internet adoption.",
            "A high value can mean digital adoption is translating into output, or that adoption has stalled while the economy grew.",
            ["World Bank IT.NET.USER.ZS", "NY.GDP.PCAP.KD.ZG"], "Interpret with care")

    # 11. Exchange-rate pressure on external cost
    fx_growth = growth(fx_pts)
    if fx_growth is not None and real_rate is not None:
        v = fx_growth - real_rate
        add("fx_real_rate_gap", "FX–real-rate gap", "financials", v, "pp",
            "Annual change in INR/USD exchange rate − real interest rate",
            "Currency depreciation not offset by the real return offered to savers.",
            "A positive gap flag means rupee weakness outpaces the real reward for holding rupee assets.",
            ["World Bank PA.NUS.FCRF", "FR.INR.RINR"], "Watch" if v and v > 0 else "Favourable")

    # 12. World growth tailwind
    if gdp_growth is not None and world_growth not in (None, 0):
        v = gdp_growth / world_growth
        add("growth_tailwind_ratio", "Growth tailwind ratio", "economy", v, "×",
            "India GDP growth ÷ world GDP growth",
            "How many times the global growth rate India is expanding.",
            "Ratios above one indicate India is outpacing the world cycle; moderate ratios can reflect a global boom lifting all economies.",
            ["World Bank NY.GDP.MKTP.KD.ZG (IND and WLD)"], alert(v, 1.5, 1))

    return kpis


# ---------------------------------------------------------------------------
# Relationships between macro, demographic and global factors
# ---------------------------------------------------------------------------

RELATIONSHIP_PAIRS = [
    ("IND", "NY.GDP.MKTP.KD.ZG", "IND", "FP.CPI.TOTL.ZG", "macro", "Growth versus inflation"),
    ("IND", "NY.GDP.MKTP.KD.ZG", "IND", "FS.AST.PRVT.GD.ZS", "macro/finance", "Growth versus financial depth"),
    ("IND", "NY.GDP.MKTP.KD.ZG", "IND", "SP.URB.TOTL.IN.ZS", "macro/demographic", "Growth versus urbanisation"),
    ("IND", "NY.GDP.MKTP.KD.ZG", "IND", "IT.NET.USER.ZS", "macro/digital", "Growth versus internet adoption"),
    ("IND", "NY.GDP.PCAP.CD", "IND", "SE.ADT.LITR.ZS", "income/education", "Income versus literacy"),
    ("IND", "NY.GDP.PCAP.CD", "IND", "EN.ATM.PM25.MC.M3", "income/environment", "Income versus air quality"),
    ("IND", "BX.KLT.DINV.WD.GD.ZS", "IND", "BN.CAB.XOKA.GD.ZS", "external", "FDI versus current account"),
    ("IND", "FR.INR.RINR", "IND", "BX.KLT.DINV.WD.GD.ZS", "finance/external", "Real rates versus FDI"),
    ("IND", "FP.CPI.TOTL.ZG", "WLD", "FP.CPI.TOTL.ZG", "global", "Indian versus world inflation"),
    ("IND", "NY.GDP.MKTP.KD.ZG", "WLD", "NY.GDP.MKTP.KD.ZG", "global", "Indian versus world growth"),
]

PEER_RELATIONSHIPS = [
    (iso, name) for iso, name in PEERS
]


def interpret_correlation(r: float, kind: str) -> str:
    strength = "strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak"
    direction = "moves with" if r > 0 else "moves against"
    return f"A {strength} {direction} the other factor over the overlapping period. Correlation is not causation."


def build_relationships(fresh: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []

    def pair(a_country, a_code, b_country, b_code, kind, label):
        a_points = fresh.get(key_for(a_code, a_country), [])
        b_points = fresh.get(key_for(b_code, b_country), [])
        b_by_year = {p["year"]: p["value"] for p in b_points}
        years = [p["year"] for p in a_points if p["year"] in b_by_year]
        xs = [p["value"] for p in a_points if p["year"] in b_by_year]
        ys = [b_by_year[y] for y in years]
        r = pearson(xs, ys)
        if r is None or not years:
            return
        out.append({
            "id": f"{a_country}-{a_code}__{b_country}-{b_code}".lower(),
            "label": label,
            "factor": kind,
            "a": next((d["label"] for d in SERIES_DEFS if d["code"] == a_code and d["country"] == a_country), a_code),
            "b": next((d["label"] for d in SERIES_DEFS if d["code"] == b_code and d["country"] == b_country), b_code),
            "coefficient": round(r, 3),
            "observations": len(years),
            "period": f"{min(years)}–{max(years)}",
            "interpretation": interpret_correlation(r, kind),
        })

    for args in RELATIONSHIP_PAIRS:
        pair(*args)

    for iso, name in PEER_RELATIONSHIPS:
        pair("IND", "NY.GDP.MKTP.KD.ZG", iso, "NY.GDP.MKTP.KD.ZG", "global peer",
             f"India versus {name} GDP growth")

    return out


# ---------------------------------------------------------------------------
# Discovery catalog
# ---------------------------------------------------------------------------

def build_discovery(series: list[dict[str, Any]], datagov: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        from api_catalog import API_CATALOG, API_CATEGORY_MAP, catalog_summary
        portals = [
            {
                "id": api["id"], "name": api["name"], "provider": api["provider"],
                "category": api["category"],
                "category_label": API_CATEGORY_MAP.get(api["category"], {}).get("title", api["category"]),
                "access": api["access"], "url": api["url"], "docs_url": api.get("docs_url", ""),
                "summary": api["summary"],
            }
            for api in API_CATALOG
        ]
        summary = catalog_summary()
    except Exception as exc:
        portals, summary = [], {"error": str(exc)}

    return {
        "scanned_at": now_iso(),
        "scope": "Curated scan: official portal metadata plus live series actually fetched in this run.",
        "key_mode": "personal token" if os.environ.get("DATA_GOV_IN_TOKEN") else "public sample key (rate-limited)",
        "portals": portals,
        "portal_summary": summary,
        "data_gov_resources": datagov,
        "api_setu": {
            "name": "API Setu (MeitY)",
            "url": "https://directory.apisetu.gov.in",
            "access": "Consumer registration and API key required for data endpoints",
            "status": "Metadata only — curated batch does not call gated data endpoints",
            "token": "configured" if os.environ.get("APISETU_TOKEN") else "not configured",
        },
        "series_count": len(series),
        "note": "Full enumeration of data.gov.in's 230,000+ datasets requires a personal API key and a paginated catalog crawl; this catalog lists the official sources and the curated resources published below.",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("[1/6] Fetching curated World Bank series…")
    series, fresh = build_series()
    print("[2/6] Checking curated data.gov.in resources…")
    datagov = build_datagov_stats()
    print("[3/6] Deriving innovative KPIs…")
    kpis = derive_kpis(fresh)
    print("[4/6] Computing relationships with macro and global factors…")
    relationships = build_relationships(fresh)
    print("[5/6] Fetching curated global feeds…")
    cache = load_cache()
    global_data = build_global_data(cache)
    save_cache(cache)
    print("[6/6] Building discovery catalog…")
    discovery = build_discovery(series, datagov)

    payload = {
        "generated_at": now_iso(),
        "methodology": (
            "Public official APIs first. Derived values are computed from the series listed "
            "in this file; Yahoo Finance market snapshots are secondary, delayed references."
        ),
        "series": series,
        "census": {"facts": CENSUS_FACTS, "source": CENSUS_SOURCE},
        "data_gov_resources": datagov,
        "kpis": kpis,
        "relationships": relationships,
        "global": global_data,
        "discovery": discovery,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    live = sum(1 for s in series if s["status"] == "live")
    print(f"[OK] {OUTPUT.relative_to(ROOT)} written")
    print(f"     series live={live}/{len(series)} | derived KPIs={len(kpis)} | "
          f"relationships={len(relationships)} | global series={global_data['counts']['series']} | "
          f"global KPIs={global_data['counts']['derived_kpis']}")


if __name__ == "__main__":
    main()
