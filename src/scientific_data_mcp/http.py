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
from .errors import AuthError, NotFound, RateLimited, UpstreamDrift, UpstreamError

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
        follow_redirects: bool = True,
        retry: bool = True,
        allow_status: tuple[int, ...] = (),
        timeout: float | None = None,
    ) -> httpx.Response:
        host = urlparse(url).netloc
        last: Exception | None = None
        attempts = self._max_retries + 1 if retry else 1
        started = time.monotonic()
        for attempt in range(attempts):
            await self._pace(host)
            try:
                request_kwargs = {}
                if timeout is not None:
                    request_kwargs["timeout"] = timeout
                resp = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    data=form,
                    headers=headers,
                    follow_redirects=follow_redirects,
                    **request_kwargs,
                )
            except httpx.HTTPError as exc:
                last = UpstreamError(f"network error from {host}: {exc}")
                if not retry:
                    raise last from exc
                delay = 0.5 * (2**attempt)
                if time.monotonic() - started + delay > self._settings.retry_budget:
                    raise last from exc
                await asyncio.sleep(delay)
                continue
            if resp.status_code in allow_status:
                return resp
            if resp.status_code in (429, 503):
                last = RateLimited(f"HTTP {resp.status_code} from {host}")
                if not retry:
                    raise last
                delay = self._retry_after(resp, attempt)
                if time.monotonic() - started + delay > self._settings.retry_budget:
                    raise last
                await asyncio.sleep(delay)
                continue
            if resp.status_code in (500, 502, 504):
                # Transient upstream failures: ChEMBL and UniProt both return
                # sporadic 5xx under load, and the same call succeeds on retry.
                last = UpstreamError(f"HTTP {resp.status_code} from {host}")
                if not retry:
                    raise last
                delay = 0.5 * (2**attempt)
                if time.monotonic() - started + delay > self._settings.retry_budget:
                    raise last
                await asyncio.sleep(delay)
                continue
            if resp.status_code in (401, 403):
                raise AuthError(f"HTTP {resp.status_code} from {host}")
            if resp.status_code == 404:
                raise NotFound(f"HTTP 404 from {host}")
            if resp.status_code in (400, 405, 406, 422):
                # Our request no longer matches the documented contract.
                raise UpstreamDrift(
                    f"HTTP {resp.status_code} from {host}: request contract mismatch"
                )
            if resp.status_code >= 400:
                raise UpstreamError(f"HTTP {resp.status_code} from {host}")
            return resp
        raise last if last is not None else UpstreamError(f"request to {host} failed")

    async def get_response(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        follow_redirects: bool = True,
        allow_status: tuple[int, ...] = (),
        retry: bool = True,
        timeout: float | None = None,
    ) -> httpx.Response:
        return await self._request(
            "GET",
            url,
            params=params,
            headers=headers,
            follow_redirects=follow_redirects,
            allow_status=allow_status,
            retry=retry,
            timeout=timeout,
        )

    async def get_json(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        follow_redirects: bool = True,
        retry: bool = True,
        timeout: float | None = None,
    ) -> Any:
        resp = await self.get_response(
            url,
            params=params,
            headers=headers,
            follow_redirects=follow_redirects,
            retry=retry,
            timeout=timeout,
        )
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamDrift(
                f"non-JSON response from {urlparse(url).netloc}: {exc}"
            ) from exc

    async def get_text(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        resp = await self.get_response(url, params=params, headers=headers)
        return resp.text

    async def post_response(
        self,
        url: str,
        json_body: dict,
        headers: dict | None = None,
        retry: bool = True,
    ) -> httpx.Response:
        """POST and return the raw response (for 204/3xx handling by callers)."""
        return await self._request(
            "POST", url, json_body=json_body, headers=headers, retry=retry
        )

    async def post_json(
        self,
        url: str,
        json_body: dict,
        headers: dict | None = None,
        retry: bool = True,
    ) -> Any:
        resp = await self._request(
            "POST", url, json_body=json_body, headers=headers, retry=retry
        )
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamDrift(
                f"non-JSON response from {urlparse(url).netloc}: {exc}"
            ) from exc

    async def post_form(
        self,
        url: str,
        fields: dict,
        headers: dict | None = None,
        retry: bool = True,
    ) -> Any:
        resp = await self._request("POST", url, form=fields, headers=headers, retry=retry)
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON response from {urlparse(url).netloc}: {exc}") from exc
