"""AlphaFold DB provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://alphafold.ebi.ac.uk/api"
_MAX_PREDICTIONS = 20


class AlphaFoldProvider(Provider):
    name = "alphafold"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def prediction(self, accession: str) -> dict:
        resp = await self.http.get_response(
            f"{self.base_url}/prediction/{accession}", allow_status=(400,)
        )
        if resp.status_code == 400:
            try:
                detail = (resp.json() or {}).get("error", "")
            except ValueError:
                detail = ""
            if "identifier" in detail.lower() or "format" in detail.lower():
                raise ValueError(
                    f"invalid AlphaFold identifier: {accession}"
                    + (f" ({detail})" if detail else "")
                )
            raise UpstreamDrift(f"AlphaFold HTTP 400: {detail or 'no detail'}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamDrift(f"non-JSON AlphaFold response: {exc}") from exc
        if not isinstance(payload, list):
            raise UpstreamDrift(
                f"AlphaFold response is {type(payload).__name__}, expected a list"
            )
        predictions = [_normalize(row) for row in payload[:_MAX_PREDICTIONS]]
        return {"accession": accession.upper(), "predictions": predictions}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "entry_id": row.get("entryId"),
            "version": row.get("latestVersion"),
            "start": row.get("uniprotStart"),
            "end": row.get("uniprotEnd"),
            "plddt": row.get("globalMetricValue"),
            "pdb_url": row.get("pdbUrl"),
            "cif_url": row.get("cifUrl"),
            "pae_image_url": row.get("paeImageUrl"),
        }
    )
