"""Protein/gene interaction tool: STRING (keyless) and BioGRID (key-gated)."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

SOURCES = ("string", "biogrid")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    string = service.providers["string"]
    biogrid = service.providers.get("biogrid")

    @guarded_tool(mcp, name="protein_interactions", source="interactions")
    async def protein_interactions(
        genes: str,
        source: str = "string",
        organism: int = 9606,
        limit: int = 20,
        min_score: int | None = None,
    ) -> dict:
        """Curated/interrogated protein and gene interactions from STRING or BioGRID.

        Pick `source`:

        - `string` (default, keyless): STRING interaction partners with the
          combined score (0-1) and per-channel evidence scores (n/f/p/a/e/d/t).
          `min_score` is STRING's combined-score cutoff on a 0-1000 scale
          (e.g. 700 = high confidence).
        - `biogrid` (requires BIOGRID_ACCESS_KEY): curated literature
          interactions with the experimental system, system type and PubMed
          id. `min_score` does not apply.

        `genes` is one symbol or pipe-separated symbols ("TP53" or
        "BRCA1|BRCA2"); `organism` is an NCBI taxonomy id (9606 human, 10090
        mouse, 559292 yeast). Only upstream fields are returned; missing
        annotations stay missing. The item shape differs by source and is
        documented above.

        Args:
            genes: Gene symbol(s), pipe-separated.
            source: "string" or "biogrid".
            organism: NCBI taxonomy id (default 9606 human).
            limit: Maximum interactions, 1-100 (default 20).
            min_score: STRING combined-score cutoff 0-1000 (string only).
        """
        source = source.strip().lower()
        if source not in SOURCES:
            return tool_error(
                f"invalid source: {source!r}",
                hint=f"use one of: {', '.join(SOURCES)}",
                source="interactions",
            )
        symbols = [part.strip() for part in genes.split("|") if part.strip()]
        if not symbols:
            return tool_error("genes must not be empty", source=source)
        if len(symbols) > 50:
            return tool_error("at most 50 genes per query", source=source)
        if not 1 <= organism <= 10_000_000:
            return tool_error(f"invalid organism tax id: {organism}", source=source)
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source=source)
        if min_score is not None and not 0 <= min_score <= 1000:
            return tool_error(
                f"min_score must be 0-1000, got {min_score}", source=source
            )
        if source == "biogrid" and min_score is not None:
            return tool_error(
                "min_score only applies to source='string'", source="biogrid"
            )

        try:
            if source == "string":
                rows = await string.partners(symbols, organism, limit, min_score)
                return {
                    "source": "string",
                    "source_url": "https://string-db.org/",
                    "count": len(rows),
                    "items": rows,
                }
            if biogrid is None:
                return tool_error(
                    "biogrid requires BIOGRID_ACCESS_KEY",
                    hint="get a free key at https://webservice.thebiogrid.org/ and set BIOGRID_ACCESS_KEY",
                    source="biogrid",
                )
            page = await biogrid.interactions("|".join(symbols), organism, limit, 0)
            return {
                "source": "biogrid",
                "source_url": "https://thebiogrid.org/",
                "count": len(page["items"]),
                "items": page["items"],
            }
        except ProviderError as exc:
            return provider_error_payload(exc, source)

    return {"protein_interactions": protein_interactions}
