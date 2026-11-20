from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.clinpgx import ClinPgxProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.clinical_assoc import register

BASE = "https://api.clinpgx.org/v1"
PAYLOAD = {
    "data": [
        {
            "id": 1043858794,
            "accessionId": "PA166134797",
            "name": "CYP2C19 and clopidogrel",
            "levelOfEvidence": {"term": "1A"},
            "location": {
                "genes": [{"id": "PA124", "symbol": "CYP2C19", "name": "cytochrome P450"}]
            },
            "relatedChemicals": [{"id": "PA449053", "name": "clopidogrel"}],
            "allelePhenotypes": [
                {"allele": "*1", "phenotype": "normal function", "limitedEvidence": False}
            ],
            "relatedGuidelines": [{"name": "CPIC guideline"}],
            "relatedDiseases": [],
            "score": 220.875,
        }
    ],
    "status": "success",
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"api.clinpgx.org": 0.0})
    async with PoliteClient(settings) as client:
        yield ClinPgxProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "api.clinpgx.org": 0.0,
            "www.ebi.ac.uk": 0.0,
            "api.monarchinitiative.org": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_annotations(provider):
    route = respx.get(f"{BASE}/data/summaryAnnotation").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    items = await provider.annotations("CYP2C19", "clopidogrel", 10)
    assert items[0]["level_of_evidence"] == "1A"
    assert items[0]["gene"] == "CYP2C19"
    assert items[0]["drug"] == "clopidogrel"
    assert route.calls.last.request.url.params["relatedChemicals.name"] == "clopidogrel"


@respx.mock
async def test_empty_is_not_error(provider):
    respx.get(f"{BASE}/data/summaryAnnotation").mock(
        return_value=httpx.Response(200, json={"data": [], "status": "success"})
    )
    assert await provider.annotations("CYP2C19", None) == []


@respx.mock
async def test_missing_data_is_drift(provider):
    respx.get(f"{BASE}/data/summaryAnnotation").mock(
        return_value=httpx.Response(200, json={"status": "success"})
    )
    with pytest.raises(UpstreamDrift):
        await provider.annotations("CYP2C19", None)


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/data/summaryAnnotation").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["clinpgx"]("CYP2C19", "clopidogrel", limit=5)
    assert result["source"] == "clinpgx"
    assert result["count"] == 1
    assert "gene" in (await tools["clinpgx"](" "))["error"]
    assert "1-50" in (await tools["clinpgx"]("CYP2C19", limit=0))["error"]
