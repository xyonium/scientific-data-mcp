from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.kegg import KeggProvider

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

