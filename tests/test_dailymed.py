from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.dailymed import DailyMedProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

PAYLOAD = {
    "data": [
        {
            "setid": "set-1",
            "title": "ASPIRIN TABLET",
            "published_date": "Nov 17, 2026",
            "spl_version": 4,
        }
    ],
    "metadata": {"total_elements": 1058},
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"dailymed.nlm.nih.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield DailyMedProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"dailymed.nlm.nih.gov": 0.0, "rest.kegg.jp": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_normalizes(provider):
    route = respx.get(f"{BASE}/spls.json").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    page = await provider.search("aspirin", 2)
    assert page["total"] == 1058
    assert page["items"][0]["setid"] == "set-1"
    assert route.calls.last.request.url.params["pagesize"] == "2"


@respx.mock
async def test_empty_is_normal(provider):
    respx.get(f"{BASE}/spls.json").mock(
        return_value=httpx.Response(200, json={"data": [], "metadata": {"total_elements": 0}})
    )
    assert await provider.search("nope") == {"items": [], "total": 0}


@respx.mock
async def test_missing_data_is_drift(provider):
    respx.get(f"{BASE}/spls.json").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("x")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/spls.json").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["dailymed"]("aspirin", limit=1)
    assert result["source"] == "dailymed"
    assert result["count"] == 1
    assert result["total"] == 1058
    assert "query" in (await tools["dailymed"](" "))["error"]
    assert "1-20" in (await tools["dailymed"]("x", limit=0))["error"]
