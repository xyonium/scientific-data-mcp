"""GWAS Catalog REST v2 provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/gwas/rest/api/v2"
_BY = ("rs_id", "efo_trait", "efo_id", "mapped_gene")


class GwasProvider(Provider):
    name = "gwas"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def associations(
        self, by: str, query: str, limit: int = 10, page: int = 0
    ) -> dict:
        if by not in _BY:
            raise ValueError(f"unsupported GWAS filter: {by}")
        payload = await self.http.get_json(
            f"{self.base_url}/associations",
            params={by: query, "size": limit, "page": page},
        )
        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        if not isinstance(embedded, dict):
            raise UpstreamDrift("GWAS response has no _embedded object")
        rows = embedded.get("associations")
        if not isinstance(rows, list):
            raise UpstreamDrift("GWAS response has no associations list")
        page_info = payload.get("page")
        if not isinstance(page_info, dict):
            raise UpstreamDrift("GWAS response has no page info")
        try:
            total = int(page_info.get("totalElements"))
        except (TypeError, ValueError) as exc:
            raise UpstreamDrift("GWAS page.totalElements is not numeric") from exc
        return {"items": [_normalize(row) for row in rows], "total": total}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "association_id": row.get("association_id"),
            "p_value": row.get("p_value"),
            "reported_trait": row.get("reported_trait") or None,
            "efo_traits": [
                {"efo_id": x.get("efo_id"), "efo_trait": x.get("efo_trait")}
                for x in (row.get("efo_traits") or [])
                if isinstance(x, dict)
            ]
            or None,
            "mapped_genes": row.get("mapped_genes") or None,
            "risk_frequency": row.get("risk_frequency"),
            "beta": row.get("beta"),
            "snp_effect_allele": row.get("snp_effect_allele") or None,
            "pubmed_id": row.get("pubmed_id"),
            "first_author": row.get("first_author"),
            "accession_id": row.get("accession_id"),
        }
    )
