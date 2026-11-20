"""Additional chemistry sources: KEGG compounds and DailyMed labels."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    kegg = service.providers["kegg"]
    dailymed = service.providers["dailymed"]
    chebi = service.providers["chebi"]
    bindingdb = service.providers["bindingdb"]

    @guarded_tool(mcp, name="kegg_compound", source="kegg")
    async def kegg_compound(query: str, limit: int = 3) -> dict:
        """Look up KEGG compounds by name or KEGG compound id.

        `query` is a compound name ("aspirin") or a KEGG id ("C01405").
        Returns entry ids, names, formula, exact/molecular weight and KEGG
        pathways. KEGG REST is free for academic use; commercial use
        requires a KEGG license. Only upstream fields are returned; missing
        fields are omitted, nothing is inferred or completed. Failures
        return an error dict (`error`, `source`).

        Args:
            query: Compound name or KEGG compound id.
            limit: Maximum compounds for a name search, 1-10 (default 3).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="kegg")
        if not 1 <= limit <= 10:
            return tool_error(f"limit must be 1-10, got {limit}", source="kegg")
        try:
            items = await kegg.compound(query.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "kegg")
        source_url = (
            f"https://www.kegg.jp/entry/{query.strip()}"
            if query.strip().upper().startswith("C") and query.strip()[1:].isdigit()
            else f"https://www.kegg.jp/kegg-bin/search?query={quote(query.strip())}"
        )
        return {
            "source": "kegg",
            "source_url": source_url,
            "count": len(items),
            "items": items,
        }

    @guarded_tool(mcp, name="dailymed", source="dailymed")
    async def dailymed_tool(query: str, limit: int = 5) -> dict:
        """Search DailyMed drug labels by drug name.

        `query` is a drug name ("aspirin"); returns SPL set ids, titles,
        published dates and SPL versions. DailyMed is NLM's official label
        repository; this is metadata search only (no full label text).
        Only upstream fields are returned; missing fields are omitted,
        nothing is inferred or completed. Failures return an error dict
        (`error`, `source`).

        Args:
            query: Drug name.
            limit: Labels to return, 1-20 (default 5).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="dailymed")
        if not 1 <= limit <= 20:
            return tool_error(f"limit must be 1-20, got {limit}", source="dailymed")
        try:
            page = await dailymed.search(query.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "dailymed")
        return {
            "source": "dailymed",
            "source_url": (
                "https://dailymed.nlm.nih.gov/dailymed/search.cfm"
                f"?labeltype=all&query={quote(query.strip())}"
            ),
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    @guarded_tool(mcp, name="chebi_compound", source="chebi")
    async def chebi_compound(query: str, limit: int = 5) -> dict:
        """Look up ChEBI chemical entities by name or ChEBI id.

        `query` is a name ("aspirin") or id ("CHEBI:15365"); returns ChEBI
        ids, names and definitions (an exact id also returns synonyms).
        ChEBI is an EBI ontology, so names are curated classes, not vendor
        products. Only upstream fields
        are returned; missing fields are omitted, nothing is inferred or
        completed. Failures return an error dict (`error`, `source`).

        Args:
            query: Compound name or ChEBI id.
            limit: Matches to return, 1-20 (default 5).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="chebi")
        if not 1 <= limit <= 20:
            return tool_error(f"limit must be 1-20, got {limit}", source="chebi")
        try:
            if re.match(r"^CHEBI[:_]\d+$", query.strip(), re.IGNORECASE):
                items = [await chebi.term(query.strip())]
                source_url = f"https://www.ebi.ac.uk/chebi/searchId.do?chebiId={items[0]['chebi_id']}"
            else:
                items = await chebi.search(query.strip(), limit)
                source_url = "https://www.ebi.ac.uk/chebi/"
        except ValueError as exc:
            return tool_error(str(exc), source="chebi")
        except ProviderError as exc:
            return provider_error_payload(exc, "chebi")
        return {
            "source": "chebi",
            "source_url": source_url,
            "count": len(items),
            "items": items,
        }

    @guarded_tool(mcp, name="bindingdb_ligands", source="bindingdb")
    async def bindingdb_ligands(
        uniprot: str, cutoff_nm: float = 10000, limit: int = 20
    ) -> dict:
        """Fetch BindingDB ligands/affinities for a UniProt target.

        `uniprot` is a UniProt accession ("P35355"); `cutoff_nm` filters
        affinities (nM, default 10000). Returns monomer id, SMILES, affinity
        type and value. BindingDB is free/keyless; keep calls to ~1/s. Only
        upstream fields are returned; missing fields are omitted, nothing is
        inferred or completed. Failures return an error dict (`error`,
        `source`).

        Args:
            uniprot: UniProt accession.
            cutoff_nm: Affinity cutoff in nM (default 10000).
            limit: Ligand rows to return, 1-100 (default 20).
        """
        if not uniprot.strip():
            return tool_error("uniprot must not be empty", source="bindingdb")
        if not 0.001 <= cutoff_nm <= 1_000_000:
            return tool_error(f"cutoff_nm out of range: {cutoff_nm}", source="bindingdb")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="bindingdb")
        try:
            page = await bindingdb.ligands(uniprot.strip(), cutoff_nm, limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "bindingdb")
        return {
            "source": "bindingdb",
            "source_url": f"https://bindingdb.org/rwd/bind/BindingDB.jsp?uniprot={uniprot.strip()}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {
        "kegg_compound": kegg_compound,
        "dailymed": dailymed_tool,
        "chebi_compound": chebi_compound,
        "bindingdb_ligands": bindingdb_ligands,
    }
