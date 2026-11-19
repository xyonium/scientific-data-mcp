"""cBioPortal study catalogue (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.cbioportal.org/api"


class CbioPortalProvider(Provider):
    name = "cbioportal"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def studies(self, query: str, limit: int = 10) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/studies",
            params={"keyword": query, "pageSize": limit, "pageNumber": 0},
        )
        if not isinstance(payload, list):
            raise UpstreamDrift("cBioPortal response is not a study list")
        return {"items": [_normalize(study) for study in payload], "total": None}


def _normalize(study: dict) -> dict:
    return omit_none(
        {
            "study_id": study.get("studyId"),
            "name": study.get("name"),
            "description": study.get("description"),
            "cancer_type_id": study.get("cancerTypeId"),
            "sample_count": study.get("allSampleCount"),
            "pmid": study.get("pmid"),
            "citation": study.get("citation"),
            "reference_genome": study.get("referenceGenome"),
        }
    )
