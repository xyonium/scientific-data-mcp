from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.reactome import ReactomeProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.biology import register

BASE = "https://reactome.org/ContentService"

PAYLOAD = {
    "results": [
        {
            "entries": [
                {
                    "stId": "R-HSA-1",
                    "name": 'Regulation of <span class="highlighting">TP53</span>',
                    "species": ["Homo sapiens"],
                    "type": "Pathway",
                    "isDisease": False,
                },
                {
                    "stId": "R-HSA-1",
                    "name": "duplicate",
                    "species": ["Homo sapiens"],
                    "type": "Pathway",
                },
            ]
        },
        {
            "entries": [
                {
                    "stId": "R-HSA-2",
                    "name": "Apoptosis",
                    "species": ["Homo sapiens"],
                    "type": "Pathway",
                }
            ]
        },
    ],
    "numberOfMatches": 2,
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"reactome.org": 0.0})
    async with PoliteClient(settings) as client:
        yield ReactomeProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"api.platform.opentargets.org": 0.0, "reactome.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_pathways_clean_dedupe_and_limit(provider):
    route = respx.get(f"{BASE}/search/query").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    page = await provider.pathways("TP53", "Homo sapiens", 1)
    assert route.calls.last.request.url.params["rows"] == "1"
    assert page["total"] == 2
    assert page["items"] == [
        {
            "st_id": "R-HSA-1",
            "name": "Regulation of TP53",
            "species": ["Homo sapiens"],
            "is_disease": False,
        }
    ]


@respx.mock
async def test_missing_results_is_drift(provider):
    respx.get(f"{BASE}/search/query").mock(
        return_value=httpx.Response(200, json={"error": "oops"})
    )
    with pytest.raises(UpstreamDrift):
        await provider.pathways("TP53")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/search/query").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["pathways"]("TP53", limit=2)
    assert result["source"] == "reactome"
    assert result["count"] == 2
    assert "query" in (await tools["pathways"](" "))["error"]
    assert "1-50" in (await tools["pathways"]("x", limit=0))["error"]
