"""Reactome Content Service provider (keyless)."""

from __future__ import annotations

import html
import re

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://reactome.org/ContentService"
_TAG = re.compile(r"<[^>]+>")


class ReactomeProvider(Provider):
    name = "reactome"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def pathways(
        self, query: str, species: str | None = "Homo sapiens", limit: int = 10
    ) -> dict:
        params: dict = {"query": query, "types": "Pathway", "cluster": "true"}
        if species:
            params["species"] = species
        payload = await self.http.get_json(f"{self.base_url}/search/query", params=params)
        if not isinstance(payload, dict) or "results" not in payload:
            raise UpstreamDrift("Reactome response has no 'results' group list")
        seen: set[str] = set()
        items: list[dict] = []
        for group in payload["results"] or []:
            for entry in group.get("entries") or []:
                if entry.get("type") != "Pathway":
                    continue
                st_id = entry.get("stId")
                if not st_id or st_id in seen:
                    continue
                seen.add(st_id)
                items.append(
                    omit_none(
                        {
                            "st_id": st_id,
                            "name": _clean(entry.get("name")),
                            "species": entry.get("species") or None,
                            "is_disease": entry.get("isDisease"),
                        }
                    )
                )
                if len(items) >= limit:
                    break
            if len(items) >= limit:
                break
        return {"items": items, "total": payload.get("numberOfMatches")}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return html.unescape(_TAG.sub("", value)).strip()
