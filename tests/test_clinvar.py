from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.clinvar import ClinVarProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.genomics import register

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

SEARCH = {"esearchresult": {"count": "2", "idlist": ["1"]}}
SUMMARY = {
    "result": {
        "uids": ["1"],
        "1": {
            "accession": "VCV000000001",
            "title": "NM_007294.4(BRCA1):c.711del",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "criteria provided, single submitter",
                "last_evaluated": "2026/09/18 00:00",
                "trait_set": [{"trait_name": "Breast cancer"}],
            },
            "genes": [{"symbol": "BRCA1"}],
            "protein_change": "E237fs",
            "molecular_consequence_list": ["frameshift variant"],
            "variation_set": [
                {"variation_name": "NM_007294.4(BRCA1):c.711del", "variant_type": "Deletion"}
            ],
        },
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield ClinVarProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_normalizes(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json=SUMMARY))
    page = await provider.search("BRCA1[gene]", 1)
    assert page["total"] == 2
    item = page["items"][0]
    assert item["classification"] == "Pathogenic"
    assert item["conditions"] == ["Breast cancer"]
    assert item["genes"] == ["BRCA1"]
    assert item["variation"]["type"] == "Deletion"


@respx.mock
async def test_empty_is_normal(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    assert await provider.search("nope") == {"items": [], "total": 0}


@respx.mock
async def test_missing_result_is_drift(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("x")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json=SUMMARY))
    result = await tools["clinvar"]("BRCA1[gene]", limit=1)
    assert result["source"] == "clinvar"
    assert result["count"] == 1
    assert result["total"] == 2
    assert "query" in (await tools["clinvar"](" "))["error"]
    assert "1-50" in (await tools["clinvar"]("x", limit=0))["error"]


@respx.mock
async def test_request_params(provider):
    route = respx.get(f"{BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json=SEARCH)
    )
    respx.get(f"{BASE}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json=SUMMARY)
    )
    await provider.search("BRCA1[gene]", 3)
    params = route.calls.last.request.url.params
    assert params["db"] == "clinvar"
    assert params["retmax"] == "3"
