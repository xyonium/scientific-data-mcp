"""FastMCP server assembly."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .runtime import Service, build_service
from .tools import register_all

INSTRUCTIONS = """\
Free, keyless scientific entity data. Chemistry: PubChem compounds and
ChEMBL bioactivity/mechanisms. Proteins: UniProt entries, search and ID
mapping; RCSB PDB structures and structure search. Literature: PubMed
records by PMID or DOI (metadata only — this server does not search the
literature across sources; use paper-search for that).

Every tool returns upstream data only. A missing field means the upstream
does not provide it; never infer it. On failure the tool returns
{"error": ..., "source": ...} instead of raising, so one bad upstream call
never aborts a turn.
"""


def build_server(service: Service | None = None) -> FastMCP:
    service = service or build_service()
    mcp = FastMCP("scientific-data-mcp", instructions=INSTRUCTIONS)
    register_all(mcp, service)
    return mcp
