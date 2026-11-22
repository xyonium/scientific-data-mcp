"""SABIO-RK export API provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://sabiork.h-its.org/export-api/sabio"


class SabioProvider(Provider):
    name = "sabio"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def kinetics(self, ec_number: str, page: int = 1, limit: int = 20) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/kinlaw-entry/json",
            params={
                "q": f"ecnumber:{ec_number}",
                "page": page,
                "pageSize": limit,
            },
        )
        if not isinstance(payload, dict):
            raise UpstreamDrift("SABIO response is not an object")
        meta = payload.get("meta")
        rows = payload.get("data")
        if not isinstance(meta, dict) or not isinstance(rows, list):
            raise UpstreamDrift("SABIO response has no meta/data")
        try:
            total = int(meta.get("total_count"))
            page_size = int(meta.get("page_size"))
        except (TypeError, ValueError) as exc:
            raise UpstreamDrift("SABIO meta counts are not numeric") from exc
        return {
            "items": [_normalize(row) for row in rows],
            "total": total,
            "page": int(meta.get("page") or page),
            "page_size": page_size,
        }


def _normalize(row: dict) -> dict:
    enzyme = row.get("enzyme_description") or {}
    reaction = row.get("reaction") or {}
    kinetic = row.get("kineticlaw") or {}
    conditions = row.get("experimental_conditions") or {}
    publication = row.get("publication") or {}
    params = []
    for p in kinetic.get("parameter") or []:
        if not isinstance(p, dict):
            continue
        params.append(
            omit_none(
                {
                    "name": p.get("name"),
                    "value": p.get("start_value"),
                    "end_value": p.get("end_value"),
                    "standard_deviation": p.get("standard_deviation"),
                    "unit": (p.get("unit") or {}).get("name"),
                    "species": (p.get("species") or {}).get("species_key"),
                    "comment": p.get("comment"),
                }
            )
        )
    ph = conditions.get("envvar_ph") or {}
    temp = conditions.get("envvar_temperature") or {}
    return omit_none(
        {
            "sabio_id": row.get("id"),
            "organism": (row.get("general") or {}).get("organism", {}).get("name"),
            "ec_number": enzyme.get("ec_number"),
            "enzyme_name": enzyme.get("enzyme_name"),
            "mutant": enzyme.get("mutant_spec"),
            "wildtype": enzyme.get("wildtype"),
            "equation": reaction.get("equation"),
            "kinetic_law_type": (kinetic.get("kinlaw_type") or {}).get("name"),
            "formula": kinetic.get("formula"),
            "parameters": params or None,
            "ph": ph.get("start_value"),
            "temperature_c": temp.get("start_value"),
            "buffer": conditions.get("buffer"),
            "pubmed_id": publication.get("pubmed_id"),
            "publication_title": publication.get("title"),
            "publication_year": publication.get("year"),
            "journal": publication.get("journal"),
        }
    )
