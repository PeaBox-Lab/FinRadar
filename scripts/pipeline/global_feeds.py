"""FinRadar — curated global data feeds
========================================

Phase 1 of the global expansion. This module is called by ``enrichment.py``
with the shared last-known-good cache and returns a JSON-serialisable payload
that is published under ``global`` in ``data/extra_metrics.json``.

Official-first sources:

* ECB Data Portal — daily foreign-exchange reference rates;
* BIS Statistics — policy rates, debt service ratios, credit gaps and
  effective exchange rates;
* IMF DataMapper — WEO growth, inflation, debt and current-account balances;
* WTO Timeseries — merchandise exports and imports;
* World Bank Open Data — PPP price levels, gender wage gap, banking,
  insurance, treasury debt and stock-market development;
* World Bank Pink Sheet — official monthly commodity prices.

Yahoo Finance is used only for clearly labelled, delayed market-reference
snapshots of equity indices, futures and FX. It is never presented as an
official statistic.

Usage:
    from global_feeds import build_global_data
    payload = build_global_data(cache)
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

USER_AGENT = "FinRadar global feeds/1.0"

WB_BASE = "https://api.worldbank.org/v2"
ECB_BASE = "https://data-api.ecb.europa.eu/service/data"
BIS_BASE = "https://stats.bis.org/api/v2/data/dataflow/BIS"
IMF_BASE = "https://www.imf.org/external/datamapper/api/v2"
WTO_BASE = "http://dataapi.wto.org/data"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
PINK_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
PINK_FALLBACK = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)

COUNTRIES = [
    {"iso2": "US", "iso3": "USA", "name": "United States"},
    {"iso2": "CN", "iso3": "CHN", "name": "China"},
    {"iso2": "JP", "iso3": "JPN", "name": "Japan"},
    {"iso2": "DE", "iso3": "DEU", "name": "Germany"},
    {"iso2": "GB", "iso3": "GBR", "name": "United Kingdom"},
    {"iso2": "FR", "iso3": "FRA", "name": "France"},
    {"iso2": "IN", "iso3": "IND", "name": "India"},
    {"iso2": "BR", "iso3": "BRA", "name": "Brazil"},
    {"iso2": "CA", "iso3": "CAN", "name": "Canada"},
    {"iso2": "AU", "iso3": "AUS", "name": "Australia"},
    {"iso2": "KR", "iso3": "KOR", "name": "South Korea"},
    {"iso2": "MX", "iso3": "MEX", "name": "Mexico"},
    {"iso2": "ZA", "iso3": "ZAF", "name": "South Africa"},
    {"iso2": "ID", "iso3": "IDN", "name": "Indonesia"},
]
COUNTRY_BY_ISO2 = {c["iso2"]: c["name"] for c in COUNTRIES}
COUNTRY_BY_ISO3 = {c["iso3"]: c["name"] for c in COUNTRIES}


ECB_CURRENCIES = [
    ("USD", "US dollar"), ("GBP", "Pound sterling"), ("JPY", "Japanese yen"),
    ("INR", "Indian rupee"), ("CNY", "Chinese yuan"), ("AUD", "Australian dollar"),
    ("CAD", "Canadian dollar"), ("CHF", "Swiss franc"), ("BRL", "Brazilian real"),
    ("MXN", "Mexican peso"), ("ZAR", "South African rand"),
    ("KRW", "South Korean won"), ("SGD", "Singapore dollar"),
]

BIS_FLOWS = [
    {
        "flow": "WS_CBPOL", "id": "policy-rates", "icon": "🏦",
        "title": "Central bank policy rates",
        "description": "Official policy rates for major economies. A higher policy rate generally slows credit and inflation, but the exact instrument differs by country.",
        "country_field": "REF_AREA", "group": ["REF_AREA", "TITLE"],
        "one_per_country": True, "limit": 18, "unit": "%",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_CBPOL",
        "definition": "Central bank policy rates are the interest rates set by monetary authorities, such as repo rates, policy deposit rates or official lending rates.",
        "guide": "Compare changes over time within one country. Cross-country levels are not perfectly comparable because instruments and reporting conventions differ.",
    },
    {
        "flow": "WS_DSR", "id": "debt-service", "icon": "🧾",
        "title": "Debt service ratios by sector",
        "description": "Debt payments as a share of income for households, corporations and the private non-financial sector.",
        "country_field": "BORROWERS_CTY", "group": ["BORROWERS_CTY", "DSR_BORROWERS"],
        "one_per_country": False, "limit": 30, "unit": "% of income",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_DSR",
        "definition": "The debt service ratio is interest payments plus principal repayments divided by the sector's disposable income.",
        "guide": "A rising ratio means more income is committed to debt repayment. Read it alongside policy rates and credit growth.",
    },
    {
        "flow": "WS_CREDIT_GAP", "id": "credit-gaps", "icon": "📉",
        "title": "Credit-to-GDP gaps",
        "description": "Deviation of credit from its long-run trend. Persistent positive gaps are often watched as a financial-stability warning sign.",
        "country_field": "BORROWERS_CTY", "group": ["BORROWERS_CTY", "CG_DTYPE"],
        "filters": {"CG_DTYPE": {"A"}}, "one_per_country": False,
        "limit": 20, "unit": "% of GDP",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_CREDIT_GAP",
        "definition": "The credit gap is the percentage difference between the credit-to-GDP ratio and its long-run trend.",
        "guide": "Use it as a risk indicator, not a forecast. Positive gaps can persist for years before a downturn.",
    },
    {
        "flow": "WS_EER", "id": "effective-exchange-rates", "icon": "💱",
        "title": "Effective exchange rate indices",
        "description": "Trade-weighted exchange rate indices that show a currency's broad movement against partner currencies.",
        "country_field": "REF_AREA", "group": ["REF_AREA", "TITLE"],
        "one_per_country": True, "limit": 18, "unit": "index",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_EER",
        "definition": "An effective exchange rate is a weighted average of bilateral exchange rates, usually weighted by trade shares.",
        "guide": "An increase means a broader appreciation. The base period varies by series, so compare direction rather than raw index levels across countries.",
    },
]

IMF_INDICATORS = [
    ("NGDP_RPCH", "Real GDP growth", "%", "macro",
     "Annual growth of real GDP at constant prices.",
     "Compare with inflation and debt to judge the quality of growth."),
    ("PCPIPCH", "Consumer price inflation", "%", "prices",
     "Annual percentage change of the consumer price index.",
     "Use the WEO value for medium-term context; national releases are usually more timely."),
    ("GGXWDG_NGDP", "General government gross debt", "% of GDP", "debt",
     "Gross general-government debt as a share of GDP.",
     "A high ratio does not by itself signal stress; interest costs and currency matter too."),
    ("BCA", "Current account balance", "% of GDP", "external",
     "Current account balance as a share of GDP.",
     "Deficits can fund productive investment, but persistent deficits need stable financing."),
]

WTO_INDICATORS = [
    ("ITS_MTV_AX", "Merchandise exports"),
    ("ITS_MTV_MM", "Merchandise imports"),
]
WTO_REPORTERS = [
    ("840", "United States"), ("156", "China"), ("276", "Germany"),
    ("392", "Japan"), ("356", "India"), ("826", "United Kingdom"),
    ("410", "South Korea"), ("250", "France"),
]

WB_GLOBAL_INDICATORS = [
    ("PA.NUS.FCRF", "Official exchange rate", "LCU per USD", "cost_of_living",
     "Official exchange rate used by the World Bank, in local currency units per US dollar.",
     "Used with the PPP conversion factor to build a cost-of-living proxy. Market quotes can differ."),
    ("PA.NUS.PPP", "PPP conversion factor", "LCU per international $", "cost_of_living",
     "Number of local currency units needed to buy the same bundle of goods that one international dollar buys in the United States.",
     "Use with the price-level ratio to separate currency effects from real price differences."),
    ("JI.WAG.GNDR", "Female-to-male gender wage gap", "ratio", "pay_parity",
     "Ratio of female to male wages for full-time dependent employees, aged 15–64.",
     "1.0 means parity; lower values mean a wider gap. Coverage and methods vary by country."),
    ("FB.BNK.CAPA.ZS", "Bank capital to assets", "%", "banking",
     "Bank capital as a share of total bank assets.",
     "A thicker capital buffer generally improves resilience, but very high ratios can also indicate a smaller loan book."),
    ("FB.AST.NPER.ZS", "Bank non-performing loans", "%", "banking",
     "Non-performing loans as a share of total gross loans.",
     "Rising NPLs can precede lower credit growth. Definitions of non-performing differ across regulators."),
    ("GFDD.DI.09", "Life insurance premium volume", "% of GDP", "insurance",
     "Direct life insurance premiums as a share of GDP.",
     "A measure of insurance depth. It is not a measure of insurer profitability or solvency."),
    ("GFDD.DI.10", "Non-life insurance premium volume", "% of GDP", "insurance",
     "Direct non-life insurance premiums as a share of GDP.",
     "Compare with life penetration to see the structure of a country's insurance market."),
    ("GC.DOD.TOTL.GD.ZS", "Central government debt", "% of GDP", "treasury_debt",
     "Total central government debt as a share of GDP.",
     "Use alongside interest rates and the currency of issuance; gross debt is not the same as net debt."),
    ("CM.MKT.LCAP.GD.ZS", "Stock market capitalisation", "% of GDP", "equity_markets",
     "Market value of listed domestic companies as a share of GDP.",
     "A proxy for equity-market depth. It rises with prices as well as with new listings."),
    ("CM.MKT.TRNR", "Stock turnover ratio", "%", "equity_markets",
     "Value of domestic shares traded divided by market capitalisation.",
     "Higher turnover usually means more liquid markets, but it can also reflect short-term speculation."),
]

MARKETS = [
    ("^GSPC", "S&P 500", "Equity indices", "index pts", "US"),
    ("^IXIC", "NASDAQ Composite", "Equity indices", "index pts", "US"),
    ("^DJI", "Dow Jones Industrial Average", "Equity indices", "index pts", "US"),
    ("^RUT", "Russell 2000", "Equity indices", "index pts", "US"),
    ("^FTSE", "FTSE 100", "Equity indices", "index pts", "UK"),
    ("^GDAXI", "DAX", "Equity indices", "index pts", "Germany"),
    ("^FCHI", "CAC 40", "Equity indices", "index pts", "France"),
    ("^N225", "Nikkei 225", "Equity indices", "index pts", "Japan"),
    ("^HSI", "Hang Seng", "Equity indices", "index pts", "Hong Kong"),
    ("^BSESN", "BSE SENSEX", "Equity indices", "index pts", "India"),
    ("^NSEI", "NIFTY 50", "Equity indices", "index pts", "India"),
    ("^KS11", "KOSPI", "Equity indices", "index pts", "South Korea"),
    ("^AXJO", "S&P/ASX 200", "Equity indices", "index pts", "Australia"),
    ("^GSPTSE", "S&P/TSX Composite", "Equity indices", "index pts", "Canada"),
    ("^SSMI", "SMI", "Equity indices", "index pts", "Switzerland"),
    ("^IBEX", "IBEX 35", "Equity indices", "index pts", "Spain"),
    ("CL=F", "WTI crude oil futures", "Commodity futures", "USD/barrel", "NYMEX"),
    ("BZ=F", "Brent crude oil futures", "Commodity futures", "USD/barrel", "ICE"),
    ("GC=F", "Gold futures", "Commodity futures", "USD/troy oz", "COMEX"),
    ("SI=F", "Silver futures", "Commodity futures", "USD/troy oz", "COMEX"),
    ("HG=F", "Copper futures", "Commodity futures", "USD/lb", "COMEX"),
    ("NG=F", "Natural gas futures", "Commodity futures", "USD/mmbtu", "NYMEX"),
    ("ZC=F", "Corn futures", "Commodity futures", "US cents/bushel", "CBOT"),
    ("ZS=F", "Soybean futures", "Commodity futures", "US cents/bushel", "CBOT"),
    ("ZW=F", "Wheat futures", "Commodity futures", "US cents/bushel", "CBOT"),
    ("KC=F", "Coffee futures", "Commodity futures", "US cents/lb", "ICE"),
    ("SB=F", "Sugar futures", "Commodity futures", "US cents/lb", "ICE"),
    ("PL=F", "Platinum futures", "Commodity futures", "USD/troy oz", "NYMEX"),
    ("PA=F", "Palladium futures", "Commodity futures", "USD/troy oz", "NYMEX"),
    ("EURUSD=X", "EUR / USD", "Foreign exchange", "USD per EUR", "FX"),
    ("USDINR=X", "USD / INR", "Foreign exchange", "INR per USD", "FX"),
    ("USDJPY=X", "USD / JPY", "Foreign exchange", "JPY per USD", "FX"),
    ("GBPUSD=X", "GBP / USD", "Foreign exchange", "USD per GBP", "FX"),
    ("USDCNY=X", "USD / CNY", "Foreign exchange", "CNY per USD", "FX"),
]

GLOBAL_GUIDES = [
    {
        "id": "policy-rate", "title": "Central bank policy rate",
        "definition": "The benchmark rate a central bank sets or targets to steer money-market conditions.",
        "guide": "Compare a country's own rate across time. Instruments differ (repo, deposit, lending rate), so levels are not directly comparable.",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_CBPOL",
    },
    {
        "id": "debt-service", "title": "Debt service ratio",
        "definition": "Principal and interest payments divided by the borrower's income.",
        "guide": "It measures repayment burden rather than the stock of debt. A high ratio can appear before defaults even when debt levels look manageable.",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_DSR",
    },
    {
        "id": "credit-gap", "title": "Credit gap",
        "definition": "The percentage deviation of the credit-to-GDP ratio from its long-run trend.",
        "guide": "Treat it as a financial-stability signal, not a timing tool. The Basel Committee uses it as a reference for countercyclical buffers.",
        "source": "Bank for International Settlements",
        "source_url": "https://stats.bis.org/statx/sseries.html?c=WS_CREDIT_GAP",
    },
    {
        "id": "ppp-price-level", "title": "PPP price-level ratio",
        "definition": "PPP conversion factor divided by the market exchange rate.",
        "guide": "It approximates how expensive a country is relative to the United States. It is not a city-level cost-of-living index.",
        "source": "World Bank Open Data",
        "source_url": "https://data.worldbank.org/indicator/PA.NUS.PPPC.RF",
    },
    {
        "id": "pay-parity", "title": "Gender wage gap",
        "definition": "Female wages divided by male wages for comparable employees.",
        "guide": "A value of 1 means parity. The World Bank series covers full-time dependent employees aged 15–64 and excludes many informal workers.",
        "source": "World Bank Open Data",
        "source_url": "https://data.worldbank.org/indicator/JI.WAG.GNDR",
    },
    {
        "id": "insurance-depth", "title": "Insurance penetration",
        "definition": "Direct insurance premiums as a share of GDP.",
        "guide": "It measures the size of the market relative to the economy. It does not say anything about claim settlement quality or insurer solvency.",
        "source": "World Bank Global Financial Development Database",
        "source_url": "https://data.worldbank.org/indicator/GFDD.DI.09",
    },
    {
        "id": "bank-resilience", "title": "Bank capital and NPLs",
        "definition": "Capital to assets shows the equity cushion; non-performing loans show the share of loans in distress.",
        "guide": "Read both together. Strong capital with rising NPLs means the sector can absorb losses but may still tighten lending.",
        "source": "World Bank Open Data",
        "source_url": "https://data.worldbank.org/indicator/FB.BNK.CAPA.ZS",
    },
    {
        "id": "treasury-debt", "title": "Central government debt",
        "definition": "Gross central-government debt as a share of GDP.",
        "guide": "Compare with the real interest rate and the currency of issuance. Gross debt is different from net debt.",
        "source": "World Bank Open Data",
        "source_url": "https://data.worldbank.org/indicator/GB.DOD.TOTL.GD.ZS",
    },
    {
        "id": "equity-depth", "title": "Equity market development",
        "definition": "Market capitalisation relative to GDP and the turnover ratio of domestic shares.",
        "guide": "Capitalisation rises with valuations as well as listings; turnover shows how actively shares trade relative to market size.",
        "source": "World Bank Open Data",
        "source_url": "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
    },
    {
        "id": "commodity-prices", "title": "Pink Sheet commodity prices",
        "definition": "World Bank monthly nominal commodity prices in US dollars, with units specific to each commodity.",
        "guide": "These are monthly benchmarks, not live quotes. Gold and silver are quoted per troy ounce, base metals per metric tonne and oil per barrel.",
        "source": "World Bank Commodity Markets",
        "source_url": PINK_PAGE,
    },
    {
        "id": "steel-benchmark", "title": "Why there is no global steel price",
        "definition": "The Pink Sheet does not publish a single worldwide steel price; iron ore is its closest upstream benchmark.",
        "guide": "Steel prices are regional and grade-specific. Use iron ore for the raw-material signal and a market quote for a specific region or grade.",
        "source": "World Bank Commodity Markets",
        "source_url": PINK_PAGE,
    },
    {
        "id": "market-snapshots", "title": "Delayed market snapshots",
        "definition": "Index, futures and FX quotes from a secondary market-data provider.",
        "guide": "These quotes are for context only. They can be delayed and are not official statistics. For publication-grade analysis use the exchange or its licensed data vendor.",
        "source": "Yahoo Finance (secondary market data)",
        "source_url": "https://finance.yahoo.com/",
    },
]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_bytes(url: str, *, timeout: int = 45, attempts: int = 2,
                headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})}
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.6 + attempt)
    raise last_error if last_error else RuntimeError("fetch failed")


def fetch_text(url: str, **kwargs: Any) -> str:
    return fetch_bytes(url, **kwargs).decode("utf-8", "replace")


def fetch_json(url: str, **kwargs: Any) -> Any:
    return json.loads(
        fetch_text(url, headers={"Accept": "application/json", **(kwargs.pop("headers", {}) or {})}, **kwargs)
    )


def with_cache(cache: dict[str, Any], key: str, loader: Callable[[], Any]) -> tuple[Any, str, str | None]:
    """Return (data, status, error) with a last-known-good fallback."""
    try:
        data = loader()
        if data in (None, [], {}):
            raise ValueError("empty response")
        cache[key] = {"fetched_at": now_iso(), "data": data}
        return data, "live", None
    except Exception as exc:
        error = str(exc)[:180]
        hit = cache.get(key) or {}
        if "data" in hit:
            return hit["data"], "cached", error
        return None, "unavailable", error


def to_float(value: Any) -> float | None:
    if value in (None, "", "...", "…", "NA", "N/A"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def make_item(*, key: str, label: str, country: str, unit: str, frequency: str,
              points: list[dict[str, Any]], definition: str, guide: str,
              source: str, source_url: str, status: str,
              note: str | None = None) -> dict[str, Any]:
    cleaned = [
        {"period": str(p["period"]), "value": float(p["value"])}
        for p in points if p.get("value") is not None and to_float(p.get("value")) is not None
    ]
    cleaned.sort(key=lambda p: p["period"])
    cleaned = cleaned[-36:]
    latest = cleaned[-1] if cleaned else None
    previous = cleaned[-2] if len(cleaned) > 1 else None
    change = None
    if latest and previous and previous["value"]:
        change = (latest["value"] / previous["value"] - 1) * 100
    item = {
        "key": key, "label": label, "country": country, "unit": unit,
        "frequency": frequency, "definition": definition, "guide": guide,
        "source": source, "source_url": source_url, "status": status,
        "points": cleaned,
        "latest_period": latest["period"] if latest else None,
        "latest_value": latest["value"] if latest else None,
        "change_pct": round(change, 2) if change is not None else None,
    }
    if note:
        item["note"] = note
    return item


def section_status(items: list[dict[str, Any]]) -> str:
    statuses = {item.get("status") for item in items}
    if "live" in statuses:
        return "live"
    if "cached" in statuses:
        return "cached"
    return "unavailable"


def section(*, id_: str, title: str, icon: str, description: str, items: list[dict[str, Any]],
            source: str, source_url: str, definition: str, guide: str,
            status_note: str | None = None) -> dict[str, Any]:
    result = {
        "id": id_, "title": title, "icon": icon, "description": description,
        "source": source, "source_url": source_url, "definition": definition,
        "guide": guide, "status": section_status(items), "items": items,
    }
    if status_note:
        result["status_note"] = status_note
    return result


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# ECB foreign exchange reference rates
# ---------------------------------------------------------------------------

def build_ecb_section(cache: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    notes: list[str] = []
    series_by_code: dict[str, list[dict[str, Any]]] = {}
    definition = (
        "ECB daily reference exchange rates are calculated at 14:15 CET from market "
        "quotes and published by the European Central Bank."
    )
    guide = (
        "Rates are units of foreign currency per euro. Use the same direction when "
        "calculating a cross rate; a rise means the foreign currency weakened against the euro."
    )
    for code, name in ECB_CURRENCIES:
        url = f"{ECB_BASE}/EXR/D.{code}.EUR.SP00.A?lastNObservations=36&format=csvdata"

        def loader(url=url):
            rows = list(csv.DictReader(io.StringIO(fetch_text(url, timeout=40))))
            points = []
            for row in rows:
                value = to_float(row.get("OBS_VALUE"))
                if row.get("TIME_PERIOD") and value is not None:
                    points.append({"period": row["TIME_PERIOD"], "value": value})
            return points

        points, status, error = with_cache(cache, f"global:ecb:exr:{code}", loader)
        series_by_code[code] = points or []
        if error and status != "live":
            notes.append(f"{code}: {error}")
        items.append(make_item(
            key=f"ecb-exr-{code.lower()}", label=f"{code} per EUR ({name})",
            country="Euro area", unit=f"{code} per EUR", frequency="Daily",
            points=series_by_code[code], definition=definition, guide=guide,
            source="European Central Bank", source_url="https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html",
            status=status,
        ))

    usd = {p["period"]: p["value"] for p in series_by_code.get("USD", [])}
    inr = {p["period"]: p["value"] for p in series_by_code.get("INR", [])}
    cross = [
        {"period": period, "value": inr[period] / usd[period]}
        for period in sorted(set(usd) & set(inr)) if usd[period]
    ]
    if cross:
        items.append(make_item(
            key="ecb-cross-inr-usd", label="INR per USD (derived from ECB)",
            country="India / United States", unit="INR per USD", frequency="Daily",
            points=cross,
            definition="INR per EUR divided by USD per EUR, using ECB reference rates on the same date.",
            guide="A derived cross rate. The ECB does not publish this pair directly; small timing differences can appear versus market quotes.",
            source="European Central Bank (derived)", source_url="https://data-api.ecb.europa.eu/service/data/EXR",
            status="live",
        ))

    return section(
        id_="fx-rates", title="Foreign exchange reference rates", icon="💱",
        description="Daily official reference rates against the euro for major currencies, plus a derived INR/USD cross rate.",
        items=items, source="ECB Data Portal",
        source_url="https://data-api.ecb.europa.eu/service/data/EXR",
        definition=definition, guide=guide,
        status_note=("; ".join(notes[:3]) + " — last-known-good values shown" if notes else None),
    )


# ---------------------------------------------------------------------------
# BIS policy rates, debt, credit gaps and exchange rates
# ---------------------------------------------------------------------------

BORROWER_LABELS = {"H": "households", "N": "non-financial corporations",
                   "P": "private non-financial sector", "T": "total"}


def build_bis_section(config: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    url = f"{BIS_BASE}/{config['flow']}/1.0?lastNObservations=24&format=csvfile"

    def loader():
        return list(csv.DictReader(io.StringIO(fetch_text(url, timeout=60))))

    rows, status, error = with_cache(cache, f"global:bis:{config['flow']}", loader)
    rows = rows or []
    country_field = config["country_field"]
    group_fields = config["group"]
    filters = config.get("filters", {})

    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        country = row.get(country_field, "")
        if country not in COUNTRY_BY_ISO2:
            continue
        if any(row.get(field) not in allowed for field, allowed in filters.items()):
            continue
        key = tuple(row.get(field, "") for field in group_fields)
        groups.setdefault(key, []).append(row)

    if config.get("one_per_country"):
        best: dict[str, tuple[tuple[str, ...], list[dict[str, Any]]]] = {}
        for key, group_rows in groups.items():
            country = key[0]
            if country not in best or len(group_rows) > len(best[country][1]):
                best[country] = (key, group_rows)
        groups = dict(best.values())

    items: list[dict[str, Any]] = []
    for key, group_rows in sorted(groups.items(), key=lambda kv: kv[0]):
        points = []
        for row in group_rows:
            value = to_float(row.get("OBS_VALUE"))
            if row.get("TIME_PERIOD") and value is not None:
                points.append({"period": row["TIME_PERIOD"], "value": value})
        if len(points) < 2:
            continue
        country = key[0]
        country_name = COUNTRY_BY_ISO2.get(country, country)
        qualifier = ""
        if "DSR_BORROWERS" in group_fields:
            borrower = key[group_fields.index("DSR_BORROWERS")]
            qualifier = f" — {BORROWER_LABELS.get(borrower, borrower)}"
        label = f"{config['title'].replace('Central bank ', '')}: {country_name}{qualifier}"
        items.append(make_item(
            key=f"bis-{config['id']}-{slug(country + qualifier)}",
            label=label, country=country_name, unit=config["unit"],
            frequency="Monthly" if config["flow"] == "WS_CBPOL" else "Quarterly",
            points=points, definition=config["definition"], guide=config["guide"],
            source=config["source"], source_url=config["source_url"], status=status,
        ))

    items = items[: config["limit"]]
    return section(
        id_=config["id"], title=config["title"], icon=config["icon"],
        description=config["description"], items=items,
        source=config["source"], source_url=config["source_url"],
        definition=config["definition"], guide=config["guide"],
        status_note=(error + " — last-known-good values shown" if error and status != "live" else None),
    )


# ---------------------------------------------------------------------------
# IMF WEO indicators
# ---------------------------------------------------------------------------

WB_IMF_FALLBACK = {
    "NGDP_RPCH": ("NY.GDP.MKTP.KD.ZG", "%", "Real GDP growth"),
    "PCPIPCH": ("FP.CPI.TOTL.ZG", "%", "Consumer price inflation"),
    "GGXWDG_NGDP": ("GC.DOD.TOTL.GD.ZS", "% of GDP", "Central government debt"),
    "BCA": ("BN.GSR.GNFS.CD", "current US$", "Current account balance"),
}


def build_imf_sections(cache: dict[str, Any]) -> list[dict[str, Any]]:
    countries = "+".join(c["iso3"] for c in COUNTRIES)
    sections = []
    for code, title, unit, category, definition, guide in IMF_INDICATORS:
        url = f"{IMF_BASE}/{code}/{countries}?periods=2015:2026"

        def loader(url=url, code=code):
            payload = fetch_json(url, timeout=50)
            return payload.get("values", {}).get(code, {})

        values, status, error = with_cache(cache, f"global:imf:{code}", loader)
        items = []
        for country in COUNTRIES:
            raw = (values or {}).get(country["iso3"], {}) or {}
            points = [
                {"period": year, "value": to_float(value)}
                for year, value in raw.items()
                if str(year).isdigit() and int(year) >= 2015
            ]
            if len([p for p in points if p["value"] is not None]) < 2:
                continue
            items.append(make_item(
                key=f"imf-{code.lower()}-{country['iso3'].lower()}",
                label=f"{title} — {country['name']}", country=country["name"],
                unit=unit, frequency="Annual", points=points,
                definition=definition, guide=guide,
                source="IMF World Economic Outlook (DataMapper)",
                source_url=f"https://www.imf.org/external/datamapper/{code}@WEO/OEMDC",
                status=status,
            ))

        if not items:
            fallback_code, fallback_unit, fallback_title = WB_IMF_FALLBACK[code]
            rows, fallback_status, _ = fetch_wb_rows(cache, fallback_code)
            by_country: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                iso3 = row.get("iso3")
                name = COUNTRY_BY_ISO3.get(iso3)
                if not name or row.get("value") is None:
                    continue
                by_country.setdefault(name, []).append(
                    {"period": str(row["year"]), "value": row["value"]}
                )
            for name, points in sorted(by_country.items()):
                if len(points) < 2:
                    continue
                items.append(make_item(
                    key=f"imf-{code.lower()}-{name.lower().replace(' ', '-')}",
                    label=f"{fallback_title} — {name}", country=name,
                    unit=fallback_unit, frequency="Annual", points=points,
                    definition=definition, guide=guide,
                    source="World Bank Open Data (IMF WEO fallback)",
                    source_url=f"https://data.worldbank.org/indicator/{fallback_code}",
                    status=fallback_status,
                ))
            status = fallback_status
            error = error + " — World Bank equivalent shown" if error else "IMF DataMapper unavailable — World Bank equivalent shown"

        sections.append(section(
            id_=f"imf-{code.lower()}",
            title=(f"IMF: {title}" if not error or "fallback" not in error else f"Global: {title} (World Bank fallback)"),
            icon="🌍",
            description=f"World Economic Outlook estimates and forecasts for {title.lower()} across {len(items)} major economies.",
            items=items,
            source="IMF DataMapper" if "fallback" not in (error or "") else "World Bank Open Data (IMF fallback)",
            source_url="https://www.imf.org/external/datamapper/api/v2",
            definition=definition, guide=guide,
            status_note=(error + " — last-known-good values shown" if error and status != "live" else None),
        ))
    return sections


# ---------------------------------------------------------------------------
# WTO merchandise trade
# ---------------------------------------------------------------------------

def build_wto_sections(cache: dict[str, Any]) -> list[dict[str, Any]]:
    sections = []
    for indicator, title in WTO_INDICATORS:
        items = []
        notes = []
        for reporter_code, reporter in WTO_REPORTERS:
            url = f"{WTO_BASE}?i={indicator}&r={reporter_code}&ps=2015-2025&max=200&fmt=json"

            def loader(url=url):
                payload = json.loads(fetch_text(url, timeout=45))
                return payload.get("Dataset", [])

            rows, status, error = with_cache(cache, f"global:wto:{indicator}:{reporter_code}", loader)
            points = []
            unit = "Million US dollar"
            for row in rows or []:
                if row.get("PartnerEconomyCode") != "000" or row.get("ProductOrSectorCode") != "TO":
                    continue
                value = to_float(row.get("Value"))
                if row.get("Year") and value is not None:
                    points.append({"period": str(row["Year"]), "value": value})
                if row.get("Unit"):
                    unit = str(row["Unit"])
            if len(points) < 2:
                if error:
                    notes.append(f"{reporter}: {error}")
                continue
            definition = (
                f"Total merchandise {'exports' if indicator.endswith('_AX') else 'imports'} "
                "to or from the world, all product groups, in current US dollars."
            )
            guide = "Use annual values for long-run trade shares and trends; the series is not seasonally adjusted."
            items.append(make_item(
                key=f"wto-{indicator.lower()}-{reporter_code}",
                label=f"{title} — {reporter}", country=reporter, unit=unit,
                frequency="Annual", points=points, definition=definition, guide=guide,
                source="WTO Timeseries", source_url="https://timeseries.wto.org/", status=status,
            ))
        sections.append(section(
            id_=f"wto-{slug(indicator)}", title=f"WTO: {title}", icon="🚢",
            description=f"Annual {title.lower()} with the world for eight major trading economies.",
            items=items, source="World Trade Organization",
            source_url="https://timeseries.wto.org/",
            definition="Total merchandise trade with the world, all product groups.",
            guide="Compare shares of world trade rather than absolute levels when economies differ in size.",
            status_note=("; ".join(notes[:3]) + " — last-known-good values shown" if notes else None),
        ))
    return sections


# ---------------------------------------------------------------------------
# World Bank multi-country indicators
# ---------------------------------------------------------------------------

def fetch_wb_rows(cache: dict[str, Any], code: str) -> tuple[list[dict[str, Any]], str, str | None]:
    """Fetch one World Bank indicator for the curated countries."""
    country_string = ";".join(c["iso3"] for c in COUNTRIES)
    params = urllib.parse.urlencode({"format": "json", "per_page": "2000", "date": "2010:2026"})
    url = f"{WB_BASE}/country/{country_string}/indicator/{code}?{params}"

    def loader():
        payload = fetch_json(url, timeout=60)
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("unexpected World Bank response")
        rows = []
        for row in payload[1]:
            if row.get("value") is None:
                continue
            rows.append({
                "iso3": row.get("countryiso3code"),
                "name": (row.get("country") or {}).get("value"),
                "year": int(row["date"]),
                "value": float(row["value"]),
            })
        return rows

    rows, status, error = with_cache(cache, f"global:wb:{code}", loader)
    normalized = []
    for row in rows or []:
        item = dict(row)
        if not item.get("iso3") and item.get("name"):
            item["iso3"] = next(
                (c["iso3"] for c in COUNTRIES if c["name"] == item["name"]), None
            )
        try:
            item["year"] = int(item["year"])
            item["value"] = float(item["value"])
        except (KeyError, TypeError, ValueError):
            continue
        normalized.append(item)
    return normalized, status, error


def build_wb_sections(cache: dict[str, Any]) -> list[dict[str, Any]]:
    sections = []
    for code, title, unit, category, definition, guide in WB_GLOBAL_INDICATORS:
        rows, status, error = fetch_wb_rows(cache, code)
        by_country: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            name = COUNTRY_BY_ISO3.get(row.get("iso3"))
            if not name:
                continue
            by_country.setdefault(name, []).append(
                {"period": str(row["year"]), "value": row["value"]}
            )
        items = []
        for name, points in sorted(by_country.items()):
            if len(points) < 2:
                continue
            items.append(make_item(
                key=f"wb-global-{slug(code)}-{slug(name)}",
                label=f"{title} — {name}", country=name, unit=unit,
                frequency="Annual", points=points, definition=definition, guide=guide,
                source="World Bank Open Data",
                source_url=f"https://data.worldbank.org/indicator/{code}",
                status=status,
            ))
        sections.append(section(
            id_=f"wb-{slug(code)}", title=f"World Bank: {title}", icon="📊",
            description=f"{title} for {len(items)} major economies, annual observations from 2010.",
            items=items, source="World Bank Open Data",
            source_url=f"https://data.worldbank.org/indicator/{code}",
            definition=definition, guide=guide,
            status_note=(error + " — last-known-good values shown" if error and status != "live"
                         else "No observations were available in this run." if not items else None),
        ))

    guide = GLOBAL_GUIDES[3]
    ppp_rows, ppp_status, ppp_error = fetch_wb_rows(cache, "PA.NUS.PPP")
    fx_rows, _, fx_error = fetch_wb_rows(cache, "PA.NUS.FCRF")
    rates = {
        (row.get("iso3"), row["year"]): row["value"]
        for row in fx_rows if row.get("value")
    }
    ratio_by_country: dict[str, list[dict[str, Any]]] = {}
    for row in ppp_rows:
        rate = rates.get((row.get("iso3"), row["year"]))
        name = COUNTRY_BY_ISO3.get(row.get("iso3"))
        if not rate or not name:
            continue
        ratio_by_country.setdefault(name, []).append(
            {"period": str(row["year"]), "value": row["value"] / rate}
        )
    ratio_items = []
    for name, points in sorted(ratio_by_country.items()):
        if len(points) < 2:
            continue
        ratio_items.append(make_item(
            key=f"wb-global-price-level-ratio-{slug(name)}",
            label=f"Price level ratio (PPP ÷ market rate) — {name}", country=name,
            unit="ratio", frequency="Annual", points=points,
            definition=guide["definition"], guide=guide["guide"],
            source="World Bank Open Data (derived)",
            source_url="https://data.worldbank.org/indicator/PA.NUS.PPP",
            status="live" if ppp_status == "live" and not fx_error else "cached",
        ))
    if ratio_items:
        sections.append(section(
            id_="wb-price-level-ratio", title="World Bank: Price level ratio", icon="🛒",
            description="PPP conversion factor divided by the official exchange rate — a broad cost-of-living proxy.",
            items=ratio_items, source="World Bank Open Data (derived)",
            source_url="https://data.worldbank.org/indicator/PA.NUS.PPP",
            definition=guide["definition"], guide=guide["guide"],
            status_note=(ppp_error + " — last-known-good values shown" if ppp_error else None),
        ))
    return sections


# ---------------------------------------------------------------------------
# World Bank Pink Sheet commodity prices
# ---------------------------------------------------------------------------

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _xlsx_rows(raw: bytes, sheet_name: str) -> list[dict[str, str]]:
    archive = zipfile.ZipFile(io.BytesIO(raw))
    shared: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iterfind(".//m:t", NS)))
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    target_sheet = None
    for sheet in workbook.find("m:sheets", NS):
        if sheet.attrib.get("name") == sheet_name:
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target_sheet = relmap[rid]
            break
    if not target_sheet:
        raise ValueError(f"sheet {sheet_name!r} not found")
    path = "xl/" + target_sheet.lstrip("/").replace("xl/", "")
    root = ET.fromstring(archive.read(path))
    rows = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        cells: dict[str, str] = {}
        for cell in row.findall("m:c", NS):
            column = "".join(ch for ch in cell.attrib.get("r", "") if ch.isalpha())
            node = cell.find("m:v", NS)
            text = "" if node is None else (node.text or "")
            cell_type = cell.attrib.get("t")
            if cell_type == "s" and text:
                text = shared[int(text)]
            elif cell_type == "inlineStr":
                text = "".join(t.text or "" for t in cell.iterfind(".//m:t", NS))
            cells[column] = text
        rows.append(cells)
    return rows


def parse_pink_sheet(raw: bytes) -> list[dict[str, Any]]:
    rows = _xlsx_rows(raw, "Monthly Prices")
    header_index = None
    for index, row in enumerate(rows[:20]):
        if any("Crude oil, average" in str(value) for value in row.values()):
            header_index = index
            break
    if header_index is None:
        raise ValueError("Pink Sheet header row not found")
    header = rows[header_index]
    units = rows[header_index + 1] if header_index + 1 < len(rows) else {}
    data_rows = [row for row in rows[header_index + 2:]
                 if re.fullmatch(r"\d{4}M\d{2}", str(row.get("A", "")).strip())]

    result = []
    for column, name in header.items():
        name = str(name).strip()
        if not name or column == "A":
            continue
        points = []
        for row in data_rows:
            value = to_float(row.get(column))
            if value is not None:
                points.append({"period": row["A"], "value": value})
        if not points:
            continue
        item = make_item(
            key=f"pink-{slug(name)}", label=name.strip("* "), country="Global",
            unit=str(units.get(column) or "$/mt").strip(), frequency="Monthly",
            points=points[-36:],
            definition=f"World Bank monthly benchmark price for {name.strip()}, in nominal US dollars.",
            guide=(
                "Monthly benchmark, not a live quote. Gold, silver and platinum are per troy ounce; "
                "crude oil per barrel; most metals and crops per metric tonne."
            ),
            source="World Bank Pink Sheet", source_url=PINK_PAGE, status="live",
        )
        result.append(item)
    return result


def build_commodity_prices(cache: dict[str, Any]) -> dict[str, Any]:
    def loader():
        page = fetch_text(PINK_PAGE, timeout=45)
        match = re.search(
            r"https://thedocs\.worldbank\.org/en/doc/[^\"'<>\s]+/related/CMO-Historical-Data-Monthly\.xlsx",
            page,
        )
        url = match.group(0) if match else PINK_FALLBACK
        cache["global:pink:url"] = {"fetched_at": now_iso(), "data": url}
        return parse_pink_sheet(fetch_bytes(url, timeout=90))

    items, status, error = with_cache(cache, "global:pink:prices", loader)
    items = items or []
    notes = None
    if error and status != "live":
        notes = error + " — last-known-good monthly prices shown"
    return {
        "id": "commodity-prices", "title": "Official monthly commodity prices",
        "source": "World Bank Pink Sheet", "source_url": PINK_PAGE,
        "definition": GLOBAL_GUIDES[9]["definition"], "guide": GLOBAL_GUIDES[9]["guide"],
        "status": status, "status_note": notes,
        "items": items,
        "headline_ids": [f"pink-{slug(name)}" for name in (
            "Crude oil, Brent", "Natural gas, Europe", "Gold", "Silver", "Copper",
            "Aluminum", "Zinc", "Nickel", "Iron ore, cfr spot", "Wheat, US SRW",
            "Maize", "Soybeans", "Coffee, Arabica", "Sugar, world",
        )],
    }


# ---------------------------------------------------------------------------
# Market reference snapshots (secondary source, clearly labelled)
# ---------------------------------------------------------------------------

def _yahoo_quote(symbol: str) -> dict[str, Any]:
    url = f"{YAHOO_BASE}/{urllib.parse.quote(symbol, safe='')}?range=5d&interval=1d"
    payload = fetch_json(url, timeout=30)
    results = (payload.get("chart") or {}).get("result") or []
    if not results:
        raise ValueError("no quote returned")
    result = results[0]
    meta = result.get("meta") or {}
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [v for v in (quote.get("close") or []) if isinstance(v, (int, float))]
    price = to_float(meta.get("regularMarketPrice"))
    if price is None and closes:
        price = float(closes[-1])
    previous = to_float(meta.get("chartPreviousClose"))
    change = (price / previous - 1) * 100 if price is not None and previous else None
    timestamp = meta.get("regularMarketTime")
    as_of = None
    if isinstance(timestamp, (int, float)):
        as_of = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "price": price, "change_pct": round(change, 2) if change is not None else None,
        "as_of": as_of, "closes": closes,
        "name": meta.get("shortName") or meta.get("longName") or symbol,
        "currency": meta.get("currency"),
    }


def build_market_snapshots(cache: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, tuple[Any, str, str | None]] = {}

    def load(symbol: str):
        return with_cache(cache, f"global:market:{symbol}", lambda: _yahoo_quote(symbol))

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(load, symbol): symbol for symbol, _, _, _, _ in MARKETS}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    groups: dict[str, list[dict[str, Any]]] = {}
    notes = []
    for symbol, label, category, unit, exchange in MARKETS:
        quote, status, error = results.get(symbol, (None, "unavailable", "not fetched"))
        if error and status != "live":
            notes.append(f"{symbol}: {error}")
        quote = quote or {}
        closes = quote.get("closes") or []
        points = [{"period": str(i), "value": v} for i, v in enumerate(closes)]
        groups.setdefault(category, []).append({
            "key": f"market-{slug(symbol)}", "symbol": symbol, "label": label,
            "exchange": exchange, "unit": unit, "currency": quote.get("currency"),
            "value": quote.get("price"), "change_pct": quote.get("change_pct"),
            "as_of": quote.get("as_of"), "status": status,
            "provider_name": quote.get("name"), "points": points[-10:],
            "definition": f"Delayed market reference quote for {label} ({exchange}).",
            "guide": "Secondary market data for context only. Not an official statistic; use the exchange for publication-grade values.",
            "source": "Yahoo Finance (secondary market data)",
            "source_url": "https://finance.yahoo.com/",
        })

    ordered = [
        {"id": slug(name), "title": name, "items": items}
        for name, items in groups.items()
    ]
    statuses = {item["status"] for items in groups.values() for item in items}
    status = "live" if "live" in statuses else "cached" if "cached" in statuses else "unavailable"
    return {
        "source": "Yahoo Finance (secondary market data)",
        "source_url": "https://finance.yahoo.com/",
        "status": status,
        "definition": GLOBAL_GUIDES[11]["definition"],
        "guide": GLOBAL_GUIDES[11]["guide"],
        "status_note": ("; ".join(notes[:3]) + " — last-known-good quotes shown" if notes else None),
        "groups": ordered,
    }


# ---------------------------------------------------------------------------
# Derived global KPIs
# ---------------------------------------------------------------------------

def _latest(items: list[dict[str, Any]], key: str) -> float | None:
    for item in items:
        if item.get("key") == key:
            return item.get("latest_value")
    return None


def _values(items: list[dict[str, Any]]) -> list[float]:
    return [float(i["latest_value"]) for i in items if i.get("latest_value") is not None]


def _kpi(id_: str, name: str, sector: str, value: float | None, unit: str,
         formula: str, definition: str, guide: str, sources: list[str],
         period: str | None = None, status: str = "Context") -> dict[str, Any]:
    return {
        "id": id_, "name": name, "sector": sector,
        "value": round(value, 2) if isinstance(value, (int, float)) else None,
        "unit": unit, "formula": formula, "definition": definition, "guide": guide,
        "sources": sources, "latest_year": period, "latest_period": period,
        "status": status, "frequency": "Latest available",
    }


def derive_global_kpis(sections: list[dict[str, Any]], commodities: dict[str, Any],
                       market: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {s["id"]: s for s in sections}
    policy = by_id.get("policy-rates", {}).get("items", [])
    dsr = by_id.get("debt-service", {}).get("items", [])
    imf_growth = by_id.get("imf-ngdp_rpch", {}).get("items", [])
    imf_debt = by_id.get("imf-ggxwdg_ngdp", {}).get("items", [])
    wb_items = [item for s in sections if s["id"].startswith("wb-") for item in s["items"]]
    wto_exports = by_id.get("wto-its-mtv-ax", {}).get("items", [])

    def wb(code: str) -> list[dict[str, Any]]:
        return [i for i in wb_items if i["key"].startswith(f"wb-global-{slug(code)}-")]

    kpis: list[dict[str, Any]] = []
    rates = _values(policy)
    if rates:
        kpis.append(_kpi(
            "global-policy-rate-spread", "Policy rate spread across major economies", "monetary",
            max(rates) - min(rates), "percentage points",
            "maximum policy rate − minimum policy rate (latest observation per country)",
            "How widely monetary policy settings differ across the curated economies.",
            "A wide spread can drive capital flows and currency moves. Read it with inflation and FX tables.",
            ["BIS WS_CBPOL"],
        ))

    household_dsr = [i for i in dsr if "households" in i.get("label", "")]
    values = _values(household_dsr)
    if values:
        kpis.append(_kpi(
            "global-household-debt-burden", "Average household debt-service burden", "debt",
            sum(values) / len(values), "% of income",
            "mean of latest household debt-service ratios across available countries",
            "Average share of household income committed to interest and principal payments.",
            "Falling rates reduce this burden only if incomes and loan balances also cooperate.",
            ["BIS WS_DSR"], status="Watch" if sum(values) / len(values) > 8 else "Context",
        ))

    commodity_items = commodities.get("items", [])
    energy_keys = [f"pink-{slug(n)}" for n in ("Crude oil, Brent", "Natural gas, Europe")]
    metal_keys = [f"pink-{slug(n)}" for n in ("Copper", "Aluminum", "Zinc", "Nickel", "Gold", "Silver")]
    changes = [
        item["change_pct"] for item in commodity_items
        if item.get("change_pct") is not None and item["key"] in energy_keys + metal_keys
    ]
    if changes:
        kpis.append(_kpi(
            "commodity-momentum", "Energy and metals price momentum", "commodities",
            sum(changes) / len(changes), "% month-on-month",
            "mean month-on-month change of Brent, European gas, copper, aluminium, zinc, nickel, gold and silver",
            "Short-run direction of benchmark commodity prices.",
            "A single monthly move is noisy. Compare it with a longer trend before drawing conclusions.",
            ["World Bank Pink Sheet"],
        ))

    gold = _latest(commodity_items, f"pink-{slug('Gold')}")
    silver = _latest(commodity_items, f"pink-{slug('Silver')}")
    if gold and silver:
        kpis.append(_kpi(
            "gold-silver-ratio", "Gold / silver price ratio", "commodities",
            gold / silver, "ounces of silver per ounce of gold",
            "gold price per troy oz ÷ silver price per troy oz",
            "How many ounces of silver one ounce of gold buys.",
            "A high ratio often means investors favour the safe-haven metal over the industrial one.",
            ["World Bank Pink Sheet"],
        ))

    copper = _latest(commodity_items, f"pink-{slug('Copper')}")
    if copper and gold:
        kpis.append(_kpi(
            "copper-gold-ratio", "Copper / gold ratio", "commodities",
            copper / gold, "tonnes of copper per ounce of gold (×1,000)",
            "copper price per tonne ÷ gold price per troy oz (scaled ×1,000)",
            "A broad industrial-demand versus risk-aversion signal.",
            "Rising values tend to accompany stronger industrial demand; falling values often accompany stress.",
            ["World Bank Pink Sheet"],
        ))

    growth_values = _values(imf_growth)
    debt_values = _values(imf_debt)
    if growth_values and debt_values:
        kpis.append(_kpi(
            "global-debt-growth-gap", "Debt-to-growth gap", "treasury",
            sum(debt_values) / len(debt_values) - sum(growth_values) / len(growth_values),
            "percentage points", "mean government debt % GDP − mean real GDP growth %",
            "The gap between the average debt burden and the average growth rate in major economies.",
            "When debt grows faster than the economy, the ratio rises unless primary balances improve.",
            ["IMF WEO"],
        ))

    capital = _values(wb("FB.BNK.CAPA.ZS"))
    npl = _values(wb("FB.AST.NPER.ZS"))
    if capital and npl:
        kpis.append(_kpi(
            "bank-cushion-gap", "Bank capital cushion above NPLs", "banking",
            sum(capital) / len(capital) - sum(npl) / len(npl), "percentage points",
            "mean bank capital / assets − mean non-performing loans / total loans",
            "Difference between the average capital buffer and the average share of distressed loans.",
            "A narrowing gap means less room to absorb credit losses.",
            ["World Bank Open Data"],
        ))

    life = _values(wb("GFDD.DI.09"))
    nonlife = _values(wb("GFDD.DI.10"))
    if life and nonlife:
        kpis.append(_kpi(
            "insurance-mix-gap", "Life versus non-life insurance depth", "insurance",
            sum(life) / len(life) - sum(nonlife) / len(nonlife), "% of GDP",
            "mean life premium volume / GDP − mean non-life premium volume / GDP",
            "How much deeper life insurance markets are than non-life markets on average.",
            "Positive values mean life insurance is more prominent; this varies with pension systems.",
            ["World Bank GFDD"],
        ))

    pay = _values(wb("JI.WAG.GNDR"))
    if pay:
        kpis.append(_kpi(
            "global-pay-parity", "Average female-to-male wage ratio", "labour",
            sum(pay) / len(pay), "ratio",
            "mean of latest female-to-male wage ratios across available countries",
            "A summary of pay parity across the curated economies.",
            "1.0 means parity. This is an unweighted average and ignores differences in coverage.",
            ["World Bank Open Data"], status="Watch",
        ))

    cap_gdp = _values(wb("CM.MKT.LCAP.GD.ZS"))
    if cap_gdp:
        kpis.append(_kpi(
            "global-equity-depth", "Average equity market depth", "equity_markets",
            sum(cap_gdp) / len(cap_gdp), "% of GDP",
            "mean market capitalisation of listed domestic companies / GDP",
            "Average size of listed equity markets relative to economic output.",
            "This rises with valuations as well as with the number of listed companies.",
            ["World Bank Open Data"],
        ))

    price_levels = [i["latest_value"] for i in wb_items
                    if i["key"].startswith("wb-global-price-level-ratio-")
                    and i.get("latest_value") is not None]
    if price_levels:
        kpis.append(_kpi(
            "cost-of-living-spread", "Cost-of-living proxy spread", "prices",
            max(price_levels) / min(price_levels) if min(price_levels) else None, "×",
            "highest PPP price-level ratio ÷ lowest ratio across curated countries",
            "How much cheaper the least expensive market is than the most expensive one in the curated set.",
            "This is a country-level proxy; city rents and taxes can differ much more.",
            ["World Bank Open Data"],
        ))

    exports = _values(wto_exports)
    if exports:
        top = max(exports)
        share = top / sum(exports) * 100 if sum(exports) else None
        kpis.append(_kpi(
            "trade-share-top-exporter", "Largest exporter's share of curated trade", "trade",
            share, "%",
            "latest merchandise export value ÷ sum of curated exporters × 100",
            "How concentrated merchandise exports are within this curated group.",
            "This is a share of the selected group, not of world trade.",
            ["WTO Timeseries"],
        ))

    market_items = [item for group in market.get("groups", []) for item in group["items"]]
    index_items = [i for i in market_items if i.get("key", "").startswith("market-")]
    equity_symbols = {slug(s) for s, _, category, _, _ in MARKETS if category == "Equity indices"}
    changes = [i["change_pct"] for i in index_items
               if i.get("change_pct") is not None and slug(i.get("symbol", "")) in equity_symbols]
    if changes:
        positive = sum(1 for c in changes if c >= 0)
        kpis.append(_kpi(
            "equity-market-breadth", "Equity index breadth", "equity_markets",
            positive / len(changes) * 100, "% of indices higher",
            "share of major indices with a non-negative market change",
            "How broad the recent move is across major equity markets.",
            "Secondary, possibly delayed market quotes. Use as context, not as an official indicator.",
            ["Yahoo Finance (secondary)"],
        ))

    return kpis


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_global_data(cache: dict[str, Any]) -> dict[str, Any]:
    """Build all global sections. ``cache`` is the shared enrichment cache."""
    print("[global] Fetching ECB, BIS, IMF, WTO, World Bank and market feeds…")
    sections: list[dict[str, Any]] = [build_ecb_section(cache)]
    for config in BIS_FLOWS:
        sections.append(build_bis_section(config, cache))
    sections.extend(build_imf_sections(cache))
    sections.extend(build_wto_sections(cache))
    sections.extend(build_wb_sections(cache))
    commodities = build_commodity_prices(cache)
    market = build_market_snapshots(cache)
    kpis = derive_global_kpis(sections, commodities, market)
    counts = {
        "sections": len(sections) + 1,
        "series": sum(len(s["items"]) for s in sections) + len(commodities["items"]),
        "market_quotes": sum(len(g["items"]) for g in market["groups"]),
        "derived_kpis": len(kpis),
        "guides": len(GLOBAL_GUIDES),
    }
    print(f"[global] {counts['series']} series/quotes | {len(kpis)} derived KPIs | "
          f"{counts['market_quotes']} delayed market quotes")
    return {
        "generated_at": now_iso(),
        "methodology": (
            "Official-first curated feeds. ECB, BIS, IMF, WTO and World Bank values are "
            "published by those institutions. Yahoo Finance quotes are secondary, delayed "
            "market references clearly labelled as such. Derived KPIs are calculated here."
        ),
        "sections": sections,
        "commodities": commodities,
        "market": market,
        "kpis": kpis,
        "guides": GLOBAL_GUIDES,
        "counts": counts,
    }
