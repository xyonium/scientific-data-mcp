"""UniChem compound cross-reference provider (keyless)."""

from __future__ import annotations

import re

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/unichem/rest"
_INCHIKEY = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")


class UniChemProvider(Provider):
    name = "unichem"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def map_inchikey(self, inchikey: str, limit: int = 20) -> list[dict]:
        if not _INCHIKEY.match(inchikey):
            raise ValueError(f"invalid InChIKey: {inchikey!r}")
        payload = await self.http.get_json(
            f"{self.base_url}/verbose_inchikey/{inchikey}"
        )
        if not isinstance(payload, list):
            raise UpstreamDrift("UniChem response is not a list")
        items = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            ids = [x for x in (row.get("src_compound_id") or []) if x]
            if not ids:
                continue
            items.append(
                omit_none(
                    {
                        "source": row.get("name_label") or row.get("name"),
                        "source_long": row.get("name_long"),
                        "source_id": row.get("src_id"),
                        "compound_ids": ids,
                        "url": row.get("src_url"),
                    }
                )
            )
            if len(items) >= limit:
                break
        return items
