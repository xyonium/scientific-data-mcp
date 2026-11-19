from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.cbioportal import CbioPortalProvider
from scientific_data_mcp.providers.gdc import GdcProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.cancer import register

GDC_BASE = "https://api.gdc.cancer.gov"
CBIO_BASE = "https://www.cbioportal.org/api"

GDC_PAYLOAD = {
    "data": {
        "hits": [
            {
                "project_id": "TCGA-BRCA",
                "name": "Breast Invasive Carcinoma",
                "primary_site": ["Breast"],
                "disease_type": ["Ductal and Lobular Neoplasms"],
            },
            {
                "project_id": "TCGA-LUAD",
                "name": "Lung Adenocarcinoma",
                "primary_site": ["Bronchus and lung"],
                "disease_type": ["Adenomas"],
            },
        ]
    }
}
CBIO_PAYLOAD = [
    {
        "studyId": "brca_tcga",
        "name": "Breast Invasive Carcinoma (TCGA)",
        "description": "Breast cancer",
        "cancerTypeId": "brca",
        "allSampleCount": 1100,
        "pmid": "123",
        "citation": "TCGA 2012",
        "referenceGenome": "hg19",
    }
]


@pytest.fixture
async def providers():
    settings = Settings(
        host_delays={"api.gdc.cancer.gov": 0.0, "www.cbioportal.org": 0.0}
    )
    async with PoliteClient(settings) as client:
        yield GdcProvider(client, settings), CbioPortalProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(
        host_delays={"api.gdc.cancer.gov": 0.0, "www.cbioportal.org": 0.0}
    )
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_gdc_filters_locally(providers):
    gdc, _ = providers
    respx.get(f"{GDC_BASE}/projects").mock(
        return_value=httpx.Response(200, json=GDC_PAYLOAD)
    )
    page = await gdc.projects("breast", 10)
    assert page["total"] == 1
    assert page["items"][0]["project_id"] == "TCGA-BRCA"


@respx.mock
async def test_cbioportal_normalizes(providers):
    _, cbio = providers
    route = respx.get(f"{CBIO_BASE}/studies").mock(
        return_value=httpx.Response(200, json=CBIO_PAYLOAD)
    )
    page = await cbio.studies("breast", 5)
    assert page["items"][0]["study_id"] == "brca_tcga"
    assert route.calls.last.request.url.params["keyword"] == "breast"
    assert route.calls.last.request.url.params["pageSize"] == "5"


@respx.mock
async def test_tool_both_sources_and_validation(tools):
    respx.get(f"{GDC_BASE}/projects").mock(
        return_value=httpx.Response(200, json=GDC_PAYLOAD)
    )
    respx.get(f"{CBIO_BASE}/studies").mock(
        return_value=httpx.Response(200, json=CBIO_PAYLOAD)
    )
    gdc = await tools["cancer_studies"]("breast", source="gdc")
    cbio = await tools["cancer_studies"]("breast", source="cbioportal")
    assert gdc["count"] == 1
    assert cbio["count"] == 1
    assert "invalid source" in (
        await tools["cancer_studies"]("x", source="nope")
    )["error"]
    assert "1-50" in (await tools["cancer_studies"]("x", limit=0))["error"]
