from __future__ import annotations

import hashlib

import pytest
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import AuthError
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.brenda import BrendaProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.enzymes import register


class FakeService:
    def __init__(self):
        self.calls = []
        self.fail = None

    def _call(self, name, args):
        if self.fail:
            raise self.fail
        self.calls.append((name, args))
        return [
            {"kmValue": "0.12", "substrate": "ethanol", "organism": "Homo sapiens"},
            {"kmValue": "0.34", "substrate": "propanol", "organism": "Homo sapiens"},
        ]

    def getKmValue(self, *args):
        return self._call("getKmValue", args)

    def getTurnoverNumber(self, *args):
        return self._call("getTurnoverNumber", args)

    def getSubstratesProducts(self, *args):
        return self._call("getSubstratesProducts", args)


@pytest.fixture
async def provider():
    settings = Settings(
        host_delays={"www.brenda-enzymes.org": 0.0},
        brenda_email="j.doe@example.edu",
        brenda_password="secret",
    )
    async with PoliteClient(settings) as client:
        yield BrendaProvider(client, settings, service=FakeService())


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={"www.brenda-enzymes.org": 0.0},
        brenda_email="j.doe@example.edu",
        brenda_password="secret",
    )
    service = build_service(settings)
    service.providers["brenda"]._service = FakeService()
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


async def test_km_args_and_hash(provider):
    items = await provider.query("km", "1.1.1.1", "Homo sapiens")
    assert len(items) == 2
    name, args = provider._service.calls[0]
    assert name == "getKmValue"
    assert args[0] == "j.doe@example.edu"
    assert args[1] == hashlib.sha256(b"secret").hexdigest()
    assert "ecNumber*1.1.1.1" in args
    assert "organism*Homo sapiens" in args
    assert "kmValue*" in args


async def test_substrates_uses_substrates_method(provider):
    await provider.query("substrates", "1.1.1.1")
    assert provider._service.calls[0][0] == "getSubstratesProducts"


async def test_auth_error_mapping(provider):
    provider._service.fail = RuntimeError("Invalid email or password")
    with pytest.raises(AuthError):
        await provider.query("km", "1.1.1.1")


async def test_tool_envelope_and_validation(tools):
    result = await tools["brenda"]("1.1.1.1", kind="km", limit=1)
    assert result["source"] == "brenda"
    assert result["count"] == 1
    assert result["total"] == 2
    assert "invalid EC" in (await tools["brenda"]("1.1.1"))["error"]
    assert (await tools["brenda"]("1.1.1.n1"))["count"] == 2
    assert "invalid kind" in (await tools["brenda"]("1.1.1.1", kind="nope"))["error"]
    assert "1-100" in (await tools["brenda"]("1.1.1.1", limit=0))["error"]


async def test_no_credentials_no_provider():
    service = build_service(Settings())
    assert "brenda" not in service.providers
    assert register(FastMCP("test"), service) == {}
    await service.aclose()
