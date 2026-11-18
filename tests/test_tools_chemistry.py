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


@respx.mock
async def test_chembl_bioactivity_requires_exactly_one_selector(tools):
    result = await tools["chembl_bioactivity"](chembl_id="CHEMBL941", target_chembl_id="CHEMBL1862")
    assert "exactly one" in result["error"]
    result = await tools["chembl_bioactivity"]()
    assert "exactly one" in result["error"]


@respx.mock
async def test_chembl_bioactivity_empty_is_not_an_error(tools):
    respx.get("https://www.ebi.ac.uk/chembl/api/data/activity.json").mock(
        return_value=httpx.Response(
            200,
            json={"activities": [], "page_meta": {"limit": 20, "offset": 0, "total_count": 0, "next": None}},
        )
    )
    result = await tools["chembl_bioactivity"](chembl_id="CHEMBL941")
    assert result["count"] == 0
    assert result["items"] == []


@respx.mock
async def test_chembl_search_404_returns_error_dict(tools):
    respx.get("https://www.ebi.ac.uk/chembl/api/data/assay/search.json").mock(
        return_value=httpx.Response(404)
    )
    result = await tools["chembl_search"]("x", resource="assay")
    assert result["source"] == "chembl"
    assert "not_found" in result["error"]


@respx.mock
async def test_malformed_similarity_payload_returns_error_dict(tools):
    respx.post(f"{BASE}/compound/similarity/smiles/JSON").mock(
        return_value=httpx.Response(202, json={"Waiting": {"ListKey": "k1"}})
    )
    respx.get(f"{BASE}/compound/listkey/k1/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": ["not-a-cid"]}})
    )
    result = await tools["chem_similar_compounds"]("CCO")
    assert result["source"] == "pubchem"
    assert "error" in result


@respx.mock
async def test_unexpected_provider_bug_returns_error_dict(tools):
    respx.get(f"{BASE}/compound/name/aspirin/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [2244]}})
    )
    respx.get(url__regex=rf"{BASE}/compound/cid/2244/property/.*/JSON").mock(
        return_value=httpx.Response(200, json={"PropertyTable": {"Properties": ["oops"]}})
    )
    respx.get(f"{BASE}/compound/cid/2244/synonyms/JSON").mock(
        return_value=httpx.Response(200, json={"InformationList": {"Information": []}})
    )
    result = await tools["chem_compound"]("aspirin")
    assert result["source"] == "pubchem"
    assert "unexpected" in result["error"]
    assert result["suspect_drift"] is True
    assert result["action"] == "contact_admin"


async def test_chembl_bioactivity_rejects_negative_offset(tools):
    result = await tools["chembl_bioactivity"](chembl_id="CHEMBL941", offset=-1)
    assert "offset" in result["error"]


@respx.mock
async def test_chembl_source_urls_point_at_report_cards(tools):
    respx.get("https://www.ebi.ac.uk/chembl/api/data/activity.json").mock(
        return_value=httpx.Response(
            200,
            json={"activities": [], "page_meta": {"limit": 20, "offset": 0, "total_count": 0, "next": None}},
        )
    )
    result = await tools["chembl_bioactivity"](chembl_id="CHEMBL941")
    assert result["source_url"] == "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL941/"
