"""M-CSA mechanism/catalytic-site atlas provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/thornton-srv/m-csa"


class McsaProvider(Provider):
    name = "mcsa"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def entries(self, params: dict, limit: int = 5) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/api/entries/", params={**params, "format": "json"}
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift("M-CSA response is not an object")
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise UpstreamDrift("M-CSA response has no results list")
        try:
            total = int(payload.get("count"))
        except (TypeError, ValueError) as exc:
            raise UpstreamDrift("M-CSA count is not numeric") from exc
        return {"items": [_normalize(row) for row in rows[:limit]], "total": total}


def _normalize(row: dict) -> dict:
    residues = []
    for res in row.get("residues") or []:
        chains = res.get("residue_chains") or []
        chain = chains[0] if chains else {}
        residues.append(
            omit_none(
                {
                    "residue": (
                        f"{chain.get('code')}{chain.get('resid')}"
                        if chain.get("code") and chain.get("resid") is not None
                        else None
                    ),
                    "roles": [
                        r.get("function") for r in (res.get("roles") or [])
                        if isinstance(r, dict) and r.get("function")
                    ]
                    or None,
                    "roles_summary": res.get("roles_summary"),
                    "pdb_id": chain.get("pdb_id"),
                    "chain": chain.get("chain_name"),
                }
            )
        )
    reaction = row.get("reaction") or {}
    compounds = [
        omit_none(
            {
                "name": c.get("name"),
                "type": c.get("type"),
                "chebi_id": c.get("chebi_id"),
                "count": c.get("count"),
            }
        )
        for c in (reaction.get("compounds") or [])
        if isinstance(c, dict)
    ]
    return omit_none(
        {
            "mcsa_id": row.get("mcsa_id"),
            "enzyme_name": row.get("enzyme_name"),
            "ec_numbers": row.get("all_ecs") or None,
            "uniprot_id": row.get("reference_uniprot_id"),
            "description": row.get("description"),
            "reaction": omit_none({"ec": reaction.get("ec"), "compounds": compounds}) if reaction else None,
            "residues": residues or None,
        }
    )
