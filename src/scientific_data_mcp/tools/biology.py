"""Biology tools: Open Targets associations and Reactome pathways."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

ENTITIES = ("target", "disease")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    opentargets = service.providers["opentargets"]
    reactome = service.providers["reactome"]

    @guarded_tool(mcp, name="opentargets", source="opentargets")
    async def opentargets_tool(
        query: str, entity: str = "target", limit: int = 5
    ) -> dict:
        """Look up Open Targets target-disease associations.

        `entity="target"` searches a gene/protein symbol (e.g. "TP53") and
        returns the top associated diseases; `entity="disease"` searches a
        disease name (e.g. "breast carcinoma") and returns the top associated
        targets. Scores are Open Targets association scores (0-1), not
        p-values.

        The response includes the resolved `hit` (id/name), `details` for
        the target or disease, the total association `count`, and up to
        `limit` items. If the search has no hit, `hit` is null and `count`
        is 0. Only upstream fields are returned; nothing is inferred.

        Args:
            query: Gene/protein symbol or disease name.
            entity: "target" or "disease".
            limit: Associations to return, 1-25 (default 5).
        """
        entity = entity.strip().lower()
        if entity not in ENTITIES:
            return tool_error(
                f"invalid entity: {entity!r}",
                hint=f"use one of: {', '.join(ENTITIES)}",
                source="opentargets",
            )
        if not query.strip():
            return tool_error("query must not be empty", source="opentargets")
        if not 1 <= limit <= 25:
            return tool_error(f"limit must be 1-25, got {limit}", source="opentargets")
        try:
            hits = await opentargets.search(query.strip(), entity, 1)
            if not hits:
                return {
                    "source": "opentargets",
                    "source_url": f"https://platform.opentargets.org/{entity}",
                    "entity": entity,
                    "hit": None,
                    "count": 0,
                    "items": [],
                }
            hit = hits[0]
            if entity == "target":
                result = await opentargets.target(hit["id"], limit)
                details = {
                    "symbol": result["symbol"],
                    "name": result["name"],
                    "function_descriptions": result["function_descriptions"],
                }
            else:
                result = await opentargets.disease(hit["id"], limit)
                details = {"name": result["name"], "description": result["description"]}
            return {
                "source": "opentargets",
                "source_url": f"https://platform.opentargets.org/{entity}/{hit['id']}",
                "entity": entity,
                "hit": hit,
                "details": {key: value for key, value in details.items() if value},
                "count": result["count"],
                "items": result["items"],
            }
        except ProviderError as exc:
            return provider_error_payload(exc, "opentargets")

    @guarded_tool(mcp, name="pathways", source="reactome")
    async def pathways(
        query: str, species: str = "Homo sapiens", limit: int = 10
    ) -> dict:
        """Search Reactome pathways by gene, protein or pathway name.

        `query` is a free-text term (e.g. "TP53" or "apoptosis"); `species`
        defaults to human, pass an empty string to search all species.
        Returns pathway stable ids, cleaned display names and species.
        Empty lists are true upstream answers; only upstream fields are
        returned.

        Args:
            query: Gene/protein/pathway search term.
            species: Species name (default "Homo sapiens"; empty = all).
            limit: Pathways to return, 1-50 (default 10).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="reactome")
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source="reactome")
        try:
            page = await reactome.pathways(
                query.strip(), species.strip() or None, limit
            )
        except ProviderError as exc:
            return provider_error_payload(exc, "reactome")
        return {
            "source": "reactome",
            "source_url": f"https://reactome.org/content/query?q={quote(query)}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {"opentargets": opentargets_tool, "pathways": pathways}
