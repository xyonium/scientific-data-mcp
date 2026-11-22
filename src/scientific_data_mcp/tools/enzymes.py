"""Enzyme tools: BRENDA (key-gated SOAP), Rhea reactions, M-CSA sites."""

from __future__ import annotations

import re
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

_EC = re.compile(r"^\d+\.\d+\.\d+\.(?:\d+|n\d+)$", re.IGNORECASE)
_UNIPROT = re.compile(r"^[A-Z0-9]{6,10}$", re.IGNORECASE)
_KINDS = ("km", "kcat", "ki", "kcat_km", "substrates", "names", "engineering")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    tools: ToolMap = {}
    rhea = service.providers.get("rhea")
    mcsa = service.providers.get("mcsa")
    brenda = service.providers.get("brenda")
    sabio = service.providers.get("sabio")

    if rhea is not None:

        @guarded_tool(mcp, name="rhea_reactions", source="rhea")
        async def rhea_reactions(query: str, limit: int = 10) -> dict:
            """Search Rhea expert-curated biochemical reactions.

            `query` can be an EC number ("1.1.1.1"), a ChEBI id, a reaction
            participant name, or a Rhea id. Returns Rhea id, equation,
            approval status, comment, balanced/transport flags. Rhea links
            reactions to EC numbers and ChEBI; it complements KEGG/Reactome
            with a curated reaction layer. Only upstream fields are returned;
            missing fields omitted, nothing is inferred. Failures return an
            error dict (`error`, `source`).

            Args:
                query: EC number, ChEBI id, compound name, or Rhea id.
                limit: Reactions to return, 1-50 (default 10).
            """
            if not query.strip():
                return tool_error("query must not be empty", source="rhea")
            if not 1 <= limit <= 50:
                return tool_error(f"limit must be 1-50, got {limit}", source="rhea")
            try:
                page = await rhea.search(query.strip(), limit)
            except ProviderError as exc:
                return provider_error_payload(exc, "rhea")
            items = page["items"][:limit]
            return {
                "source": "rhea",
                "source_url": "https://www.rhea-db.org/",
                "count": len(items),
                "total": page["total"],
                "items": items,
            }

        tools["rhea_reactions"] = rhea_reactions

    if mcsa is not None:

        @guarded_tool(mcp, name="mcsa_sites", source="mcsa")
        async def mcsa_sites(
            enzyme: str = "",
            uniprot: str = "",
            mcsa_id: str = "",
            limit: int = 5,
        ) -> dict:
            """Fetch M-CSA enzyme mechanisms and catalytic residues.

            Provide exactly one filter: `enzyme` (EC number), `uniprot`
            accession, or `mcsa_id`. Returns enzyme name, EC numbers,
            reference UniProt, mechanism description, reaction participants
            and catalytic residues with their roles/PDB chain. M-CSA is
            hand-curated structural mechanism data; it complements
            BRENDA/SABIO-RK kinetics. Only upstream fields are returned;
            missing fields omitted, nothing is inferred. Failures return an
            error dict (`error`, `source`).

            Args:
                enzyme: EC number, e.g. "1.1.1.1".
                uniprot: UniProt accession.
                mcsa_id: Numeric M-CSA entry id.
                limit: Entries to return, 1-20 (default 5).
            """
            filters = [x for x in (enzyme.strip(), uniprot.strip(), mcsa_id.strip()) if x]
            if len(filters) != 1:
                return tool_error(
                    "provide exactly one of enzyme, uniprot, mcsa_id",
                    source="mcsa",
                )
            if not 1 <= limit <= 20:
                return tool_error(f"limit must be 1-20, got {limit}", source="mcsa")
            params: dict[str, str] = {}
            if enzyme.strip():
                if not _EC.match(enzyme.strip()):
                    return tool_error(
                        f"invalid EC number: {enzyme.strip()!r}",
                        hint='use a full EC number such as "1.1.1.1"',
                        source="mcsa",
                    )
                params["entries.reactions.ecs.codes"] = enzyme.strip()
            elif uniprot.strip():
                if not _UNIPROT.match(uniprot.strip()):
                    return tool_error(
                        f"invalid UniProt accession: {uniprot.strip()!r}",
                        source="mcsa",
                    )
                params["entries.proteins.sequences.uniprot_ids"] = uniprot.strip().upper()
            else:
                if not mcsa_id.strip().isdigit():
                    return tool_error(f"invalid M-CSA id: {mcsa_id.strip()!r}", source="mcsa")
                params["entries.mcsa_ids"] = mcsa_id.strip()
            try:
                page = await mcsa.entries(params, limit)
            except ProviderError as exc:
                return provider_error_payload(exc, "mcsa")
            return {
                "source": "mcsa",
                "source_url": "https://www.ebi.ac.uk/thornton-srv/m-csa/",
                "count": len(page["items"]),
                "total": page["total"],
                "items": page["items"],
            }

        tools["mcsa_sites"] = mcsa_sites

    if sabio is not None:

        @guarded_tool(mcp, name="sabio_kinetics", source="sabio")
        async def sabio_kinetics(
            ec_number: str, page: int = 1, limit: int = 20
        ) -> dict:
            """Fetch SABIO-RK kinetic law entries by EC number.

            Returns kinetic parameters (kcat, Km, Ki, kcat/Km...), units,
            organism, enzyme/mutant, reaction equation, pH/temperature/buffer
            and PubMed reference. SABIO-RK includes experimental conditions
            that BRENDA rows do not; use it alongside `brenda`. Only upstream
            fields are returned; missing fields omitted, nothing is inferred.
            Failures return an error dict (`error`, `source`).

            Args:
                ec_number: Full EC number, e.g. "1.1.1.1".
                page: 1-based page (default 1).
                limit: Entries per page, 1-50 (default 20).
            """
            ec = ec_number.strip()
            if not _EC.match(ec):
                return tool_error(
                    f"invalid EC number: {ec!r}",
                    hint='use a full EC number such as "1.1.1.1"',
                    source="sabio",
                )
            if not 1 <= page <= 10_000:
                return tool_error(f"page out of range: {page}", source="sabio")
            if not 1 <= limit <= 50:
                return tool_error(f"limit must be 1-50, got {limit}", source="sabio")
            try:
                result = await sabio.kinetics(ec, page, limit)
            except ProviderError as exc:
                return provider_error_payload(exc, "sabio")
            total = result["total"]
            next_page = page + 1 if page * result["page_size"] < total else None
            return {
                "source": "sabio",
                "source_url": f"https://sabiork.h-its.org/ui/search?q=ecnumber:{ec}",
                "count": len(result["items"]),
                "total": total,
                "next_page": next_page,
                "items": result["items"],
            }

        tools["sabio_kinetics"] = sabio_kinetics

    if brenda is not None:

        @guarded_tool(mcp, name="brenda", source="brenda")
        async def brenda_tool(
            enzyme: str, kind: str = "km", organism: str = "", limit: int = 20
        ) -> dict:
            """Fetch BRENDA enzyme data by EC number (requires registration).

            `enzyme` is a full EC number ("1.1.1.1"). `kind` selects:

            - `km`: Michaelis constants with substrate, commentary, literature
            - `kcat`: turnover numbers
            - `ki`: inhibition constants with inhibitor
            - `kcat_km`: catalytic efficiency entries
            - `substrates`: substrates/products and reversibility
            - `names`: enzyme names/synonyms
            - `engineering`: protein variants/engineering entries

            `organism` optionally filters by scientific name. BRENDA SOAP
            allows at most 1 request/second; this tool never retries. Only
            upstream fields are returned; missing fields omitted, nothing is
            inferred. Failures return an error dict (`error`, `source`).

            Args:
                enzyme: Full EC number, e.g. "1.1.1.1".
                kind: One of km, kcat, ki, kcat_km, substrates, names, engineering.
                organism: Optional organism scientific name.
                limit: Rows to return, 1-100 (default 20).
            """
            kind = kind.strip().lower()
            if kind not in _KINDS:
                return tool_error(
                    f"invalid kind: {kind!r}",
                    hint=f"use one of: {', '.join(_KINDS)}",
                    source="brenda",
                )
            ec = enzyme.strip()
            if not _EC.match(ec):
                return tool_error(
                    f"invalid EC number: {ec!r}",
                    hint='use a full EC number such as "1.1.1.1"',
                    source="brenda",
                )
            if not 1 <= limit <= 100:
                return tool_error(f"limit must be 1-100, got {limit}", source="brenda")
            try:
                items = await brenda.query(kind, ec, organism.strip())
            except ProviderError as exc:
                return provider_error_payload(exc, "brenda")
            return {
                "source": "brenda",
                "source_url": f"https://www.brenda-enzymes.org/enzyme.php?ecno={ec}",
                "count": len(items[:limit]),
                "total": len(items),
                "items": items[:limit],
            }

        tools["brenda"] = brenda_tool

    return tools
