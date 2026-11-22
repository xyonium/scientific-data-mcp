"""Rhea reaction database provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.rhea-db.org"


class RheaProvider(Provider):
    name = "rhea"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(self, query: str, limit: int = 10) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/rhea", params={"query": query, "format": "json"}
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift("Rhea response is not an object")
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise UpstreamDrift("Rhea response has no results list")
        try:
            total = int(payload.get("count"))
        except (TypeError, ValueError) as exc:
            raise UpstreamDrift("Rhea count is not numeric") from exc
        return {"items": [_normalize(row) for row in rows[:limit]], "total": total}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "rhea_id": row.get("id"),
            "equation": row.get("equation"),
            "status": row.get("status"),
            "comment": row.get("comment"),
            "balanced": row.get("balanced"),
            "transport": row.get("transport"),
        }
    )
