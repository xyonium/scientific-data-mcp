"""QuickGO provider (keyless, EBI)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/QuickGO/services"


class QuickGoProvider(Provider):
    name = "quickgo"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def annotations(self, accession: str, limit: int = 20) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/annotation/search",
            params={"geneProductId": f"UniProtKB:{accession}", "limit": limit},
        )
        if not isinstance(payload, dict) or "results" not in payload:
            raise UpstreamDrift("QuickGO response has no results list")
        items = [_normalize(row) for row in payload["results"] or []]
        return {"items": items, "total": payload.get("numberOfHits")}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "go_id": row.get("goId"),
            "go_name": row.get("goName"),
            "qualifier": row.get("qualifier"),
            "evidence": row.get("goEvidence") or row.get("evidenceCode"),
            "aspect": row.get("goAspect"),
            "reference": row.get("reference"),
            "assigned_by": row.get("assignedBy"),
            "taxon_id": row.get("taxonId"),
        }
    )
