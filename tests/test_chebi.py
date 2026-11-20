from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.chebi import ChebiProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

BASE = "https://www.ebi.ac.uk/ols4/api"
SEARCH = {
    "response": {
        "docs": [
            {
                "obo_id": "CHEBI:15365",
                "label": "acetylsalicylic acid",
                "description": ["A benzoic acid..."],
                "type": "class",
            }
        ]
    }
}
TERM = {
    "_embedded": {
        "terms": [
            {
                "obo_id": "CHEBI:15365",
                "label": "acetylsalicylic acid",
                "description": ["A benzoic acid..."],
                "synonyms": ["aspirin"],
                "is_obsolete": False,
            }
        ]
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield ChebiProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0, "bindingdb.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_normalizes(provider):
    route = respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=SEARCH)
    )
    items = await provider.search("aspirin", 3)
    assert items[0]["chebi_id"] == "CHEBI:15365"
    assert route.calls.last.request.url.params["ontology"] == "chebi"


@respx.mock
async def test_term(provider):
    respx.get(f"{BASE}/ontologies/chebi/terms").mock(
        return_value=httpx.Response(200, json=TERM)
    )
    term = await provider.term("CHEBI:15365")
    assert term["synonyms"] == ["aspirin"]


@respx.mock
async def test_missing_term_is_not_found(provider):
    respx.get(f"{BASE}/ontologies/chebi/terms").mock(
        return_value=httpx.Response(200, json={"_embedded": {"terms": []}})
    )
    with pytest.raises(NotFound):
        await provider.term("CHEBI:9999999")


@respx.mock
async def test_missing_docs_is_drift(provider):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("x")


@respx.mock
async def test_tool_search_and_id(tools):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/ontologies/chebi/terms").mock(
        return_value=httpx.Response(200, json=TERM)
    )
    search = await tools["chebi_compound"]("aspirin")
    exact = await tools["chebi_compound"]("CHEBI:15365")
    assert search["count"] == 1
    assert exact["items"][0]["chebi_id"] == "CHEBI:15365"
    assert "query" in (await tools["chebi_compound"](" "))["error"]
    assert "1-20" in (await tools["chebi_compound"]("x", limit=0))["error"]
