from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.opentargets import OpenTargetsProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.biology import register

BASE = "https://api.platform.opentargets.org/api/v4/graphql"

SEARCH = {"data": {"search": {"hits": [{"id": "ENSG00000141510", "name": "TP53", "entity": "target"}]}}}
TARGET = {
    "data": {
        "target": {
            "id": "ENSG00000141510",
            "approvedSymbol": "TP53",
            "approvedName": "tumor protein p53",
            "functionDescriptions": ["TF"],
            "associatedDiseases": {
                "count": 2,
                "rows": [
                    {"score": 0.9, "disease": {"id": "MONDO:1", "name": "Li-Fraumeni"}},
                    {"score": 0.8, "disease": {"id": "MONDO:2", "name": "HCC"}},
                ],
            },
        }
    }
}
DISEASE = {
    "data": {
        "disease": {
            "id": "MONDO:1",
            "name": "breast carcinoma",
            "description": "A disease",
            "associatedTargets": {
                "count": 1,
                "rows": [
                    {"score": 0.7, "target": {"id": "ENSG1", "approvedSymbol": "BRCA1", "approvedName": "BRCA1"}}
                ],
            },
        }
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"api.platform.opentargets.org": 0.0})
    async with PoliteClient(settings) as client:
        yield OpenTargetsProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"api.platform.opentargets.org": 0.0, "reactome.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_and_target(provider):
    route = respx.post(BASE)
    route.side_effect = [
        httpx.Response(200, json=SEARCH),
        httpx.Response(200, json=TARGET),
    ]
    hits = await provider.search("TP53", "target", 1)
    assert hits[0]["id"] == "ENSG00000141510"
    result = await provider.target("ENSG00000141510", 2)
    assert result["count"] == 2
    assert result["items"][0]["disease"]["name"] == "Li-Fraumeni"


@respx.mock
async def test_disease(provider):
    respx.post(BASE).mock(return_value=httpx.Response(200, json=DISEASE))
    result = await provider.disease("MONDO:1", 1)
    assert result["items"][0]["target"]["approvedSymbol"] == "BRCA1"


@respx.mock
async def test_missing_target_is_not_found(provider):
    respx.post(BASE).mock(return_value=httpx.Response(200, json={"data": {"target": None}}))
    with pytest.raises(NotFound):
        await provider.target("ENSG0", 1)


@respx.mock
async def test_graphql_error_is_drift(provider):
    respx.post(BASE).mock(
        return_value=httpx.Response(200, json={"errors": [{"message": "bad field"}]})
    )
    with pytest.raises(UpstreamDrift, match="bad field"):
        await provider.search("TP53", "target", 1)


@respx.mock
async def test_tool_envelope_and_no_hit(tools):
    route = respx.post(BASE)
    route.side_effect = [
        httpx.Response(200, json=SEARCH),
        httpx.Response(200, json=TARGET),
    ]
    result = await tools["opentargets"]("TP53", limit=2)
    assert result["entity"] == "target"
    assert result["details"]["symbol"] == "TP53"
    assert result["count"] == 2
    assert "invalid entity" in (await tools["opentargets"]("x", entity="nope"))["error"]
    assert "limit" in (await tools["opentargets"]("x", limit=0))["error"]


@respx.mock
async def test_tool_no_hit(tools):
    respx.post(BASE).mock(
        return_value=httpx.Response(200, json={"data": {"search": {"hits": []}}})
    )
    result = await tools["opentargets"]("nope")
    assert result["count"] == 0
    assert result["hit"] is None
