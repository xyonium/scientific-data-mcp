"""NCBI Gene provider via E-utilities (optional NCBI_API_KEY)."""

from __future__ import annotations

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "scientific-data-mcp"


class GeneProvider(Provider):
    name = "ncbi_gene"
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

    async def record(self, identifier: str, organism: int = 9606) -> dict:
        if identifier.isdigit():
            gene_id = identifier
        else:
            payload = await self.http.get_json(
                f"{self.base_url}/esearch.fcgi",
                params=self._params(
                    db="gene",
                    term=f"{identifier}[gene] AND {organism}[taxid]",
                    retmode="json",
                    retmax=1,
                ),
            )
            result = payload.get("esearchresult")
            if not isinstance(result, dict):
                raise UpstreamDrift("NCBI Gene esearch response has no esearchresult")
            ids = result.get("idlist") or []
            if not ids:
                raise NotFound(f"no NCBI Gene record for {identifier!r}")
            gene_id = str(ids[0])
        payload = await self.http.get_json(
            f"{self.base_url}/esummary.fcgi",
            params=self._params(db="gene", id=gene_id, retmode="json"),
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise UpstreamDrift("NCBI Gene esummary response has no result")
        item = result.get(str(gene_id))
        if not isinstance(item, dict):
            raise NotFound(f"no NCBI Gene record for id {gene_id}")
        organism_info = item.get("organism") or {}
        return omit_none(
            {
                "gene_id": str(gene_id),
                "symbol": item.get("name"),
                "description": item.get("description"),
                "chromosome": item.get("chromosome"),
                "map_location": item.get("maplocation"),
                "aliases": item.get("otheraliases"),
                "summary": item.get("summary"),
                "organism": organism_info.get("scientificname"),
                "taxid": organism_info.get("taxid"),
                "gene_type": item.get("geneticsource"),
            }
        )
