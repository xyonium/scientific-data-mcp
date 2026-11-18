from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.protein import register

UNIPROT = "https://rest.uniprot.org"
RCSB = "https://data.rcsb.org/rest/v1/core"
RCSB_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"

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
PDB_ENTRY = {
    "struct": {"title": "HUMAN DEOXYHAEMOGLOBIN"},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_entry_info": {"resolution_combined": [1.74]},
    "rcsb_entry_container_identifiers": {"polymer_entity_ids": []},
}


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "rest.uniprot.org": 0.0,
            "data.rcsb.org": 0.0,
            "search.rcsb.org": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_protein_record_uniprot(tools):
    respx.get(f"{UNIPROT}/uniprotkb/P05067.json").mock(
        return_value=httpx.Response(200, json=ENTRY)
    )
    result = await tools["protein_record"]("P05067", kind="uniprot")
    assert result["source"] == "uniprot"
    assert result["record"]["protein_name"] == "Amyloid-beta precursor protein"
    assert result["source_url"] == "https://www.uniprot.org/uniprotkb/P05067/entry"


@respx.mock
async def test_protein_record_pdb(tools):
    respx.get(f"{RCSB}/entry/4HHB").mock(return_value=httpx.Response(200, json=PDB_ENTRY))
    result = await tools["protein_record"]("4hhb", kind="pdb")
    assert result["source"] == "rcsb"
    assert result["record"]["pdb_id"] == "4HHB"
    assert result["source_url"] == "https://www.rcsb.org/structure/4HHB"


async def test_protein_record_validates_kind_and_id(tools):
    assert "invalid kind" in (await tools["protein_record"]("X", kind="nope"))["error"]
    assert "identifier" in (await tools["protein_record"](" "))["error"]


@respx.mock
async def test_protein_entry_404_returns_error_dict(tools):
    respx.get(f"{UNIPROT}/uniprotkb/XXXX.json").mock(return_value=httpx.Response(404))
    result = await tools["protein_record"]("XXXX", kind="uniprot")
    assert result["source"] == "uniprot"
    assert "not_found" in result["error"]


@respx.mock
async def test_protein_search_uniprot_exposes_next_cursor(tools):
    respx.get(f"{UNIPROT}/uniprotkb/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [ENTRY]},
            headers={"Link": '<https://rest.uniprot.org/uniprotkb/search?cursor=c2>; rel="next"'},
        )
    )
    result = await tools["protein_search"]("gene:APP", kind="uniprot", size=1)
    assert result["source"] == "uniprot"
    assert result["count"] == 1
    assert result["next_cursor"] == "c2"


@respx.mock
async def test_protein_search_pdb_uses_cursor_as_offset(tools):
    respx.post(RCSB_SEARCH).mock(
        return_value=httpx.Response(
            200,
            json={
                "total_count": 3,
                "result_set": [{"identifier": "1A3N"}, {"identifier": "1IT2"}],
            },
        )
    )
    result = await tools["protein_search"]("hemoglobin", kind="pdb", size=2)
    assert result["source"] == "rcsb"
    assert result["total"] == 3
    assert result["items"] == [{"pdb_id": "1A3N"}, {"pdb_id": "1IT2"}]
    assert result["next_cursor"] == "2"


async def test_protein_search_validates_inputs(tools):
    assert "1-500" in (await tools["protein_search"]("x", kind="uniprot", size=0))["error"]
    assert "1-100" in (await tools["protein_search"]("x", kind="pdb", size=0))["error"]
    assert "cursor" in (await tools["protein_search"]("x", kind="pdb", cursor="abc"))["error"]


async def test_protein_map_ids_validates_inputs(tools):
    assert "ids" in (
        await tools["protein_map_ids"]("UniProtKB_AC-ID", "PDB", "  ")
    )["error"]
