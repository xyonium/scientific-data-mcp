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
