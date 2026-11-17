"""ChEMBL provider (EMBL-EBI REST, keyless).

Text search uses the documented ``/<resource>/search.json?q=`` endpoint. Note:
the older ``search_parameters__q`` filter form is silently ignored by the API
and can return unfiltered rows — it is not used here.
"""

from __future__ import annotations

from urllib.parse import quote

from ..config import Settings
from ..errors import UpstreamError
from ..http import PoliteClient
from .base import Provider

_BASE = "https://www.ebi.ac.uk/chembl/api/data"
RESOURCES = ("molecule", "target", "assay")
_PAGE_SIZE = 1000
_MAX_PAGES = 10


class ChemBLProvider(Provider):
    name = "chembl"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def _page(self, payload: dict, key: str, offset: int, limit: int) -> dict:
        items = payload.get(key) or []
        meta = payload.get("page_meta") or {}
        total = meta.get("total_count")
        next_offset = offset + len(items) if meta.get("next") else None
        return {"items": items, "total": total, "next_offset": next_offset}

    async def search(self, resource: str, query: str, limit: int, offset: int) -> dict:
        if resource not in RESOURCES:
            raise ValueError(f"resource must be one of {', '.join(RESOURCES)}")
        payload = await self.http.get_json(
            f"{self.base_url}/{resource}/search.json",
            params={"q": query, "limit": limit, "offset": offset},
        )
        page = await self._page(payload, f"{resource}s", offset, limit)
        page["items"] = [normalize(resource, row) for row in page["items"]]
        return page

    async def molecule(self, chembl_id: str) -> dict:
        payload = await self._get("molecule", chembl_id)
        return normalize("molecule", payload)

    async def target(self, chembl_id: str) -> dict:
        payload = await self._get("target", chembl_id)
        return normalize("target", payload)

    async def activities(
        self,
        chembl_id: str | None,
        target_chembl_id: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if chembl_id:
            params["molecule_chembl_id"] = chembl_id
        if target_chembl_id:
            params["target_chembl_id"] = target_chembl_id
        payload = await self.http.get_json(f"{self.base_url}/activity.json", params=params)
        page = await self._page(payload, "activities", offset, limit)
        page["items"] = [_pick(row, ACTIVITY_FIELDS) for row in page["items"]]
        return page

    async def mechanisms(self, chembl_id: str) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        for _ in range(_MAX_PAGES):
            payload = await self.http.get_json(
                f"{self.base_url}/mechanism.json",
                params={"molecule_chembl_id": chembl_id, "limit": _PAGE_SIZE, "offset": offset},
            )
            page = payload.get("mechanisms") or []
            rows.extend(_pick(row, MECHANISM_FIELDS) for row in page)
            meta = payload.get("page_meta") or {}
            if not meta.get("next") or not page:
                break
            offset += len(page)
        return rows

    async def _get(self, resource: str, chembl_id: str) -> dict:
        payload = await self.http.get_json(f"{self.base_url}/{resource}/{quote(chembl_id, safe='')}.json")
        if not isinstance(payload, dict):
            raise UpstreamError(f"unexpected ChEMBL {resource} payload")
        return payload


MOLECULE_FIELDS = (
    "molecule_chembl_id",
    "pref_name",
    "molecule_type",
    "max_phase",
    "first_approval",
    "black_box_warning",
    "natural_product",
    "oral",
    "parenteral",
    "topical",
)
TARGET_FIELDS = ("target_chembl_id", "pref_name", "target_type", "organism", "tax_id")
ASSAY_FIELDS = (
    "assay_chembl_id",
    "description",
    "assay_type",
    "confidence_score",
    "organism",
)
ACTIVITY_FIELDS = (
    "activity_id",
    "molecule_chembl_id",
    "target_chembl_id",
    "standard_type",
    "standard_value",
    "standard_units",
    "pchembl_value",
    "assay_chembl_id",
)
MECHANISM_FIELDS = (
    "molecule_chembl_id",
    "target_chembl_id",
    "mechanism_of_action",
    "action_type",
    "direct_interaction",
)
PROPERTY_FIELDS = (
    "mw_freebase",
    "full_mwt",
    "alogp",
    "psa",
    "hba",
    "hbd",
    "rtb",
    "num_ro5_violations",
)


def _pick(row: dict, fields: tuple[str, ...]) -> dict:
    return {f: row[f] for f in fields if row.get(f) is not None}


def normalize(resource: str, row: dict) -> dict:
    if resource == "molecule":
        out = _pick(row, MOLECULE_FIELDS)
        structures = row.get("molecule_structures") or {}
        for key, name in (
            ("canonical_smiles", "canonical_smiles"),
            ("isomeric_smiles", "isomeric_smiles"),
            ("standard_inchi_key", "standard_inchi_key"),
        ):
            if structures.get(key):
                out[name] = structures[key]
        props = row.get("molecule_properties") or {}
        for key in PROPERTY_FIELDS:
            if props.get(key) is not None:
                out[key] = props[key]
        return out
    if resource == "target":
        return _pick(row, TARGET_FIELDS)
    return _pick(row, ASSAY_FIELDS)
