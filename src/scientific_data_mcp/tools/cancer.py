"""Cancer genomics tools: GDC and cBioPortal study catalogues."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]
SOURCES = ("gdc", "cbioportal")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    gdc = service.providers["gdc"]
    cbioportal = service.providers["cbioportal"]

    @guarded_tool(mcp, name="cancer_studies", source="cancer")
    async def cancer_studies(
        query: str, source: str = "gdc", limit: int = 10
    ) -> dict:
        """Search cancer genomics studies in GDC or cBioPortal.

        `source="gdc"` searches NCI GDC projects by id/name/primary site/
        disease type; `source="cbioportal"` searches cBioPortal study names
        and descriptions. Both return study id, name, cancer type/site,
        sample count and citation fields where available. Empty results are
        `count: 0`; only upstream fields are returned, missing fields are
        omitted, nothing is inferred or completed. Failures return an error
        dict (`error`, `source`).

        Args:
            query: Free-text study/project search term.
            source: "gdc" or "cbioportal".
            limit: Studies to return, 1-50 (default 10).
        """
        source = source.strip().lower()
        if source not in SOURCES:
            return tool_error(
                f"invalid source: {source!r}",
                hint=f"use one of: {', '.join(SOURCES)}",
                source="cancer",
            )
        if not query.strip():
            return tool_error("query must not be empty", source=source)
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source=source)
        try:
            if source == "gdc":
                page = await gdc.projects(query.strip(), limit)
                source_url = "https://portal.gdc.cancer.gov/projects"
            else:
                page = await cbioportal.studies(query.strip(), limit)
                source_url = (
                    "https://www.cbioportal.org/studies"
                    f"?keyword={quote(query.strip())}"
                )
        except ProviderError as exc:
            return provider_error_payload(exc, source)
        result = {
            "source": source,
            "source_url": source_url,
            "count": len(page["items"]),
            "items": page["items"],
        }
        if page.get("total") is not None:
            result["total"] = page["total"]
        return result

    return {"cancer_studies": cancer_studies}
