from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.sabio import SabioProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.enzymes import register

BASE = "https://sabiork.h-its.org/export-api/sabio"
PAYLOAD = {
    "meta": {"page": 1, "page_size": 1, "total_count": 768, "total_pages": 768},
    "data": [
        {
            "id": 1,
            "general": {"organism": {"name": "Homo sapiens"}},
            "reaction": {"equation": "ethanol + NAD(+) = acetaldehyde + NADH + H(+)"},
            "kineticlaw": {
                "kinlaw_type": {"name": "Michaelis-Menten"},
                "formula": None,
                "parameter": [
                    {
                        "name": "Km",
                        "start_value": 0.1,
                        "end_value": None,
                        "standard_deviation": None,
                        "unit": {"name": "mM"},
                        "species": {"species_key": "ethanol | Substrate"},
                        "comment": "-",
                    }
                ],
            },
            "experimental_conditions": {
                "buffer": "50 mM phosphate",
                "envvar_ph": {"start_value": 7.5},
                "envvar_temperature": {"start_value": 25, "unit": "°C"},
            },
            "enzyme_description": {
                "ec_number": "1.1.1.1",
                "enzyme_name": "alcohol dehydrogenase",
                "mutant_spec": None,
                "wildtype": "Wildtype",
            },
            "publication": {
                "pubmed_id": "12345",
                "title": "A paper",
                "year": 2001,
                "journal": "Biochem J",
            },
        }
    ],
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"sabiork.h-its.org": 0.0})
    async with PoliteClient(settings) as client:
        yield SabioProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "sabiork.h-its.org": 0.0,
            "www.rhea-db.org": 0.0,
            "www.ebi.ac.uk": 0.0,
            "www.brenda-enzymes.org": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_kinetics(provider):
    route = respx.get(f"{BASE}/kinlaw-entry/json").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await provider.kinetics("1.1.1.1", 1, 1)
    assert result["total"] == 768
    assert result["items"][0]["parameters"][0]["name"] == "Km"
    assert route.calls.last.request.url.params["q"] == "ecnumber:1.1.1.1"


@respx.mock
async def test_missing_meta_is_drift(provider):
    respx.get(f"{BASE}/kinlaw-entry/json").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    with pytest.raises(UpstreamDrift):
        await provider.kinetics("1.1.1.1")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/kinlaw-entry/json").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["sabio_kinetics"]("1.1.1.1", limit=1)
    assert result["source"] == "sabio"
    assert result["count"] == 1
    assert result["next_page"] == 2
    assert "invalid EC" in (await tools["sabio_kinetics"]("1.1.1"))["error"]
    assert "1-50" in (await tools["sabio_kinetics"]("1.1.1.1", limit=0))["error"]
