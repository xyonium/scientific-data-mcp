"""Open Targets Platform GraphQL provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider

_BASE = "https://api.platform.opentargets.org/api/v4/graphql"

_SEARCH = """
query Search($q: String!, $entity: [String!]!, $size: Int!) {
  search(queryString: $q, entityNames: $entity, page: {index: 0, size: $size}) {
    hits { id name entity }
  }
}
"""

_TARGET = """
query Target($id: String!, $size: Int!) {
  target(ensemblId: $id) {
    id
    approvedSymbol
    approvedName
    functionDescriptions
    associatedDiseases(page: {index: 0, size: $size}) {
      count
      rows { score disease { id name } }
    }
  }
}
"""

_DISEASE = """
query Disease($id: String!, $size: Int!) {
  disease(efoId: $id) {
    id
    name
    description
    associatedTargets(page: {index: 0, size: $size}) {
      count
      rows { score target { id approvedSymbol approvedName } }
    }
  }
}
"""


class OpenTargetsProvider(Provider):
    name = "opentargets"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(self, query: str, entity: str, size: int = 1) -> list[dict]:
        payload = await self._query(_SEARCH, {"q": query, "entity": [entity], "size": size})
        hits = ((payload.get("data") or {}).get("search") or {}).get("hits")
        if not isinstance(hits, list):
            raise UpstreamDrift("Open Targets search response has no hits list")
        return hits

    async def target(self, ensembl_id: str, size: int = 5) -> dict:
        payload = await self._query(_TARGET, {"id": ensembl_id, "size": size})
        target = (payload.get("data") or {}).get("target")
        if target is None:
            raise NotFound(f"Open Targets target not found: {ensembl_id}")
        assoc = target.get("associatedDiseases") or {}
        return {
            "id": target.get("id"),
            "symbol": target.get("approvedSymbol"),
            "name": target.get("approvedName"),
            "function_descriptions": target.get("functionDescriptions") or [],
            "count": assoc.get("count"),
            "items": [
                {"score": row.get("score"), "disease": row.get("disease")}
                for row in assoc.get("rows") or []
            ],
        }

    async def disease(self, efo_id: str, size: int = 5) -> dict:
        payload = await self._query(_DISEASE, {"id": efo_id, "size": size})
        disease = (payload.get("data") or {}).get("disease")
        if disease is None:
            raise NotFound(f"Open Targets disease not found: {efo_id}")
        assoc = disease.get("associatedTargets") or {}
        return {
            "id": disease.get("id"),
            "name": disease.get("name"),
            "description": disease.get("description"),
            "count": assoc.get("count"),
            "items": [
                {"score": row.get("score"), "target": row.get("target")}
                for row in assoc.get("rows") or []
            ],
        }

    async def _query(self, query: str, variables: dict) -> dict:
        payload = await self.http.post_json(
            self.base_url,
            {"query": query, "variables": variables},
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift("Open Targets response is not an object")
        errors = payload.get("errors")
        if errors:
            message = "; ".join(str(err.get("message", err)) for err in errors)
            raise UpstreamDrift(f"Open Targets GraphQL error: {message}")
        return payload
