"""Materials Project tools (registered only when a key is configured)."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import tool_error
from ..runtime import Service
from ._guard import guarded_tool

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    provider = service.providers.get("materials_project")
    if provider is None:
        return {}

    @guarded_tool(mcp, name="material_get", source="materials_project")
    async def material_get(material_id: str) -> dict:
        """Fetch one Materials Project summary by material id.

        Returns only fields the summary endpoint carries: formula, chemical
        system, band gap, energy above hull, density, stability, site count,
        theoretical flag and crystal symmetry. Requires a free
        MATERIALS_PROJECT_API_KEY; without one this tool is not registered.

        Args:
            material_id: Materials Project id, e.g. "mp-149" or "mp-aaaa...".
        """
        if not material_id.strip():
            return tool_error("material_id must not be empty", source="materials_project")
        record = await provider.get(material_id.strip())
        return {
            "source": "materials_project",
            "source_url": f"https://materialsproject.org/materials/{record['material_id']}",
            "record": record,
        }

    @guarded_tool(mcp, name="material_search", source="materials_project")
    async def material_search(
        formula: str | None = None,
        chemsys: str | None = None,
        elements: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Search Materials Project summaries by formula, chemical system or elements.

        Pass exactly one selector: `formula` ("SiO2"), `chemsys` ("Si-O") or
        `elements` ("Si,O"). Results are upstream summaries, nothing is
        inferred; an empty list is a valid answer. Requires a free
        MATERIALS_PROJECT_API_KEY.

        Args:
            formula: Reduced formula.
            chemsys: Dash-separated chemical system.
            elements: Comma-separated elements that must all be present.
            limit: Maximum rows, 1-100 (default 10).
        """
        selectors = [value.strip() for value in (formula, chemsys, elements) if value and value.strip()]
        if len(selectors) != 1:
            return tool_error(
                "pass exactly one of formula, chemsys or elements",
                source="materials_project",
            )
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="materials_project")
        rows = await provider.search(
            formula=formula.strip() if formula and formula.strip() else None,
            chemsys=chemsys.strip() if chemsys and chemsys.strip() else None,
            elements=elements.strip() if elements and elements.strip() else None,
            limit=limit,
        )
        return {
            "source": "materials_project",
            "source_url": "https://materialsproject.org/",
            "count": len(rows),
            "items": rows,
        }

    return {"material_get": material_get, "material_search": material_search}
