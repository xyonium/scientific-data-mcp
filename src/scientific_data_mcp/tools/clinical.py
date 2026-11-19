"""Clinical/regulatory tools: openFDA and ClinicalTrials.gov."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from ..errors import ProviderError, tool_error
from ..providers.openfda import ENDPOINTS as FDA_ENDPOINTS
from ..runtime import Service
from ._guard import guarded_tool, provider_error_payload

ToolMap = dict[str, Callable]


def register(mcp: FastMCP, service: Service) -> ToolMap:
    openfda = service.providers["openfda"]
    clinicaltrials = service.providers["clinicaltrials"]

    @guarded_tool(mcp, name="openfda", source="openfda")
    async def openfda_tool(
        query: str, endpoint: str = "drug/label", limit: int = 3, skip: int = 0
    ) -> dict:
        """Search openFDA drug labels, adverse events or enforcement reports.

        `query` is an openFDA search expression (field:term), for example
        `openfda.brand_name:"advil"` or `indications_and_usage:"pain"` for
        labels, `patient.drug.medicinalproduct:"ibuprofen"` for events, and
        `reason_for_recall:"contamination"` for enforcement. No matches are a
        normal `count: 0`, not an error.

        Records are upstream JSON and can be large (a drug label is ~10 KB),
        so the default limit is 3; keep it small. An optional free
        OPENFDA_API_KEY raises rate limits but is not required.

        Args:
            query: openFDA search expression.
            endpoint: "drug/label", "drug/event" or "drug/enforcement".
            limit: Records to return, 1-10 (default 3).
            skip: Records to skip, 0-1000.
        """
        endpoint = endpoint.strip().lower()
        if endpoint not in FDA_ENDPOINTS:
            return tool_error(
                f"invalid endpoint: {endpoint!r}",
                hint=f"use one of: {', '.join(FDA_ENDPOINTS)}",
                source="openfda",
            )
        if not query.strip():
            return tool_error("query must not be empty", source="openfda")
        if not 1 <= limit <= 10:
            return tool_error(f"limit must be 1-10, got {limit}", source="openfda")
        if not 0 <= skip <= 1000:
            return tool_error(f"skip must be 0-1000, got {skip}", source="openfda")
        try:
            page = await openfda.search(endpoint, query.strip(), limit, skip)
        except ProviderError as exc:
            return provider_error_payload(exc, "openfda")
        return {
            "source": "openfda",
            "source_url": f"https://open.fda.gov/apis/{endpoint}/",
            "count": len(page["items"]),
            "total": page["total"],
            "items": page["items"],
        }

    @guarded_tool(mcp, name="clinical_trials", source="clinicaltrials")
    async def clinical_trials(
        query: str,
        status: str | None = None,
        limit: int = 10,
        cursor: str | None = None,
    ) -> dict:
        """Search ClinicalTrials.gov v2 studies (keyless).

        `query` is a free-text term (condition, drug, title...). `status`
        filters by overall status, e.g. "RECRUITING" or "COMPLETED". Returns
        compact study records (NCT id, title, status, type, phases,
        conditions, interventions, enrollment, start date, sponsor) plus
        `total` and `next_cursor`; pass the cursor for the next page. Empty
        lists are true upstream answers.

        Args:
            query: Free-text search term.
            status: Optional overall status filter.
            limit: Studies per page, 1-100 (default 10).
            cursor: nextPageToken from a previous call.
        """
        if not query.strip():
            return tool_error("query must not be empty", source="clinicaltrials")
        if not 1 <= limit <= 100:
            return tool_error(f"limit must be 1-100, got {limit}", source="clinicaltrials")
        try:
            page = await clinicaltrials.search(
                query.strip(),
                status=status.strip() if status else None,
                limit=limit,
                cursor=cursor,
            )
        except ProviderError as exc:
            return provider_error_payload(exc, "clinicaltrials")
        return {
            "source": "clinicaltrials",
            "source_url": f"https://clinicaltrials.gov/search?term={quote(query)}",
            "total": page["total"],
            "count": len(page["items"]),
            "items": page["items"],
            "next_cursor": page["next_cursor"],
        }

    return {"openfda": openfda_tool, "clinical_trials": clinical_trials}
