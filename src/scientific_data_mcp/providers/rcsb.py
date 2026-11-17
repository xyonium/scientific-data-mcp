"""RCSB PDB provider: Data API for entries/entities, Search API for text search.

Keyless. Entity descriptions are fetched for the first few polymer entities
only, so a large assembly does not fan out into dozens of calls.
"""

from __future__ import annotations

from urllib.parse import quote

from ..config import Settings
from ..errors import ProviderError, UpstreamError
from ..http import PoliteClient
from .base import Provider, omit_none

_DATA = "https://data.rcsb.org/rest/v1/core"
_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
_MAX_ENTITIES = 5


class RcsbProvider(Provider):
    name = "rcsb"
    base_url = _DATA

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def entry(self, pdb_id: str) -> dict:
        pdb_id = pdb_id.upper()
        payload = await self.http.get_json(f"{self.base_url}/entry/{quote(pdb_id, safe='')}")
        identifiers = payload.get("rcsb_entry_container_identifiers") or {}
        entity_ids = list(identifiers.get("polymer_entity_ids") or [])
        entities = []
        for entity_id in entity_ids[:_MAX_ENTITIES]:
            try:
                entities.append(await self.entity(pdb_id, entity_id))
            except ProviderError:
                # A missing entity must not sink the whole entry.
                continue
        return omit_none(
            {
                "pdb_id": pdb_id,
                "title": (payload.get("struct") or {}).get("title"),
                "method": ((payload.get("exptl") or [{}])[0]).get("method"),
                "resolution": ((payload.get("rcsb_entry_info") or {}).get("resolution_combined") or [None])[0],
                "deposited": (payload.get("rcsb_accession_info") or {}).get("deposit_date"),
                "polymer_entity_ids": entity_ids,
                "entities": entities,
            }
        )

    async def entity(self, pdb_id: str, entity_id: str) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/polymer_entity/{quote(pdb_id.upper(), safe='')}/{quote(str(entity_id), safe='')}"
        )
        return omit_none(
            {
                "entity_id": str(entity_id),
                "description": (payload.get("rcsb_polymer_entity") or {}).get("pdbx_description"),
                "type": (payload.get("entity_poly") or {}).get("type"),
                "length": (payload.get("entity_poly") or {}).get("rcsb_sample_sequence_length"),
                "chains": (
                    payload.get("rcsb_polymer_entity_container_identifiers") or {}
                ).get("auth_asym_ids") or [],
            }
        )

    async def search(self, query: str, rows: int = 10, start: int = 0) -> dict:
        resp = await self.http.post_response(
            _SEARCH,
            {
                "query": {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {"value": query},
                },
                "return_type": "entry",
                "request_options": {"paginate": {"start": start, "rows": rows}},
            },
        )
        # RCSB answers 204 with an empty body when a search matches nothing.
        if resp.status_code == 204:
            return {"total": 0, "identifiers": [], "next_start": None}
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON RCSB search response: {exc}") from exc
        total = payload.get("total_count", 0)
        identifiers = [row["identifier"] for row in payload.get("result_set") or []]
        next_start = start + rows if start + rows < total else None
        return {"total": total, "identifiers": identifiers, "next_start": next_start}
