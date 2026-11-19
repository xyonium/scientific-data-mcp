from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.interactions import register

STRING = "https://string-db.org/api/json"
BIOGRID = "https://webservice.thebiogrid.org/interactions/"


@pytest.fixture
async def tools():
    settings = Settings(
        biogrid_access_key="k",
        host_delays={"string-db.org": 0.0, "webservice.thebiogrid.org": 0.0},
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@pytest.fixture
async def tools_no_biogrid():
    settings = Settings(host_delays={"string-db.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_string_envelope(tools):
    respx.get(f"{STRING}/interaction_partners").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "preferredName_A": "TP53",
                    "preferredName_B": "MDM2",
                    "ncbiTaxonId": 9606,
                    "score": 0.999,
                }
            ],
        )
    )
    result = await tools["protein_interactions"]("TP53")
    assert result["source"] == "string"
    assert result["count"] == 1
    assert result["items"][0]["gene_b"] == "MDM2"


@respx.mock
async def test_biogrid_envelope(tools):
    respx.get(BIOGRID).mock(
        return_value=httpx.Response(
            200,
            json={
                "1": {
                    "BIOGRID_INTERACTION_ID": 1,
                    "OFFICIAL_SYMBOL_A": "TP53",
                    "OFFICIAL_SYMBOL_B": "MDM2",
                }
            },
        )
    )
    result = await tools["protein_interactions"]("TP53", source="biogrid")
    assert result["source"] == "biogrid"
    assert result["items"][0]["gene_b"] == "MDM2"


async def test_biogrid_without_key_is_a_clear_error(tools_no_biogrid):
    result = await tools_no_biogrid["protein_interactions"]("TP53", source="biogrid")
    assert "BIOGRID_ACCESS_KEY" in result["error"]


async def test_validation(tools):
    assert "invalid source" in (await tools["protein_interactions"]("TP53", source="x"))["error"]
    assert "genes" in (await tools["protein_interactions"](" "))["error"]
    assert "100" in (await tools["protein_interactions"]("TP53", limit=0))["error"]
    assert "min_score" in (await tools["protein_interactions"]("TP53", min_score=1001))["error"]
    assert "min_score" in (
        await tools["protein_interactions"]("TP53", source="biogrid", min_score=700)
    )["error"]


@respx.mock
async def test_string_drift_is_marked(tools):
    respx.get(f"{STRING}/interaction_partners").mock(
        return_value=httpx.Response(200, json={"error": "bad"})
    )
    result = await tools["protein_interactions"]("TP53")
    assert result["suspect_drift"] is True
