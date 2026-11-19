"""ClinicalTrials.gov v2 provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsProvider(Provider):
    name = "clinicaltrials"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(
        self,
        query: str,
        status: str | None = None,
        limit: int = 10,
        cursor: str | None = None,
    ) -> dict:
        params: dict = {
            "query.term": query,
            "pageSize": limit,
            "countTotal": "true",
        }
        if status:
            params["filter.overallStatus"] = status
        if cursor:
            params["pageToken"] = cursor
        payload = await self.http.get_json(self.base_url, params=params)
        if not isinstance(payload, dict) or "studies" not in payload:
            raise UpstreamDrift("ClinicalTrials response has no 'studies' list")
        return {
            "items": [_normalize(study) for study in payload["studies"] or []],
            "total": payload.get("totalCount"),
            "next_cursor": payload.get("nextPageToken"),
        }


def _normalize(study: dict) -> dict:
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    arms = protocol.get("armsInterventionsModule") or {}
    sponsor = (protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    start = status.get("startDateStruct") or {}
    enrollment = design.get("enrollmentInfo") or {}
    interventions = [
        item.get("name") for item in arms.get("interventions") or [] if item.get("name")
    ]
    return omit_none(
        {
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "status": status.get("overallStatus"),
            "study_type": design.get("studyType"),
            "phases": design.get("phases"),
            "conditions": conditions.get("conditions"),
            "interventions": interventions,
            "enrollment": enrollment.get("count"),
            "start_date": start.get("date"),
            "sponsor": sponsor.get("name"),
        }
    )
