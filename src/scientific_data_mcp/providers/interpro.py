"""InterPro provider (keyless, EBI)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/interpro/api"


class InterProProvider(Provider):
    name = "interpro"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def entries(self, accession: str, limit: int = 20) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/entry/all/protein/uniprot/{accession}/",
            params={"page_size": limit},
        )
        if payload is None:  # InterPro returns 204 for an unknown/no-entry protein
            return {"items": [], "total": 0}
        if not isinstance(payload, dict) or "results" not in payload:
            raise UpstreamDrift("InterPro response has no results list")
        items = [
            _normalize(result.get("metadata") or {})
            for result in payload["results"] or []
        ]
        return {"items": items, "total": payload.get("count")}


def _normalize(metadata: dict) -> dict:
    go_terms = [
        {"id": term.get("identifier"), "name": term.get("name")}
        for term in metadata.get("go_terms") or []
        if term.get("identifier")
    ]
    return omit_none(
        {
            "accession": metadata.get("accession"),
            "name": metadata.get("name"),
            "type": metadata.get("type"),
            "source_database": metadata.get("source_database"),
            "go_terms": go_terms or None,
        }
    )
