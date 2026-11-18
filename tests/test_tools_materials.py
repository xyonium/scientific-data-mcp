from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.materials import register

BASE = "https://api.materialsproject.org/materials/summary/"
ROW = {
    "material_id": "mp-149",
    "formula_pretty": "SiO2",
    "chemsys": "Si-O",
    "band_gap": 1.15,
    "symmetry": {"crystal_system": "tetragonal"},
}


@pytest.fixture
async def tools():
    settings = Settings(
        materials_project_api_key="k",
        host_delays={"api.materialsproject.org": 0.0},
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


async def test_not_registered_without_key():
    service = build_service(Settings())
    assert register(FastMCP("test"), service) == {}


@respx.mock
async def test_material_by_id(tools):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [ROW], "meta": {}}))
    result = await tools["material"](by="id", query="mp-149")
    assert result["count"] == 1
    assert result["items"][0]["formula"] == "SiO2"
    assert result["source_url"] == "https://materialsproject.org/materials/mp-149"


@respx.mock
async def test_material_by_formula(tools):
    route = respx.get(BASE).mock(
        return_value=httpx.Response(200, json={"data": [ROW], "meta": {}})
    )
    result = await tools["material"](by="formula", query="SiO2", limit=5)
    assert route.calls.last.request.url.params["formula"] == "SiO2"
    assert route.calls.last.request.url.params["_limit"] == "5"
    assert result["count"] == 1


async def test_material_validates_inputs(tools):
    assert "invalid by" in (await tools["material"](by="nope", query="x"))["error"]
    assert "query" in (await tools["material"](query="  "))["error"]
    assert "1-100" in (await tools["material"](by="formula", query="SiO2", limit=0))["error"]


@respx.mock
async def test_material_400_marks_contact_admin(tools):
    respx.get(BASE).mock(
        return_value=httpx.Response(400, json={"detail": "unknown query parameter"})
    )
    result = await tools["material"](by="id", query="mp-149")
    assert result["suspect_drift"] is True
    assert result["action"] == "contact_admin"


@respx.mock
async def test_material_401_is_auth_not_drift(tools):
    respx.get(BASE).mock(return_value=httpx.Response(401))
    result = await tools["material"](by="id", query="mp-149")
    assert "auth" in result["error"]
    assert "suspect_drift" not in result
