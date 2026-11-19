from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.interpro import InterProProvider
from scientific_data_mcp.providers.quickgo import QuickGoProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.annotations import register

INTERPRO = "https://www.ebi.ac.uk/interpro/api"
QUICKGO = "https://www.ebi.ac.uk/QuickGO/services"

IP_PAYLOAD = {
    "count": 1,
    "results": [
        {
            "metadata": {
                "accession": "IPR002117",
                "name": "p53 tumour suppressor family",
                "type": "family",
                "source_database": "interpro",
                "go_terms": [{"identifier": "GO:0003677", "name": "DNA binding"}],
            }
        }
    ],
}
GO_PAYLOAD = {
    "numberOfHits": 1,
    "results": [
        {
            "goId": "GO:0008285",
            "goName": None,
            "qualifier": "acts_upstream_of",
            "goEvidence": "ISS",
            "goAspect": "biological_process",
            "reference": "PMID:30514107",
            "assignedBy": "ARUK-UCL",
            "taxonId": 9606,
        }
    ],
}


@pytest.fixture
async def providers():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield InterProProvider(client, settings), QuickGoProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_interpro_normalizes(providers):
    interpro, _ = providers
    respx.get(f"{INTERPRO}/entry/all/protein/uniprot/P04637/").mock(
        return_value=httpx.Response(200, json=IP_PAYLOAD)
    )
    page = await interpro.entries("P04637", 5)
    assert page["total"] == 1
    assert page["items"][0]["accession"] == "IPR002117"
    assert page["items"][0]["go_terms"][0]["id"] == "GO:0003677"


@respx.mock
async def test_quickgo_normalizes(providers):
    _, quickgo = providers
    respx.get(f"{QUICKGO}/annotation/search").mock(
        return_value=httpx.Response(200, json=GO_PAYLOAD)
    )
    page = await quickgo.annotations("P04637", 5)
    assert page["total"] == 1
    assert page["items"][0]["go_id"] == "GO:0008285"
    assert page["items"][0]["evidence"] == "ISS"


@respx.mock
async def test_missing_results_is_drift(providers):
    interpro, _ = providers
    respx.get(f"{INTERPRO}/entry/all/protein/uniprot/P04637/").mock(
        return_value=httpx.Response(200, json={"count": 1})
    )
    with pytest.raises(UpstreamDrift):
        await interpro.entries("P04637")


@respx.mock
async def test_tool_both_sources_and_validation(tools):
    respx.get(f"{INTERPRO}/entry/all/protein/uniprot/P04637/").mock(
        return_value=httpx.Response(200, json=IP_PAYLOAD)
    )
    respx.get(f"{QUICKGO}/annotation/search").mock(
        return_value=httpx.Response(200, json=GO_PAYLOAD)
    )
    ip = await tools["protein_annotations"]("P04637")
    go = await tools["protein_annotations"]("UniProtKB:P04637", source="quickgo")
    assert ip["source"] == "interpro"
    assert go["source"] == "quickgo"
    assert "invalid source" in (
        await tools["protein_annotations"]("P04637", source="x")
    )["error"]
    assert "1-50" in (await tools["protein_annotations"]("P04637", limit=0))["error"]


@respx.mock
async def test_interpro_204_is_empty(providers):
    interpro, _ = providers
    respx.get(f"{INTERPRO}/entry/all/protein/uniprot/UNKNOWN/").mock(
        return_value=httpx.Response(204)
    )
    assert await interpro.entries("UNKNOWN") == {"items": [], "total": 0}


@respx.mock
async def test_request_params(providers):
    interpro, quickgo = providers
    ip_route = respx.get(f"{INTERPRO}/entry/all/protein/uniprot/P04637/").mock(
        return_value=httpx.Response(200, json=IP_PAYLOAD)
    )
    await interpro.entries("P04637", 5)
    assert ip_route.calls.last.request.url.params["page_size"] == "5"

    go_route = respx.get(f"{QUICKGO}/annotation/search").mock(
        return_value=httpx.Response(200, json=GO_PAYLOAD)
    )
    await quickgo.annotations("P04637", 5)
    params = go_route.calls.last.request.url.params
    assert params["geneProductId"] == "UniProtKB:P04637"
    assert params["limit"] == "5"
