"""Materials Project tool (registered only when a key is configured)."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

BY = ("id", "formula", "chemsys", "elements")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    provider = service.providers.get("materials_project")
    if provider is None:
        return {}

    @guarded_tool(mcp, name="material", source="materials_project")
    async def material(query: str, by: str = "formula", limit: int = 10) -> dict:
        """Query Materials Project summaries (requires MATERIALS_PROJECT_API_KEY).

        Pick `by`:

        - `id`: one Materials Project id, e.g. "mp-149"; returns count 0/1.
        - `formula`: reduced formula, e.g. "SiO2".
        - `chemsys`: dash-separated chemical system, e.g. "Si-O".
        - `elements`: comma-separated elements that must all be present,
          e.g. "Si,O".

        Returns a list envelope (`count`, `items`) of upstream summaries:
        formula, chemical system, band gap, energy above hull, density,
        stability, site count, theoretical flag and crystal symmetry. Values
        are upstream only; missing fields stay missing. This tool is not
        registered when no key is configured.

        Args:
            query: Identifier or formula/system/elements string.
            by: "id", "formula", "chemsys" or "elements".
            limit: Maximum rows for non-id queries, 1-100.
        """
        by = by.strip().lower()
        if by not in BY:
            return tool_error(
                f"invalid by: {by!r}", hint=f"use one of: {', '.join(BY)}",
                source="materials_project",
            )
        query = query.strip()
        if not query:
            return tool_error("query must not be empty", source="materials_project")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="materials_project")
        try:
            if by == "id":
                record = await provider.get(query)
                return {
                    "source": "materials_project",
                    "source_url": f"https://materialsproject.org/materials/{record['material_id']}",
                    "count": 1,
                    "items": [record],
                }
            rows = await provider.search(
                formula=query if by == "formula" else None,
                chemsys=query if by == "chemsys" else None,
                elements=query if by == "elements" else None,
                limit=limit,
            )
        except ProviderError as exc:
            return provider_error_payload(exc, "materials_project")
        return {
            "source": "materials_project",
            "source_url": "https://materialsproject.org/",
            "count": len(rows),
            "items": rows,
        }

    return {"material": material}
