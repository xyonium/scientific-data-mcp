"""openFDA provider (keyless; optional free key raises limits).

openFDA answers *no matches* with HTTP 404 + ``error.code == "NOT_FOUND"``,
which is a normal empty result, not an error.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider

_BASE = "https://api.fda.gov"
ENDPOINTS = ("drug/label", "drug/event", "drug/enforcement")


class OpenFdaProvider(Provider):
    name = "openfda"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)
        self._key = settings.openfda_api_key

    async def search(
        self, endpoint: str, query: str, limit: int = 3, skip: int = 0
    ) -> dict:
        params: dict = {"search": query, "limit": limit, "skip": skip}
        if self._key:
            params["api_key"] = self._key
        resp = await self.http.get_response(
            f"{self.base_url}/{endpoint}.json",
            params=params,
            allow_status=(404,),
        )
        if resp.status_code == 404:
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
            if (payload.get("error") or {}).get("code") == "NOT_FOUND":
                return {"items": [], "total": 0}
            raise NotFound(f"openFDA endpoint not found: {endpoint}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamDrift(f"non-JSON openFDA response: {exc}") from exc
        if "results" not in payload:
            raise UpstreamDrift("openFDA response has no 'results' list")
        total = ((payload.get("meta") or {}).get("results") or {}).get("total")
        return {"items": payload["results"], "total": total}
