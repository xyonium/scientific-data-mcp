from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.mcsa import McsaProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.enzymes import register

BASE = "https://www.ebi.ac.uk/thornton-srv/m-csa"
PAYLOAD = {
    "count": 5,
    "results": [
        {
            "mcsa_id": 255,
            "enzyme_name": "alcohol dehydrogenase (SDR type)",
            "reference_uniprot_id": "P00334",
            "all_ecs": ["1.1.1.1"],
            "description": "An NAD+-dependent enzyme.",
            "residues": [
                {
                    "roles": [{"function": "hydrogen bond donor"}],
                    "roles_summary": "hydrogen bond donor",
                    "residue_chains": [
                        {
                            "code": "Ser",
                            "resid": 139,
                            "pdb_id": "1mg5",
                            "chain_name": "A",
                        }
                    ],
                }
            ],
            "reaction": {
                "ec": "1.1.1.1",
                "compounds": [
                    {"name": "NAD(+)", "type": "reactant", "chebi_id": "15846", "count": 1}
                ],
            },
        }
    ],
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield McsaProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
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
async def test_entries(provider):
    route = respx.get(f"{BASE}/api/entries/").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await provider.entries({"entries.reactions.ecs.codes": "1.1.1.1"}, 1)
    assert result["total"] == 5
    assert result["items"][0]["residues"][0]["residue"] == "Ser139"
    assert route.calls.last.request.url.params["entries.reactions.ecs.codes"] == "1.1.1.1"


@respx.mock
async def test_empty_is_not_error(provider):
    respx.get(f"{BASE}/api/entries/").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    assert await provider.entries({"entries.mcsa_ids": "1"}) == {"items": [], "total": 0}


@respx.mock
async def test_missing_results_is_drift(provider):
    respx.get(f"{BASE}/api/entries/").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.entries({"entries.proteins.sequences.uniprot_ids": "P00334"})


@respx.mock
async def test_tool_filters_and_validation(tools):
    respx.get(f"{BASE}/api/entries/").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await tools["mcsa_sites"]("1.1.1.1", limit=1)
    assert result["source"] == "mcsa"
    assert result["count"] == 1
    assert "exactly one" in (await tools["mcsa_sites"]())["error"]
    assert "invalid EC" in (await tools["mcsa_sites"]("1.1.1"))["error"]
    assert "invalid UniProt" in (await tools["mcsa_sites"](uniprot="XX"))["error"]
