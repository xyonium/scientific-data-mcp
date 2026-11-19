"""Genomics tools: NCBI Gene records and ClinVar variants."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    gene = service.providers["ncbi_gene"]
    clinvar = service.providers["clinvar"]

    @guarded_tool(mcp, name="gene_record", source="ncbi_gene")
    async def gene_record(identifier: str, organism: int = 9606) -> dict:
        """Fetch one NCBI Gene record by symbol or Gene ID.

        `identifier` is a gene symbol ("TP53") or a numeric NCBI Gene ID
        ("7157"); `organism` is an NCBI taxonomy id (9606 human, 10090
        mouse). Returns symbol, description, chromosome, map location,
        aliases, summary, organism and taxid. Missing annotations stay
        missing; nothing is inferred.

        Args:
            identifier: Gene symbol or numeric NCBI Gene ID.
            organism: NCBI taxonomy id (default 9606 human).
        """
        identifier = identifier.strip()
        if not identifier:
            return tool_error("identifier must not be empty", source="ncbi_gene")
        if not 1 <= organism <= 10_000_000:
            return tool_error(f"invalid organism tax id: {organism}", source="ncbi_gene")
        try:
            record = await gene.record(identifier, organism)
        except ProviderError as exc:
            return provider_error_payload(exc, "ncbi_gene")
        return {
            "source": "ncbi_gene",
            "source_url": f"https://www.ncbi.nlm.nih.gov/gene/{record['gene_id']}",
            "record": record,
        }

    @guarded_tool(mcp, name="clinvar", source="clinvar")
    async def clinvar_tool(query: str, limit: int = 10) -> dict:
        """Search ClinVar variants by gene, variant or clinical significance.

        `query` uses ClinVar search syntax, e.g. `BRCA1[gene] AND
        pathogenic[clinical_significance]` or `NM_007294.4(BRCA1):c.711del`.
        Returns variant accessions, titles, germline classification, review
        status, conditions, genes, protein change and molecular consequences.
        Empty results are a true upstream answer (`count: 0`).

        Args:
            query: ClinVar search expression.
            limit: Variants to return, 1-50 (default 10).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="clinvar")
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source="clinvar")
        try:
            page = await clinvar.search(query.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "clinvar")
        return {
            "source": "clinvar",
            "source_url": f"https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(query)}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {"gene_record": gene_record, "clinvar": clinvar_tool}
