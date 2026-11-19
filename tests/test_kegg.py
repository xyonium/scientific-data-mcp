from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.kegg import KeggProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

BASE = "https://rest.kegg.jp"

FLAT = """ENTRY       C01405                      Compound
NAME        Aspirin;
            Acetylsalicylic acid
FORMULA     C9H8O4
EXACT_MASS  180.0423
MOL_WEIGHT  180.16
PATHWAY     map04976  Bile secretion
            map04080  Neuroactive ligand-receptor interaction
///
"""


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"rest.kegg.jp": 0.0})
    async with PoliteClient(settings) as client:
        yield KeggProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"rest.kegg.jp": 0.0, "dailymed.nlm.nih.gov": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_compound_by_name(provider):
    respx.get(f"{BASE}/find/compound/aspirin").mock(
        return_value=httpx.Response(200, text="C01405\tAspirin; Acetylsalicylic acid\n")
    )
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=FLAT)
    )
    items = await provider.compound("aspirin", 3)
    assert items[0]["entry"] == "C01405"
    assert items[0]["names"] == ["Aspirin", "Acetylsalicylic acid"]
    assert items[0]["formula"] == "C9H8O4"
    assert [p["id"] for p in items[0]["pathways"]] == ["map04976", "map04080"]


@respx.mock
async def test_compound_by_id_skips_find(provider):
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=FLAT)
    )
    items = await provider.compound("C01405")
    assert items[0]["mol_weight"] == "180.16"


@respx.mock
async def test_empty_find(provider):
    respx.get(f"{BASE}/find/compound/nope").mock(
        return_value=httpx.Response(200, text="")
    )
    assert await provider.compound("nope") == []


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/find/compound/aspirin").mock(
        return_value=httpx.Response(200, text="C01405\tAspirin\n")
    )
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=FLAT)
    )
    result = await tools["kegg_compound"]("aspirin", limit=1)
    assert result["source"] == "kegg"
    assert result["count"] == 1
    assert "query" in (await tools["kegg_compound"](" "))["error"]
    assert "1-10" in (await tools["kegg_compound"]("x", limit=0))["error"]


@respx.mock
async def test_missing_entry_is_drift(provider):
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text="NAME  Aspirin\n")
    )
    with pytest.raises(UpstreamDrift):
        await provider.compound("C01405")


@respx.mock
async def test_empty_get_is_not_found(provider):
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text="")
    )
    with pytest.raises(NotFound):
        await provider.compound("C01405")


@respx.mock
async def test_tool_limit_upper_bound(tools):
    respx.get(f"{BASE}/find/compound/aspirin").mock(
        return_value=httpx.Response(200, text="C01405\tAspirin\n")
    )
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=FLAT)
    )
    assert (await tools["kegg_compound"]("aspirin", limit=10))["count"] == 1
    assert "1-10" in (await tools["kegg_compound"]("x", limit=11))["error"]


@respx.mock
async def test_malformed_find_is_drift(provider):
    respx.get(f"{BASE}/find/compound/aspirin").mock(
        return_value=httpx.Response(200, text="not-a-kegg-line\n")
    )
    with pytest.raises(UpstreamDrift):
        await provider.compound("aspirin")


@respx.mock
async def test_multiple_records_is_drift(provider):
    respx.get(f"{BASE}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=FLAT + "///\n" + FLAT)
    )
    with pytest.raises(UpstreamDrift):
        await provider.compound("C01405")
