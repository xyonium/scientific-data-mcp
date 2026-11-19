"""Additional chemistry sources: KEGG compounds and DailyMed labels."""

from __future__ import annotations

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
        return {
            "source": "kegg",
            "source_url": f"https://www.kegg.jp/entry/{quote(query.strip())}",
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

    return {"kegg_compound": kegg_compound, "dailymed": dailymed_tool}
