"""ClinPGx (PharmGKB) summary annotations provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://api.clinpgx.org/v1"


class ClinPgxProvider(Provider):
    name = "clinpgx"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def annotations(
        self, gene: str, drug: str | None, limit: int = 10
    ) -> list[dict]:
        params = {"location.genes.symbol": gene}
        if drug:
            params["relatedChemicals.name"] = drug
        payload = await self.http.get_json(
            f"{self.base_url}/data/summaryAnnotation", params=params
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift("ClinPGx response is not an object")
        if payload.get("status") not in (None, "success"):
            raise UpstreamDrift(f"ClinPGx status: {payload.get('status')!r}")
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise UpstreamDrift("ClinPGx response has no data list")
        return [_normalize(row) for row in rows[:limit]]


def _names(items, key="name"):
    out = []
    for item in items or []:
        if isinstance(item, dict) and item.get(key):
            out.append(item[key])
    return out or None


def _normalize(row: dict) -> dict:
    genes = (row.get("location") or {}).get("genes") or []
    chemicals = row.get("relatedChemicals") or []
    return omit_none(
        {
            "annotation_id": row.get("id"),
            "accession_id": row.get("accessionId"),
            "name": row.get("name"),
            "gene": genes[0].get("symbol") if genes else None,
            "gene_id": genes[0].get("id") if genes else None,
            "drug": chemicals[0].get("name") if chemicals else None,
            "drug_id": chemicals[0].get("id") if chemicals else None,
            "level_of_evidence": (row.get("levelOfEvidence") or {}).get("term"),
            "allele_phenotypes": [
                {
                    "allele": x.get("allele"),
                    "phenotype": x.get("phenotype"),
                    "limited_evidence": x.get("limitedEvidence"),
                }
                for x in (row.get("allelePhenotypes") or [])
                if isinstance(x, dict)
            ]
            or None,
            "related_guidelines": _names(row.get("relatedGuidelines")),
            "related_diseases": _names(row.get("relatedDiseases")),
            "related_labels": _names(row.get("relatedLabels")),
            "score": row.get("score"),
        }
    )
