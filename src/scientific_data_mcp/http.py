"""Shared async HTTP client: per-host pacing, bounded retry, error translation.

Every provider goes through this client. It paces requests per host, honours
``Retry-After`` on 429/503, retries transient network errors, and maps HTTP
status codes onto the taxonomy in :mod:`scientific_data_mcp.errors`.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings
from .errors import AuthError, NotFound, RateLimited, UpstreamError

_MAX_RETRY_AFTER = 10.0


class PoliteClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=settings.timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )
        self._max_retries = settings.max_retries
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> PoliteClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _pace(self, host: str) -> None:
        gap = self._settings.host_delay(host)
        async with self._lock:
            elapsed = time.monotonic() - self._last.get(host, 0.0)
            if elapsed < gap:
                await asyncio.sleep(gap - elapsed)
            self._last[host] = time.monotonic()

    @staticmethod
    def _retry_after(resp: httpx.Response, attempt: int) -> float:
        raw = resp.headers.get("Retry-After", "")
        if raw.replace(".", "", 1).isdigit():
            return min(float(raw), _MAX_RETRY_AFTER)
        return 0.5 * (2**attempt)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        form: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        host = urlparse(url).netloc
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._pace(host)
            try:
                resp = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    data=form,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                last = UpstreamError(f"network error from {host}: {exc}")
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            if resp.status_code in (429, 503):
                last = RateLimited(f"HTTP {resp.status_code} from {host}")
                await asyncio.sleep(self._retry_after(resp, attempt))
                continue
            if resp.status_code in (401, 403):
                raise AuthError(f"HTTP {resp.status_code} from {host}")
            if resp.status_code == 404:
                raise NotFound(f"HTTP 404 from {host}")
            if resp.status_code >= 400:
                raise UpstreamError(f"HTTP {resp.status_code} from {host}")
            return resp
        raise last if last is not None else UpstreamError(f"request to {host} failed")

    async def get_response(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        return await self._request("GET", url, params=params, headers=headers)

    async def get_json(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        resp = await self.get_response(url, params=params, headers=headers)
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON response from {urlparse(url).netloc}: {exc}") from exc

    async def get_text(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        resp = await self.get_response(url, params=params, headers=headers)
        return resp.text

    async def post_json(
        self,
        url: str,
        json_body: dict,
        headers: dict | None = None,
    ) -> Any:
        resp = await self._request("POST", url, json_body=json_body, headers=headers)
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON response from {urlparse(url).netloc}: {exc}") from exc

    async def post_form(
        self,
        url: str,
        fields: dict,
        headers: dict | None = None,
    ) -> Any:
        resp = await self._request("POST", url, form=fields, headers=headers)
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON response from {urlparse(url).netloc}: {exc}") from exc
