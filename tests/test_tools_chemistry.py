from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chemistry import register

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"pubchem.ncbi.nlm.nih.gov": 0.0})
    service = build_service(settings)
    mcp = FastMCP("test")
    registered = register(mcp, service)
    yield registered
    await service.aclose()


@respx.mock
async def test_chem_compound_returns_record(tools):
    respx.get(f"{BASE}/compound/name/aspirin/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [2244]}})
    )
    respx.get(url__regex=rf"{BASE}/compound/cid/2244/property/.*/JSON").mock(
        return_value=httpx.Response(
            200,
            json={
                "PropertyTable": {
                    "Properties": [{"CID": 2244, "MolecularFormula": "C9H8O4"}]
                }
            },
        )
    )
    respx.get(f"{BASE}/compound/cid/2244/synonyms/JSON").mock(
        return_value=httpx.Response(
            200, json={"InformationList": {"Information": [{"Synonym": ["ASPIRIN"]}]}}
        )
    )
    result = await tools["chem_compound"]("aspirin")
    assert result["source"] == "pubchem"
    assert result["record"]["cid"] == 2244
    assert result["record"]["molecular_formula"] == "C9H8O4"
    assert result["source_url"] == "https://pubchem.ncbi.nlm.nih.gov/compound/2244"


@respx.mock
async def test_chem_compound_missing_returns_error_dict(tools):
    respx.get(f"{BASE}/compound/name/nope/cids/JSON").mock(return_value=httpx.Response(404))
    result = await tools["chem_compound"]("nope")
    assert result["source"] == "pubchem"
    assert "not_found" in result["error"]


async def test_chem_compound_rejects_unknown_id_type(tools):
    result = await tools["chem_compound"]("x", id_type="foo")
    assert "error" in result
    assert "name" in result["hint"]


@respx.mock
async def test_chem_similar_compounds_count(tools):
    respx.post(f"{BASE}/compound/similarity/smiles/JSON").mock(
        return_value=httpx.Response(202, json={"Waiting": {"ListKey": "k1"}})
    )
    respx.get(f"{BASE}/compound/listkey/k1/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [1, 2]}})
    )
    result = await tools["chem_similar_compounds"]("CCO")
    assert result["count"] == 2
    assert result["items"] == [{"cid": 1}, {"cid": 2}]
