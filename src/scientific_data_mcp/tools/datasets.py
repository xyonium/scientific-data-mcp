"""Dataset tools: NCBI GEO DataSets."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    geo = service.providers["geo"]

    @guarded_tool(mcp, name="geo_datasets", source="geo")
    async def geo_datasets(query: str, limit: int = 10) -> dict:
        """Search NCBI GEO DataSets (GDS) by gene, disease or platform.

        `query` is a GEO search expression, e.g. "TP53" or
        "breast cancer[All Fields]". Returns dataset accessions (GSE...),
        titles, summaries, dataset type, organism, sample count, release
        date and PubMed ids. Empty results are `count: 0`, not an error.
        The NCBI key (if configured) lifts the E-utilities rate limit.

        Args:
            query: GEO search expression.
            limit: Datasets to return, 1-50 (default 10).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="geo")
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source="geo")
        try:
            page = await geo.search(query.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "geo")
        return {
            "source": "geo",
            "source_url": f"https://www.ncbi.nlm.nih.gov/gds/?term={quote(query)}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {"geo_datasets": geo_datasets}
