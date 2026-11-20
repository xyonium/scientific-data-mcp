"""NCI Genomic Data Commons (GDC) project catalogue (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://api.gdc.cancer.gov"


class GdcProvider(Provider):
    name = "gdc"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def projects(self, query: str, limit: int = 10) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/projects", params={"size": 2000, "format": "json"}
        )
        if not isinstance(payload, dict) or "data" not in payload:
            raise UpstreamDrift("GDC response has no data object")
        hits = (payload["data"] or {}).get("hits")
        if not isinstance(hits, list):
            raise UpstreamDrift("GDC response has no project hits list")
        needle = query.casefold()
        items = []
        for hit in hits:
            haystack = " ".join(
                [
                    str(hit.get("project_id") or ""),
                    str(hit.get("name") or ""),
                    " ".join(hit.get("primary_site") or []),
                    " ".join(hit.get("disease_type") or []),
                ]
            ).casefold()
            if needle in haystack:
                items.append(_normalize(hit))
        return {"items": items[:limit], "total": len(items)}


def _normalize(hit: dict) -> dict:
    return omit_none(
        {
            "project_id": hit.get("project_id"),
            "name": hit.get("name"),
            "primary_site": hit.get("primary_site") or None,
            "disease_type": hit.get("disease_type") or None,
        }
    )
