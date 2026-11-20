"""BindingDB REST provider (keyless; courtesy limit ~1 req/s)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://bindingdb.org/rest"


class BindingDbProvider(Provider):
    name = "bindingdb"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def ligands(
        self, uniprot: str, cutoff_nm: float = 10000, limit: int = 20
    ) -> dict:
        resp = await self.http.get_response(
            f"{self.base_url}/getLigandsByUniprot",
            params={
                "uniprot": f"{uniprot};{cutoff_nm:g}",
                "response": "application/json",
            },
            retry=False,
        )
        if not resp.text.strip():
            return {"items": [], "total": 0}
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamDrift(f"non-JSON BindingDB response: {exc}") from exc
        data = payload.get("getLindsByUniprotResponse") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise UpstreamDrift("BindingDB response has no getLindsByUniprotResponse")
        rows = data.get("bdb.affinities") or []
        items = [_normalize(row) for row in rows[:limit]]
        return {"items": items, "total": int(data.get("bdb.hit") or len(rows))}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "monomer_id": row.get("bdb.monomerid"),
            "smiles": row.get("bdb.smile"),
            "affinity_type": row.get("bdb.affinity_type"),
            "affinity": (row.get("bdb.affinity") or "").strip() or None,
        }
    )
