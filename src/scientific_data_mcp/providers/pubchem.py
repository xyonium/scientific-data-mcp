"""PubChem PUG-REST provider.

Keyless. Name/inchikey lookups are GETs on the path; SMILES must go through a
POST form because the path segment cannot carry the special characters, and
similarity search is asynchronous: POST returns a ListKey that is polled.
"""

from __future__ import annotations

import asyncio
from urllib.parse import quote

from ..config import Settings
from ..errors import NotFound, UpstreamError
from ..http import PoliteClient
from .base import Provider

_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# PubChem property name -> normalized key. Keep the upstream value untouched.
PROPERTY_MAP: dict[str, str] = {
    "MolecularFormula": "molecular_formula",
    "MolecularWeight": "molecular_weight",
    "IUPACName": "iupac_name",
    "CanonicalSMILES": "canonical_smiles",
    "IsomericSMILES": "isomeric_smiles",
    "InChIKey": "inchikey",
    "XLogP": "xlogp",
    "TPSA": "tpsa",
    "HBondDonorCount": "h_bond_donors",
    "HBondAcceptorCount": "h_bond_acceptors",
    "RotatableBondCount": "rotatable_bonds",
    "HeavyAtomCount": "heavy_atoms",
    "Charge": "charge",
    "Complexity": "complexity",
}

DEFAULT_PROPERTIES: tuple[str, ...] = (
    "MolecularFormula",
    "MolecularWeight",
    "IUPACName",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChIKey",
    "XLogP",
    "TPSA",
    "HBondDonorCount",
    "HBondAcceptorCount",
    "RotatableBondCount",
    "HeavyAtomCount",
    "Charge",
    "Complexity",
)

ID_TYPES = ("name", "cid", "smiles", "inchikey")

_SIMILARITY_ATTEMPTS = 10
_SIMILARITY_INTERVAL = 0.5


class PubChemProvider(Provider):
    name = "pubchem"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def resolve_cid(self, identifier: str, id_type: str) -> int:
        if id_type == "cid":
            try:
                cid = int(identifier)
            except ValueError as exc:
                raise NotFound(f"invalid CID: {identifier!r}") from exc
            if cid < 1:
                raise NotFound(f"invalid CID: {identifier!r}")
            return cid
        if id_type == "name":
            payload = await self.http.get_json(f"{self.base_url}/compound/name/{quote(identifier, safe='')}/cids/JSON")
        elif id_type == "inchikey":
            payload = await self.http.get_json(
                f"{self.base_url}/compound/inchikey/{quote(identifier, safe='')}/cids/JSON"
            )
        elif id_type == "smiles":
            payload = await self.http.post_form(
                f"{self.base_url}/compound/smiles/cids/JSON", {"smiles": identifier}
            )
        else:
            raise ValueError(f"id_type must be one of {', '.join(ID_TYPES)}")
        return _first_cid(payload, identifier)

    async def properties(self, cid: int, properties: list[str] | None = None) -> dict:
        names = list(properties) if properties else list(DEFAULT_PROPERTIES)
        unknown = [n for n in names if n not in PROPERTY_MAP]
        if unknown:
            raise ValueError(
                f"unknown PubChem properties: {', '.join(unknown)}; "
                f"allowed: {', '.join(PROPERTY_MAP)}"
            )
        payload = await self.http.get_json(
            f"{self.base_url}/compound/cid/{cid}/property/{','.join(names)}/JSON"
        )
        rows = payload.get("PropertyTable", {}).get("Properties") or []
        if not rows:
            raise NotFound(f"no properties for CID {cid}")
        row = rows[0]
        return {PROPERTY_MAP[k]: v for k, v in row.items() if k in PROPERTY_MAP}

    async def synonyms(self, cid: int, limit: int = 20) -> list[str]:
        payload = await self.http.get_json(f"{self.base_url}/compound/cid/{cid}/synonyms/JSON")
        info = payload.get("InformationList", {}).get("Information") or []
        names = info[0].get("Synonym") if info else []
        return list(names or [])[: max(limit, 0)]

    async def compound(self, identifier: str, id_type: str) -> dict:
        cid = await self.resolve_cid(identifier, id_type)
        props = await self.properties(cid)
        names = await self.synonyms(cid)
        return {"cid": cid, **props, "synonyms": names}

    async def similar_cids(
        self, smiles: str, threshold: int = 90, max_records: int = 20
    ) -> list[int]:
        # Not idempotent: a retried submit starts a second server-side job.
        payload = await self.http.post_form(
            f"{self.base_url}/compound/similarity/smiles/JSON",
            {"smiles": smiles, "Threshold": threshold, "MaxRecords": max_records},
            retry=False,
        )
        key = (payload.get("Waiting") or {}).get("ListKey")
        if not key:
            return _cids(payload)
        for _ in range(_SIMILARITY_ATTEMPTS):
            await asyncio.sleep(_SIMILARITY_INTERVAL)
            payload = await self.http.get_json(f"{self.base_url}/compound/listkey/{key}/cids/JSON")
            if "IdentifierList" in payload:
                return _cids(payload)
        raise UpstreamError(f"similarity search for ListKey {key} did not finish in time")


def _cids(payload: dict) -> list[int]:
    values = payload.get("IdentifierList", {}).get("CID") or []
    return [int(v) for v in values]


def _first_cid(payload: dict, identifier: str) -> int:
    cids = _cids(payload)
    if not cids:
        raise NotFound(f"no PubChem compound matches {identifier!r}")
    return cids[0]
