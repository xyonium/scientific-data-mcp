"""NCBI GEO DataSets provider via E-utilities (optional NCBI_API_KEY)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "scientific-data-mcp"


class GeoProvider(Provider):
    name = "geo"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    def _params(self, **extra: object) -> dict:
        params: dict = {"tool": _TOOL, **extra}
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        if self.settings.ncbi_email:
            params["email"] = self.settings.ncbi_email
        return params

    async def search(self, query: str, limit: int = 10) -> dict:
        search = await self.http.get_json(
            f"{self.base_url}/esearch.fcgi",
            params=self._params(
                db="gds", term=query, retmode="json", retmax=limit
            ),
        )
        result = search.get("esearchresult")
        if not isinstance(result, dict):
            raise UpstreamDrift("GEO esearch response has no esearchresult")
        ids = result.get("idlist") or []
        total = int(result.get("count") or 0)
        if not ids:
            return {"items": [], "total": total}
        summary = await self.http.get_json(
            f"{self.base_url}/esummary.fcgi",
            params=self._params(db="gds", id=",".join(ids), retmode="json"),
        )
        data = summary.get("result")
        if not isinstance(data, dict):
            raise UpstreamDrift("GEO esummary response has no result")
        items = [
            _normalize(data[str(uid)])
            for uid in ids
            if isinstance(data.get(str(uid)), dict)
        ]
        return {"items": items, "total": total}


def _normalize(item: dict) -> dict:
    return omit_none(
        {
            "accession": item.get("accession"),
            "title": item.get("title"),
            "summary": item.get("summary"),
            "dataset_type": item.get("gdstype"),
            "organism": item.get("taxon"),
            "n_samples": item.get("n_samples"),
            "release_date": item.get("pdat"),
            "pubmed_ids": item.get("pubmedids") or None,
        }
    )
