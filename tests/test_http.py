from __future__ import annotations

import time

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import AuthError, NotFound, UpstreamError
from scientific_data_mcp.http import PoliteClient

URL = "https://api.test/thing"


@respx.mock
async def test_404_becomes_not_found():
    respx.get(URL).mock(return_value=httpx.Response(404))
    async with PoliteClient(Settings()) as client:
        with pytest.raises(NotFound):
            await client.get_json(URL)


@respx.mock
async def test_429_retries_then_succeeds():
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with PoliteClient(Settings()) as client:
        assert await client.get_json(URL) == {"ok": True}
    assert route.call_count == 2


@respx.mock
async def test_401_becomes_auth_error():
    respx.get(URL).mock(return_value=httpx.Response(401))
    async with PoliteClient(Settings()) as client:
        with pytest.raises(AuthError):
            await client.get_json(URL)


@respx.mock
async def test_500_becomes_upstream_error():
    respx.get(URL).mock(return_value=httpx.Response(500))
    async with PoliteClient(Settings()) as client:
        with pytest.raises(UpstreamError):
            await client.get_json(URL)


@respx.mock
async def test_paces_requests_per_host():
    respx.get(URL).mock(return_value=httpx.Response(200, json={"ok": 1}))
    settings = Settings(host_delays={"api.test": 0.05})
    async with PoliteClient(settings) as client:
        start = time.monotonic()
        await client.get_json(URL)
        await client.get_json(URL)
        assert time.monotonic() - start >= 0.04


@respx.mock
async def test_post_form_sends_urlencoded_body():
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    async with PoliteClient(Settings()) as client:
        assert await client.post_form(URL, {"smiles": "C/C"}) == {"ok": True}
    assert route.calls.last.request.content == b"smiles=C%2FC"
