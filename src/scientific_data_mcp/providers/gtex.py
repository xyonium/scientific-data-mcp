"""GTEx expression provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://gtexportal.org/api/v2"


class GtexProvider(Provider):
    name = "gtex"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def expression(
        self, gene_id: str, dataset: str = "gtex_v8", limit: int = 20
    ) -> dict:
        reference = await self.http.get_json(
            f"{self.base_url}/reference/gene", params={"geneId": gene_id}
        )
        data = reference.get("data") if isinstance(reference, dict) else None
        if not isinstance(data, list):
            raise UpstreamDrift("GTEx reference response has no data list")
        if not data:
            raise NotFound(f"no GTEx gene for {gene_id}")
        gencode_id = data[0].get("gencodeId")
        if not gencode_id:
            raise UpstreamDrift("GTEx reference response has no gencodeId")
        payload = await self.http.get_json(
            f"{self.base_url}/expression/medianGeneExpression",
            params={"gencodeId": gencode_id, "datasetId": dataset},
        )
        if not isinstance(payload, dict) or "data" not in payload:
            raise UpstreamDrift("GTEx expression response has no data list")
        rows = payload["data"] or []
        total = (payload.get("paging_info") or {}).get("totalNumberOfItems")
        return {
            "items": [_normalize(row) for row in rows[:limit]],
            "total": total,
            "gene_symbol": data[0].get("geneSymbol"),
            "gencode_id": gencode_id,
        }


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "tissue_site_detail_id": row.get("tissueSiteDetailId"),
            "ontology_id": row.get("ontologyId"),
            "median": row.get("median"),
            "unit": row.get("unit"),
            "dataset_id": row.get("datasetId"),
        }
    )
