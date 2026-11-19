from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.geo import GeoProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.datasets import register

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

SEARCH = {"esearchresult": {"count": "20989", "idlist": ["200307364"]}}
SUMMARY = {
    "result": {
        "uids": ["200307364"],
        "200307364": {
            "accession": "GSE307364",
            "title": "Trp53 loss ...",
            "summary": "Ribosome biogenesis ...",
            "gdstype": "Expression profiling by high throughput sequencing",
            "taxon": "Mus musculus",
            "n_samples": 18,
            "pdat": "2026/11/15",
            "pubmedids": [],
        },
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield GeoProvider(client, settings)


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
    page = await provider.search("TP53", 1)
    assert page["total"] == 20989
    assert page["items"][0]["accession"] == "GSE307364"
    assert page["items"][0]["organism"] == "Mus musculus"


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
    result = await tools["geo_datasets"]("TP53", limit=1)
    assert result["source"] == "geo"
    assert result["count"] == 1
    assert result["total"] == 20989
    assert "query" in (await tools["geo_datasets"](" "))["error"]
    assert "1-50" in (await tools["geo_datasets"]("x", limit=0))["error"]


@respx.mock
async def test_empty_tool_envelope(tools):
    respx.get(f"{BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    result = await tools["geo_datasets"]("nope")
    assert result["count"] == 0
    assert result["total"] == 0


@respx.mock
async def test_missing_esummary_result_is_drift(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.search("TP53")


@respx.mock
async def test_ncbi_key_and_email_on_both_calls():
    settings = Settings(
        ncbi_api_key="key",
        ncbi_email="me@example.com",
        host_delays={"eutils.ncbi.nlm.nih.gov": 0.0},
    )
    async with PoliteClient(settings) as client:
        provider = GeoProvider(client, settings)
        search_route = respx.get(f"{BASE}/esearch.fcgi").mock(
            return_value=httpx.Response(200, json=SEARCH)
        )
        summary_route = respx.get(f"{BASE}/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=SUMMARY)
        )
        await provider.search("TP53", 1)
        assert search_route.calls.last.request.url.params["api_key"] == "key"
        assert search_route.calls.last.request.url.params["email"] == "me@example.com"
        assert summary_route.calls.last.request.url.params["api_key"] == "key"


@respx.mock
async def test_limit_upper_bound(tools):
    respx.get(f"{BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    assert (await tools["geo_datasets"]("TP53", limit=50))["count"] == 0
    assert "1-50" in (await tools["geo_datasets"]("TP53", limit=51))["error"]
