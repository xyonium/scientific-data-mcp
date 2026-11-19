"""Human Phenotype Ontology provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://ontology.jax.org/api/hp"


class HpoProvider(Provider):
    name = "hpo"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        payload = await self.http.get_json(
            f"{self.base_url}/search", params={"q": query, "limit": limit}
        )
        if not isinstance(payload, dict) or "terms" not in payload:
            raise UpstreamDrift("HPO search response has no terms list")
        return [_normalize(term) for term in payload["terms"] or []]

    async def term(self, term_id: str) -> dict:
        payload = await self.http.get_json(f"{self.base_url}/terms/{term_id}")
        if not isinstance(payload, dict) or "id" not in payload:
            raise UpstreamDrift("HPO term response has no id")
        return _normalize(payload)


def _normalize(term: dict) -> dict:
    return omit_none(
        {
            "id": term.get("id"),
            "name": term.get("name"),
            "definition": term.get("definition"),
            "synonyms": term.get("synonyms") or None,
            "descendant_count": term.get("descendantCount"),
        }
    )
