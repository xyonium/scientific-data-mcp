"""Additional chemistry sources: KEGG compounds and DailyMed labels."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    kegg = service.providers["kegg"]
    dailymed = service.providers["dailymed"]
    chebi = service.providers["chebi"]
    bindingdb = service.providers["bindingdb"]
    cod = service.providers["cod"]

    @guarded_tool(mcp, name="dailymed", source="dailymed")
    async def dailymed_tool(query: str, limit: int = 5) -> dict:
        """Search DailyMed drug labels by drug name.

        `query` is a drug name ("aspirin"); returns SPL set ids, titles,
        published dates and SPL versions. DailyMed is NLM's official label
        repository; this is metadata search only (no full label text).
        Only upstream fields are returned; missing fields are omitted,
        nothing is inferred or completed. Failures return an error dict
        (`error`, `source`).

        Args:
            query: Drug name.
            limit: Labels to return, 1-20 (default 5).
        """
        if not query.strip():
            return tool_error("query must not be empty", source="dailymed")
        if not 1 <= limit <= 20:
            return tool_error(f"limit must be 1-20, got {limit}", source="dailymed")
        try:
            page = await dailymed.search(query.strip(), limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "dailymed")
        return {
            "source": "dailymed",
            "source_url": (
                "https://dailymed.nlm.nih.gov/dailymed/search.cfm"
                f"?labeltype=all&query={quote(query.strip())}"
            ),
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    @guarded_tool(mcp, name="bindingdb_ligands", source="bindingdb")
    async def bindingdb_ligands(
        uniprot: str, cutoff_nm: float = 10000, limit: int = 20
    ) -> dict:
        """Fetch BindingDB ligands/affinities for a UniProt target.

        `uniprot` is a UniProt accession ("P35355"); `cutoff_nm` filters
        affinities (nM, default 10000). Returns monomer id, SMILES, affinity
        type and value. BindingDB is free/keyless; keep calls to ~1/s. Only
        upstream fields are returned; missing fields are omitted, nothing is
        inferred or completed. Failures return an error dict (`error`,
        `source`).

        Args:
            uniprot: UniProt accession.
            cutoff_nm: Affinity cutoff in nM (default 10000).
            limit: Ligand rows to return, 1-100 (default 20).
        """
        if not uniprot.strip():
            return tool_error("uniprot must not be empty", source="bindingdb")
        if not 0.001 <= cutoff_nm <= 1_000_000:
            return tool_error(f"cutoff_nm out of range: {cutoff_nm}", source="bindingdb")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="bindingdb")
        try:
            page = await bindingdb.ligands(uniprot.strip(), cutoff_nm, limit)
        except ProviderError as exc:
            return provider_error_payload(exc, "bindingdb")
        return {
            "source": "bindingdb",
            "source_url": f"https://bindingdb.org/rwd/bind/BindingDB.jsp?uniprot={uniprot.strip()}",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    @guarded_tool(mcp, name="compound_lookup", source="compound")
    async def compound_lookup(
        query: str, source: str = "chebi", limit: int = 5
    ) -> dict:
        """Look up compounds in ChEBI or KEGG.

        Pick `source`:

        - `chebi` (default): EBI ChEBI ontology; item shape is
          `chebi_id/name/description/synonyms/type`. A name is searched; an
          exact `CHEBI:15365` returns that term with synonyms.
        - `kegg`: KEGG compound; item shape is
          `entry/names/formula/exact_mass/mol_weight/pathways`. KEGG REST is
          free for academic use; commercial use requires a KEGG license.

        `query` is a compound name or source id (KEGG `C01405`). Only
        upstream fields are returned; missing fields are omitted, nothing is
        inferred or completed. Failures return an error dict (`error`,
        `source`).

        Args:
            query: Compound name or ChEBI/KEGG id.
            source: "chebi" or "kegg".
            limit: Matches/records to return, 1-10 (default 5).
        """
        source = source.strip().lower()
        if source not in ("chebi", "kegg"):
            return tool_error(
                f"invalid source: {source!r}",
                hint="use one of: chebi, kegg",
                source="compound",
            )
        if not query.strip():
            return tool_error("query must not be empty", source=source)
        if not 1 <= limit <= 10:
            return tool_error(f"limit must be 1-10, got {limit}", source=source)
        query = query.strip()
        try:
            if source == "chebi":
                if re.match(r"^CHEBI[:_]\d+$", query, re.IGNORECASE):
                    items = [await chebi.term(query)]
                    source_url = (
                        "https://www.ebi.ac.uk/chebi/searchId.do?"
                        f"chebiId={items[0]['chebi_id']}"
                    )
                else:
                    items = await chebi.search(query, limit)
                    source_url = "https://www.ebi.ac.uk/chebi/"
            else:
                items = await kegg.compound(query, limit)
                source_url = (
                    f"https://www.kegg.jp/entry/{query}"
                    if query.upper().startswith("C") and query[1:].isdigit()
                    else f"https://www.kegg.jp/kegg-bin/search?query={quote(query)}"
                )
        except ValueError as exc:
            return tool_error(str(exc), source=source)
        except ProviderError as exc:
            return provider_error_payload(exc, source)
        return {
            "source": source,
            "source_url": source_url,
            "count": len(items),
            "items": items,
        }

    @guarded_tool(mcp, name="cod_crystals", source="cod")
    async def cod_crystals(
        cod_id: str = "",
        formula: str = "",
        elements: str = "",
        text: str = "",
        limit: int = 10,
    ) -> dict:
        """Search experimental crystal structures in the COD.

        Provide exactly one filter: `cod_id` (e.g. "1526463"), `formula`
        ("Fe2 O3" or "Fe2O3"), `elements` (comma/space list, e.g. "Fe,O") or
        `text`. Returns COD id, formula, chemical/mineral name, title,
        authors, journal/year, DOI, space group and unit cell. COD is
        experimental data (complements Materials Project's DFT data); a
        mirror may lag the main site. Only upstream fields are returned;
        missing fields omitted, nothing is inferred or completed. Failures
        return an error dict.

        Args:
            cod_id: Exact COD entry id.
            formula: COD formula (spaces between element groups).
            elements: Comma/space separated elements.
            text: Free-text search (title/author/journal).
            limit: Entries to return, 1-50 (default 10).
        """
        filters = [x for x in (cod_id.strip(), formula.strip(), elements.strip(), text.strip()) if x]
        if len(filters) != 1:
            return tool_error(
                "provide exactly one of cod_id, formula, elements, text",
                source="cod",
            )
        if not 1 <= limit <= 50:
            return tool_error(f"limit must be 1-50, got {limit}", source="cod")
        params: dict[str, str] = {}
        if cod_id.strip():
            params["id"] = cod_id.strip()
        elif formula.strip():
            normalized = re.sub(r"(?<=[0-9])(?=[A-Z])", " ", formula.strip())
            params["formula"] = normalized
        elif elements.strip():
            parts = [p for p in re.split(r"[,;\s]+", elements.strip()) if p]
            if not 1 <= len(parts) <= 5:
                return tool_error("elements accepts 1-5 element symbols", source="cod")
            for i, part in enumerate(parts, 1):
                params[f"el{i}"] = part
        else:
            params["text"] = text.strip()
        try:
            result = await cod.search(params)
        except ProviderError as exc:
            return provider_error_payload(exc, "cod")
        items = [cod.normalize(row) for row in result["items"][:limit]]
        host = result["host"]
        source_url = f"{host}/{cod_id.strip()}.html" if cod_id.strip() else f"{host}/"
        return {
            "source": "cod",
            "source_url": source_url,
            "via_mirror": result["via_mirror"],
            "count": len(items),
            "items": items,
        }

    return {
        "dailymed": dailymed_tool,
        "bindingdb_ligands": bindingdb_ligands,
        "compound_lookup": compound_lookup,
        "cod_crystals": cod_crystals,
    }
