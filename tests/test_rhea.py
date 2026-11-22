from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.rhea import RheaProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.enzymes import register

BASE = "https://www.rhea-db.org"
PAYLOAD = {
    "count": 3,
    "results": [
        {
            "id": "10736",
            "equation": "a primary alcohol + NAD(+) = an aldehyde + NADH + H(+)",
            "status": "approved",
            "comment": "",
            "balanced": True,
            "transport": False,
        }
    ],
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.rhea-db.org": 0.0})
    async with PoliteClient(settings) as client:
        yield RheaProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "www.rhea-db.org": 0.0,
            "www.ebi.ac.uk": 0.0,
            "www.brenda-enzymes.org": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search(provider):
    route = respx.get(f"{BASE}/rhea").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await provider.search("1.1.1.1", 10)
    assert result["total"] == 3
    assert result["items"][0]["rhea_id"] == "10736"
    assert route.calls.last.request.url.params["query"] == "1.1.1.1"


@respx.mock
async def test_empty_is_not_error(provider):
    respx.get(f"{BASE}/rhea").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    assert await provider.search("nope") == {"items": [], "total": 0}


@respx.mock
async def test_missing_results_is_drift(provider):
    respx.get(f"{BASE}/rhea").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("1.1.1.1")


@respx.mock
async def test_tool(tools):
    respx.get(f"{BASE}/rhea").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["rhea_reactions"]("1.1.1.1", limit=1)
    assert result["source"] == "rhea"
    assert result["count"] == 1
    assert "query" in (await tools["rhea_reactions"](" "))["error"]
