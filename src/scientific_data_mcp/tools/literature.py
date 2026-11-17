"""Literature tool: one PubMed record by PMID or DOI (metadata only)."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service

ToolMap = dict[str, Callable]



def register(mcp: FastMCP, service: Service) -> ToolMap:
    pubmed = service.providers["pubmed"]

    @mcp.tool(name="pubmed_record")
    async def pubmed_record(pmid: str | None = None, doi: str | None = None) -> dict:
        """Return one structured PubMed record by PMID or DOI.

        Metadata only (title, authors, journal, year/volume/issue/pages,
        abstract, DOI, PMCID) — no full text and no cross-source literature
        search; use paper-search for that. Pass exactly one identifier.

        Args:
            pmid: PubMed id, e.g. "23903748".
            doi: DOI, e.g. "10.1038/nature12373".
        """
        if bool(pmid) == bool(doi):
            return tool_error("pass exactly one of pmid or doi", source="pubmed")
        try:
            record = await (pubmed.by_pmid(pmid.strip()) if pmid else pubmed.by_doi(doi.strip()))
        except ProviderError as exc:
            return tool_error(f"{exc.kind}: {exc}", source="pubmed")
        return {
            "source": "pubmed",
            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{record['pmid']}/",
            "record": record,
        }

    return {"pubmed_record": pubmed_record}
