"""
FinRadar — Analytics Engine
===========================
Turns raw data points into *meaningful* insights: verdicts (strong /
moderate / weak / on target), trend notes and plain-English explanations.

Each insight is produced from a KPI definition plus the computed value, e.g.:
    "Real Interest Rate = 5.45% → Strong. Positive means savers beat price rises..."
"""

from kpi_registry import KPI_REGISTRY, interpret, kpi_by_id, kpis_by_sector, all_sectors


def build_insight(kpi_def, value, trend=None):
    """
    Produce a full insight object for one KPI.

    Returns dict:
        {
            kpi_id, name, sector,
            value, unit, direction, verdict,
            good_range, moderate_range, poor_range,
            formula, source_fields,
            insight_text, benchmark,
            frequency,
            trend,            # optional {prev: value, change: value} or None
        }
    """
    verdict_obj = interpret(value, kpi_def)
    verdict = verdict_obj.split(".")[0].lower() if verdict_obj else "unknown"

    insight = {
        "kpi_id": kpi_def["id"],
        "name": kpi_def["name"],
        "sector": kpi_def["sector"],
        "value": value,
        "unit": kpi_def["unit"],
        "direction": kpi_def["direction"],
        "verdict": verdict,
        "good_range": kpi_def.get("ranges", {}).get("good"),
        "moderate_range": kpi_def.get("ranges", {}).get("moderate"),
        "poor_range": kpi_def.get("ranges", {}).get("poor"),
        "formula": kpi_def.get("formula", ""),
        "source_fields": kpi_def.get("source_fields", []),
        "source_resource_id": kpi_def.get("source_resource_id", ""),
        "insight_text": kpi_def.get("insight", ""),
        "benchmark": kpi_def.get("benchmark"),
        "frequency": kpi_def.get("frequency", "monthly"),
        "trend": trend,
        "verdict_text": verdict_obj,
    }
    return insight


def build_insights_for_value(kpi_id, value, trend=None):
    """Convenience wrapper: build an insight for a single KPI id + value."""
    kpi_def = kpi_by_id(kpi_id)
    if kpi_def is None:
        return None
    return build_insight(kpi_def, value, trend)


def build_all_insights(values_by_kpi_id):
    """
    values_by_kpi_id: {kpi_id: value} — build insights for every known KPI.

    Unknown ids are ignored (only KPIs registered in kpi_registry.py are
    publishable, keeping the site honest about sources).
    """
    insights = []
    for kpi_def in KPI_REGISTRY:
        value = values_by_kpi_id.get(kpi_def["id"])
        insight = build_insight(kpi_def, value)
        if value is None and not kpi_def.get("source_resource_id", "").startswith(("rbi", "wb", "mspi", "npci", "gst", "agri", "rbi:")):
            # skip truly unresolvable ones in the default output; but we still
            # emit them so the site can show the registry.
            pass
        insights.append(insight)
    return insights


def build_kpi_catalog():
    """Return the full KPI registry formatted for the website / JSON feed."""
    return KPI_REGISTRY
