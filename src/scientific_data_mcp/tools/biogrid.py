"""BioGRID interaction tool (registered only when a key is configured)."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    provider = service.providers.get("biogrid")
    if provider is None:
        return {}

    @guarded_tool(mcp, name="biogrid_interactions", source="biogrid")
    async def biogrid_interactions(
        genes: str, organism: int = 9606, limit: int = 100, offset: int = 0
    ) -> dict:
        """Curated protein/gene interactions from BioGRID (requires BIOGRID_ACCESS_KEY).

        `genes` is one symbol or pipe-separated symbols ("TP53" or
        "BRCA1|BRCA2"); `organism` is an NCBI taxonomy id (9606 human, 10090
        mouse, 559292 yeast). Returns physical and genetic interactions with
        the experimental system, system type, PubMed id and BioGRID id.

        Returns only fields BioGRID actually provides; missing annotations stay
        missing, nothing is inferred or completed. BioGRID has no documented
        total count in this response, so `next_offset` is set only when a full
        page came back; treat it as "there may be more", not an exact total.
        This tool is not registered when no key is configured.

        Args:
            genes: Gene symbol(s), pipe-separated.
            organism: NCBI taxonomy id (default 9606 human).
            limit: Maximum interactions, 1-1000 (default 100).
            offset: Rows to skip.
        """
        symbols = [part.strip() for part in genes.split("|") if part.strip()]
        if not symbols:
            return tool_error("genes must not be empty", source="biogrid")
        if len(symbols) > 50:
            return tool_error("at most 50 genes per query", source="biogrid")
        if not 1 <= organism <= 10_000_000:
            return tool_error(f"invalid organism tax id: {organism}", source="biogrid")
        if not 1 <= limit <= 1000:
            return tool_error(f"limit must be 1-1000, got {limit}", source="biogrid")
        if offset < 0:
            return tool_error(f"offset must be >= 0, got {offset}", source="biogrid")
        try:
            page = await provider.interactions("|".join(symbols), organism, limit, offset)
        except ProviderError as exc:
            return provider_error_payload(exc, "biogrid")
        return {
            "source": "biogrid",
            "source_url": "https://thebiogrid.org/",
            "count": len(page["items"]),
            "items": page["items"],
            "next_offset": page["next_offset"],
        }

    return {"biogrid_interactions": biogrid_interactions}
