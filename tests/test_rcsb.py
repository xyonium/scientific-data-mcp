from __future__ import annotations

import json
import re

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.rcsb import RcsbProvider

DATA = "https://data.rcsb.org/rest/v1/core"
SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"

ENTRY = {
    "struct": {"title": "THE CRYSTAL STRUCTURE OF HUMAN DEOXYHAEMOGLOBIN AT 1.74 ANGSTROMS"},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_entry_info": {"resolution_combined": [1.74]},
    "rcsb_accession_info": {"deposit_date": "1984-03-07T00:00:00.000+00:00"},
    "rcsb_entry_container_identifiers": {"polymer_entity_ids": ["1", "2"]},
}

ENTITY_1 = {
    "rcsb_polymer_entity": {"pdbx_description": "Hemoglobin subunit alpha"},
    "entity_poly": {"type": "polypeptide(L)", "rcsb_sample_sequence_length": 141},
    "rcsb_polymer_entity_container_identifiers": {"auth_asym_ids": ["A", "C"]},
}
ENTITY_2 = {
    "rcsb_polymer_entity": {"pdbx_description": "Hemoglobin subunit beta"},
    "entity_poly": {"type": "polypeptide(L)", "rcsb_sample_sequence_length": 146},
    "rcsb_polymer_entity_container_identifiers": {"auth_asym_ids": ["B", "D"]},
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"data.rcsb.org": 0.0, "search.rcsb.org": 0.0})
    async with PoliteClient(settings) as client:
        yield RcsbProvider(client, settings)


@respx.mock
async def test_entry_includes_entity_summaries(provider):
    respx.get(f"{DATA}/entry/4HHB").mock(return_value=httpx.Response(200, json=ENTRY))
    respx.get(f"{DATA}/polymer_entity/4HHB/1").mock(return_value=httpx.Response(200, json=ENTITY_1))
    respx.get(f"{DATA}/polymer_entity/4HHB/2").mock(return_value=httpx.Response(200, json=ENTITY_2))
    record = await provider.entry("4hhb")
    assert record["pdb_id"] == "4HHB"
    assert record["method"] == "X-RAY DIFFRACTION"
    assert record["resolution"] == 1.74
    assert len(record["entities"]) == 2
    assert record["entities"][0]["chains"] == ["A", "C"]


@respx.mock
async def test_search_body_and_pagination(provider):
    route = respx.post(SEARCH).mock(
        return_value=httpx.Response(
            200,
            json={"total_count": 569, "result_set": [{"identifier": "1A3N"}, {"identifier": "1IT2"}]},
        )
    )
    result = await provider.search("hemoglobin", rows=2)
    body = json.loads(route.calls.last.request.content)
    assert body["query"]["service"] == "full_text"
    assert body["query"]["parameters"]["value"] == "hemoglobin"
    assert result["total"] == 569
    assert result["identifiers"] == ["1A3N", "1IT2"]
    assert result["next_start"] == 2


@respx.mock
async def test_unknown_entry_raises(provider):
    respx.get(url__regex=re.escape(f"{DATA}/entry/XXXX") + r".*").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(NotFound):
        await provider.entry("XXXX")
