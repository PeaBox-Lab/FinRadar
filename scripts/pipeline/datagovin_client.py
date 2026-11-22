"""
FinRadar — data.gov.in API Client
=================================

Wrapper around the data.gov.in REST API (`https://api.data.gov.in/resource/<id>`).

Authentication
--------------
Use the `DATA_GOV_IN_TOKEN` environment variable (your personal API key from
My Account on data.gov.in). If absent, the client falls back to the sample key
provided by the portal, which returns at most 10 records — good enough for
schema discovery and demos, not for production numbers.

API shape (verified against api.data.gov.in):

    GET https://api.data.gov.in/resource/<resource_id>
        ?api-key=<token>
        &format=json            # json | xml | csv (default json)
        &limit=<n>              # max records per request (max 1000)
        &offset=<n>             # pagination
        &filters[<field>]=<v>   # equality filter
        &filters[<field>]=v1,v2 # multiple values (OR)

The response looks like:

    {
      "index_name": "<resource_id>",
      "title": "...",
      "field": [...],              # schema: name, id, type
      "records": [...],            # actual data rows
      "total": <N>,
      "count": <n>,
      "limit": "<n>",
      "offset": "<n>",
      "status": "ok"
    }

Catalog endpoints:

    GET https://api.data.gov.in/catalog/<catalog_uuid>?api-key=...
    GET https://api.data.gov.in/resource/<resource_id>?api-key=...&limit=0

The sample key:
    579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Any


SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
BASE = "https://api.data.gov.in"


def _api_key() -> str:
    return os.environ.get("DATA_GOV_IN_TOKEN", SAMPLE_KEY)


def fetch_resource(
    resource_id: str,
    *,
    limit: int = 1000,
    offset: int = 0,
    filters: dict[str, str | list[str]] | None = None,
    format: str = "json",
    timeout: int = 20,
) -> dict[str, Any]:
    """Fetch a single page of records from a data.gov.in resource.

    Returns the parsed JSON dict. On any network / HTTP / JSON error, returns
    a dict with ``{"status": "error", "message": ...}`` so the pipeline can
    degrade gracefully to snapshots.
    """
    params = {
        "api-key": _api_key(),
        "format": format,
        "limit": str(min(max(limit, 1), 1000)),
        "offset": str(offset),
    }
    if filters:
        for k, v in filters.items():
            values = ",".join(v) if isinstance(v, list) else str(v)
            params[f"filters[{k}]"] = values

    url = f"{BASE}/resource/{resource_id}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "FinRadar/1.0 data.gov.in client",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
        return json.loads(payload)
    except Exception as exc:  # network / HTTP / JSON failures
        return {
            "status": "error",
            "message": str(exc),
            "resource_id": resource_id,
            "url": url,
        }


def fetch_all(resource_id: str, *, limit: int = 1000, filters=None) -> dict[str, Any]:
    """Fetch every page of a resource until we have all records.

    Convenience wrapper around fetch_resource that handles pagination and
    caps total requests at 25 to avoid runaway loops on broken resources.
    """
    all_records = []
    offset = 0
    total_seen = None
    max_requests = 25

    for _ in range(max_requests):
        page = fetch_resource(resource_id, limit=limit, offset=offset, filters=filters)
        if page.get("status") == "error":
            return page
        records = page.get("records", [])
        all_records.extend(records)
        if total_seen is None:
            total_seen = page.get("total", len(all_records))
        if len(all_records) >= total_seen or len(records) == 0:
            break
        offset += limit

    return {
        "status": "ok",
        "resource_id": resource_id,
        "records": all_records,
        "total": total_seen,
        "count": len(all_records),
    }


def get_schema(resource_id: str) -> dict[str, Any]:
    """Return just the field schema for a resource (one record is enough)."""
    return fetch_resource(resource_id, limit=1)


if __name__ == "__main__":
    import sys

    rid = sys.argv[1] if len(sys.argv) > 1 else "8b68ae56-84cf-4728-a0a6-1be11028dea7"
    result = fetch_resource(rid, limit=3)
    print(json.dumps(result, indent=2)[:4000])
