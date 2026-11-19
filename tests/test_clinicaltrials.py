from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.clinicaltrials import ClinicalTrialsProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.clinical import register

BASE = "https://clinicaltrials.gov/api/v2/studies"

STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT1", "briefTitle": "A Study"},
        "statusModule": {
            "overallStatus": "RECRUITING",
            "startDateStruct": {"date": "2024-01-01"},
        },
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE2"],
            "enrollmentInfo": {"count": 100},
        },
        "conditionsModule": {"conditions": ["Cancer"]},
        "armsInterventionsModule": {
            "interventions": [{"name": "Drug A"}, {"name": "Drug B"}]
        },
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "ACME"}},
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"clinicaltrials.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield ClinicalTrialsProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"clinicaltrials.gov": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_search_normalizes_and_paginates(provider):
    route = respx.get(BASE).mock(
        return_value=httpx.Response(
            200,
            json={"totalCount": 3150, "studies": [STUDY], "nextPageToken": "tok"},
        )
    )
    page = await provider.search("pembrolizumab", status="RECRUITING", limit=1)
    params = route.calls.last.request.url.params
    assert params["query.term"] == "pembrolizumab"
    assert params["pageSize"] == "1"
    assert params["countTotal"] == "true"
    assert params["filter.overallStatus"] == "RECRUITING"
    assert page["total"] == 3150
    assert page["next_cursor"] == "tok"
    item = page["items"][0]
    assert item["nct_id"] == "NCT1"
    assert item["status"] == "RECRUITING"
    assert item["interventions"] == ["Drug A", "Drug B"]
    assert item["sponsor"] == "ACME"


@respx.mock
async def test_empty_studies_is_normal(provider):
    respx.get(BASE).mock(
        return_value=httpx.Response(200, json={"totalCount": 0, "studies": []})
    )
    page = await provider.search("nope")
    assert page["items"] == []
    assert page["next_cursor"] is None


@respx.mock
async def test_missing_studies_is_drift(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"totalCount": 0}))
    with pytest.raises(UpstreamDrift):
        await provider.search("x")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(BASE).mock(
        return_value=httpx.Response(
            200, json={"totalCount": 1, "studies": [STUDY], "nextPageToken": None}
        )
    )
    result = await tools["clinical_trials"]("pembrolizumab", limit=1)
    assert result["source"] == "clinicaltrials"
    assert result["total"] == 1
    assert result["count"] == 1
    assert result["next_cursor"] is None
    assert "query" in (await tools["clinical_trials"](" "))["error"]
    assert "1-100" in (await tools["clinical_trials"]("x", limit=0))["error"]
