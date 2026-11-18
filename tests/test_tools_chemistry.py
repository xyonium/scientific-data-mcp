from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chemistry import register

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={"pubchem.ncbi.nlm.nih.gov": 0.0, "www.ebi.ac.uk": 0.0}
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


def _mock_compound(cid=2244):
    respx.get(f"{PUBCHEM}/compound/name/aspirin/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [cid]}})
    )
    respx.get(url__regex=rf"{PUBCHEM}/compound/cid/{cid}/property/.*/JSON").mock(
        return_value=httpx.Response(
            200,
            json={"PropertyTable": {"Properties": [{"CID": cid, "MolecularFormula": "C9H8O4"}]}},
        )
    )
    respx.get(f"{PUBCHEM}/compound/cid/{cid}/synonyms/JSON").mock(
        return_value=httpx.Response(
            200, json={"InformationList": {"Information": [{"Synonym": ["ASPIRIN"]}]}}
        )
    )


@respx.mock
async def test_chem_compound_returns_record(tools):
    _mock_compound()
    result = await tools["chem_compound"]("aspirin")
    assert result["source"] == "pubchem"
    assert result["record"]["cid"] == 2244
    assert result["record"]["molecular_formula"] == "C9H8O4"
    assert result["source_url"] == "https://pubchem.ncbi.nlm.nih.gov/compound/2244"


@respx.mock
async def test_chem_compound_accepts_a_property_subset(tools):
    _mock_compound()
    route = respx.get(url__regex=rf"{PUBCHEM}/compound/cid/2244/property/.*/JSON").mock(
        return_value=httpx.Response(
            200, json={"PropertyTable": {"Properties": [{"CID": 2244, "XLogP": 1.2}]}}
        )
    )
    result = await tools["chem_compound"](
        "aspirin", properties=["MolecularFormula", "XLogP"]
    )
    assert "MolecularFormula,XLogP" in route.calls.last.request.url.path
    assert result["record"]["xlogp"] == 1.2


@respx.mock
async def test_chem_compound_rejects_unknown_property(tools):
    result = await tools["chem_compound"]("aspirin", properties=["Nope"])
    assert "allowed" in result["hint"]


@respx.mock
async def test_chem_compound_missing_returns_error_dict(tools):
    respx.get(f"{PUBCHEM}/compound/name/nope/cids/JSON").mock(return_value=httpx.Response(404))
    result = await tools["chem_compound"]("nope")
    assert "not_found" in result["error"]


async def test_chem_compound_rejects_unknown_id_type(tools):
    result = await tools["chem_compound"]("x", id_type="foo")
    assert "name" in result["hint"]


@respx.mock
async def test_chem_similar_compounds_count(tools):
    respx.post(f"{PUBCHEM}/compound/similarity/smiles/JSON").mock(
        return_value=httpx.Response(202, json={"Waiting": {"ListKey": "k1"}})
    )
    respx.get(f"{PUBCHEM}/compound/listkey/k1/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [1, 2]}})
    )
    result = await tools["chem_similar_compounds"]("CCO")
    assert result["count"] == 2
    assert result["items"] == [{"cid": 1}, {"cid": 2}]


@respx.mock
async def test_malformed_similarity_payload_is_drift(tools):
    respx.post(f"{PUBCHEM}/compound/similarity/smiles/JSON").mock(
        return_value=httpx.Response(202, json={"Waiting": {"ListKey": "k1"}})
    )
    respx.get(f"{PUBCHEM}/compound/listkey/k1/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": ["not-a-cid"]}})
    )
    result = await tools["chem_similar_compounds"]("CCO")
    assert result["suspect_drift"] is True
    assert result["action"] == "contact_admin"


@respx.mock
async def test_unexpected_provider_bug_returns_error_dict(tools):
    _mock_compound()
    respx.get(url__regex=rf"{PUBCHEM}/compound/cid/2244/property/.*/JSON").mock(
        return_value=httpx.Response(200, json={"PropertyTable": {"Properties": ["oops"]}})
    )
    result = await tools["chem_compound"]("aspirin")
    assert "unexpected" in result["error"]
    assert result["suspect_drift"] is True


@respx.mock
async def test_chembl_data_search(tools):
    respx.get(f"{CHEMBL}/molecule/search.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "molecules": [{"molecule_chembl_id": "CHEMBL941", "pref_name": "IMATINIB"}],
                "page_meta": {"limit": 2, "offset": 0, "total_count": 5, "next": "x"},
            },
        )
    )
    result = await tools["chembl_data"](kind="search", query="imatinib", limit=2)
    assert result["count"] == 1
    assert result["total"] == 5
    assert result["next_offset"] == 1
    assert result["items"][0]["molecule_chembl_id"] == "CHEMBL941"


@respx.mock
async def test_chembl_data_activities_empty_is_not_an_error(tools):
    respx.get(f"{CHEMBL}/activity.json").mock(
        return_value=httpx.Response(
            200,
            json={"activities": [], "page_meta": {"limit": 20, "offset": 0, "total_count": 0, "next": None}},
        )
    )
    result = await tools["chembl_data"](kind="activities", chembl_id="CHEMBL941")
    assert result["count"] == 0
    assert result["items"] == []
    assert result["source_url"].endswith("/CHEMBL941/")


@respx.mock
async def test_chembl_data_mechanisms(tools):
    respx.get(f"{CHEMBL}/mechanism.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "mechanisms": [
                    {"molecule_chembl_id": "CHEMBL1642", "mechanism_of_action": "ABL inhibitor"}
                ]
            },
        )
    )
    result = await tools["chembl_data"](kind="mechanisms", chembl_id="CHEMBL1642")
    assert result["count"] == 1
    assert result["items"][0]["mechanism_of_action"] == "ABL inhibitor"


async def test_chembl_data_validates_combinations(tools):
    assert "exactly one" in (
        await tools["chembl_data"](kind="activities", chembl_id="A", target_chembl_id="B")
    )["error"]
    assert "exactly one" in (await tools["chembl_data"](kind="activities"))["error"]
    assert "query is required" in (await tools["chembl_data"](kind="search"))["error"]
    assert "invalid kind" in (await tools["chembl_data"](kind="nope"))["error"]
    assert "limit" in (await tools["chembl_data"](kind="search", query="x", limit=0))["error"]
    assert "offset" in (await tools["chembl_data"](kind="search", query="x", offset=-1))["error"]


@respx.mock
async def test_chembl_data_404_returns_error_dict(tools):
    respx.get(f"{CHEMBL}/assay/search.json").mock(return_value=httpx.Response(404))
    result = await tools["chembl_data"](kind="search", query="x", resource="assay")
    assert result["source"] == "chembl"
    assert "not_found" in result["error"]
