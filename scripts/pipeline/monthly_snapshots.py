#!/usr/bin/env python3
"""Readers and render helpers for the curated monthly snapshot layer.

A monthly snapshot is an explicitly non-live dataset transcribed from an
official publication (or a clearly labelled authoritative industry body).
It is versioned in ``data/monthly-snapshots/`` and is never generated from
random, simulated or indicative values.
"""

from __future__ import annotations

import json
import html
import re
from datetime import datetime
from pathlib import Path

BADGE_TEXT = "Static Snapshot • Updated Monthly (Not Live)"
SCHEMA_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "data" / "monthly-snapshots"


def load_all(directory: Path | None = None) -> dict:
    """Load validated monthly snapshot JSON files keyed by ``dataset_id``."""
    directory = Path(directory) if directory else SNAPSHOT_DIR
    if not directory.exists():
        return {}
    result = {}
    for path in sorted(directory.glob("*.json")):
        if path.name in ("schema.json", "index.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not payload.get("dataset_id"):
            continue
        payload["_path"] = str(path.relative_to(ROOT).as_posix())
        result[payload["dataset_id"]] = payload
    return result


def esc(value) -> str:
    return html.escape(str(value if value is not None else "—"), quote=True)


def last_updated_label(snapshot: dict) -> str:
    """Return a human-readable 'Month YYYY' label from ``last_updated``."""
    raw = str(snapshot.get("last_updated", ""))
    date = None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m", "%Y"):
        try:
            date = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if date is None:
        return raw or "Unknown"
    return date.strftime("%B %Y")


def snapshot_badge(snapshot: dict) -> str:
    """The mandatory disclosure attached to every snapshot-powered card/chart."""
    return (f'<span class="snapshot-badge">{esc(BADGE_TEXT)}'
            f'<span class="snapshot-updated">Last Updated: {esc(last_updated_label(snapshot))}</span>'
            '</span>')


def fmt_value(value, unit: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        abs_value = abs(value)
        if "crore" in unit.lower() or "million" in unit.lower():
            shown = f"{value:,.0f}"
        elif abs_value >= 1_000_000_000_000:
            shown = f"{value / 1_000_000_000_000:,.2f} tn"
        elif abs_value >= 1_000_000_000:
            shown = f"{value / 1_000_000_000:,.2f} bn"
        elif abs_value >= 1_000_000:
            shown = f"{value / 1_000_000:,.1f} mn"
        elif abs_value >= 1000:
            shown = f"{value:,.0f}"
        elif abs_value >= 10:
            shown = f"{value:,.1f}"
        else:
            shown = f"{value:,.2f}".rstrip("0").rstrip(".")
    else:
        shown = str(value)
    if unit and unit not in shown:
        return f"{shown} {unit}"
    return shown


def metric_points(metric: dict) -> list[dict]:
    return [p for p in metric.get("values", []) if p.get("value") is not None]


def latest_point(metric: dict) -> dict:
    points = metric_points(metric)
    return points[-1] if points else {"period": "—", "value": None}


def yoy_change(metric: dict):
    """Use a published YoY value when present, otherwise derive it."""
    if metric.get("yoy_change_pct") is not None:
        return metric["yoy_change_pct"]
    points = metric_points(metric)
    if len(points) < 2:
        return None
    current, previous = points[-1]["value"], points[-2]["value"]
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)) or previous == 0:
        return None
    return (current - previous) / previous * 100


def render_metric_card(snapshot: dict, metric: dict, detail_url: str = "") -> str:
    """Render one snapshot KPI card with the mandatory transparency badge."""
    point = latest_point(metric)
    change = yoy_change(metric)
    change_html = ""
    if change is not None:
        direction = "up" if change >= 0 else "down"
        change_html = f'<span class="metric-change {direction}">{change:+.1f}% YoY</span>'
    spark = ""
    points = [p["value"] for p in metric_points(metric)]
    if len(points) >= 2:
        spark = (f'<div class="sparkline snapshot-sparkline" data-points='
                 f"'{html.escape(json.dumps(points), quote=True)}'></div>")
    source = metric.get("source") or snapshot.get("source", {})
    source_link = ""
    if source.get("url"):
        source_link = (f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">'
                       f'{esc(source.get("organization") or "Source")}</a>')
    detail_link = ""
    if detail_url:
        detail_link = f'<a class="btn small" href="{esc(detail_url)}">View series</a>'
    return f"""<article class="card snapshot-card">
      <div class="snapshot-card-top">
        <span class="eyebrow dark">{esc(metric.get('category') or snapshot.get('category', 'Snapshot'))}</span>
        {snapshot_badge(snapshot)}
      </div>
      <h3>{esc(metric.get('name'))}</h3>
      <div class="snapshot-value">{esc(fmt_value(point.get('value'), metric.get('unit', '')))}</div>
      <div class="snapshot-period">Latest: {esc(point.get('period', '—'))} {change_html}</div>
      {spark}
      <p class="small muted">{esc(metric.get('definition') or '')}</p>
      <div class="snapshot-card-foot">{detail_link}<span>Source: {source_link or esc(source.get('organization') or '—')}</span></div>
    </article>"""


def render_dataset_table(snapshot: dict, metrics=None) -> str:
    """Render a compact authentic multi-period table for snapshot metrics."""
    selected = metrics or snapshot.get("metrics", [])
    periods = []
    for metric in selected:
        for point in metric_points(metric):
            if point.get("period") not in periods:
                periods.append(point["period"])
    if not periods:
        return ""
    head = "".join(f"<th>{esc(p)}</th>" for p in periods)
    rows = []
    for metric in selected:
        cells = []
        for period in periods:
            value = next((p.get("value") for p in metric_points(metric) if p.get("period") == period), None)
            cells.append(f'<td class="num">{esc(fmt_value(value, ""))}</td>')
        rows.append(f"<tr><th scope=\"row\">{esc(metric.get('name'))} <span class=\"muted\">({esc(metric.get('unit', ''))})</span></th>{''.join(cells)}</tr>")
    source = snapshot.get("source", {})
    source_html = ""
    if source.get("url"):
        source_html = f'<a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source.get("organization", "Source"))}</a>'
    return f"""<div class="snapshot-table-wrap">
      {snapshot_badge(snapshot)}
      <table class="data-table snapshot-table">
        <thead><tr><th>Metric</th>{head}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <p class="small muted">Source: {source_html or esc(source.get('organization') or '—')} · {esc(source.get('title') or '')}</p>
    </div>"""


def search_items(snapshots: dict) -> list[dict]:
    """Expose snapshot datasets and metrics in the site-wide search index."""
    items = []
    for dataset_id, snapshot in snapshots.items():
        source = snapshot.get("source", {})
        haystack = " ".join([
            snapshot.get("title", ""),
            snapshot.get("description", ""),
            " ".join(m.get("name", "") for m in snapshot.get("metrics", [])),
            " ".join(m.get("definition", "") for m in snapshot.get("metrics", [])),
            source.get("organization", ""),
            BADGE_TEXT,
        ])
        items.append({
            "id": dataset_id,
            "title": snapshot.get("title", dataset_id),
            "category": snapshot.get("category", "Snapshots"),
            "text": haystack,
            "source": f"Monthly snapshot · {source.get('organization', 'Official publication')}",
            "url": snapshot.get("page", f"monthly-snapshots.html#{dataset_id}"),
            "type": "snapshot",
            "badge": BADGE_TEXT,
            "last_updated": last_updated_label(snapshot),
        })
    return items


def validate(snapshot: dict) -> list[str]:
    """Return a list of schema problems for one snapshot payload."""
    errors = []
    required = ("dataset_id", "title", "category", "last_updated", "source", "metrics")
    for key in required:
        if not snapshot.get(key):
            errors.append(f"missing {key}")
    source = snapshot.get("source", {})
    if not source.get("organization") or not source.get("url"):
        errors.append("source.organization and source.url are required")
    for metric in snapshot.get("metrics", []):
        if not metric.get("id") or not metric.get("name"):
            errors.append("each metric needs id and name")
        if not isinstance(metric.get("values"), list) or not metric["values"]:
            errors.append(f"metric {metric.get('id')} has no values")
            continue
        for point in metric["values"]:
            if not point.get("period"):
                errors.append(f"metric {metric.get('id')} has an unlabelled period")
            value = point.get("value")
            if value is not None and not isinstance(value, (int, float)):
                errors.append(f"metric {metric.get('id')} has a non-numeric value")
    return errors


def normalise(snapshot: dict) -> dict:
    """Derive latest values and YoY changes, and stamp the shared badge text."""
    snapshot = dict(snapshot)
    snapshot["schema_version"] = SCHEMA_VERSION
    snapshot["badge"] = BADGE_TEXT
    metrics = []
    for metric in snapshot.get("metrics", []):
        metric = dict(metric)
        points = metric_points(metric)
        if points:
            metric["latest_period"] = points[-1]["period"]
            metric["latest_value"] = points[-1]["value"]
            metric["yoy_change_pct"] = yoy_change(metric)
        metrics.append(metric)
    snapshot["metrics"] = metrics
    return snapshot
