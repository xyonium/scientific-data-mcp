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

    @guarded_tool(mcp, name="compound_lookup", source="compound")
    async def compound_lookup(
        query: str, source: str = "chebi", limit: int = 5
    ) -> dict:
        """Look up compounds in ChEBI or KEGG.

        Pick `source`:

        - `chebi` (default): EBI ChEBI ontology; item shape is
          `chebi_id/name/description/synonyms/type`. A name is searched; an
          exact `CHEBI:15365` returns that term with synonyms.
        - `kegg`: KEGG compound; item shape is
          `entry/names/formula/exact_mass/mol_weight/pathways`. KEGG REST is
          free for academic use; commercial use requires a KEGG license.

        `query` is a compound name or source id (KEGG `C01405`). Only
        upstream fields are returned; missing fields are omitted, nothing is
        inferred or completed. Failures return an error dict (`error`,
        `source`).

        Args:
            query: Compound name or ChEBI/KEGG id.
            source: "chebi" or "kegg".
            limit: Matches/records to return, 1-10 (default 5).
        """
        source = source.strip().lower()
        if source not in ("chebi", "kegg"):
            return tool_error(
                f"invalid source: {source!r}",
                hint="use one of: chebi, kegg",
                source="compound",
            )
        if not query.strip():
            return tool_error("query must not be empty", source=source)
        if not 1 <= limit <= 10:
            return tool_error(f"limit must be 1-10, got {limit}", source=source)
        query = query.strip()
        try:
            if source == "chebi":
                if re.match(r"^CHEBI[:_]\d+$", query, re.IGNORECASE):
                    items = [await chebi.term(query)]
                    source_url = (
                        "https://www.ebi.ac.uk/chebi/searchId.do?"
                        f"chebiId={items[0]['chebi_id']}"
                    )
                else:
                    items = await chebi.search(query, limit)
                    source_url = "https://www.ebi.ac.uk/chebi/"
            else:
                items = await kegg.compound(query, limit)
                source_url = (
                    f"https://www.kegg.jp/entry/{query}"
                    if query.upper().startswith("C") and query[1:].isdigit()
                    else f"https://www.kegg.jp/kegg-bin/search?query={quote(query)}"
                )
        except ValueError as exc:
            return tool_error(str(exc), source=source)
        except ProviderError as exc:
            return provider_error_payload(exc, source)
        return {
            "source": source,
            "source_url": source_url,
            "count": len(items),
            "items": items,
        }

    return {
        "dailymed": dailymed_tool,
        "bindingdb_ligands": bindingdb_ligands,
        "compound_lookup": compound_lookup,
    }
