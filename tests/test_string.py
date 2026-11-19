from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.string_db import StringDbProvider

BASE = "https://string-db.org/api/json"

ROW = {
    "stringId_A": "9606.ENSP00000269305",
    "stringId_B": "9606.ENSP00000212015",
    "preferredName_A": "TP53",
    "preferredName_B": "SIRT1",
    "ncbiTaxonId": 9606,
    "score": 0.999,
    "nscore": 0,
    "fscore": 0,
    "pscore": 0,
    "ascore": 0,
    "escore": 0.999,
    "dscore": 0.9,
    "tscore": 0.886,
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"string-db.org": 0.0})
    async with PoliteClient(settings) as client:
        yield StringDbProvider(client, settings)


@respx.mock
async def test_partners_params_and_normalization(provider):
    route = respx.get(f"{BASE}/interaction_partners").mock(
        return_value=httpx.Response(200, json=[ROW])
    )
    rows = await provider.partners(["TP53", "MDM2"], organism=9606, limit=5, min_score=700)
    params = route.calls.last.request.url.params
    assert params["identifiers"] == "TP53\rMDM2"
    assert params["species"] == "9606"
    assert params["limit"] == "5"
    assert params["required_score"] == "700"
    assert rows[0]["gene_b"] == "SIRT1"
    assert rows[0]["score"] == 0.999
    assert rows[0]["scores"]["escore"] == 0.999
    assert "nscore" not in rows[0]["scores"]


@respx.mock
async def test_empty_list_is_normal(provider):
    respx.get(f"{BASE}/interaction_partners").mock(
        return_value=httpx.Response(200, json=[])
    )
    assert await provider.partners(["NOPE"]) == []


@respx.mock
async def test_non_list_payload_is_drift(provider):
    respx.get(f"{BASE}/interaction_partners").mock(
        return_value=httpx.Response(200, json={"error": "bad"})
    )
    with pytest.raises(UpstreamDrift):
        await provider.partners(["TP53"])
