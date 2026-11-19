"""STRING provider (keyless).

Uses the interaction_partners endpoint: given one or more identifiers it
returns the partners and the combined/evidence channel scores (0-1).
"""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://string-db.org/api/json"
_CHANNELS = ("nscore", "fscore", "pscore", "ascore", "escore", "dscore", "tscore")


class StringDbProvider(Provider):
    name = "string"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def partners(
        self,
        identifiers: list[str],
        organism: int = 9606,
        limit: int = 20,
        min_score: int | None = None,
    ) -> list[dict]:
        params: dict = {
            "identifiers": "\r".join(identifiers),
            "species": organism,
            "limit": limit,
            "caller_identity": "scientific-data-mcp",
        }
        if min_score is not None:
            params["required_score"] = min_score
        payload = await self.http.get_json(f"{self.base_url}/interaction_partners", params=params)
        if not isinstance(payload, list):
            raise UpstreamDrift(
                f"STRING response is {type(payload).__name__}, expected a list"
            )
        return [_normalize(row) for row in payload]


def _normalize(row: dict) -> dict:
    scores = {name: row.get(name) for name in _CHANNELS if row.get(name)}
    return omit_none(
        {
            "gene_a": row.get("preferredName_A"),
            "gene_b": row.get("preferredName_B"),
            "organism": row.get("ncbiTaxonId"),
            "score": row.get("score"),
            "scores": scores or None,
            "string_id_a": row.get("stringId_A"),
            "string_id_b": row.get("stringId_B"),
        }
    )
