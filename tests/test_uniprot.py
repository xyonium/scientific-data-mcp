from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamError
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers import uniprot as uniprot_module
from scientific_data_mcp.providers.uniprot import UniProtProvider

BASE = "https://rest.uniprot.org"

ENTRY = {
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "primaryAccession": "P05067",
    "uniProtkbId": "A4_HUMAN",
    "proteinDescription": {"recommendedName": {"fullName": {"value": "Amyloid-beta precursor protein"}}},
    "genes": [{"geneName": {"value": "APP"}}],
    "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "comments": [
        {"commentType": "FUNCTION", "texts": [{"value": "Functions as a cell surface receptor."}]},
        {"commentType": "SUBCELLULAR LOCATION", "texts": [{"value": "Membrane."}]},
    ],
    "keywords": [{"name": "Amyloid"}, {"name": "Notch signaling pathway"}],
    "sequence": {"length": 770, "molWeight": 86943, "value": "MLPGLALLLL"},
    "uniProtKBCrossReferences": [
        {"database": "PDB", "id": "1A1U"},
        {"database": "PDB", "id": "1A1U"},
        {"database": "PDB", "id": "1AAP"},
        {"database": "EMBL", "id": "X06989"},
    ],
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"rest.uniprot.org": 0.0})
    async with PoliteClient(settings) as client:
        yield UniProtProvider(client, settings)


@respx.mock
async def test_entry_normalizes_and_omits_sequence_by_default(provider):
    respx.get(f"{BASE}/uniprotkb/P05067.json").mock(return_value=httpx.Response(200, json=ENTRY))
    record = await provider.entry("P05067")
    assert record["accession"] == "P05067"
    assert record["protein_name"] == "Amyloid-beta precursor protein"
    assert record["genes"] == ["APP"]
    assert record["reviewed"] is True
    assert record["function"] == "Functions as a cell surface receptor."
    assert record["pdb_ids"] == ["1A1U", "1AAP"]
    assert "sequence" not in record


@respx.mock
async def test_entry_includes_sequence_on_request(provider):
    respx.get(f"{BASE}/uniprotkb/P05067.json").mock(return_value=httpx.Response(200, json=ENTRY))
    record = await provider.entry("P05067", include_sequence=True)
    assert record["sequence"] == "MLPGLALLLL"


@respx.mock
async def test_search_extracts_next_cursor(monkeypatch, provider):
    monkeypatch.setattr(uniprot_module, "_POLL_INTERVAL", 0)
    route = respx.get(f"{BASE}/uniprotkb/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [ENTRY]},
            headers={
                "Link": '<https://rest.uniprot.org/uniprotkb/search?cursor=abc123&size=1>; rel="next"'
            },
        )
    )
    page = await provider.search("gene:APP", size=1)
    assert route.calls.last.request.url.params["format"] == "json"
    assert page["next_cursor"] == "abc123"
    assert page["items"][0]["accession"] == "P05067"


@respx.mock
async def test_search_without_link_has_no_cursor(provider):
    respx.get(f"{BASE}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    page = await provider.search("nothing")
    assert page["next_cursor"] is None
    assert page["items"] == []


@respx.mock
async def test_idmapping_polls_until_finished(monkeypatch, provider):
    monkeypatch.setattr(uniprot_module, "_POLL_INTERVAL", 0)
    respx.post(f"{BASE}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "j1"})
    )
    respx.get(f"{BASE}/idmapping/status/j1").mock(
        side_effect=[
            httpx.Response(200, json={"jobStatus": "RUNNING"}),
            httpx.Response(200, json={"jobStatus": "FINISHED"}),
        ]
    )
    respx.get(f"{BASE}/idmapping/results/j1").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"from": "P04637", "to": "1A1U"},
                    {"from": "P04637", "to": "1AIE"},
                    {"from": "P05067", "to": "1AAP"},
                ]
            },
        )
    )
    result = await provider.map_ids("UniProtKB_AC-ID", "PDB", "P04637,P05067")
    assert result["job_id"] == "j1"
    assert result["mappings"] == {"P04637": ["1A1U", "1AIE"], "P05067": ["1AAP"]}


@respx.mock
async def test_idmapping_failure_raises(monkeypatch, provider):
    monkeypatch.setattr(uniprot_module, "_POLL_INTERVAL", 0)
    respx.post(f"{BASE}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "j1"})
    )
    respx.get(f"{BASE}/idmapping/status/j1").mock(
        return_value=httpx.Response(200, json={"jobStatus": "ERROR"})
    )
    with pytest.raises(UpstreamError):
        await provider.map_ids("UniProtKB_AC-ID", "PDB", "P04637")


@respx.mock
async def test_idmapping_finishes_on_303_redirect(monkeypatch, provider):
    monkeypatch.setattr(uniprot_module, "_POLL_INTERVAL", 0)
    respx.post(f"{BASE}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "j2"})
    )
    respx.get(f"{BASE}/idmapping/status/j2").mock(
        return_value=httpx.Response(
            303,
            json={"jobStatus": "FINISHED"},
            headers={"Location": f"{BASE}/idmapping/results/j2"},
        )
    )
    respx.get(f"{BASE}/idmapping/results/j2").mock(
        return_value=httpx.Response(200, json={"results": [{"from": "P04637", "to": "1A1U"}]})
    )
    result = await provider.map_ids("UniProtKB_AC-ID", "PDB", "P04637")
    assert result["mappings"] == {"P04637": ["1A1U"]}


@respx.mock
async def test_idmapping_follows_all_result_pages(monkeypatch, provider):
    monkeypatch.setattr(uniprot_module, "_POLL_INTERVAL", 0)
    respx.post(f"{BASE}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "j3"})
    )
    respx.get(f"{BASE}/idmapping/status/j3").mock(
        return_value=httpx.Response(303, json={"jobStatus": "FINISHED"})
    )
    route = respx.get(f"{BASE}/idmapping/results/j3").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"results": [{"from": "P1", "to": "A1"}]},
                headers={"Link": f'<{BASE}/idmapping/results/j3?cursor=c1&size=1>; rel="next"'},
            ),
            httpx.Response(200, json={"results": [{"from": "P2", "to": "A2"}]}),
        ]
    )
    result = await provider.map_ids("UniProtKB_AC-ID", "PDB", "P1,P2")
    assert result["mappings"] == {"P1": ["A1"], "P2": ["A2"]}
    assert route.call_count == 2
