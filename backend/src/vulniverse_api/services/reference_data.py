from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

CWE_API_ROOT = "https://cwe-api.mitre.org/api/v1"
CAPEC_STIX_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/capec/2.1/stix-capec.json"
)

CACHE_TTL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 30.0
CWE_NAME_BATCH_SIZE = 100

_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}


def _fetch_cwe_ids() -> list[str]:
    """
    cwe-api.mitre.org's own /cwe/weakness/all endpoint truncates its
    response mid-string somewhere past ~9.5MB (confirmed: 200 OK,
    but invalid JSON at the cutoff) — apparently a size limit on
    MITRE's side, not something a client-side fix can work around.
    The descendants tree for View 1000 is a small fraction of that
    size and, per that view's own stated design goal, is guaranteed
    to include every weakness in CWE, so it's used here purely to
    enumerate IDs; names are fetched separately in small batches.
    """
    response = httpx.get(
        f"{CWE_API_ROOT}/cwe/1000/descendants",
        params={"view": "1000"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    ids: set[str] = set()

    def walk(node: dict[str, Any]) -> None:
        data = node.get("Data") or {}
        node_type = data.get("Type") or ""

        if "weakness" in node_type and data.get("ID"):
            ids.add(data["ID"])

        for child in node.get("Children") or []:
            walk(child)

    for root in response.json():
        walk(root)

    return sorted(ids, key=int)


def _fetch_cwe_name_batch(
    client: httpx.Client,
    batch: list[str],
) -> dict[str, str]:
    response = client.get(f"/cwe/weakness/{','.join(batch)}")
    response.raise_for_status()

    return {
        weakness["ID"]: weakness["Name"]
        for weakness in response.json().get("Weaknesses", [])
        if weakness.get("ID") and weakness.get("Name")
    }


def _fetch_cwe_names(
    ids: list[str],
) -> dict[str, str]:
    """
    ~944 IDs / CWE_NAME_BATCH_SIZE works out to about a dozen
    requests — fine once a day (this only runs on a cache miss), but
    noticeably slow one at a time (~15s observed), so they're fired
    concurrently instead.
    """
    batches = [
        ids[start:start + CWE_NAME_BATCH_SIZE]
        for start in range(0, len(ids), CWE_NAME_BATCH_SIZE)
    ]

    names: dict[str, str] = {}

    with httpx.Client(
        base_url=CWE_API_ROOT,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client, ThreadPoolExecutor(max_workers=len(batches) or 1) as executor:
        for batch_names in executor.map(
            lambda batch: _fetch_cwe_name_batch(client, batch),
            batches,
        ):
            names.update(batch_names)

    return names


def _fetch_cwe_list() -> list[dict[str, str]]:
    ids = _fetch_cwe_ids()
    names = _fetch_cwe_names(ids)

    return [
        {"id": f"CWE-{cwe_id}", "name": names[cwe_id]}
        for cwe_id in ids
        if cwe_id in names
    ]


def _fetch_capec_list() -> list[dict[str, str]]:
    response = httpx.get(CAPEC_STIX_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    items: list[dict[str, str]] = []

    for obj in response.json().get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        name = obj.get("name")
        capec_id = next(
            (
                ref.get("external_id")
                for ref in obj.get("external_references", [])
                if ref.get("source_name") == "capec"
            ),
            None,
        )

        if capec_id and name:
            items.append({"id": capec_id, "name": name})

    items.sort(key=lambda item: int(item["id"].removeprefix("CAPEC-")))

    return items


_FETCHERS = {
    "cwe": _fetch_cwe_list,
    "capec": _fetch_capec_list,
}


def known_reference_kinds() -> set[str]:
    return set(_FETCHERS)


def get_reference_list(
    kind: str,
) -> list[dict[str, str]]:
    """
    In-memory, per-process cache refreshed at most once every
    CACHE_TTL_SECONDS. If a refresh fails (MITRE/GitHub unreachable
    or rate-limiting), this falls back to whatever was last cached
    successfully — a stale list is still useful for an autocomplete
    that never blocks free-text entry — and only propagates the
    error if nothing has ever been fetched.
    """
    fetcher = _FETCHERS[kind]
    cached = _cache.get(kind)
    now = time.monotonic()

    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        fresh = fetcher()
    except httpx.HTTPError:
        if cached:
            return cached[1]

        raise

    _cache[kind] = (now, fresh)

    return fresh
