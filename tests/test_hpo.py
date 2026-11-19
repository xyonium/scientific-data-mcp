from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.hpo import HpoProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.ontology import register

BASE = "https://ontology.jax.org/api/hp"
TERM = {
    "id": "HP:0001250",
    "name": "Seizure",
    "definition": "A seizure is ...",
    "synonyms": ["Seizures"],
    "descendantCount": 228,
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"ontology.jax.org": 0.0})
    async with PoliteClient(settings) as client:
        yield HpoProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"ontology.jax.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_normalizes(provider):
    route = respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json={"terms": [TERM]})
    )
    terms = await provider.search("seizure", 3)
    assert terms[0]["id"] == "HP:0001250"
    assert terms[0]["descendant_count"] == 228
    assert route.calls.last.request.url.params["limit"] == "3"


@respx.mock
async def test_term_and_404(provider):
    respx.get(f"{BASE}/terms/HP:0001250").mock(
        return_value=httpx.Response(200, json=TERM)
    )
    assert (await provider.term("HP:0001250"))["name"] == "Seizure"
    respx.get(f"{BASE}/terms/HP:9999999").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFound):
        await provider.term("HP:9999999")


@respx.mock
async def test_missing_terms_is_drift(provider):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("seizure")


@respx.mock
async def test_tool_search_and_exact_id(tools):
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json={"terms": [TERM]})
    )
    respx.get(f"{BASE}/terms/HP:0001250").mock(
        return_value=httpx.Response(200, json=TERM)
    )
    search = await tools["phenotypes"]("seizure")
    exact = await tools["phenotypes"]("HP:0001250")
    assert search["count"] == 1
    assert exact["items"][0]["id"] == "HP:0001250"
    assert exact["source_url"].endswith("HP:0001250")
    assert "query" in (await tools["phenotypes"](" "))["error"]
    assert "1-50" in (await tools["phenotypes"]("x", limit=0))["error"]
