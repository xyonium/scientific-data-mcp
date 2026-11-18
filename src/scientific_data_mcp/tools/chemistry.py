"""Chemistry tools: PubChem compounds and ChEMBL lookups."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..providers.chembl import RESOURCES as CHEMBL_RESOURCES
from ..providers.pubchem import ID_TYPES, PROPERTY_MAP
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

KINDS = ("search", "activities", "mechanisms")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    pubchem = service.providers["pubchem"]
    chembl = service.providers["chembl"]

    @guarded_tool(mcp, name="chem_compound", source="pubchem")
    async def chem_compound(
        identifier: str, id_type: str = "name", properties: list[str] | None = None
    ) -> dict:
        """Look up one compound in PubChem and return its upstream record.

        Use this for both a full record and a chosen property subset: pass
        `properties` (PubChem property names such as "MolecularFormula",
        "XLogP") to narrow the fields, or omit it for the default set.
        Unknown property names are rejected with the allowed list.

        Returns only fields PubChem actually carries (CID, formula, molecular
        weight, IUPAC name, SMILES, InChIKey, XLogP, TPSA, H-bond counts,
        rotatable bonds, heavy atoms, charge, complexity, up to 20 synonyms).
        Fields the upstream omits stay omitted — nothing is inferred.

        Args:
            identifier: Compound name, numeric CID, SMILES or InChIKey.
            id_type: One of "name", "cid", "smiles", "inchikey".
            properties: Optional PubChem property names (default: all).
        """
        if id_type not in ID_TYPES:
            return tool_error(
                f"invalid id_type: {id_type!r}",
                hint=f"use one of: {', '.join(ID_TYPES)}",
                source="pubchem",
            )
        try:
            record = await pubchem.compound(identifier, id_type, properties)
        except ProviderError as exc:
            return provider_error_payload(exc, "pubchem")
        except ValueError as exc:
            return tool_error(
                str(exc), hint=f"allowed: {', '.join(PROPERTY_MAP)}", source="pubchem"
            )
        return {
            "source": "pubchem",
            "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{record['cid']}",
            "record": record,
        }

    @guarded_tool(mcp, name="chem_similar_compounds", source="pubchem")
    async def chem_similar_compounds(
        smiles: str, threshold: int = 90, max_records: int = 20
    ) -> dict:
        """Find PubChem CIDs structurally similar to a SMILES string.

        Similarity is computed by PubChem (Tanimoto, threshold 0-100); this
        tool returns the CID list only and never invents structures. The query
        is submitted as a form body, so SMILES special characters are safe.

        Args:
            smiles: Query SMILES.
            threshold: Minimum similarity 0-100 (default 90).
            max_records: Maximum CIDs to return, 1-1000 (default 20).
        """
        if not 0 <= threshold <= 100:
            return tool_error(f"threshold must be 0-100, got {threshold}", source="pubchem")
        if not 1 <= max_records <= 1000:
            return tool_error(f"max_records must be 1-1000, got {max_records}", source="pubchem")
        try:
            cids = await pubchem.similar_cids(smiles, threshold, max_records)
        except ProviderError as exc:
            return provider_error_payload(exc, "pubchem")
        return {
            "source": "pubchem",
            "source_url": "https://pubchem.ncbi.nlm.nih.gov/search/",
            "count": len(cids),
            "items": [{"cid": cid} for cid in cids],
        }

    @guarded_tool(mcp, name="chembl_data", source="chembl")
    async def chembl_data(
        kind: str = "search",
        query: str | None = None,
        resource: str = "molecule",
        chembl_id: str | None = None,
        target_chembl_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """One entry point for ChEMBL text search, activities and mechanisms.

        Pick `kind`:

        - `search` (default): free-text search. Requires `query`; `resource`
          is "molecule", "target" or "assay".
        - `activities`: bioactivity rows. Pass exactly one of `chembl_id`
          (molecule) or `target_chembl_id`.
        - `mechanisms`: mechanism-of-action rows for one molecule. Requires
          `chembl_id`; mechanisms are attached to the salt form, so a free
          base can legitimately return an empty list.

        All kinds return a list envelope: `count`, `items`, plus `total` and
        `next_offset` for search/activities. Values are upstream standard
        type/value/units and pChEMBL; nothing is converted or normalized.
        Empty lists are true upstream answers, not errors.

        Args:
            kind: "search", "activities" or "mechanisms".
            query: Search text (kind=search).
            resource: "molecule", "target" or "assay" (kind=search).
            chembl_id: ChEMBL molecule id (activities/mechanisms).
            target_chembl_id: ChEMBL target id (kind=activities).
            limit: Rows per page, 1-100.
            offset: Rows to skip.
        """
        kind = kind.strip().lower()
        if kind not in KINDS:
            return tool_error(
                f"invalid kind: {kind!r}", hint=f"use one of: {', '.join(KINDS)}",
                source="chembl",
            )
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="chembl")
        if offset < 0:
            return tool_error(f"offset must be >= 0, got {offset}", source="chembl")

        if kind == "search":
            if resource not in CHEMBL_RESOURCES:
                return tool_error(
                    f"invalid resource: {resource!r}",
                    hint=f"use one of: {', '.join(CHEMBL_RESOURCES)}",
                    source="chembl",
                )
            if not query or not query.strip():
                return tool_error("query is required when kind='search'", source="chembl")
            try:
                page = await chembl.search(resource, query.strip(), limit, offset)
            except ProviderError as exc:
                return provider_error_payload(exc, "chembl")
            return {
                "source": "chembl",
                "source_url": f"https://www.ebi.ac.uk/chembl/g/#search_results/all/query={quote(query)}",
                "count": len(page["items"]),
                "total": page["total"],
                "items": page["items"],
                "next_offset": page["next_offset"],
            }

        if bool(chembl_id) == bool(target_chembl_id):
            return tool_error(
                "kind='activities' needs exactly one of chembl_id or target_chembl_id",
                source="chembl",
            )
        try:
            if kind == "activities":
                page = await chembl.activities(chembl_id, target_chembl_id, limit, offset)
                return {
                    "source": "chembl",
                    "source_url": (
                        f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/"
                        if chembl_id
                        else f"https://www.ebi.ac.uk/chembl/target_report_card/{target_chembl_id}/"
                    ),
                    "count": len(page["items"]),
                    "total": page["total"],
                    "items": page["items"],
                    "next_offset": page["next_offset"],
                }
            rows = await chembl.mechanisms(chembl_id)
        except ProviderError as exc:
            return provider_error_payload(exc, "chembl")
        return {
            "source": "chembl",
            "source_url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
            "count": len(rows),
            "items": rows,
        }

    return {
        "chem_compound": chem_compound,
        "chem_similar_compounds": chem_similar_compounds,
        "chembl_data": chembl_data,
    }
