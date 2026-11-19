from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import AuthError, NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.openfda import OpenFdaProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.clinical import register

BASE = "https://api.fda.gov"


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"api.fda.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield OpenFdaProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"api.fda.gov": 0.0, "clinicaltrials.gov": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_returns_results_and_total(provider):
    respx.get(f"{BASE}/drug/label.json").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"id": "x"}], "meta": {"results": {"total": 39}}},
        )
    )
    page = await provider.search("drug/label", 'openfda.brand_name:"advil"', 1, 0)
    assert page["total"] == 39
    assert page["items"][0]["id"] == "x"


@respx.mock
async def test_no_matches_404_is_empty(provider):
    respx.get(f"{BASE}/drug/label.json").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
        )
    )
    page = await provider.search("drug/label", "nope", 1, 0)
    assert page == {"items": [], "total": 0}


@respx.mock
async def test_404_without_not_found_is_not_found(provider):
    respx.get(f"{BASE}/drug/label.json").mock(
        return_value=httpx.Response(404, json={"error": {"code": "OTHER"}})
    )
    with pytest.raises(NotFound):
        await provider.search("drug/label", "x", 1, 0)


@respx.mock
async def test_401_is_auth(provider):
    respx.get(f"{BASE}/drug/label.json").mock(return_value=httpx.Response(401))
    with pytest.raises(AuthError):
        await provider.search("drug/label", "x", 1, 0)


@respx.mock
async def test_missing_results_is_drift(provider):
    respx.get(f"{BASE}/drug/label.json").mock(
        return_value=httpx.Response(200, json={"meta": {}})
    )
    with pytest.raises(UpstreamDrift):
        await provider.search("drug/label", "x", 1, 0)


@respx.mock
async def test_tool_empty_and_validation(tools):
    respx.get(f"{BASE}/drug/label.json").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
        )
    )
    result = await tools["openfda"]('openfda.brand_name:"zzzz"')
    assert result["count"] == 0
    assert result["items"] == []
    assert "endpoint" in (await tools["openfda"]("x", endpoint="nope"))["error"]
    assert "limit" in (await tools["openfda"]("x", limit=0))["error"]
    assert "skip" in (await tools["openfda"]("x", skip=-1))["error"]
