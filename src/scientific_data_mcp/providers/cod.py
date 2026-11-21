"""Crystallography Open Database provider with mirror failover.

The main host is intermittently unreachable; each tool call tries at most
two hosts once, with short timeouts and a per-host cooldown. Never probes
in the background and never retries a 403/429.
"""

from __future__ import annotations

import time

from ..config import Settings
from ..errors import AuthError, ProviderError, RateLimited, UpstreamError
from ..http import PoliteClient
from .base import Provider, omit_none

_MAIN = "https://www.crystallography.net/cod"
_UK = "https://cod.psdi.ac.uk"
_ES = "https://qiserver.ugr.es/cod"
_HOSTS = (_MAIN, _UK, _ES)


class CodProvider(Provider):
    name = "cod"
    base_url = _MAIN

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)
        self._preferred: str | None = None
        self._preferred_until = 0.0
        self._cooldown_until: dict[str, float] = {}

    def _ordered_hosts(self) -> list[str]:
        now = time.monotonic()
        hosts = []
        if self._preferred and self._preferred_until > now:
            hosts.append(self._preferred)
        hosts.extend(h for h in _HOSTS if h not in hosts)
        ready = [h for h in hosts if self._cooldown_until.get(h, 0.0) <= now]
        return ready[:2]

    async def search(self, params: dict) -> dict:
        hosts = self._ordered_hosts()
        if not hosts:
            raise UpstreamError("all COD hosts are cooling down")
        errors = []
        for host in hosts:
            timeout = 4.0 if host == _MAIN else 8.0
            try:
                payload = await self.http.get_json(
                    f"{host}/result",
                    params={**params, "format": "json"},
                    retry=False,
                    timeout=timeout,
                )
            except ProviderError as exc:
                errors.append(f"{host}: {exc}")
                now = time.monotonic()
                cooldown = 3600.0 if isinstance(exc, (RateLimited, AuthError)) else 600.0
                # main is known-flaky: cool it longer than mirrors
                if host == _MAIN:
                    cooldown = max(cooldown, 600.0)
                self._cooldown_until[host] = now + cooldown
                continue
            except Exception as exc:  # non-JSON etc. is also host-specific
                errors.append(f"{host}: {exc}")
                self._cooldown_until[host] = time.monotonic() + 600.0
                continue
            if not isinstance(payload, list):
                errors.append(f"{host}: response is not a list")
                self._cooldown_until[host] = time.monotonic() + 600.0
                continue
            self._preferred = host
            self._preferred_until = time.monotonic() + 600.0
            self._cooldown_until.pop(host, None)
            return {"items": payload, "host": host, "via_mirror": host != _MAIN}
        raise UpstreamError("COD unavailable; " + " | ".join(errors))

    def normalize(self, row: dict) -> dict:
        return omit_none(
            {
                "cod_id": row.get("file"),
                "formula": row.get("formula"),
                "chemname": row.get("chemname"),
                "mineral": row.get("mineral"),
                "title": row.get("title"),
                "authors": row.get("authors"),
                "journal": row.get("journal"),
                "year": row.get("year"),
                "doi": row.get("doi"),
                "space_group": row.get("sg"),
                "space_group_number": row.get("sgNumber"),
                "method": row.get("method"),
                "cell": _cell(row),
            }
        )


def _cell(row: dict) -> dict | None:
    keys = ("a", "b", "c", "alpha", "beta", "gamma", "vol")
    cell = {k: row.get(k) for k in keys if row.get(k) is not None}
    return cell or None
