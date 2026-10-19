from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any

import httpx

CPE_API_ROOT = "https://cpe.gcve.eu/api"

REQUEST_HEADERS = {
    "User-Agent": "Vulniverse CPE Search",
}

REQUEST_TIMEOUT_SECONDS = 5.0

CACHE_TTL_SECONDS = 45.0
CACHE_MAX_ENTRIES = 128


JsonPayload = dict[str, Any] | list[Any]

CacheKey = tuple[
    str,
    tuple[tuple[str, str], ...],
]

CacheEntry = tuple[
    float,
    JsonPayload,
]


_cache: OrderedDict[
    CacheKey,
    CacheEntry,
] = OrderedDict()

_cache_lock = Lock()


def _cache_key(
    path: str,
    params: dict[str, str | int],
) -> CacheKey:
    return (
        path,
        tuple(
            sorted(
                (
                    key,
                    str(value),
                )
                for key, value in params.items()
            )
        ),
    )


def _get_cached(
    key: CacheKey,
) -> JsonPayload | None:
    now = time.monotonic()

    with _cache_lock:
        cached = _cache.get(key)

        if cached is None:
            return None

        expires_at, value = cached

        if now >= expires_at:
            del _cache[key]
            return None

        # Keep recently reused entries at the end so the
        # cache behaves as a small LRU when it reaches its cap.
        _cache.move_to_end(key)

        return value


def _store_cached(
    key: CacheKey,
    value: JsonPayload,
) -> None:
    expires_at = time.monotonic() + CACHE_TTL_SECONDS

    with _cache_lock:
        _cache[key] = (
            expires_at,
            value,
        )

        _cache.move_to_end(key)

        while len(_cache) > CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)


def _get(
    path: str,
    params: dict[str, str | int],
) -> JsonPayload:
    key = _cache_key(
        path,
        params,
    )

    cached = _get_cached(key)

    if cached is not None:
        return cached

    response = httpx.get(
        f"{CPE_API_ROOT}{path}",
        params=params,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(
        payload,
        (dict, list),
    ):
        raise TypeError("CPE API returned an unexpected JSON response.")

    _store_cached(
        key,
        payload,
    )

    return payload


def search_vendors(
    q: str,
    *,
    page: int = 1,
    per_page: int = 25,
) -> JsonPayload:
    params: dict[
        str,
        str | int,
    ] = {
        "q": q.strip(),
        "page": page,
        "per_page": per_page,
    }

    return _get(
        "/vendors",
        params,
    )


def search_cpes(
    q: str | None = None,
    vendor_q: str | None = None,
    product_q: str | None = None,
    part: str | None = None,
    *,
    page: int = 1,
    per_page: int = 25,
) -> JsonPayload:
    params: dict[
        str,
        str | int,
    ] = {
        "page": page,
        "per_page": per_page,
    }

    if q:
        params["q"] = q.strip()

    if vendor_q:
        params["vendor_q"] = vendor_q.strip()

    if product_q:
        params["product_q"] = product_q.strip()

    if part:
        params["part"] = part.strip()

    return _get(
        "/cpes",
        params,
    )
