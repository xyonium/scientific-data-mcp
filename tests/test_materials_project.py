from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.materials_project import MaterialsProjectProvider
from scientific_data_mcp.runtime import build_service

BASE = "https://api.materialsproject.org/materials/summary/"

ROW = {
    "material_id": "mp-149",
    "formula_pretty": "SiO2",
    "chemsys": "Si-O",
    "elements": ["Si", "O"],
    "band_gap": 1.15,
    "energy_above_hull": 0.0,
    "density": 2.9,
    "is_stable": True,
    "nsites": 3,
    "theoretical": False,
    "symmetry": {"crystal_system": "tetragonal", "space_group_symbol": "P4_2/mnm"},
}


@pytest.fixture
async def provider():
    settings = Settings(
        materials_project_api_key="k",
        host_delays={"api.materialsproject.org": 0.0},
    )
    async with PoliteClient(settings) as client:
        yield MaterialsProjectProvider(client, settings)


def test_provider_is_gated_on_the_key():
    assert "materials_project" not in build_service(Settings()).providers
    assert "materials_project" in build_service(
        Settings(materials_project_api_key="k")
    ).providers


@respx.mock
async def test_get_sends_key_header_and_normalizes(provider):
    route = respx.get(BASE).mock(
        return_value=httpx.Response(200, json={"data": [ROW], "meta": {}})
    )
    record = await provider.get("mp-149")
    assert route.calls.last.request.headers["X-API-KEY"] == "k"
    assert record["formula"] == "SiO2"
    assert record["crystal_system"] == "tetragonal"
    assert record["band_gap"] == 1.15


@respx.mock
async def test_search_by_formula(provider):
    route = respx.get(BASE).mock(
        return_value=httpx.Response(200, json={"data": [ROW], "meta": {}})
    )
    rows = await provider.search(formula="SiO2", limit=5)
    params = route.calls.last.request.url.params
    assert params["formula"] == "SiO2"
    assert params["_limit"] == "5"
    assert rows[0]["material_id"] == "mp-149"


@respx.mock
async def test_search_empty_data_is_an_empty_list(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [], "meta": {}}))
    assert await provider.search(chemsys="Xx-Yy") == []


@respx.mock
async def test_unknown_material_raises_not_found(provider):
    respx.get(BASE).mock(return_value=httpx.Response(200, json={"data": [], "meta": {}}))
    with pytest.raises(NotFound):
        await provider.get("mp-999999")
