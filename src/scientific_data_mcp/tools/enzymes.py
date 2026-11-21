"""Enzyme tools: BRENDA (key-gated SOAP)."""

from __future__ import annotations

import re
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]

_EC = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
_KINDS = ("km", "kcat", "ki", "kcat_km", "substrates", "names", "engineering")


def register(mcp: FastMCP, service: Service) -> ToolMap:
    brenda = service.providers.get("brenda")
    if brenda is None:
        return {}

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

        `organism` optionally filters by scientific name. BRENDA SOAP allows
        at most 1 request/second; this tool never retries. Only upstream
        fields are returned; missing fields omitted, nothing is inferred.
        Failures return an error dict (`error`, `source`).

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

    return {"brenda": brenda_tool}
