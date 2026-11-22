"""
FinRadar — KPI Registry
=======================
The single source of truth for every derived KPI FinRadar publishes.

Each entry defines what the KPI means, where its data comes from, how it is
calculated, and how a reader should judge whether a number is "good" or "bad".

A KPI is never a raw copy of a government table. It is always a *derived*
metric — a ratio, a spread, a velocity, a percentile or a composite — so the
site stays a media/research brand rather than a republisher.

Field ID notes for data.gov.in (api.data.gov.in/resource/<id>?api-key=...)
are listed where known. If the live sample key cannot return a field, the
pipeline falls back to snapshot values and marks the KPI as "demo".
"""

# ---------------------------------------------------------------------------
# Helper to keep definitions terse and consistent.
# ---------------------------------------------------------------------------

def kpi(kpi_id, name, sector, resource_id, source_fields, formula,
        unit, direction, ranges, insight, benchmark=None, frequency="monthly"):
    """
    Build a KPI definition.

    direction : "higher_better" | "lower_better" | "closer_to_target"
    ranges    : dict with keys good / moderate / poor -> (low, high) bounds
                (only used for higher_better / lower_better KPIs)
    insight   : plain-English sentence describing what a change means
    """
    return {
        "id": kpi_id,
        "name": name,
        "sector": sector,
        "source_resource_id": resource_id,
        "source_fields": source_fields,
        "formula": formula,
        "unit": unit,
        "direction": direction,
        "ranges": ranges,
        "insight": insight,
        "benchmark": benchmark,
        "frequency": frequency,
    }


KPI_REGISTRY = [
    # =======================================================================
    # SECTOR: ECONOMY
    # =======================================================================
    kpi(
        "real_interest_rate",
        "Real Interest Rate (Saver's Yield)",
        "Economy",
        "wb:FP.CPI.TOTL.ZG + RBI 10Y G-Sec yield",
        ["FP.CPI.TOTL.ZG", "10Y_GSEC_YIELD"],
        "10Y G-Sec Yield − CPI Inflation",
        "%",
        "higher_better",
        {"good": (0.5, 8), "moderate": (-1.0, 0.5), "poor": (-20, -1.0)},
        "Positive means savers beat price rises; negative means money in the bank quietly loses value. Every 100bps of fall is a signal to lock FD rates before they drop further.",
        "RBI 10Y G-Sec vs World Bank CPI",
    ),
    kpi(
        "real_inflation_rate",
        "Real Inflation Rate (Headline)",
        "Economy",
        "wb:FP.CPI.TOTL.ZG",
        ["FP.CPI.TOTL.ZG"],
        "Headline CPI growth (annual %)",
        "%",
        "lower_better",
        {"good": (0, 2), "moderate": (2, 4), "poor": (4, 50)},
        "The single most quoted cost-of-living number. Below 2% is stable; 2-4% is the RBI comfort zone; above 4% erodes real wages and usually triggers rate hikes.",
        "RBI target: 4% (±2%)",
    ),
    kpi(
        "gdp_growth_pct",
        "GDP Growth (Annual %)",
        "Economy",
        "wb:NY.GDP.MKTP.KD.ZG",
        ["NY.GDP.MKTP.KD.ZG"],
        "Real GDP growth, year over year",
        "%",
        "higher_better",
        {"good": (6, 15), "moderate": (3, 6), "poor": (-10, 3)},
        "Above 6% is strong expansion; 3-6% is steady; below 3% is a slowdown worth watching for job and income stress.",
        "World Bank; IMF WEO",
    ),
    kpi(
        "gdp_per_capita_usd",
        "GDP per Capita (Nominal)",
        "Economy",
        "wb:NY.GDP.PCAP.CD",
        ["NY.GDP.PCAP.CD"],
        "GDP ÷ population, in current US$",
        "USD",
        "higher_better",
        {"good": (10000, 200000), "moderate": (3000, 10000), "poor": (0, 3000)},
        "Average economic output per person. It is the usual headline number global rankings use, but it hides inequality — always pair with the PPP gap.",
        "World Bank",
    ),
    kpi(
        "gdp_per_capita_ppp_usd",
        "GDP per Capita, PPP",
        "Economy",
        "wb:NY.GDP.PCAP.PP.CD",
        ["NY.GDP.PCAP.PP.CD"],
        "GDP per capita adjusted for purchasing power",
        "int$",
        "higher_better",
        {"good": (20000, 500000), "moderate": (8000, 20000), "poor": (0, 8000)},
        "What the same output buys inside the country. The gap vs nominal tells you how much cheaper daily life is — which is why a ₹20 LPA salary in Jaipur buys more than in Mumbai.",
        "World Bank",
    ),
    kpi(
        "ppp_gap_usd",
        "PPP Gap (Nominal − PPP)",
        "Economy",
        "wb:NY.GDP.PCAP.CD − NY.GDP.PCAP.PP.CD",
        ["NY.GDP.PCAP.CD", "NY.GDP.PCAP.PP.CD"],
        "Nominal GDP per capita − PPP GDP per capita",
        "USD",
        "lower_better",
        {"good": (-40000, 0), "moderate": (-40000, -10000), "poor": (-10000, 100000)},
        "A large negative gap means local prices are far cheaper than the exchange rate implies — money goes further inside the country. The bigger the gap, the more a remote or migrant salary is worth relative to its dollar figure.",
        "World Bank",
    ),
    kpi(
        "current_account_pct_gdp",
        "Current Account Balance (% of GDP)",
        "Economy",
        "wb:NE.CAB.TOTL.PT",
        ["NE.CAB.TOTL.PT"],
        "Trade balance + net transfers, as % of GDP",
        "%",
        "higher_better",
        {"good": (0, 5), "moderate": (-3, 0), "poor": (-20, -3)},
        "A surplus means more money flows in than out (exports, remittances). A deficit above -3% is a warning that the country depends on foreign capital to fund its imports.",
        "IMF BOP statistics",
    ),
    kpi(
        "fdi_inflows_pct_gdp",
        "FDI Inflows (% of GDP)",
        "Economy",
        "wb:BX.KD.FDI.DT.GP",
        ["BX.KD.FDI.DT.GP"],
        "Foreign direct investment as % of GDP",
        "%",
        "higher_better",
        {"good": (2, 15), "moderate": (0.5, 2), "poor": (-5, 0.5)},
        "Foreign money building factories, offices and infrastructure. Above 2% signals confidence; near zero means capital is staying home or leaving.",
        "UNCTAD World Investment Report",
    ),
    kpi(
        "debt_service_burden",
        "Debt Service Burden (% of Revenue)",
        "Economy",
        "rbi:debt_service",
        ["share_of_revenue_pct"],
        "Interest paid on public debt ÷ total revenue",
        "%",
        "lower_better",
        {"good": (0, 8), "moderate": (8, 15), "poor": (15, 100)},
        "Every rupee of interest is a rupee that cannot fund schools, hospitals or roads. Rising debt service crowds out development spending — watch it alongside the fiscal deficit.",
        "RBI DBIE / Union Budget",
    ),
    kpi(
        "import_cover_ratio",
        "Import Cover Ratio",
        "Economy",
        "rbi:reserves ÷ (annual imports / 12)",
        ["fx_reserves_usd", "annual_imports_usd"],
        "Forex reserves ÷ (annual imports ÷ 12)",
        "months",
        "higher_better",
        {"good": (6, 24), "moderate": (3, 6), "poor": (0, 3)},
        "How many months the country can keep importing if all export earnings stopped. Below 3 months is a balance-of-payments crisis zone; 6+ months is comfortable.",
        "IMF reserve adequacy metric",
    ),
    kpi(
        "reserve_adequacy_ratio",
        "Reserve Adequacy Ratio",
        "Economy",
        "rbi:reserves ÷ short-term debt",
        ["fx_reserves_usd", "short_term_debt_usd"],
        "Forex reserves ÷ short-term external debt",
        "x",
        "higher_better",
        {"good": (1.5, 10), "moderate": (1.0, 1.5), "poor": (0, 1.0)},
        "Can the country repay all debt due within a year? Above 1.0x means yes; below 1.0x means reserves alone cannot cover near-term obligations — a downgrade risk.",
        "Guidotti-Greenspan rule: >1.0x",
    ),
    kpi(
        "fiscal_deficit_pct_gdp",
        "Fiscal Deficit (% of GDP)",
        "Economy",
        "rbi:fiscal_deficit + wb:GC.DOD.TOTL.GD.ZG",
        ["fiscal_deficit_pct", "GC.DOD.TOTL.GD.ZG"],
        "Government borrowing ÷ GDP",
        "%",
        "lower_better",
        {"good": (0, 3), "moderate": (3, 6), "poor": (6, 20)},
        "How much the government must borrow to fund its spending. Above 6% is typically inflationary and crowds out private investment; below 3% is the FRBM target.",
        "FRBM Act target: 3%",
    ),

    # =======================================================================
    # SECTOR: ENERGY & POWER
    # =======================================================================
    kpi(
        "power_demand_growth_pct",
        "Power Demand Growth",
        "Energy",
        "cea:pwr_demand",
        ["growth_pct"],
        "YoY growth in electricity consumption",
        "%",
        "higher_better",
        {"good": (3, 15), "moderate": (0, 3), "poor": (-10, 0)},
        "Electricity demand is a near-real-time proxy for industrial and commercial activity. Falling demand is an early warning that factories are idling.",
        "CEA / POSOCO monthly reports",
    ),
    kpi(
        "iip_growth_pct",
        "Index of Industrial Production Growth",
        "Economy",
        "mospi:iip",
        ["growth_pct"],
        "YoY growth in industrial output (factory, mine, utility)",
        "%",
        "higher_better",
        {"good": (4, 15), "moderate": (0, 4), "poor": (-10, 0)},
        "The cleanest read on whether factories are actually producing more. IIP leads GDP by a quarter — a falling IIP today is a slower GDP tomorrow.",
        "MoSPI IIP series",
    ),
    kpi(
        "gst_growth_pct",
        "GST Collections Growth",
        "Economy",
        "gst:gst_growth",
        ["current_year_growth_pct"],
        "YoY growth in GST collections",
        "%",
        "higher_better",
        {"good": (8, 25), "moderate": (3, 8), "poor": (-10, 3)},
        "GST is levied on consumption, so its growth is a high-frequency read on consumer and business spending. Below 5% growth often means households are pulling back.",
        "GST portal monthly collections",
    ),
    kpi(
        "digital_consumption_velocity",
        "Digital Consumption Velocity (UPI Ticket)",
        "Economy",
        "npci:upi",
        ["avg_ticket_usd"],
        "UPI transaction value ÷ UPI volume",
        "USD/tx",
        "higher_better",
        {"good": (1.5, 5), "moderate": (0.5, 1.5), "poor": (0, 0.5)},
        "The average amount Indians move per UPI payment. Rising ticket size means bigger-ticket transactions are going digital — a sign of formalisation and consumption upgrading. Track it with GST growth.",
        "NPCI monthly UPI statistics",
    ),

    # =======================================================================
    # SECTOR: AGRICULTURE & RURAL
    # =======================================================================
    kpi(
        "foodgrain_growth_pct",
        "Foodgrain Production Growth",
        "Agriculture",
        "agri:foodgrain",
        ["growth_pct"],
        "YoY growth in total foodgrain output",
        "%",
        "higher_better",
        {"good": (2, 15), "moderate": (-2, 2), "poor": (-20, -2)},
        "Food output growth. Two bad monsoon years in a row push food inflation up and squeeze rural incomes — the first domino in a rural distress cycle.",
        "Ministry of Agriculture 4th Advance Estimates",
    ),
    kpi(
        "fertilizer_intensity",
        "Fertilizer Intensity (kg / hectare)",
        "Agriculture",
        "agri:fertilizer",
        ["consumption_kg", "net_sown_area_ha"],
        "Fertilizer consumption ÷ net sown area",
        "kg/ha",
        "closer_to_target",
        {"good": (120, 200), "moderate": (80, 120), "poor": (0, 80)},
        "How much plant nutrient each hectare of farmland receives. Too low means soil mining and falling yields; too high (above ~200 kg/ha) means overuse, water pollution and rising input costs.",
        "Recommended: 120-200 kg/ha (varies by crop mix)",
    ),
    kpi(
        "irrigation_coverage_pct",
        "Irrigation Coverage",
        "Agriculture",
        "agri:irrigation",
        ["irrigated_area_ha", "net_sown_area_ha"],
        "Net irrigated area ÷ net sown area × 100",
        "%",
        "higher_better",
        {"good": (60, 100), "moderate": (40, 60), "poor": (0, 40)},
        "Share of farmland with assured irrigation. Above 60% insulates farmers from monsoon failure; below 40% means a single dry year can wipe out a harvest.",
        "Economic Survey of India",
    ),
    kpi(
        "crop_insurance_penetration_pct",
        "Crop Insurance Penetration",
        "Agriculture",
        "agri:insurance",
        ["insured_area_ha", "net_sown_area_ha"],
        "Insured area ÷ net sown area × 100",
        "%",
        "higher_better",
        {"good": (40, 100), "moderate": (15, 40), "poor": (0, 15)},
        "Share of farmland covered by PMFBY or state schemes. Low coverage means a single failed monsoon translates directly into farmer distress and rural NPA spikes.",
        "PMFBY annual reports",
    ),

    # =======================================================================
    # SECTOR: FINANCE & BANKING
    # =======================================================================
    kpi(
        "bank_credit_deposit_ratio",
        "Bank Credit-to-Deposit Ratio",
        "Finance",
        "rbi:cd_ratio",
        ["credit_outstanding", "deposits_outstanding"],
        "Total bank credit ÷ total deposits × 100",
        "%",
        "higher_better",
        {"good": (70, 90), "moderate": (50, 70), "poor": (30, 50)},
        "How much of every rupee Indians deposit is lent back out. Above 80% is a fast-growing, credit-hungry economy; below 60% signals weak loan demand or cautious banks — often a slowdown signal.",
        "RBI DBIE — Scheduled Commercial Banks",
    ),
    kpi(
        "priority_sector_lending_pct",
        "Priority Sector Lending Share",
        "Finance",
        "rbi:psl",
        ["psl_outstanding", "total_bank_credit"],
        "PSL advances ÷ total bank credit × 100",
        "%",
        "higher_better",
        {"good": (40, 75), "moderate": (30, 40), "poor": (0, 30)},
        "Share of bank credit mandated to flow to agriculture, MSMEs and low-income housing. The RBI target is 40%; shortfalls mean credit is not reaching the sectors that employ the most people.",
        "RBI PSL master directions: 40% target",
    ),
    kpi(
        "gnpa_ratio_pct",
        "Gross NPA Ratio",
        "Finance",
        "rbi:gnpa",
        ["gross_np_as", "gross_advances"],
        "Gross non-performing assets ÷ gross advances × 100",
        "%",
        "lower_better",
        {"good": (0, 2), "moderate": (2, 5), "poor": (5, 20)},
        "Share of bank loans that borrowers have stopped repaying. Below 2% is healthy; above 5% means banks are sitting on losses that eat into capital and choke new lending.",
        "RBI Financial Stability Report",
    ),
    kpi(
        "msme_credit_penetration_pct",
        "MSME Credit Penetration",
        "Finance",
        "msme:units + rbi:msme_credit",
        ["msme_loans_outstanding", "msme_gdp_estimate"],
        "Outstanding MSME credit ÷ estimated MSME GDP × 100",
        "%",
        "higher_better",
        {"good": (15, 60), "moderate": (8, 15), "poor": (0, 8)},
        "How much bank credit reaches the MSME sector relative to its economic weight. India's MSMEs contribute ~30% of GDP but receive a far smaller share of formal credit — a large, persistent gap worth tracking.",
        "RBI MSME surveys",
    ),

    # =======================================================================
    # SECTOR: HEALTH
    # =======================================================================
    kpi(
        "hospital_bed_density",
        "Hospital Bed Density (per 1,000 people)",
        "Health",
        "health:hMIS",
        ["total_beds", "population"],
        "Total hospital beds ÷ population × 1,000",
        "beds/1000",
        "higher_better",
        {"good": (3, 8), "moderate": (1.5, 3), "poor": (0, 1.5)},
        "How many hospital beds exist for every 1,000 people. Below 2 is a capacity crisis — a pandemic or even a bad flu season overwhelms the system. WHO recommends ~5 per 1,000 for ageing populations.",
        "WHO / NHP India",
    ),
    kpi(
        "immunization_coverage_pct",
        "Full Immunization Coverage",
        "Health",
        "health:nfHS",
        ["immunized_children", "total_children_12_35m"],
        "Fully immunized children ÷ children aged 12-35 months × 100",
        "%",
        "higher_better",
        {"good": (90, 100), "moderate": (70, 90), "poor": (0, 70)},
        "Share of young children who received all basic vaccines. Below 85% means pockets of population remain vulnerable to outbreaks — measles, diphtheria, polio.",
        "NFHS-5; WHO target ≥90%",
    ),
    kpi(
        "oope_share_pct",
        "Out-of-Pocket Health Expenditure Share",
        "Health",
        "health:oope",
        ["household_health_spend", "total_health_spend"],
        "Household out-of-pocket spending ÷ total health spending × 100",
        "%",
        "lower_better",
        {"good": (0, 30), "moderate": (30, 50), "poor": (50, 100)},
        "How much of all health spending comes directly from patients' pockets. Above 50% means a serious illness can bankrupt a family — a key driver of poverty and of demand for health insurance.",
        "National Health Accounts; WHO target <30%",
    ),

    # =======================================================================
    # SECTOR: EDUCATION
    # =======================================================================
    kpi(
        "pupil_teacher_ratio",
        "Pupil-Teacher Ratio",
        "Education",
        "edu:udise",
        ["total_students", "total_teachers"],
        "Total enrolled students ÷ total teachers",
        "students/teacher",
        "lower_better",
        {"good": (0, 30), "moderate": (30, 40), "poor": (40, 100)},
        "How many students each teacher is responsible for. Above 35-40, individual attention collapses and learning outcomes fall — a leading indicator of future workforce quality.",
        "RTE Act norm: ≤30 (primary), ≤35 (upper primary)",
    ),
    kpi(
        "literacy_rate_pct",
        "Literacy Rate",
        "Education",
        "census:literacy",
        ["literate_population", "total_population_7plus"],
        "Literate population (age 7+) ÷ total population (age 7+) × 100",
        "%",
        "higher_better",
        {"good": (85, 100), "moderate": (65, 85), "poor": (0, 65)},
        "Share of people aged 7+ who can read and write with understanding. Above 85% is near-universal literacy; below 65% means large segments of the workforce cannot fully participate in a modern economy.",
        "Census of India 2011; UNESCO",
    ),

    # =======================================================================
    # SECTOR: TRANSPORT & URBAN
    # =======================================================================
    kpi(
        "road_density",
        "Road Density (km per 100 sq km)",
        "Transport",
        "morth:road",
        ["total_road_length_km", "geographical_area_sq_km"],
        "Total road length ÷ geographical area",
        "km/100km²",
        "higher_better",
        {"good": (150, 600), "moderate": (80, 150), "poor": (0, 80)},
        "How densely roads blanket a region. Higher density means lower logistics costs and better market access; very high density in cities often signals congestion rather than connectivity.",
        "Ministry of Road Transport & Highways",
    ),
    kpi(
        "vehicle_density",
        "Vehicle Density (per 1,000 people)",
        "Transport",
        "morth:vehicles",
        ["registered_vehicles", "population"],
        "Registered vehicles ÷ population × 1,000",
        "veh/1000",
        "closer_to_target",
        {"good": (100, 300), "moderate": (50, 100), "poor": (0, 50)},
        "Vehicle ownership intensity. Rising density signals mobility and prosperity, but beyond ~300 per 1,000 cities face severe congestion and pollution — the point where public transport investment becomes urgent.",
        "MoRTH / SIAM",
    ),

    # =======================================================================
    # SECTOR: WELFARE & EMPLOYMENT
    # =======================================================================
    kpi(
        "mgnrega_person_days",
        "MGNREGA Person-Days Generated",
        "Welfare",
        "mgnrega:person_days",
        ["person_days_generated"],
        "Total person-days of wage employment generated under MGNREGA",
        "crore person-days",
        "higher_better",
        {"good": (150, 400), "moderate": (80, 150), "poor": (0, 80)},
        "Demand for rural wage work under MGNREGA. Spikes above 250 crore person-days typically signal rural distress — people are turning to guaranteed wage work because private rural employment has dried up.",
        "MGNREGA MIS monthly reports",
    ),
    kpi(
        "pds_coverage_pct",
        "PDS / Food Security Coverage",
        "Welfare",
        "food:pds",
        ["ration_cards_active", "estimated_eligible_population"],
        "Active ration cards ÷ estimated eligible population × 100",
        "%",
        "higher_better",
        {"good": (85, 100), "moderate": (60, 85), "poor": (0, 60)},
        "Share of eligible households actually holding an active ration card under NFSA. Below 85% means entitled families are missing subsidised food — a direct food-security risk.",
        "NFSA coverage target: 81 crore people",
    ),

    # =======================================================================
    # SECTOR: ENVIRONMENT & CLIMATE
    # =======================================================================
    kpi(
        "renewable_capacity_share_pct",
        "Renewable Energy Share of Installed Capacity",
        "Environment",
        "mnre:renewable",
        ["renewable_capacity_mw", "total_capacity_mw"],
        "Renewable installed capacity ÷ total installed capacity × 100",
        "%",
        "higher_better",
        {"good": (40, 100), "moderate": (20, 40), "poor": (0, 20)},
        "How much of India's power generation capacity comes from solar, wind, hydro and biomass. Above 40% signals a genuine energy transition; below 20% means fossil dependence is still deepening.",
        "India's NDC target: 50% non-fossil by 2030",
    ),
    kpi(
        "per_capita_co2_emissions",
        "Per-Capita CO₂ Emissions",
        "Environment",
        "wb:EN.ATM.CO2E.PC",
        ["EN.ATM.CO2E.PC"],
        "Total CO₂ emissions ÷ population",
        "tonnes/capita",
        "lower_better",
        {"good": (0, 2), "moderate": (2, 5), "poor": (5, 30)},
        "Carbon footprint per person. India's ~2 t/capita is well below the world average (~4.7) — a key equity argument in climate negotiations and a growing focus for ESG investors.",
        "World Bank / Global Carbon Project",
    ),
]


def kpi_by_id(kpi_id):
    """Return the KPI definition with the given id, or None."""
    for k in KPI_REGISTRY:
        if k["id"] == kpi_id:
            return k
    return None


def kpis_by_sector(sector):
    """Return all KPI definitions in a given sector."""
    return [k for k in KPI_REGISTRY if k["sector"].lower() == sector.lower()]


def all_sectors():
    """Return the sorted list of unique sector names in the registry."""
    return sorted(set(k["sector"] for k in KPI_REGISTRY))


def interpret(value, kpi_def):
    """
    Return a human-readable interpretation string for a computed value.

    Uses the KPI's `ranges` and `direction` to decide whether the value is
    good / moderate / poor, then combines that with the insight sentence.
    """
    if value is None:
        return "No data available yet."

    direction = kpi_def["direction"]
    ranges = kpi_def.get("ranges", {})
    insight = kpi_def.get("insight", "")

    if direction == "higher_better":
        if value >= ranges.get("good", (0, 0))[0]:
            verdict = "strong"
        elif value >= ranges.get("moderate", (0, 0))[0]:
            verdict = "moderate"
        else:
            verdict = "weak"
    elif direction == "lower_better":
        if value <= ranges.get("good", (0, 0))[1]:
            verdict = "strong"
        elif value <= ranges.get("moderate", (0, 0))[1]:
            verdict = "moderate"
        else:
            verdict = "weak"
    else:  # closer_to_target
        good = ranges.get("good", (0, 0))
        mod = ranges.get("moderate", (0, 0))
        if good[0] <= value <= good[1]:
            verdict = "on target"
        elif mod[0] <= value <= mod[1]:
            verdict = "near target"
        else:
            verdict = "off target"

    return f"{verdict.capitalize()}. {insight}"


if __name__ == "__main__":
    print(f"Registered {len(KPI_REGISTRY)} KPIs across {len(all_sectors())} sectors.")
    for sector in all_sectors():
        print(f"  {sector}: {len(kpis_by_sector(sector))} KPIs")