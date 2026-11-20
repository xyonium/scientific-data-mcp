from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.chebi import ChebiProvider

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
async def test_empty_terms_is_not_found(provider):
    respx.get(f"{BASE}/ontologies/chebi/terms").mock(
        return_value=httpx.Response(200, json={"_embedded": {"terms": []}})
    )
    with pytest.raises(NotFound):
        await provider.term("CHEBI:9999999")


@respx.mock
async def test_malformed_term_is_drift(provider):
    respx.get(f"{BASE}/ontologies/chebi/terms").mock(
        return_value=httpx.Response(200, json={"_embedded": {}})
    )
    with pytest.raises(UpstreamDrift):
        await provider.term("CHEBI:15365")


@respx.mock
async def test_missing_docs_is_drift(provider):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("x")

