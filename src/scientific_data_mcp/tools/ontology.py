"""Phenotype tools: Human Phenotype Ontology terms."""

from __future__ import annotations

import re
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]
_HP_ID = re.compile(r"^HP:\d{7}$")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    hpo = service.providers["hpo"]

    @guarded_tool(mcp, name="phenotypes", source="hpo")
    async def phenotypes(query: str, limit: int = 10) -> dict:
        """Search Human Phenotype Ontology (HPO) terms.

        `query` is a phenotype phrase (e.g. "seizure") or an exact HPO id
        (e.g. "HP:0001250"). Returns term ids, names, definitions, synonyms
        and descendant counts. An exact id returns that single term; a text
        query returns up to `limit` matches. Empty text results are a true
        upstream answer; only upstream fields are returned.

        Args:
            query: Phenotype phrase or HP id.
            limit: Matches to return, 1-50 (default 10).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="hpo")
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source="hpo")
        query = query.strip()
        try:
            if _HP_ID.match(query):
                items = [await hpo.term(query)]
                source_url = f"https://hpo.jax.org/browse/term/{query}"
            else:
                items = await hpo.search(query, limit)
                source_url = "https://hpo.jax.org/browse/terms"
        except ProviderError as exc:
            return provider_error_payload(exc, "hpo")
        return {
            "source": "hpo",
            "source_url": source_url,
            "count": len(items),
            "items": items,
        }

    return {"phenotypes": phenotypes}
