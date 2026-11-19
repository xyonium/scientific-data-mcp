"""Expression tools: GTEx median gene expression."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    gtex = service.providers["gtex"]

    @guarded_tool(mcp, name="gene_expression", source="gtex")
    async def gene_expression(
        gene_id: str, dataset: str = "gtex_v8", limit: int = 20
    ) -> dict:
        """Fetch GTEx median gene expression across tissues.

        `gene_id` is an Ensembl gene id ("ENSG00000141510"); a versioned id
        is accepted. `dataset` defaults to "gtex_v8" (GTEx v10 may be
        available upstream). Returns tissue site, ontology id, median
        expression and unit (TPM), plus gene symbol/gencode id. Empty tissue
        lists are true upstream answers; only upstream fields are returned,
        missing fields are omitted, nothing is inferred or completed.
        Failures return an error dict (`error`, `source`).

        Args:
            gene_id: Ensembl gene id.
            dataset: GTEx dataset id (default "gtex_v8").
            limit: Tissue rows to return, 1-100 (default 20).
        """
        if not gene_id.strip():
            return tool_error("gene_id must not be empty", source="gtex")
        if not dataset.strip():
            return tool_error("dataset must not be empty", source="gtex")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="gtex")
        try:
            page = await gtex.expression(gene_id.strip(), dataset.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "gtex")
        return {
            "source": "gtex",
            "source_url": f"https://gtexportal.org/home/gene/{gene_id.strip()}",
            "gene_symbol": page["gene_symbol"],
            "gencode_id": page["gencode_id"],
            "dataset": dataset.strip(),
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    return {"gene_expression": gene_expression}
