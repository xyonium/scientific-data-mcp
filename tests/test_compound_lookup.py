from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

OLS = "https://www.ebi.ac.uk/ols4/api"
KEGG = "https://rest.kegg.jp"

CHEBI_SEARCH = {
    "response": {
        "docs": [
            {
                "obo_id": "CHEBI:15365",
                "label": "acetylsalicylic acid",
                "description": ["A benzoic acid..."],
                "type": "class",
            }
        ]
    }
}
KEGG_FLAT = """ENTRY       C01405                      Compound
NAME        Aspirin
FORMULA     C9H8O4
EXACT_MASS  180.0423
MOL_WEIGHT  180.16
PATHWAY     map04976  Bile secretion
///
"""


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "www.ebi.ac.uk": 0.0,
            "rest.kegg.jp": 0.0,
            "bindingdb.org": 0.0,
        }
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_chebi_source(tools):
    respx.get(f"{OLS}/search").mock(return_value=httpx.Response(200, json=CHEBI_SEARCH))
    result = await tools["compound_lookup"]("aspirin", source="chebi")
    assert result["source"] == "chebi"
    assert result["items"][0]["chebi_id"] == "CHEBI:15365"


@respx.mock
async def test_kegg_source(tools):
    respx.get(f"{KEGG}/find/compound/aspirin").mock(
        return_value=httpx.Response(200, text="C01405\tAspirin\n")
    )
    respx.get(f"{KEGG}/get/cpd:C01405").mock(
        return_value=httpx.Response(200, text=KEGG_FLAT)
    )
    result = await tools["compound_lookup"]("aspirin", source="kegg", limit=1)
    assert result["source"] == "kegg"
    assert result["items"][0]["entry"] == "C01405"


async def test_validation(tools):
    assert "invalid source" in (
        await tools["compound_lookup"]("x", source="nope")
    )["error"]
    assert "query" in (await tools["compound_lookup"](" "))["error"]
    assert "1-10" in (
        await tools["compound_lookup"]("x", limit=0)
    )["error"]
