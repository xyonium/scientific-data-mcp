from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamError
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.cod import CodProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.chem_sources import register

MAIN = "https://www.crystallography.net/cod"
UK = "https://cod.psdi.ac.uk"
ES = "https://qiserver.ugr.es/cod"
ROW = {
    "file": "1526463",
    "formula": "- Li2.78 O12 P3 V1.8 Zr0.2 -",
    "chemname": "Li2.78 (V0.9 Zr0.1)2 (P O4)3",
    "title": "Enhancement of discharge capacity",
    "authors": "Sato, M.; Ohkawa, H.",
    "journal": "J. Power Sources",
    "year": "2001",
    "doi": "10.1016/S0378-7753(01)00801-1",
    "sg": "P b c n",
    "sgNumber": "60",
    "a": "12.1005",
    "b": "8.6539",
    "c": "8.6546",
    "alpha": "90",
    "beta": "90",
    "gamma": "90",
    "vol": "906.28",
}


@pytest.fixture
async def provider():
    settings = Settings(
        host_delays={
            "www.crystallography.net": 0.0,
            "cod.psdi.ac.uk": 0.0,
            "qiserver.ugr.es": 0.0,
        }
    )
    async with PoliteClient(settings) as client:
        yield CodProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={
            "www.crystallography.net": 0.0,
            "cod.psdi.ac.uk": 0.0,
            "qiserver.ugr.es": 0.0,
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
async def test_main_success(provider):
    route = respx.get(f"{MAIN}/result").mock(
        return_value=httpx.Response(200, json=[ROW])
    )
    result = await provider.search({"id": "1526463"})
    assert result["via_mirror"] is False
    assert route.call_count == 1


@respx.mock
async def test_timeout_falls_back_to_uk(provider):
    main = respx.get(f"{MAIN}/result").mock(
        side_effect=httpx.ConnectTimeout("main down")
    )
    uk = respx.get(f"{UK}/result").mock(return_value=httpx.Response(200, json=[ROW]))
    result = await provider.search({"id": "1526463"})
    assert result["via_mirror"] is True
    assert result["host"] == UK
    assert main.call_count == 1
    assert uk.call_count == 1


@respx.mock
async def test_403_falls_back_without_retry(provider):
    main = respx.get(f"{MAIN}/result").mock(return_value=httpx.Response(403))
    uk = respx.get(f"{UK}/result").mock(return_value=httpx.Response(200, json=[ROW]))
    result = await provider.search({"id": "1526463"})
    assert result["host"] == UK
    assert main.call_count == 1
    assert uk.call_count == 1


@respx.mock
async def test_all_fail_is_unavailable(provider):
    respx.get(f"{MAIN}/result").mock(side_effect=httpx.ConnectTimeout("main down"))
    respx.get(f"{UK}/result").mock(return_value=httpx.Response(500))
    with pytest.raises(UpstreamError):
        await provider.search({"id": "1526463"})


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{MAIN}/result").mock(return_value=httpx.Response(200, json=[ROW]))
    result = await tools["cod_crystals"]("1526463", limit=1)
    assert result["source"] == "cod"
    assert result["count"] == 1
    assert result["items"][0]["cod_id"] == "1526463"
    assert "exactly one" in (await tools["cod_crystals"]())["error"]
    assert "exactly one" in (
        await tools["cod_crystals"]("1", formula="Fe2 O3")
    )["error"]
    assert "1-50" in (await tools["cod_crystals"]("1", limit=0))["error"]
