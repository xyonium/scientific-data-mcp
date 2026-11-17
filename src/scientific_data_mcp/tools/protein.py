"""Protein tools: UniProt entries/search/ID mapping and RCSB structures."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    uniprot = service.providers["uniprot"]

    @mcp.tool(name="protein_entry")
    async def protein_entry(accession: str, include_sequence: bool = False) -> dict:
        """Fetch one UniProtKB entry by accession.

        Returns the reviewed status, protein name, genes, organism, function
        comment, keywords, sequence length/mass and every PDB cross-reference.
        Missing annotations are omitted rather than guessed. Call again with
        `include_sequence=True` for the full amino-acid sequence.

        Args:
            accession: UniProt accession, e.g. "P05067".
            include_sequence: Include the full sequence string (long).
        """
        if not accession.strip():
            return tool_error("accession must not be empty", source="uniprot")
        try:
            record = await uniprot.entry(accession.strip(), include_sequence)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="uniprot")
        return {
            "source": "uniprot",
            "source_url": f"https://www.uniprot.org/uniprotkb/{accession.strip()}/entry",
            "record": record,
        }

    @mcp.tool(name="protein_search")
    async def protein_search(query: str, size: int = 10, cursor: str | None = None) -> dict:
        """Search UniProtKB with a UniProt query string.

        Use UniProt field syntax, e.g. `gene:TP53 AND organism_id:9606` or
        `reviewed:true AND keyword:kinase`. Results are trimmed summaries;
        pass the returned `next_cursor` to fetch the next page. An empty list
        is the true upstream answer, not an error.

        Args:
            query: UniProt query string.
            size: Results per page, 1-500 (default 10).
            cursor: Opaque cursor from a previous call's `next_cursor`.
        """
        if not query.strip():
            return tool_error("query must not be empty", source="uniprot")
        if not 1 <= size <= 500:
            return tool_error(f"size must be 1-500, got {size}", source="uniprot")
        try:
            page = await uniprot.search(query.strip(), size, cursor)
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="uniprot")
        return {
            "source": "uniprot",
            "source_url": f"https://www.uniprot.org/uniprotkb?query={query}",
            "count": len(page["items"]),
            "items": page["items"],
            "next_cursor": page["next_cursor"],
        }

    @mcp.tool(name="protein_map_ids")
    async def protein_map_ids(from_db: str, to_db: str, ids: str) -> dict:
        """Map identifiers between UniProt and other databases.

        Submits the official UniProt ID-mapping job, polls it for up to 30s
        and returns `mappings` keyed by each input id. Database names are
        UniProt's own (e.g. "UniProtKB_AC-ID", "PDB", "Ensembl"); an invalid
        pair is rejected upstream and reported as an error.

        Args:
            from_db: Source database name.
            to_db: Target database name.
            ids: Comma-separated identifiers, e.g. "P04637,P05067".
        """
        if not from_db.strip() or not to_db.strip():
            return tool_error("from_db and to_db must not be empty", source="uniprot")
        if not ids.strip():
            return tool_error("ids must not be empty", source="uniprot")
        try:
            result = await uniprot.map_ids(from_db.strip(), to_db.strip(), ids.strip())
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="uniprot")
        return {
            "source": "uniprot",
            "source_url": "https://www.uniprot.org/id-mapping",
            "job_id": result["job_id"],
            "count": len(result["mappings"]),
            "mappings": result["mappings"],
        }

    return {
        "protein_entry": protein_entry,
        "protein_search": protein_search,
        "protein_map_ids": protein_map_ids,
    }
