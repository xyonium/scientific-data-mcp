from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.unichem import UniChemProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

BASE = "https://www.ebi.ac.uk/unichem/rest"
IK = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
PAYLOAD = [
    {
        "name": "chembl",
        "name_long": "ChEMBL",
        "src_id": 1,
        "src_compound_id": ["CHEMBL25"],
        "src_url": "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL25/",
    },
    {
        "name": "pubchem",
        "name_long": "PubChem",
        "src_id": 22,
        "src_compound_id": ["2244"],
        "src_url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
    },
]


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield UniChemProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "www.ebi.ac.uk": 0.0,
            "rest.kegg.jp": 0.0,
            "bindingdb.org": 0.0,
            "www.crystallography.net": 0.0,
            "cod.psdi.ac.uk": 0.0,
            "qiserver.ugr.es": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_map(provider):
    route = respx.get(f"{BASE}/verbose_inchikey/{IK}").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    items = await provider.map_inchikey(IK, 10)
    assert items[0]["source"] == "chembl"
    assert items[1]["compound_ids"] == ["2244"]
    assert route.call_count == 1


@respx.mock
async def test_malformed_is_drift(provider):
    respx.get(f"{BASE}/verbose_inchikey/{IK}").mock(
        return_value=httpx.Response(200, json={})
    )
    with pytest.raises(UpstreamDrift):
        await provider.map_inchikey(IK)


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/verbose_inchikey/{IK}").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["unichem_map"](IK, limit=2)
    assert result["source"] == "unichem"
    assert result["count"] == 2
    assert "invalid InChIKey" in (await tools["unichem_map"]("nope"))["error"]
    assert "1-50" in (await tools["unichem_map"](IK, limit=0))["error"]
