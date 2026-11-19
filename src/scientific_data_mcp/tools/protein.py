"""Protein tools: UniProt, RCSB PDB and AlphaFold DB behind merged entry points."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

RECORD_KINDS = ("uniprot", "pdb", "alphafold")
SEARCH_KINDS = ("uniprot", "pdb")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    uniprot = service.providers["uniprot"]
    rcsb = service.providers["rcsb"]
    alphafold = service.providers["alphafold"]

    @guarded_tool(mcp, name="protein_record", source="protein")
    async def protein_record(
        identifier: str, kind: str = "uniprot", include_sequence: bool = False
    ) -> dict:
        """Fetch one protein record from UniProt, RCSB PDB or AlphaFold DB.

        Pick `kind`:

        - `uniprot` (default): `identifier` is a UniProt accession such as
          "P05067"; returns name, genes, organism, function, keywords,
          sequence length/mass and PDB cross-references. Set
          `include_sequence=True` for the full sequence (long).
        - `pdb`: `identifier` is a 4-character PDB id such as "4HHB";
          returns title, method, resolution, deposit date and up to five
          polymer entities. `include_sequence` is ignored.
        - `alphafold`: `identifier` is a UniProt accession; returns up to 20
          predicted models (entry id, version, residue range, pLDDT, PDB/CIF
          and PAE image URLs). No prediction returns an empty list.
          `include_sequence` is ignored.

        Only upstream fields are returned; missing annotations stay missing.

        Args:
            identifier: UniProt accession, PDB id, or UniProt accession for
                AlphaFold.
            kind: "uniprot", "pdb" or "alphafold".
            include_sequence: UniProt only; include the full sequence.
        """
        kind = kind.strip().lower()
        if kind not in RECORD_KINDS:
            return tool_error(
                f"invalid kind: {kind!r}",
                hint=f"use one of: {', '.join(RECORD_KINDS)}",
                source="protein",
            )
        identifier = identifier.strip()
        if not identifier:
            return tool_error("identifier must not be empty", source=kind)
        try:
            if kind == "uniprot":
                record = await uniprot.entry(identifier, include_sequence)
                source_url = f"https://www.uniprot.org/uniprotkb/{identifier}/entry"
                source_name = "uniprot"
            elif kind == "pdb":
                record = await rcsb.entry(identifier)
                source_url = f"https://www.rcsb.org/structure/{record['pdb_id']}"
                source_name = "rcsb"
            else:
                record = await alphafold.prediction(identifier)
                source_url = f"https://alphafold.ebi.ac.uk/entry/{identifier}"
                source_name = "alphafold"
        except ProviderError as exc:
            return provider_error_payload(
                exc, "uniprot" if kind == "uniprot" else ("rcsb" if kind == "pdb" else "alphafold")
            )
        except ValueError as exc:
            return tool_error(str(exc), source="alphafold")
        return {"source": source_name, "source_url": source_url, "record": record}

    @guarded_tool(mcp, name="protein_search", source="protein")
    async def protein_search(
        query: str,
        kind: str = "uniprot",
        size: int = 10,
        cursor: str | None = None,
    ) -> dict:
        """Search UniProtKB or RCSB PDB.

        Pick `kind`:

        - `uniprot` (default): `query` uses UniProt syntax, e.g.
          `gene:TP53 AND organism_id:9606`. Item shape: accession, entry
          name, protein name, genes, organism, taxid, reviewed, length.
          `size` is 1-500; pass the returned `next_cursor` for the next page.
        - `pdb`: `query` is free text (e.g. "hemoglobin"); item shape is
          `{"pdb_id": "..."}` only. `size` is 1-100; `cursor` is the numeric
          start offset as a string.

        Both kinds return `count`, `items` and `next_cursor` (null on the
        last page); `pdb` also returns `total`. Empty lists are true upstream
        answers. Use `protein_record` to fetch a full record for an id.

        Args:
            query: UniProt query string or PDB free text.
            kind: "uniprot" or "pdb".
            size: Page size (uniprot 1-500, pdb 1-100).
            cursor: Opaque next-page token from a previous call.
        """
        kind = kind.strip().lower()
        if kind not in SEARCH_KINDS:
            return tool_error(
                f"invalid kind: {kind!r}",
                hint=f"use one of: {', '.join(SEARCH_KINDS)}",
                source="protein",
            )
        if not query.strip():
            return tool_error("query must not be empty", source=kind)
        max_size = 500 if kind == "uniprot" else 100
        if not 1 <= size <= max_size:
            return tool_error(f"size must be 1-{max_size}, got {size}", source=kind)
        try:
            if kind == "uniprot":
                page = await uniprot.search(query.strip(), size, cursor)
                return {
                    "source": "uniprot",
                    "source_url": f"https://www.uniprot.org/uniprotkb?query={query}",
                    "count": len(page["items"]),
                    "items": page["items"],
                    "next_cursor": page["next_cursor"],
                }
            start = 0
            if cursor:
                try:
                    start = int(cursor)
                except ValueError:
                    return tool_error(
                        f"pdb cursor must be a non-negative integer, got {cursor!r}",
                        source="pdb",
                    )
                if start < 0:
                    return tool_error("pdb cursor must be >= 0", source="pdb")
            page = await rcsb.search(query.strip(), size, start)
        except ProviderError as exc:
            return provider_error_payload(exc, "uniprot" if kind == "uniprot" else "rcsb")
        next_cursor = str(page["next_start"]) if page["next_start"] is not None else None
        return {
            "source": "rcsb",
            "source_url": "https://www.rcsb.org/search",
            "total": page["total"],
            "count": len(page["identifiers"]),
            "items": [{"pdb_id": pdb_id} for pdb_id in page["identifiers"]],
            "next_cursor": next_cursor,
        }

    @guarded_tool(mcp, name="protein_map_ids", source="uniprot")
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
            return provider_error_payload(exc, "uniprot")
        return {
            "source": "uniprot",
            "source_url": "https://www.uniprot.org/id-mapping",
            "job_id": result["job_id"],
            "count": len(result["mappings"]),
            "mappings": result["mappings"],
        }

    return {
        "protein_record": protein_record,
        "protein_search": protein_search,
        "protein_map_ids": protein_map_ids,
    }
