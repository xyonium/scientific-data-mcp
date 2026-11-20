from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.bindingdb import BindingDbProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

BASE = "https://bindingdb.org/rest"
PAYLOAD = {
    "getLindsByUniprotResponse": {
        "bdb.hit": "15",
        "bdb.affinities": [
            {
                "bdb.monomerid": 50260467,
                "bdb.smile": "CN1C=CN...",
                "bdb.affinity_type": "IC50",
                "bdb.affinity": " 79",
            }
        ],
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"bindingdb.org": 0.0})
    async with PoliteClient(settings) as client:
        yield BindingDbProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"bindingdb.org": 0.0, "www.ebi.ac.uk": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_ligands_normalizes(provider):
    route = respx.get(f"{BASE}/getLigandsByUniprot").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    page = await provider.ligands("P35355", 100, 10)
    assert page["total"] == 15
    assert page["items"][0]["affinity"] == "79"
    assert route.calls.last.request.url.params["uniprot"] == "P35355;100"


@respx.mock
async def test_empty_body_is_empty(provider):
    respx.get(f"{BASE}/getLigandsByUniprot").mock(
        return_value=httpx.Response(200, text="")
    )
    assert await provider.ligands("P00000") == {"items": [], "total": 0}


@respx.mock
async def test_missing_key_is_drift(provider):
    respx.get(f"{BASE}/getLigandsByUniprot").mock(
        return_value=httpx.Response(200, json={"oops": 1})
    )
    with pytest.raises(UpstreamDrift):
        await provider.ligands("P35355")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/getLigandsByUniprot").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["bindingdb_ligands"]("P35355", limit=1)
    assert result["source"] == "bindingdb"
    assert result["count"] == 1
    assert "uniprot" in (await tools["bindingdb_ligands"](" "))["error"]
    assert "1-100" in (await tools["bindingdb_ligands"]("P35355", limit=0))["error"]
