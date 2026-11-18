from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.who import WhoProvider

BASE = "https://ghoapi.azureedge.net/api"

ROW = {
    "IndicatorCode": "WHOSIS_000001",
    "SpatialDimType": "COUNTRY",
    "SpatialDim": "CHN",
    "TimeDim": 2022,
    "Dim1": "SEX_BTSX",
    "Value": "78.2 [76-80.6]",
    "NumericValue": 78.2,
    "Low": 76.0,
    "High": 80.6,
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"ghoapi.azureedge.net": 0.0})
    async with PoliteClient(settings) as client:
        yield WhoProvider(client, settings)


@respx.mock
async def test_data_builds_odata_filters(provider):
    route = respx.get(f"{BASE}/WHOSIS_000001").mock(
        return_value=httpx.Response(200, json={"value": [ROW]})
    )
    rows = await provider.data("WHOSIS_000001", country="chn", year=2022, limit=5)
    params = route.calls.last.request.url.params
    assert params["$top"] == "5"
    assert params["$filter"] == "SpatialDim eq 'CHN' and TimeDim eq 2022"
    assert rows[0]["value"] == 78.2
    assert rows[0]["value_text"] == "78.2 [76-80.6]"


@respx.mock
async def test_empty_value_is_an_empty_list(provider):
    respx.get(f"{BASE}/WHOSIS_000001").mock(
        return_value=httpx.Response(200, json={"value": []})
    )
    assert await provider.data("WHOSIS_000001") == []


@respx.mock
async def test_missing_value_list_is_drift(provider):
    respx.get(f"{BASE}/WHOSIS_000001").mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )
    with pytest.raises(UpstreamDrift):
        await provider.data("WHOSIS_000001")
