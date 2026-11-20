"""Ensembl REST provider (keyless).

Access policy: one request per tool call, no retries, conservative pacing.
A 403/429 from the Ensembl edge is treated as unavailable and is NOT
retried; do not probe this host outside real tool calls.
"""

from __future__ import annotations

import re

from ..config import Settings
from ..errors import UpstreamDrift, UpstreamError
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://rest.ensembl.org"
_GENE_ID = re.compile(r"^ENS[A-Z]*G\d+$")


class EnsemblProvider(Provider):
    name = "ensembl"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def gene(self, identifier: str, species: str) -> dict:
        if _GENE_ID.match(identifier):
            url = f"{self.base_url}/lookup/id/{identifier}"
            params = {"species": species, "content-type": "application/json"}
        else:
            url = f"{self.base_url}/lookup/symbol/{species}/{identifier}"
            params = {"content-type": "application/json"}
        resp = await self.http.get_response(
            url,
            params=params,
            headers={"Accept": "application/json"},
            retry=False,
            allow_status=(403,),
        )
        if resp.status_code in (403, 429):
            raise UpstreamError(
                f"HTTP {resp.status_code} from rest.ensembl.org (edge/WAF); not retrying"
            )
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamDrift(f"non-JSON Ensembl response: {exc}") from exc
        if not isinstance(payload, dict) or "id" not in payload:
            raise UpstreamDrift("Ensembl gene response has no id")
        return _normalize(payload)


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "gene_id": row.get("id"),
            "symbol": row.get("display_name"),
            "description": row.get("description"),
            "biotype": row.get("biotype"),
            "species": row.get("species"),
            "chromosome": row.get("seq_region_name"),
            "start": row.get("start"),
            "end": row.get("end"),
            "strand": row.get("strand"),
            "assembly": row.get("assembly_name"),
            "canonical_transcript": row.get("canonical_transcript"),
            "version": row.get("version"),
        }
    )
