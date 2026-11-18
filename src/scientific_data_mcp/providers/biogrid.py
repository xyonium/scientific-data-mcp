"""BioGRID provider (key-gated).

The REST API needs a free access key as a query parameter. The provider is
only constructed when ``BIOGRID_ACCESS_KEY`` is set, so a keyless install
keeps the base tool surface.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://webservice.thebiogrid.org"


class BioGridProvider(Provider):
    name = "biogrid"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)
        self._key = settings.biogrid_access_key or ""

    async def interactions(
        self,
        genes: str,
        organism: int = 9606,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/interactions/",
            params={
                "accesskey": self._key,
                "format": "json",
                "searchNames": "true",
                "geneList": genes,
                "taxId": organism,
                "max": limit,
                "start": offset,
            },
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift(
                f"BioGRID interactions response is {type(payload).__name__}, expected object"
            )
        rows = [_normalize(key, row) for key, row in payload.items()]
        rows.sort(key=lambda row: row.get("interaction_id") or 0)
        return {
            "items": rows,
            "next_offset": offset + len(rows) if len(rows) >= limit else None,
        }


def _normalize(key: str, row: dict) -> dict:
    return omit_none(
        {
            "interaction_id": row.get("BIOGRID_INTERACTION_ID") or _maybe_int(key),
            "gene_a": row.get("OFFICIAL_SYMBOL_A"),
            "gene_b": row.get("OFFICIAL_SYMBOL_B"),
            "entrez_a": row.get("ENTREZ_GENE_A"),
            "entrez_b": row.get("ENTREZ_GENE_B"),
            "organism_a": row.get("ORGANISM_A"),
            "organism_b": row.get("ORGANISM_B"),
            "experimental_system": row.get("EXPERIMENTAL_SYSTEM"),
            "system_type": row.get("EXPERIMENTAL_SYSTEM_TYPE"),
            "pubmed_id": row.get("PUBMED_ID"),
            "throughput": row.get("THROUGHPUT"),
            "score": row.get("SCORE"),
        }
    )


def _maybe_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
