"""DailyMed provider (keyless, NLM)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


class DailyMedProvider(Provider):
    name = "dailymed"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(self, query: str, limit: int = 5) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/spls.json",
            params={"drug_name": query, "pagesize": limit, "page": 1},
        )
        if not isinstance(payload, dict) or "data" not in payload:
            raise UpstreamDrift("DailyMed response has no data list")
        items = [_normalize(row) for row in payload["data"] or []]
        total = (payload.get("metadata") or {}).get("total_elements")
        return {"items": items, "total": total}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "setid": row.get("setid"),
            "title": row.get("title"),
            "published_date": row.get("published_date"),
            "spl_version": row.get("spl_version"),
        }
    )
