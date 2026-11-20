"""Clinical association tools: GWAS Catalog and Monarch."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

_EFO_ID = re.compile(r"^(MONDO|EFO|HP|ORPHA|DOID)[:_]\d+$", re.IGNORECASE)
_MONARCH_CATEGORIES = {
    "gene_disease": "biolink:CausalGeneToDiseaseAssociation",
    "gene_phenotype": "biolink:GeneToPhenotypicFeatureAssociation",
    "disease_phenotype": "biolink:DiseaseToPhenotypicFeatureAssociation",
    "all": None,
}


def register(mcp: FastMCP, service: Service) -> ToolMap:
    gwas = service.providers["gwas"]
    monarch = service.providers["monarch"]

    @guarded_tool(mcp, name="gwas_associations", source="gwas")
    async def gwas_associations(
        query: str,
        by: str = "auto",
        limit: int = 10,
        page: int = 0,
    ) -> dict:
        """Fetch GWAS Catalog SNP-trait associations.

        `query` is an rs id ("rs7412"), an EFO/MONDO trait id
        ("MONDO_0005150"), an exact EFO trait name, or a mapped gene symbol.
        `by="auto"` treats `rs...` as `rs_id`, ontology ids as `efo_id`, and
        everything else as `efo_trait` (the trait name must match the
        catalog's EFO label). Returns association id, p-value, reported/EFO
        traits, mapped genes, effect allele, beta, PMID and study accession.
        Only upstream fields are returned; missing fields are omitted,
        nothing is inferred. Failures return an error dict (`error`,
        `source`).

        Args:
            query: rs id, trait id/name, or gene symbol.
            by: "auto", "rs_id", "efo_trait", "efo_id" or "mapped_gene".
            limit: Associations per page, 1-100 (default 10).
            page: Zero-based page (default 0).
        """
        by = by.strip().lower()
        if by not in ("auto", "rs_id", "efo_trait", "efo_id", "mapped_gene"):
            return tool_error(
                f"invalid by: {by!r}",
                hint="use one of: auto, rs_id, efo_trait, efo_id, mapped_gene",
                source="gwas",
            )
        if not query.strip():
            return tool_error("query must not be empty", source="gwas")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="gwas")
        if not 0 <= page <= 100_000:
            return tool_error(f"page out of range: {page}", source="gwas")
        query = query.strip()
        if by == "auto":
            if re.fullmatch(r"rs\d+", query, re.IGNORECASE):
                by = "rs_id"
            elif _EFO_ID.match(query):
                by = "efo_id"
            else:
                by = "efo_trait"
        if by == "efo_id":
            query = re.sub(r"[:_]", "_", query)
        try:
            result = await gwas.associations(by, query, limit, page)
        except ValueError as exc:
            return tool_error(str(exc), source="gwas")
        except ProviderError as exc:
            return provider_error_payload(exc, "gwas")
        total = result["total"]
        next_page = page + 1 if (page + 1) * limit < total else None
        source_url = (
            f"https://www.ebi.ac.uk/gwas/variants/{query}"
            if by == "rs_id"
            else "https://www.ebi.ac.uk/gwas/"
        )
        return {
            "source": "gwas",
            "source_url": source_url,
            "count": len(result["items"]),
            "total": total,
            "next_page": next_page,
            "items": result["items"],
        }

    @guarded_tool(mcp, name="monarch_associations", source="monarch")
    async def monarch_associations(
        entity: str,
        category: str = "gene_disease",
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """Fetch Monarch Initiative associations for one entity.

        `entity` is a Monarch/Biolink curie: HGNC:3603 (gene), MONDO:0007947
        (disease), HP:0001250 (phenotype), NCBIGene:7157. `category` picks
        gene-disease causal, gene-phenotype, disease-phenotype, or all
        associations. Returns subject/object ids and labels, predicate,
        publications and primary knowledge source. Only upstream fields are
        returned; missing fields are omitted, nothing is inferred. Failures
        return an error dict (`error`, `source`).

        Args:
            entity: Curie such as HGNC:3603.
            category: "gene_disease", "gene_phenotype",
                "disease_phenotype" or "all".
            limit: Associations per page, 1-100 (default 10).
            offset: Zero-based offset (default 0).
        """
        category = category.strip().lower()
        if category not in _MONARCH_CATEGORIES:
            return tool_error(
                f"invalid category: {category!r}",
                hint="use one of: gene_disease, gene_phenotype, disease_phenotype, all",
                source="monarch",
            )
        if not entity.strip():
            return tool_error("entity must not be empty", source="monarch")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="monarch")
        if not 0 <= offset <= 1_000_000:
            return tool_error(f"offset out of range: {offset}", source="monarch")
        try:
            result = await monarch.associations(
                entity.strip(), _MONARCH_CATEGORIES[category], limit, offset
            )
        except ProviderError as exc:
            return provider_error_payload(exc, "monarch")
        total = result["total"]
        next_offset = offset + limit if offset + limit < total else None
        return {
            "source": "monarch",
            "source_url": f"https://monarchinitiative.org/{quote(entity.strip(), safe=':')}",
            "count": len(result["items"]),
            "total": total,
            "next_offset": next_offset,
            "items": result["items"],
        }

    return {"gwas_associations": gwas_associations, "monarch_associations": monarch_associations}
