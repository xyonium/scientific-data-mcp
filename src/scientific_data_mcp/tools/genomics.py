"""Genomics tools: NCBI Gene records and ClinVar variants."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

_ENSEMBL_SPECIES = {
    9606: "homo_sapiens",
    10090: "mus_musculus",
    10116: "rattus_norvegicus",
    559292: "saccharomyces_cerevisiae",
    7227: "drosophila_melanogaster",
    6239: "caenorhabditis_elegans",
    7955: "danio_rerio",
    3702: "arabidopsis_thaliana",
    9031: "gallus_gallus",
    9615: "canis_lupus_familiaris",
    9823: "sus_scrofa",
    9913: "bos_taurus",
    9544: "macaca_mulatta",
}


def register(mcp: FastMCP, service: Service) -> ToolMap:
    gene = service.providers["ncbi_gene"]
    clinvar = service.providers["clinvar"]
    ensembl = service.providers["ensembl"]

    @guarded_tool(mcp, name="gene_record", source="ncbi_gene")
    async def gene_record(
        identifier: str, organism: int = 9606, kind: str = "ncbi"
    ) -> dict:
        """Fetch one gene record from NCBI Gene or Ensembl.

        Pick `kind`:

        - `ncbi` (default): `identifier` is a gene symbol ("TP53") or a
          numeric NCBI Gene ID ("7157"); returns symbol, description,
          chromosome, map location, aliases, summary, organism and taxid.
        - `ensembl`: `identifier` is a gene symbol or Ensembl gene id; the
          NCBI taxid in `organism` is mapped to an Ensembl species. Returns
          symbol, description, biotype, chromosome, coordinates, assembly
          and canonical transcript. One request per call, no retries.

        Missing annotations stay missing; nothing is inferred or completed.
        Failures return an error dict (`error`, `source`).

        Args:
            identifier: Gene symbol, NCBI Gene ID, or Ensembl gene id.
            organism: NCBI taxonomy id (default 9606 human).
            kind: "ncbi" or "ensembl".
        """
        identifier = identifier.strip()
        kind = kind.strip().lower()
        if kind not in ("ncbi", "ensembl"):
            return tool_error(
                f"invalid kind: {kind!r}", hint="use one of: ncbi, ensembl",
                source="ncbi_gene",
            )
        if not identifier:
            return tool_error("identifier must not be empty", source=kind)
        if not 1 <= organism <= 10_000_000:
            return tool_error(f"invalid organism tax id: {organism}", source=kind)
        try:
            if kind == "ncbi":
                record = await gene.record(identifier, organism)
                source_name = "ncbi_gene"
                source_url = f"https://www.ncbi.nlm.nih.gov/gene/{record['gene_id']}"
            else:
                species = _ENSEMBL_SPECIES.get(organism)
                if species is None:
                    return tool_error(
                        f"unsupported organism for Ensembl: {organism}",
                        hint=f"use one of: {', '.join(str(k) for k in _ENSEMBL_SPECIES)}",
                        source="ensembl",
                    )
                record = await ensembl.gene(identifier, species)
                source_name = "ensembl"
                source_url = (
                    f"https://www.ensembl.org/{species.capitalize()}/Gene/Summary"
                    f"?g={record['gene_id']}"
                )
        except ProviderError as exc:
            return provider_error_payload(exc, "ncbi_gene" if kind == "ncbi" else "ensembl")
        return {"source": source_name, "source_url": source_url, "record": record}

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
