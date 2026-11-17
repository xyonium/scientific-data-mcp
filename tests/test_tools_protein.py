from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.protein import register

BASE = "https://rest.uniprot.org"

ENTRY = {
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "primaryAccession": "P05067",
    "uniProtkbId": "A4_HUMAN",
    "proteinDescription": {"recommendedName": {"fullName": {"value": "Amyloid-beta precursor protein"}}},
    "genes": [{"geneName": {"value": "APP"}}],
    "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "sequence": {"length": 770, "molWeight": 86943, "value": "MLPGLALLLL"},
    "uniProtKBCrossReferences": [],
}


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"rest.uniprot.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_protein_entry_envelope(tools):
    respx.get(f"{BASE}/uniprotkb/P05067.json").mock(
        return_value=httpx.Response(200, json=ENTRY)
    )
    result = await tools["protein_entry"]("P05067")
    assert result["source"] == "uniprot"
    assert result["source_url"] == "https://www.uniprot.org/uniprotkb/P05067/entry"
    assert result["record"]["protein_name"] == "Amyloid-beta precursor protein"


async def test_protein_entry_rejects_blank_accession(tools):
    result = await tools["protein_entry"]("  ")
    assert "error" in result


@respx.mock
async def test_protein_entry_404_returns_error_dict(tools):
    respx.get(f"{BASE}/uniprotkb/XXXX.json").mock(return_value=httpx.Response(404))
    result = await tools["protein_entry"]("XXXX")
    assert result["source"] == "uniprot"
    assert "not_found" in result["error"]


@respx.mock
async def test_protein_search_exposes_next_cursor(tools):
    respx.get(f"{BASE}/uniprotkb/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [ENTRY]},
            headers={"Link": '<https://rest.uniprot.org/uniprotkb/search?cursor=c2>; rel="next"'},
        )
    )
    result = await tools["protein_search"]("gene:APP", size=1)
    assert result["count"] == 1
    assert result["next_cursor"] == "c2"


async def test_protein_search_rejects_bad_size(tools):
    result = await tools["protein_search"]("gene:APP", size=0)
    assert "1-500" in result["error"]


async def test_protein_map_ids_requires_ids(tools):
    result = await tools["protein_map_ids"]("UniProtKB_AC-ID", "PDB", "  ")
    assert "ids" in result["error"]


@respx.mock
async def test_protein_structure_envelope(tools):
    respx.get("https://data.rcsb.org/rest/v1/core/entry/4HHB").mock(
        return_value=httpx.Response(
            200,
            json={
                "struct": {"title": "HUMAN DEOXYHAEMOGLOBIN"},
                "exptl": [{"method": "X-RAY DIFFRACTION"}],
                "rcsb_entry_info": {"resolution_combined": [1.74]},
                "rcsb_entry_container_identifiers": {"polymer_entity_ids": []},
            },
        )
    )
    result = await tools["protein_structure"]("4hhb")
    assert result["source"] == "rcsb"
    assert result["record"]["pdb_id"] == "4HHB"
    assert result["source_url"] == "https://www.rcsb.org/structure/4HHB"


@respx.mock
async def test_protein_structure_search_returns_ids(tools):
    respx.post("https://search.rcsb.org/rcsbsearch/v2/query").mock(
        return_value=httpx.Response(
            200, json={"total_count": 1, "result_set": [{"identifier": "1A3N"}]}
        )
    )
    result = await tools["protein_structure_search"]("hemoglobin")
    assert result["total"] == 1
    assert result["items"] == [{"pdb_id": "1A3N"}]


async def test_protein_structure_search_validates_rows(tools):
    result = await tools["protein_structure_search"]("x", rows=0)
    assert "1-100" in result["error"]


@respx.mock
async def test_structure_search_empty_204_returns_count_zero(tools):
    respx.post("https://search.rcsb.org/rcsbsearch/v2/query").mock(
        return_value=httpx.Response(204)
    )
    result = await tools["protein_structure_search"]("no-such-structure")
    assert result["count"] == 0
    assert result["items"] == []
    assert result["total"] == 0
