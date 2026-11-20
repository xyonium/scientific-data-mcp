from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.monarch import MonarchProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.clinical_assoc import register

BASE = "https://api.monarchinitiative.org/v3/api"
PAYLOAD = {
    "limit": 1,
    "offset": 0,
    "total": 18,
    "items": [
        {
            "subject": "HGNC:3603",
            "subject_label": "FBN1",
            "subject_category": "biolink:Gene",
            "predicate": "biolink:causes",
            "object": "MONDO:0007055",
            "object_label": "Acromicric dysplasia",
            "object_category": "biolink:Disease",
            "category": "biolink:CausalGeneToDiseaseAssociation",
            "publications": ["PMID:21683322"],
            "primary_knowledge_source": "infores:omim",
        }
    ],
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"api.monarchinitiative.org": 0.0})
    async with PoliteClient(settings) as client:
        yield MonarchProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0, "api.monarchinitiative.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_gene_disease(provider):
    route = respx.get(f"{BASE}/association").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await provider.associations(
        "HGNC:3603", "biolink:CausalGeneToDiseaseAssociation", 1
    )
    assert result["total"] == 18
    assert result["items"][0]["object_label"] == "Acromicric dysplasia"
    assert route.calls.last.request.url.params["category"] == (
        "biolink:CausalGeneToDiseaseAssociation"
    )


@respx.mock
async def test_empty_is_not_error(provider):
    respx.get(f"{BASE}/association").mock(
        return_value=httpx.Response(200, json={"limit": 1, "offset": 0, "total": 0, "items": []})
    )
    assert await provider.associations("HGNC:3603", None) == {"items": [], "total": 0}


@respx.mock
async def test_missing_items_is_drift(provider):
    respx.get(f"{BASE}/association").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.associations("HGNC:3603", None)


@respx.mock
async def test_tool_mapping_and_validation(tools):
    respx.get(f"{BASE}/association").mock(return_value=httpx.Response(200, json=PAYLOAD))
    result = await tools["monarch_associations"]("HGNC:3603", limit=1)
    assert result["total"] == 18
    assert result["next_offset"] == 1
    assert "invalid category" in (
        await tools["monarch_associations"]("HGNC:3603", category="nope")
    )["error"]
    assert "entity" in (await tools["monarch_associations"](" "))["error"]
