"""Materials Project provider (key-gated).

The API needs a free key in the ``X-API-KEY`` header. The provider is only
constructed when ``MATERIALS_PROJECT_API_KEY`` is set, so a keyless install
keeps the base 12-tool surface and never advertises a tool that cannot work.
"""

from __future__ import annotations

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://api.materialsproject.org"
_FIELDS = (
    "material_id,formula_pretty,chemsys,elements,band_gap,energy_above_hull,"
    "density,is_stable,symmetry,nsites,theoretical"
)


class MaterialsProjectProvider(Provider):
    name = "materials_project"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)
        self._key = settings.materials_project_api_key or ""

    def _headers(self) -> dict:
        return {"X-API-KEY": self._key}

    async def get(self, material_id: str) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/materials/summary/",
            params={"material_ids": material_id, "_fields": _FIELDS},
            headers=self._headers(),
        )
        if "data" not in payload:
            raise UpstreamDrift("Materials Project response has no 'data' list")
        rows = payload["data"] or []
        if not rows:
            raise NotFound(f"no Materials Project entry for {material_id!r}")
        return _normalize(rows[0])

    async def search(
        self,
        formula: str | None = None,
        chemsys: str | None = None,
        elements: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        params: dict = {"_fields": _FIELDS, "_limit": limit}
        if formula:
            params["formula"] = formula
        elif chemsys:
            params["chemsys"] = chemsys
        elif elements:
            params["elements"] = elements
        payload = await self.http.get_json(
            f"{self.base_url}/materials/summary/",
            params=params,
            headers=self._headers(),
        )
        if "data" not in payload:
            raise UpstreamDrift("Materials Project search response has no 'data' list")
        return [_normalize(row) for row in payload["data"] or []]


def _normalize(row: dict) -> dict:
    symmetry = row.get("symmetry") or {}
    return omit_none(
        {
            "material_id": row.get("material_id"),
            "formula": row.get("formula_pretty"),
            "chemsys": row.get("chemsys"),
            "elements": row.get("elements"),
            "band_gap": row.get("band_gap"),
            "energy_above_hull": row.get("energy_above_hull"),
            "density": row.get("density"),
            "is_stable": row.get("is_stable"),
            "nsites": row.get("nsites"),
            "theoretical": row.get("theoretical"),
            "crystal_system": symmetry.get("crystal_system"),
            "space_group_symbol": symmetry.get("space_group_symbol"),
        }
    )
