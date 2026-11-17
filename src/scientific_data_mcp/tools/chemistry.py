"""Chemistry tools: PubChem compounds and ChEMBL bioactivity."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..providers.pubchem import ID_TYPES, PROPERTY_MAP
from ..runtime import Service

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    pubchem = service.providers["pubchem"]

    @mcp.tool(name="chem_compound")
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

    @mcp.tool(name="chem_compound_properties")
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

    @mcp.tool(name="chem_similar_compounds")
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

    return {
        "chem_compound": chem_compound,
        "chem_compound_properties": chem_compound_properties,
        "chem_similar_compounds": chem_similar_compounds,
    }
