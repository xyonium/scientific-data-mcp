"""ClinVar provider via E-utilities (optional NCBI_API_KEY)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "scientific-data-mcp"


class ClinVarProvider(Provider):
    name = "clinvar"
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
                db="clinvar", term=query, retmode="json", retmax=limit
            ),
        )
        result = search.get("esearchresult")
        if not isinstance(result, dict):
            raise UpstreamDrift("ClinVar esearch response has no esearchresult")
        ids = result.get("idlist") or []
        total = int(result.get("count") or 0)
        if not ids:
            return {"items": [], "total": total}
        summary = await self.http.get_json(
            f"{self.base_url}/esummary.fcgi",
            params=self._params(db="clinvar", id=",".join(ids), retmode="json"),
        )
        data = summary.get("result")
        if not isinstance(data, dict):
            raise UpstreamDrift("ClinVar esummary response has no result")
        items = [_normalize(data[str(uid)]) for uid in ids if isinstance(data.get(str(uid)), dict)]
        return {"items": items, "total": total}


def _normalize(item: dict) -> dict:
    germline = item.get("germline_classification") or {}
    traits = [
        trait.get("trait_name")
        for trait in germline.get("trait_set") or []
        if trait.get("trait_name")
    ]
    variation = (item.get("variation_set") or [{}])[0]
    genes = [
        gene.get("symbol") for gene in item.get("genes") or [] if gene.get("symbol")
    ]
    return omit_none(
        {
            "accession": item.get("accession"),
            "title": item.get("title"),
            "classification": germline.get("description") or None,
            "review_status": germline.get("review_status") or None,
            "last_evaluated": germline.get("last_evaluated") or None,
            "conditions": traits or None,
            "genes": genes or None,
            "protein_change": item.get("protein_change") or None,
            "molecular_consequences": item.get("molecular_consequence_list") or None,
            "variation": {
                "name": variation.get("variation_name"),
                "type": variation.get("variant_type"),
                "spdi": variation.get("canonical_spdi"),
            }
            if variation.get("variation_name")
            else None,
        }
    )
