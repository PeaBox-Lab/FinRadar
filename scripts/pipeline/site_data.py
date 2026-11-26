"""
Radar — Site Content Data
============================
Single source of truth for the multi-page site: categories (sectors),
facts, and historical trends drawn from public government APIs
(data.gov.in, apisetu.gov.in, World Bank, RBI, NPCI, MoSPI, IMF, FRED).
"""

# ---------------------------------------------------------------------------
# SECTORS / PAGES
# ---------------------------------------------------------------------------

SECTORS = [
    {"id": "central", "title": "Central Government", "icon": "🏛️",
     "description": "All-India macro data from the Union Government: GDP, inflation, fiscal deficit, monetary policy, forex reserves, trade balance."},
    {"id": "states", "title": "State Level", "icon": "🗺️",
     "description": "State-wise data: GST collections, state debt, state CPI, power demand, agri production, literacy, health and roads."},
    {"id": "financials", "title": "Financials", "icon": "🏦",
     "description": "Banking, credit, insurance, pensions, NBFCs, capital markets and fiscal sustainability."},
    {"id": "geo", "title": "Geo Levels", "icon": "📍",
     "description": "Geographic and district-level data: population density, urbanisation, boundaries, land use, climate zones."},
    {"id": "transport", "title": "Transport", "icon": "🚗",
     "description": "Roads, railways, aviation, shipping, vehicles, FASTag, UPI mobility and logistics."},
    {"id": "economy", "title": "Economy", "icon": "💰",
     "description": "GDP, inflation, trade flows, PPP and global comparisons."},
    {"id": "agriculture", "title": "Agriculture", "icon": "🌾",
     "description": "Crop production, fertiliser, irrigation, MSP and farmer welfare."},
    {"id": "energy", "title": "Energy & Power", "icon": "⚡",
     "description": "Electricity demand, renewables, fossil-fuel dependency and grid data."},
    {"id": "health", "title": "Health", "icon": "🏥",
     "description": "Hospital capacity, immunisation, healthcare finance and disease surveillance."},
    {"id": "education", "title": "Education", "icon": "📚",
     "description": "Literacy, enrolment, teacher-pupil ratios and learning outcomes."},
    {"id": "welfare", "title": "Welfare & Employment", "icon": "🤝",
     "description": "Food security, MGNREGA, social protection and employment."},
    {"id": "environment", "title": "Environment & Climate", "icon": "🌍",
     "description": "Emissions, renewable share, air and water quality."},
    {"id": "commerce", "title": "Trade & Commerce", "icon": "🛒",
     "description": "Exports, imports, GST collections, trade balance and digital payments."},
    {"id": "housing", "title": "Housing & Urban", "icon": "🏠",
     "description": "Urbanisation, housing costs, municipal finance and smart cities."},
]

SECTOR_MAP = {s["id"]: s for s in SECTORS}

# ---------------------------------------------------------------------------
# CATEGORY GROUPS — used for the top-level index page and segregated nav
# ---------------------------------------------------------------------------
CATEGORY_GROUPS = [
    # Macro & National Accounts
    {
        "group": "Macro & National Accounts",
        "icon": "🏛️",
        "categories": ["central", "economy", "financials"],
        "description": "India's top-level economic indicators, fiscal metrics and financial system health.",
    },
    # Sector Categories
    {
        "group": "Sector Categories",
        "icon": "🌾",
        "categories": ["agriculture", "energy", "transport", "commerce"],
        "description": "Production, infrastructure and commerce across key productive sectors.",
    },
    # Geographic & Sub-national
    {
        "group": "Geographic & Sub-national",
        "icon": "📍",
        "categories": ["geo", "states"],
        "description": "Region-level data, district metrics and state-wise performance.",
    },
    # Social Services
    {
        "group": "Social Services",
        "icon": "🏥",
        "categories": ["health", "education", "welfare"],
        "description": "Healthcare access, education outcomes and social protection programmes.",
    },
    # Environment & Urban
    {
        "group": "Environment & Urban",
        "icon": "🌍",
        "categories": ["environment", "housing"],
        "description": "Climate metrics, urban development and housing markets.",
    },
]


# ---------------------------------------------------------------------------
# FACTS — straight, defensible numbers across sources
# ---------------------------------------------------------------------------

FACTS = [
    {"id": "f1", "kpi_id": "real_inflation_rate", "category": "economy",
     "source": "World Bank / MoSPI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Inflation is the annual percentage change in the Consumer Price Index.",
     "why_it_matters": "It determines whether incomes keep up with prices and whether the RBI can hold rates steady."},
    {"id": "f2", "kpi_id": "gdp_growth_pct", "category": "economy",
     "source": "World Bank / MoSPI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "GDP growth is the annual percentage change in real (inflation-adjusted) GDP.",
     "why_it_matters": "Strong growth lifts incomes, but it also puts pressure on the fiscal deficit and climate targets."},
    {"id": "f3", "kpi_id": "gdp_per_capita_usd", "category": "economy",
     "source": "World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "GDP per capita = GDP ÷ population, in current US$.",
     "why_it_matters": "Per-capita values are the standard lens for welfare comparisons between countries."},
    {"id": "f4", "kpi_id": "ppp_gap_usd", "category": "economy",
     "source": "World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "PPP gap = nominal GDP per capita − PPP-adjusted GDP per capita.",
     "why_it_matters": "Explains why cross-country salary comparisons need PPP conversion, not nominal exchange rates."},
    {"id": "f5", "kpi_id": "real_interest_rate", "category": "finance",
     "source": "RBI / World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Real rate = nominal rate − inflation.",
     "why_it_matters": "Positive real rates mean bank deposits actually grow in purchasing power."},
    {"id": "f6", "kpi_id": "import_cover_ratio", "category": "finance",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Import cover = forex reserves ÷ (annual imports ÷ 12).",
     "why_it_matters": "Measures how long India can sustain imports if exports freeze."},
    {"id": "f7", "kpi_id": "bank_credit_deposit_ratio", "category": "finance",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Credit-to-deposit ratio = total bank credit ÷ total deposits × 100.",
     "why_it_matters": "A high ratio signals a credit-hungry, expansionary economy."},
    {"id": "f8", "kpi_id": "hospital_bed_density", "category": "health",
     "source": "MoSPI / WHO",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Bed density = total hospital beds ÷ population × 1,000.",
     "why_it_matters": "Low density signals pressure on critical-care capacity during outbreaks."},
    {"id": "f9", "kpi_id": "immunization_coverage_pct", "category": "health",
     "source": "MoSPI / NFHS",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Immunisation coverage = fully immunised children ÷ total children × 100.",
     "why_it_matters": "Below 90% creates pockets of vulnerability to vaccine-preventable diseases."},
    {"id": "f10", "kpi_id": "mgnrega_person_days", "category": "welfare",
     "source": "MGNREGA MIS",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Person-days = total days of wage employment generated.",
     "why_it_matters": "High demand for wage work can signal weakened private rural employment."},
    {"id": "f11", "kpi_id": "renewable_capacity_share_pct", "category": "environment",
     "source": "MNRE",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Renewable share = renewable installed capacity ÷ total installed capacity × 100.",
     "why_it_matters": "The energy-transition speed directly affects long-run import dependence."},
    {"id": "f12", "kpi_id": "digital_consumption_velocity", "category": "transport",
     "source": "NPCI / GST",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Ticket size = total UPI value ÷ total UPI volume.",
     "why_it_matters": "Rising ticket size means bigger-ticket digital transactions — formalisation of consumption."},
]

FACTS_BY_CATEGORY = {}
for _f in FACTS:
    FACTS_BY_CATEGORY.setdefault(_f["category"], []).append(_f)

# ---------------------------------------------------------------------------
# EXTENDED FACTS — mapped to the new taxonomy (central, states, financials, geo, transport)
# ---------------------------------------------------------------------------

EXTENDED_FACTS = [
    # CENTRAL GOVERNMENT LEVEL
    {"id": "c1", "kpi_id": "real_inflation_rate", "category": "central",
     "source": "World Bank / MoSPI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Annual % change in Consumer Price Index.",
     "why_it_matters": "Sets the anchor for RBI rate decisions and household real-income growth."},
    {"id": "c2", "kpi_id": "gdp_growth_pct", "category": "central",
     "source": "World Bank / MoSPI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Annual % change in real GDP.",
     "why_it_matters": "Strong growth lifts incomes, but it also puts pressure on the fiscal deficit and climate targets."},
    {"id": "c3", "kpi_id": "import_cover_ratio", "category": "central",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Import cover = forex reserves ÷ (annual imports ÷ 12).",
     "why_it_matters": "Measures how long India can sustain imports if exports freeze."},
    {"id": "c4", "kpi_id": "fiscal_deficit_pct_gdp", "category": "central",
     "source": "RBI / Union Budget",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Fiscal deficit = total borrowing ÷ GDP × 100.",
     "why_it_matters": "Above 6% is typically inflationary and crowds out private investment."},
    {"id": "c5", "kpi_id": "current_account_pct_gdp", "category": "central",
     "source": "World Bank / IMF",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Current account balance = trade + net transfers ÷ GDP × 100.",
     "why_it_matters": "A widening CAD signals dependence on foreign capital to fund imports."},

    # STATE LEVEL
    {"id": "s1", "kpi_id": "gst_growth_pct", "category": "states",
     "source": "GST Portal / MoF",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "YoY growth in state GST collections.",
     "why_it_matters": "State GST is the biggest own-revenue source for states; divergence signals fiscal stress."},
    {"id": "s2", "kpi_id": "state_inflation_spread", "category": "states",
     "source": "MoSPI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "State CPI minus national CPI in percentage points.",
     "why_it_matters": "National average hides huge cost-of-living gaps — policy must be state-specific."},
    {"id": "s3", "kpi_id": "state_debt_to_gsdp", "category": "states",
     "source": "RBI State Finances",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "State outstanding liabilities ÷ Gross State Domestic Product × 100.",
     "why_it_matters": "High debt-to-GSDP limits capex and risks central bailout pressures."},
    {"id": "s4", "kpi_id": "power_demand_growth_pct", "category": "states",
     "source": "CEA / POSOCO",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "YoY % change in electricity consumption by state.",
     "why_it_matters": "Real-time proxy for industrial activity at the state level."},
    {"id": "s5", "kpi_id": "state_literacy_rate", "category": "states",
     "source": "Census / NFHS",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Literate population (7+) ÷ total population (7+) × 100.",
     "why_it_matters": "Human-capital divergence drives long-run income gaps across states."},

    # FINANCIALS
    {"id": "fn1", "kpi_id": "real_interest_rate", "category": "financials",
     "source": "RBI / World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Real rate = nominal rate − inflation.",
     "why_it_matters": "Positive real rates mean bank deposits actually grow in purchasing power."},
    {"id": "fn2", "kpi_id": "bank_credit_deposit_ratio", "category": "financials",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Credit-to-deposit = total bank credit ÷ total deposits × 100.",
     "why_it_matters": "A high ratio signals a credit-hungry, expansionary economy."},
    {"id": "fn3", "kpi_id": "gnpa_ratio_pct", "category": "financials",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Gross NPA ÷ gross advances × 100.",
     "why_it_matters": "Lower NPAs free up bank capital for fresh lending."},
    {"id": "fn4", "kpi_id": "msme_credit_penetration_pct", "category": "financials",
     "source": "RBI / MSME Ministry",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Outstanding MSME credit ÷ estimated MSME GDP × 100.",
     "why_it_matters": "The credit gap is a binding constraint on small-firm growth."},
    {"id": "fn5", "kpi_id": "priority_sector_lending_pct", "category": "financials",
     "source": "RBI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "PSL advances ÷ total bank credit × 100.",
     "why_it_matters": "Ensures credit flows to agriculture, MSMEs and low-income housing."},

    # GEO LEVELS
    {"id": "g1", "kpi_id": "population_density", "category": "geo",
     "source": "Census 2011 / World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Population ÷ geographical area (people per sq km).",
     "why_it_matters": "Density drives infrastructure cost, service delivery and climate vulnerability."},
    {"id": "g2", "kpi_id": "urbanisation_rate_pct", "category": "geo",
     "source": "Census / World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Urban population ÷ total population × 100.",
     "why_it_matters": "Urbanisation level determines demand for housing, transport and municipal services."},
    {"id": "g3", "kpi_id": "road_density", "category": "geo",
     "source": "MoRTH",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total road length ÷ geographical area.",
     "why_it_matters": "Low density means higher logistics costs and weaker market access."},
    {"id": "g4", "kpi_id": "district_gdp_per_capita", "category": "geo",
     "source": "MoSPI / State Directorates",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "District GDP ÷ district population.",
     "why_it_matters": "Intra-state inequality is often larger than inter-state inequality."},
    {"id": "g5", "kpi_id": "agri_land_holding", "category": "geo",
     "source": "Agriculture Census",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total operated area ÷ number of operational holdings.",
     "why_it_matters": "Small holdings limit mechanisation and scale economies in farming."},

    # TRANSPORT
    {"id": "t1", "kpi_id": "digital_consumption_velocity", "category": "transport",
     "source": "NPCI / GST",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Ticket size = total UPI value ÷ total UPI volume.",
     "why_it_matters": "Rising ticket size means bigger-ticket digital transactions — formalisation."},
    {"id": "t2", "kpi_id": "fastag_volume", "category": "transport",
     "source": "NHAI / NPCI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Monthly FASTag transactions (millions).",
     "why_it_matters": "Digital tolling cuts leakage and enables real-time traffic analytics."},
    {"id": "t3", "kpi_id": "vehicle_density", "category": "transport",
     "source": "MoRTH",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Registered vehicles ÷ population × 1,000.",
     "why_it_matters": "High density signals mobility but also congestion and pollution pressure."},
    {"id": "t4", "kpi_id": "railway_freight_growth", "category": "transport",
     "source": "Indian Railways",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "YoY % change in freight tonnage (million tonnes).",
     "why_it_matters": "The rail freight share is rising — key for logistics cost."},
    {"id": "t5", "kpi_id": "aviation_passenger_growth", "category": "transport",
     "source": "DGCA / MoCA",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Annual domestic passengers (millions).",
     "why_it_matters": "Air travel is a leading indicator of business travel and premium consumption."},

    # ECONOMY (supplementary)
    {"id": "e1", "kpi_id": "gdp_per_capita_usd", "category": "economy",
     "source": "World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "GDP per capita = GDP ÷ population, in current US$.",
     "why_it_matters": "Per-capita values are the standard lens for welfare comparisons between countries."},
    {"id": "e2", "kpi_id": "ppp_gap_usd", "category": "economy",
     "source": "World Bank",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "PPP gap = nominal GDP per capita − PPP-adjusted GDP per capita.",
     "why_it_matters": "Explains why cross-country salary comparisons need PPP conversion."},

    # AGRICULTURE
    {"id": "a1", "kpi_id": "foodgrain_growth_pct", "category": "agriculture",
     "source": "MoAFW",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "YoY % change in total foodgrain output.",
     "why_it_matters": "Food output growth anchors food inflation and rural incomes."},
    {"id": "a2", "kpi_id": "fertilizer_intensity", "category": "agriculture",
     "source": "MoAFW / FAI",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Fertiliser consumption ÷ net sown area.",
     "why_it_matters": "Overuse degrades soil, pollutes water and raises input costs."},

    # ENERGY
    {"id": "en1", "kpi_id": "renewable_capacity_share_pct", "category": "energy",
     "source": "MNRE",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Renewable installed capacity ÷ total installed capacity × 100.",
     "why_it_matters": "Energy-transition speed directly affects long-run import dependence."},

    # HEALTH
    {"id": "h1", "kpi_id": "hospital_bed_density", "category": "health",
     "source": "MoSPI / WHO",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total hospital beds ÷ population × 1,000.",
     "why_it_matters": "Low density signals pressure on critical-care capacity during outbreaks."},

    # EDUCATION
    {"id": "ed1", "kpi_id": "pupil_teacher_ratio", "category": "education",
     "source": "UDISE / MoE",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total enrolled students ÷ total teachers.",
     "why_it_matters": "Higher ratios correlate with lower learning outcomes."},

    # WELFARE
    {"id": "w1", "kpi_id": "mgnrega_person_days", "category": "welfare",
     "source": "MGNREGA MIS",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total days of wage employment generated.",
     "why_it_matters": "High demand at wage rates signals weakened private rural employment."},

    # ENVIRONMENT
    {"id": "ev1", "kpi_id": "per_capita_co2_emissions", "category": "environment",
     "source": "World Bank / Global Carbon Project",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Total CO₂ emissions ÷ population.",
     "why_it_matters": "Low per-capita emissions is a key equity argument in climate negotiations."},

    # COMMERCE
    {"id": "cm1", "kpi_id": "fdi_inflows_pct_gdp", "category": "commerce",
     "source": "World Bank / DIPP",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "FDI inflows ÷ GDP × 100.",
     "why_it_matters": "FDI brings capital, technology and export linkages."},

    # HOUSING
    {"id": "hs1", "kpi_id": "housing_price_to_income", "category": "housing",
     "source": "RBI / NHB",
     "fact": "Current published values are rendered from the source dataset.",
     "scale": "Median house price ÷ median annual household income.",
     "why_it_matters": "Above 5× means housing is severely unaffordable for median earners."},
]

# Merge FACTS with EXTENDED_FACTS (Extended replaces original where ID conflicts)
ALL_FACTS = {f["id"]: f for f in EXTENDED_FACTS}
ALL_FACTS_LIST = list(ALL_FACTS.values())

FACTS = ALL_FACTS_LIST
FACTS_BY_CATEGORY = {}
for _f in FACTS:
    FACTS_BY_CATEGORY.setdefault(_f["category"], []).append(_f)


# ---------------------------------------------------------------------------
# HISTORICAL TRENDS — published reference series per KPI
# ---------------------------------------------------------------------------

HISTORICAL_TRENDS = {
    "real_inflation_rate": {
        "label": "Headline CPI Inflation (%)",
        "source": "MoSPI / World Bank",
        "unit": "%",
        "points": [
            {"year": 2015, "value": 5.40}, {"year": 2016, "value": 3.70},
            {"year": 2017, "value": 3.60}, {"year": 2018, "value": 4.10},
            {"year": 2019, "value": 3.20}, {"year": 2020, "value": 4.80},
            {"year": 2021, "value": 5.90}, {"year": 2022, "value": 6.50},
            {"year": 2023, "value": 5.20}, {"year": 2024, "value": 2.40},
            {"year": 2025, "value": 2.40},
        ],
    },
    "gdp_growth_pct": {
        "label": "Real GDP Growth (%)",
        "source": "World Bank / MoSPI",
        "unit": "%",
        "points": [
            {"year": 2015, "value": 7.90}, {"year": 2016, "value": 8.20},
            {"year": 2017, "value": 7.70}, {"year": 2018, "value": 7.20},
            {"year": 2019, "value": 6.10}, {"year": 2020, "value": -6.60},
            {"year": 2021, "value": 8.70}, {"year": 2022, "value": 7.80},
            {"year": 2023, "value": 7.20}, {"year": 2024, "value": 7.00},
            {"year": 2025, "value": 7.57},
        ],
    },
    "digital_consumption_velocity": {
        "label": "Avg UPI Ticket Size (USD/tx)",
        "source": "NPCI / GST",
        "unit": "USD/tx",
        "points": [
            {"year": 2020, "value": 0.90}, {"year": 2021, "value": 1.05},
            {"year": 2022, "value": 1.35}, {"year": 2023, "value": 1.42},
            {"year": 2024, "value": 1.38}, {"year": 2025, "value": 1.40},
        ],
    },
    "import_cover_ratio": {
        "label": "Import Cover Ratio (months)",
        "source": "RBI",
        "unit": "months",
        "points": [
            {"year": 2019, "value": 18.2}, {"year": 2020, "value": 20.1},
            {"year": 2021, "value": 18.4}, {"year": 2022, "value": 15.8},
            {"year": 2023, "value": 16.2}, {"year": 2024, "value": 15.9},
            {"year": 2025, "value": 16.39},
        ],
    },
    "gst_growth_pct": {
        "label": "GST Collections Growth (%)",
        "source": "GST Portal",
        "unit": "%",
        "points": [
            {"year": 2019, "value": 9.5}, {"year": 2020, "value": 4.5},
            {"year": 2021, "value": 10.2}, {"year": 2022, "value": 14.2},
            {"year": 2023, "value": 11.0}, {"year": 2024, "value": 11.7},
        ],
    },
    "mgnrega_person_days": {
        "label": "MGNREGA Person-Days (crore)",
        "source": "MGNREGA MIS",
        "unit": "crore",
        "points": [
            {"year": 2020, "value": 80.2}, {"year": 2021, "value": 120.4},
            {"year": 2022, "value": 158.3}, {"year": 2023, "value": 212.6},
            {"year": 2024, "value": 245.3}, {"year": 2025, "value": 235.0},
        ],
    },
    "renewable_capacity_share_pct": {
        "label": "Renewable Capacity Share (%)",
        "source": "MNRE",
        "unit": "%",
        "points": [
            {"year": 2017, "value": 32.2}, {"year": 2018, "value": 34.9},
            {"year": 2019, "value": 36.6}, {"year": 2020, "value": 38.8},
            {"year": 2021, "value": 40.5}, {"year": 2022, "value": 42.5},
            {"year": 2023, "value": 44.3}, {"year": 2024, "value": 46.1},
        ],
    },
    "gnpa_ratio_pct": {
        "label": "Gross NPA Ratio (%)",
        "source": "RBI",
        "unit": "%",
        "points": [
            {"year": 2017, "value": 1.40}, {"year": 2018, "value": 2.10},
            {"year": 2019, "value": 2.90}, {"year": 2020, "value": 3.50},
            {"year": 2021, "value": 5.80}, {"year": 2022, "value": 5.30},
            {"year": 2023, "value": 3.90}, {"year": 2024, "value": 2.80},
            {"year": 2025, "value": 2.80},
        ],
    },
}


def get_trend(kpi_id):
    return HISTORICAL_TRENDS.get(kpi_id)


def trends_by_category():
    result = {}
    for kpi_id, t in HISTORICAL_TRENDS.items():
        cat = None
        for f in FACTS:
            if f["kpi_id"] == kpi_id:
                cat = f["category"]
                break
        if cat:
            result.setdefault(cat, []).append((kpi_id, t))
    return result


def fact_text(fact: dict, latest: dict | None = None) -> str:
    """Return a current, sourced statement for a fact card.

    The static ``fact`` field is only a neutral definition. The displayed
    sentence is built from the current KPI payload so no stale or generated
    number can be published in prose.
    """
    kpi_id = fact.get("kpi_id", "")
    item = next((k for k in (latest or {}).get("kpis", [])
                 if k.get("kpi_id") == kpi_id), None)
    if item and item.get("value") is not None:
        value = item["value"]
        shown = f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, (int, float)) else str(value)
        unit = str(item.get("unit") or "").strip()
        insight = str(item.get("insight_text") or "").strip()
        sentence = f"Latest published value: {shown}{(' ' + unit) if unit else ''}."
        return f"{sentence} {insight}".strip()
    reason = ""
    if item and item.get("source_type") == "unavailable":
        reason = "No authenticated latest value is published in this build for this metric."
    else:
        reason = "No authenticated latest value is available for this metric in this build."
    return f"{reason} {fact.get('why_it_matters', '')}".strip()


def search_index(latest: dict | None = None):
    """Return all searchable content (facts) for the search page."""
    items = []
    for f in FACTS:
        items.append({
            "type": "fact",
            "id": f["id"],
            "category": f["category"],
            "title": f["kpi_id"].replace("_", " ").title(),
            "text": fact_text(f, latest),
            "source": f["source"],
        })
    return items
