"""Chemistry tools: PubChem compounds and ChEMBL bioactivity."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..providers.chembl import RESOURCES as CHEMBL_RESOURCES
from ..providers.pubchem import ID_TYPES, PROPERTY_MAP
from ..runtime import Service
from ._guard import guarded_tool

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    pubchem = service.providers["pubchem"]
    chembl = service.providers["chembl"]

    @guarded_tool(mcp, name="chem_compound", source="pubchem")
    async def chem_compound(identifier: str, id_type: str = "name") -> dict:
        """Look up one compound in PubChem and return its upstream record.

        Returns only fields PubChem actually carries (CID, formula, molecular
        weight, IUPAC name, SMILES, InChIKey, XLogP, TPSA, H-bond counts,
        rotatable bonds, heavy atoms, charge, complexity, up to 20 synonyms).
        Fields the upstream omits stay omitted — nothing is inferred or filled
        in. The record page is linked in `source_url` for manual verification.

        Args:
            identifier: Compound name, numeric CID, SMILES or InChIKey.
            id_type: One of "name", "cid", "smiles", "inchikey".
        """
        if id_type not in ID_TYPES:
            return tool_error(
                f"invalid id_type: {id_type!r}",
                hint=f"use one of: {', '.join(ID_TYPES)}",
                source="pubchem",
            )
        try:
            record = await pubchem.compound(identifier, id_type)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="pubchem")
        except ValueError as exc:
            return tool_error(str(exc), source="pubchem")
        return {
            "source": "pubchem",
            "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{record['cid']}",
            "record": record,
        }

    @guarded_tool(mcp, name="chem_compound_properties", source="pubchem")
    async def chem_compound_properties(cid: int, properties: list[str] | None = None) -> dict:
        """Return selected PubChem properties for a known CID.

        Pass PubChem property names (e.g. "MolecularFormula", "XLogP"); omit
        them for the default set. Unknown names are rejected with the allowed
        list instead of being silently dropped.

        Args:
            cid: PubChem compound id (positive integer).
            properties: Optional list of PubChem property names.
        """
        if cid < 1:
            return tool_error(f"invalid CID: {cid}", source="pubchem")
        try:
            values = await pubchem.properties(cid, properties)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="pubchem")
        except ValueError as exc:
            return tool_error(str(exc), hint=f"allowed: {', '.join(PROPERTY_MAP)}", source="pubchem")
        return {
            "source": "pubchem",
            "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            "record": {"cid": cid, **values},
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
            return tool_error(f"{exc.kind}: {exc}", source="pubchem")
        return {
            "source": "pubchem",
            "source_url": "https://pubchem.ncbi.nlm.nih.gov/search/",
            "count": len(cids),
            "items": [{"cid": cid} for cid in cids],
        }

    @guarded_tool(mcp, name="chembl_search", source="chembl")
    async def chembl_search(
        query: str, resource: str = "molecule", limit: int = 10, offset: int = 0
    ) -> dict:
        """Full-text search ChEMBL molecules, targets or assays.

        Returns only rows ChEMBL returns, trimmed to stable identifier and
        annotation fields. Empty results are a normal answer (`count: 0`),
        not an error.

        Args:
            query: Free-text query, e.g. "imatinib", "ABL1", "kinase".
            resource: "molecule", "target" or "assay".
            limit: Rows per page, 1-100.
            offset: Rows to skip.
        """
        if resource not in CHEMBL_RESOURCES:
            return tool_error(
                f"invalid resource: {resource!r}",
                hint=f"use one of: {', '.join(CHEMBL_RESOURCES)}",
                source="chembl",
            )
        if not query.strip():
            return tool_error("query must not be empty", source="chembl")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="chembl")
        if offset < 0:
            return tool_error(f"offset must be >= 0, got {offset}", source="chembl")
        try:
            page = await chembl.search(resource, query, limit, offset)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="chembl")
        return {
            "source": "chembl",
            "source_url": f"https://www.ebi.ac.uk/chembl/g/#search_results/all/query={quote(query)}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
            "next_offset": page["next_offset"],
        }

    @guarded_tool(mcp, name="chembl_bioactivity", source="chembl")
    async def chembl_bioactivity(
        chembl_id: str | None = None,
        target_chembl_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """List ChEMBL bioactivity measurements for one molecule or one target.

        Pass exactly one of `chembl_id` (molecule, e.g. CHEMBL941) or
        `target_chembl_id` (e.g. CHEMBL1862). Values are upstream standard
        type/value/units and pChEMBL; nothing is converted or normalized.
        An empty list is a valid answer for some molecules (ChEMBL records
        mechanisms on the salt form) and is returned as `count: 0`.

        Args:
            chembl_id: ChEMBL molecule id.
            target_chembl_id: ChEMBL target id.
            limit: Rows per page, 1-100.
            offset: Rows to skip.
        """
        if bool(chembl_id) == bool(target_chembl_id):
            return tool_error(
                "pass exactly one of chembl_id or target_chembl_id",
                source="chembl",
            )
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="chembl")
        if offset < 0:
            return tool_error(f"offset must be >= 0, got {offset}", source="chembl")
        try:
            page = await chembl.activities(chembl_id, target_chembl_id, limit, offset)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="chembl")
        if chembl_id:
            source_url = f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/"
        else:
            source_url = f"https://www.ebi.ac.uk/chembl/target_report_card/{target_chembl_id}/"
        return {
            "source": "chembl",
            "source_url": source_url,
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
            "next_offset": page["next_offset"],
        }

    @guarded_tool(mcp, name="chembl_mechanisms", source="chembl")
    async def chembl_mechanisms(chembl_id: str) -> dict:
        """Return ChEMBL mechanism-of-action records for one molecule.

        Mechanisms are attached to the molecule form ChEMBL records them on
        (often a salt, e.g. CHEMBL1642 for imatinib mesylate). An empty list
        for a free-base id is the true upstream answer, not an error.

        Args:
            chembl_id: ChEMBL molecule id.
        """
        if not chembl_id.strip():
            return tool_error("chembl_id must not be empty", source="chembl")
        try:
            rows = await chembl.mechanisms(chembl_id)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="chembl")
        return {
            "source": "chembl",
            "source_url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
            "count": len(rows),
            "items": rows,
        }

    return {
        "chem_compound": chem_compound,
        "chem_compound_properties": chem_compound_properties,
        "chem_similar_compounds": chem_similar_compounds,
        "chembl_search": chembl_search,
        "chembl_bioactivity": chembl_bioactivity,
        "chembl_mechanisms": chembl_mechanisms,
    }
