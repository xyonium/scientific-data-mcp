from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.who import register

BASE = "https://ghoapi.azureedge.net/api"


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"ghoapi.azureedge.net": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


async def test_who_data_validates_inputs(tools):
    assert "indicator" in (await tools["who_data"]("bad code!"))["error"]
    assert "ISO3" in (await tools["who_data"]("WHOSIS_000001", country="China"))["error"]
    assert "1900" in (await tools["who_data"]("WHOSIS_000001", year=1800))["error"]
    assert "SEX_" in (await tools["who_data"]("WHOSIS_000001", sex="female"))["error"]
    assert "1-1000" in (await tools["who_data"]("WHOSIS_000001", limit=0))["error"]


@respx.mock
async def test_who_data_empty_is_count_zero(tools):
    respx.get(f"{BASE}/WHOSIS_000001").mock(
        return_value=httpx.Response(200, json={"value": []})
    )
    result = await tools["who_data"]("WHOSIS_000001", country="CHN")
    assert result["count"] == 0
    assert result["items"] == []
    assert result["source"] == "who"


@respx.mock
async def test_who_drift_marks_contact_admin(tools):
    respx.get(f"{BASE}/WHOSIS_000001").mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )
    result = await tools["who_data"]("WHOSIS_000001")
    assert result["suspect_drift"] is True
    assert result["action"] == "contact_admin"
    assert "联系管理员" in result["hint"]


@respx.mock
async def test_who_504_is_transient_not_drift(tools):
    respx.get(f"{BASE}/WHOSIS_000001").mock(return_value=httpx.Response(504))
    result = await tools["who_data"]("WHOSIS_000001")
    assert "suspect_drift" not in result
    assert "unavailable" in result["error"]
