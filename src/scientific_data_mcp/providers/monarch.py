"""Monarch Initiative v3 provider (keyless)."""

from __future__ import annotations

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://api.monarchinitiative.org/v3/api"


class MonarchProvider(Provider):
    name = "monarch"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def associations(
        self, entity: str, category: str | None, limit: int = 10, offset: int = 0
    ) -> dict:
        params = {"entity": entity, "limit": limit, "offset": offset}
        if category:
            params["category"] = category
        payload = await self.http.get_json(f"{self.base_url}/association", params=params)
        rows = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise UpstreamDrift("Monarch response has no items list")
        try:
            total = int(payload.get("total"))
        except (TypeError, ValueError) as exc:
            raise UpstreamDrift("Monarch total is not numeric") from exc
        return {"items": [_normalize(row) for row in rows], "total": total}


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "subject_id": row.get("subject"),
            "subject_label": row.get("subject_label"),
            "subject_category": row.get("subject_category"),
            "predicate": row.get("predicate"),
            "object_id": row.get("object"),
            "object_label": row.get("object_label"),
            "object_category": row.get("object_category"),
            "category": row.get("category"),
            "publications": row.get("publications") or None,
            "primary_knowledge_source": row.get("primary_knowledge_source"),
        }
    )
