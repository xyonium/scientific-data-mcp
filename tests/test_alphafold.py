from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.alphafold import AlphaFoldProvider

BASE = "https://alphafold.ebi.ac.uk/api"

ROW = {
    "entryId": "AF-P04637-F1",
    "latestVersion": 6,
    "uniprotStart": 1,
    "uniprotEnd": 393,
    "globalMetricValue": 72.5,
    "pdbUrl": "https://example.org/model.pdb",
    "cifUrl": "https://example.org/model.cif",
    "paeImageUrl": "https://example.org/pae.png",
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"alphafold.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield AlphaFoldProvider(client, settings)


@respx.mock
async def test_prediction_normalizes(provider):
    respx.get(f"{BASE}/prediction/P04637").mock(
        return_value=httpx.Response(200, json=[ROW])
    )
    result = await provider.prediction("P04637")
    assert result["accession"] == "P04637"
    assert result["predictions"][0]["entry_id"] == "AF-P04637-F1"
    assert result["predictions"][0]["plddt"] == 72.5


@respx.mock
async def test_empty_prediction_list_is_normal(provider):
    respx.get(f"{BASE}/prediction/P04637").mock(return_value=httpx.Response(200, json=[]))
    assert await provider.prediction("P04637") == {"accession": "P04637", "predictions": []}


@respx.mock
async def test_bad_identifier_is_value_error(provider):
    respx.get(f"{BASE}/prediction/XXXXXX").mock(
        return_value=httpx.Response(400, json={"error": "Invalid identifier format"})
    )
    with pytest.raises(ValueError, match="Invalid identifier"):
        await provider.prediction("XXXXXX")


@respx.mock
async def test_missing_entry_is_not_found(provider):
    respx.get(f"{BASE}/prediction/P04637").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFound):
        await provider.prediction("P04637")


@respx.mock
async def test_non_list_payload_is_drift(provider):
    respx.get(f"{BASE}/prediction/P04637").mock(
        return_value=httpx.Response(200, json={"error": "oops"})
    )
    with pytest.raises(UpstreamDrift):
        await provider.prediction("P04637")


@respx.mock
async def test_non_identifier_400_is_drift(provider):
    respx.get(f"{BASE}/prediction/P04637").mock(
        return_value=httpx.Response(400, json={"error": "temporary backend failure"})
    )
    with pytest.raises(UpstreamDrift):
        await provider.prediction("P04637")


@respx.mock
async def test_prediction_caps_at_twenty(provider):
    rows = [dict(ROW, entryId=f"AF-P04637-F{i}") for i in range(25)]
    respx.get(f"{BASE}/prediction/P04637").mock(
        return_value=httpx.Response(200, json=rows)
    )
    result = await provider.prediction("P04637")
    assert len(result["predictions"]) == 20
