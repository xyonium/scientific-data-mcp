from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.gtex import GtexProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.expression import register

BASE = "https://gtexportal.org/api/v2"

GENE = {
    "data": [
        {
            "gencodeId": "ENSG00000141510.16",
            "geneSymbol": "TP53",
            "description": "tumor protein p53",
        }
    ]
}
EXPR = {
    "data": [
        {
            "tissueSiteDetailId": "Adipose_Subcutaneous",
            "ontologyId": "UBERON:0002190",
            "median": 22.459,
            "unit": "TPM",
            "datasetId": "gtex_v8",
        }
    ],
    "paging_info": {"totalNumberOfItems": 54},
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"gtexportal.org": 0.0})
    async with PoliteClient(settings) as client:
        yield GtexProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"gtexportal.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_expression_resolves_gencode(provider):
    respx.get(f"{BASE}/reference/gene").mock(return_value=httpx.Response(200, json=GENE))
    route = respx.get(f"{BASE}/expression/medianGeneExpression").mock(
        return_value=httpx.Response(200, json=EXPR)
    )
    page = await provider.expression("ENSG00000141510", "gtex_v8", 10)
    assert page["gene_symbol"] == "TP53"
    assert page["total"] == 54
    assert page["items"][0]["median"] == 22.459
    assert route.calls.last.request.url.params["gencodeId"] == "ENSG00000141510.16"


@respx.mock
async def test_unknown_gene_is_not_found(provider):
    respx.get(f"{BASE}/reference/gene").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    with pytest.raises(NotFound):
        await provider.expression("ENSG00000000000")


@respx.mock
async def test_missing_expression_data_is_drift(provider):
    respx.get(f"{BASE}/reference/gene").mock(return_value=httpx.Response(200, json=GENE))
    respx.get(f"{BASE}/expression/medianGeneExpression").mock(
        return_value=httpx.Response(200, json={})
    )
    with pytest.raises(UpstreamDrift):
        await provider.expression("ENSG00000141510")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/reference/gene").mock(return_value=httpx.Response(200, json=GENE))
    respx.get(f"{BASE}/expression/medianGeneExpression").mock(
        return_value=httpx.Response(200, json=EXPR)
    )
    result = await tools["gene_expression"]("ENSG00000141510", limit=1)
    assert result["source"] == "gtex"
    assert result["gene_symbol"] == "TP53"
    assert result["count"] == 1
    assert "gene_id" in (await tools["gene_expression"](" "))["error"]
    assert "1-100" in (await tools["gene_expression"]("ENSG", limit=0))["error"]
