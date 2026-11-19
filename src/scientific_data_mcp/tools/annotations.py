"""Protein annotation tools: InterPro entries and QuickGO annotations."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

SOURCES = ("interpro", "quickgo")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    interpro = service.providers["interpro"]
    quickgo = service.providers["quickgo"]

    @guarded_tool(mcp, name="protein_annotations", source="annotations")
    async def protein_annotations(
        identifier: str, source: str = "interpro", limit: int = 20
    ) -> dict:
        """Fetch InterPro entries or QuickGO GO annotations for a UniProt protein.

        `source="interpro"` returns integrated and member-database entries
        (accession, name, type, source database, GO terms); `source="quickgo"`
        returns GO annotations (GO id, qualifier, evidence, aspect, reference,
        assigned by). `identifier` is a UniProt accession such as "P04637"
        (a `UniProtKB:` prefix is accepted and stripped).

        Only upstream fields are returned; missing names/evidence stay
        missing. Empty lists are true upstream answers.

        Args:
            identifier: UniProt accession.
            source: "interpro" or "quickgo".
            limit: Entries/annotations to return, 1-50 (default 20).
        """
        source = source.strip().lower()
        if source not in SOURCES:
            return tool_error(
                f"invalid source: {source!r}",
                hint=f"use one of: {', '.join(SOURCES)}",
                source="annotations",
            )
        accession = identifier.strip()
        if accession.upper().startswith("UNIPROTKB:"):
            accession = accession.split(":", 1)[1].strip()
        if not accession:
            return tool_error("identifier must not be empty", source=source)
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source=source)
        try:
            if source == "interpro":
                page = await interpro.entries(accession, limit)
                source_url = f"https://www.ebi.ac.uk/interpro/protein/UniProt/{accession}/"
            else:
                page = await quickgo.annotations(accession, limit)
                source_url = (
                    "https://www.ebi.ac.uk/QuickGO/annotations"
                    f"?geneProductId=UniProtKB:{accession}"
                )
        except ProviderError as exc:
            return provider_error_payload(exc, source)
        return {
            "source": source,
            "source_url": source_url,
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {"protein_annotations": protein_annotations}
