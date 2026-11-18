from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.materials import register

BASE = "https://api.materialsproject.org/materials/summary/"


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


async def test_search_requires_exactly_one_selector(tools):
    empty = await tools["material_search"]()
    both = await tools["material_search"](formula="SiO2", chemsys="Si-O")
    assert "exactly one" in empty["error"]
    assert "exactly one" in both["error"]


async def test_search_rejects_bad_limit(tools):
    result = await tools["material_search"](formula="SiO2", limit=0)
    assert "1-100" in result["error"]


@respx.mock
async def test_search_empty_is_count_zero(tools):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [], "meta": {}}))
    result = await tools["material_search"](chemsys="Xx-Yy")
    assert result["count"] == 0
    assert result["items"] == []


@respx.mock
async def test_get_404_returns_error_dict(tools):
    respx.get(BASE).mock(return_value=httpx.Response(404))
    result = await tools["material_get"]("mp-999999")
    assert result["source"] == "materials_project"
    assert "not_found" in result["error"]


@respx.mock
async def test_auth_error_is_reported(tools):
    respx.get(BASE).mock(return_value=httpx.Response(401))
    result = await tools["material_get"]("mp-149")
    assert "auth" in result["error"]
