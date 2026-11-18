"""WHO Global Health Observatory tool."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..errors import tool_error
from ..runtime import Service
from ._guard import guarded_tool

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    who = service.providers["who"]

    @guarded_tool(mcp, name="who_data", source="who")
    async def who_data(
        indicator: str,
        country: str | None = None,
        year: int | None = None,
        sex: str | None = None,
        limit: int = 100,
    ) -> dict:
        """Fetch WHO Global Health Observatory observations by indicator code.

        Returns upstream observations only (country, year, sex, numeric value,
        the upstream value text with its confidence interval, low/high). An
        empty list is the true upstream answer. The code must be a GHO
        indicator code such as `WHOSIS_000001` (life expectancy at birth);
        this tool cannot search the indicator catalogue, so ask the user for
        a code or use the WHO GHO site to find one.

        Args:
            indicator: GHO indicator code, e.g. "WHOSIS_000001".
            country: Optional ISO3 country code, e.g. "CHN".
            year: Optional year, e.g. 2022.
            sex: Optional GHO sex code, e.g. "SEX_FMLE" / "SEX_MLE".
            limit: Maximum observations, 1-1000 (default 100).
        """
        code = indicator.strip().upper()
        if not code or not all(ch.isalnum() or ch == "_" for ch in code):
            return tool_error(
                "indicator must be a GHO indicator code like WHOSIS_000001",
                source="who",
            )
        if country:
            token = country.strip().upper()
            if not (token.isalpha() and (len(token) == 3 or token == "GLOBAL")):
                return tool_error(
                    f"country must be an ISO3 code like CHN, got {country!r}",
                    source="who",
                )
        if year is not None and not 1900 <= year <= 2100:
            return tool_error(f"year must be 1900-2100, got {year}", source="who")
        if sex and not sex.strip().upper().startswith("SEX_"):
            return tool_error(
                f"sex must be a GHO code like SEX_FMLE, got {sex!r}", source="who"
            )
        if not 1 <= limit <= 1000:
            return tool_error(f"limit must be 1-1000, got {limit}", source="who")
        rows = await who.data(
            code,
            country=country.strip() if country else None,
            year=year,
            sex=sex.strip() if sex else None,
            limit=limit,
        )
        return {
            "source": "who",
            "source_url": "https://www.who.int/data/gho",
            "count": len(rows),
            "items": rows,
        }

    return {"who_data": who_data}
