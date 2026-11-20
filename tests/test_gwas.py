from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.gwas import GwasProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.clinical_assoc import register

BASE = "https://www.ebi.ac.uk/gwas/rest/api/v2"
PAYLOAD = {
    "_embedded": {
        "associations": [
            {
                "association_id": 123,
                "p_value": 4e-12,
                "reported_trait": ["Biological Sibling: High cholesterol"],
                "efo_traits": [{"efo_id": "HP_0003124", "efo_trait": "hypercholesterolemia"}],
                "mapped_genes": ["APOE"],
                "risk_frequency": "0.9193",
                "beta": "0.1437 unit increase",
                "snp_effect_allele": ["rs7412-C"],
                "pubmed_id": "39024449",
                "first_author": "Verma A",
                "accession_id": "GCST90476371",
            }
        ]
    },
    "page": {"size": 1, "totalElements": 1185, "totalPages": 1185, "number": 0},
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield GwasProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0, "api.monarchinitiative.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_rs_associations(provider):
    route = respx.get(f"{BASE}/associations").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    result = await provider.associations("rs_id", "rs7412", 1)
    assert result["total"] == 1185
    assert result["items"][0]["mapped_genes"] == ["APOE"]
    assert route.calls.last.request.url.params["rs_id"] == "rs7412"


@respx.mock
async def test_empty_is_not_error(provider):
    respx.get(f"{BASE}/associations").mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"associations": []}, "page": {"totalElements": 0}}
        )
    )
    result = await provider.associations("efo_trait", "nope")
    assert result == {"items": [], "total": 0}


@respx.mock
async def test_missing_embedded_is_drift(provider):
    respx.get(f"{BASE}/associations").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.associations("rs_id", "rs7412")


@respx.mock
async def test_tool_auto_and_efo_id(tools):
    respx.get(f"{BASE}/associations").mock(return_value=httpx.Response(200, json=PAYLOAD))
    rs = await tools["gwas_associations"]("rs7412", limit=1)
    assert rs["next_page"] == 1
    assert rs["source_url"].endswith("/variants/rs7412")
    efo = await tools["gwas_associations"]("MONDO:0005150", by="auto")
    assert efo["count"] == 1
    assert "invalid by" in (await tools["gwas_associations"]("x", by="nope"))["error"]
    assert "1-100" in (await tools["gwas_associations"]("rs7412", limit=0))["error"]
