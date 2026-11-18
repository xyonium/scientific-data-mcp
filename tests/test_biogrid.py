from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import AuthError, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.biogrid import BioGridProvider
from scientific_data_mcp.runtime import build_service

BASE = "https://webservice.thebiogrid.org/interactions/"

PAYLOAD = {
    "16306": {
        "BIOGRID_INTERACTION_ID": 16306,
        "OFFICIAL_SYMBOL_A": "TP53",
        "OFFICIAL_SYMBOL_B": "BRCA1",
        "EXPERIMENTAL_SYSTEM": "Affinity Capture-Western",
        "EXPERIMENTAL_SYSTEM_TYPE": "physical",
        "ORGANISM_A": 9606,
        "ORGANISM_B": 9606,
    },
    "16305": {
        "BIOGRID_INTERACTION_ID": 16305,
        "ENTREZ_GENE_A": "7157",
        "ENTREZ_GENE_B": "51741",
        "OFFICIAL_SYMBOL_A": "TP53",
        "OFFICIAL_SYMBOL_B": "WWOX",
        "EXPERIMENTAL_SYSTEM": "Two-hybrid",
        "EXPERIMENTAL_SYSTEM_TYPE": "physical",
        "PUBMED_ID": "9482880",
        "ORGANISM_A": 9606,
        "ORGANISM_B": 9606,
        "THROUGHPUT": "Low Throughput",
        "SCORE": "-",
    },
}


@pytest.fixture
async def provider():
    settings = Settings(
        biogrid_access_key="k", host_delays={"webservice.thebiogrid.org": 0.0}
    )
    async with PoliteClient(settings) as client:
        yield BioGridProvider(client, settings)


def test_provider_is_gated_on_the_key():
    assert "biogrid" not in build_service(Settings()).providers
    assert "biogrid" in build_service(Settings(biogrid_access_key="k")).providers


@respx.mock
async def test_interactions_sends_key_and_normalizes(provider):
    route = respx.get(BASE).mock(return_value=httpx.Response(200, json=PAYLOAD))
    page = await provider.interactions("TP53", organism=9606, limit=2, offset=0)
    params = route.calls.last.request.url.params
    assert params["accesskey"] == "k"
    assert params["format"] == "json"
    assert params["searchNames"] == "true"
    assert params["geneList"] == "TP53"
    assert params["taxId"] == "9606"
    assert params["start"] == "0"
    assert params["max"] == "2"
    assert [row["gene_b"] for row in page["items"]] == ["WWOX", "BRCA1"]
    assert page["items"][0]["interaction_id"] == 16305
    assert page["next_offset"] == 2


@respx.mock
async def test_short_page_has_no_next_offset(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json=PAYLOAD))
    page = await provider.interactions("TP53", limit=10)
    assert page["next_offset"] is None


@respx.mock
async def test_empty_result_is_an_empty_list(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={}))
    page = await provider.interactions("NOPE")
    assert page["items"] == []
    assert page["next_offset"] is None


@respx.mock
async def test_invalid_key_is_auth_error(provider):
    respx.get(BASE).mock(
        return_value=httpx.Response(401, json={"STATUS": "ERROR", "TYPE": "UNAUTHORIZED ACCESS"})
    )
    with pytest.raises(AuthError):
        await provider.interactions("TP53")


@respx.mock
async def test_non_object_payload_is_drift(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json=[1, 2]))
    with pytest.raises(UpstreamDrift):
        await provider.interactions("TP53")


@respx.mock
async def test_multiple_genes_are_pipe_joined(provider):
    route = respx.get(BASE).mock(return_value=httpx.Response(200, json={}))
    await provider.interactions("BRCA1|BRCA2", limit=5)
    assert route.calls.last.request.url.params["geneList"] == "BRCA1|BRCA2"
