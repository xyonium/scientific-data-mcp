from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.biogrid import register

BASE = "https://webservice.thebiogrid.org/interactions/"


@pytest.fixture
async def tools():
    settings = Settings(
        biogrid_access_key="k", host_delays={"webservice.thebiogrid.org": 0.0}
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


async def test_not_registered_without_key():
    service = build_service(Settings())
    assert register(FastMCP("test"), service) == {}


async def test_validates_inputs(tools):
    assert "genes" in (await tools["biogrid_interactions"](" "))["error"]
    assert "50 genes" in (
        await tools["biogrid_interactions"]("|".join(f"G{i}" for i in range(51)))
    )["error"]
    assert "organism" in (await tools["biogrid_interactions"]("TP53", organism=0))["error"]
    assert "1-1000" in (await tools["biogrid_interactions"]("TP53", limit=0))["error"]
    assert "offset" in (await tools["biogrid_interactions"]("TP53", offset=-1))["error"]


@respx.mock
async def test_envelope(tools):
    respx.get(BASE).mock(
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
    result = await tools["biogrid_interactions"]("TP53")
    assert result["source"] == "biogrid"
    assert result["count"] == 1
    assert result["items"][0]["gene_b"] == "MDM2"


@respx.mock
async def test_401_is_auth_not_drift(tools):
    respx.get(BASE).mock(return_value=httpx.Response(401))
    result = await tools["biogrid_interactions"]("TP53")
    assert "auth" in result["error"]
    assert "suspect_drift" not in result
