from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.gene import GeneProvider
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.genomics import register

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

SEARCH = {"esearchresult": {"count": "1", "idlist": ["7157"]}}
SUMMARY = {
    "result": {
        "uids": ["7157"],
        "7157": {
            "name": "TP53",
            "description": "tumor protein p53",
            "chromosome": "17",
            "maplocation": "17p13.1",
            "otheraliases": "P53, TRP53",
            "summary": "Tumor suppressor.",
            "organism": {"scientificname": "Homo sapiens", "taxid": 9606},
        },
    }
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0, "rest.ensembl.org": 0.0})
    async with PoliteClient(settings) as client:
        yield GeneProvider(client, settings)


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0, "rest.ensembl.org": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


@respx.mock
async def test_record_by_symbol(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json=SUMMARY))
    record = await provider.record("TP53")
    assert record["gene_id"] == "7157"
    assert record["symbol"] == "TP53"
    assert record["organism"] == "Homo sapiens"
    assert record["taxid"] == 9606


@respx.mock
async def test_record_by_numeric_id_skips_search(provider):
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json=SUMMARY))
    record = await provider.record("7157")
    assert record["symbol"] == "TP53"


@respx.mock
async def test_no_hit_is_not_found(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
    )
    with pytest.raises(NotFound):
        await provider.record("NOPE")


@respx.mock
async def test_missing_esearchresult_is_drift(provider):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(UpstreamDrift):
        await provider.record("TP53")


@respx.mock
async def test_tool_envelope_and_validation(tools):
    respx.get(f"{BASE}/esearch.fcgi").mock(return_value=httpx.Response(200, json=SEARCH))
    respx.get(f"{BASE}/esummary.fcgi").mock(return_value=httpx.Response(200, json=SUMMARY))
    result = await tools["gene_record"]("TP53")
    assert result["source"] == "ncbi_gene"
    assert result["source_url"].endswith("/7157")
    assert "identifier" in (await tools["gene_record"](" "))["error"]
    assert "organism" in (await tools["gene_record"]("TP53", organism=0))["error"]


@respx.mock
async def test_unknown_numeric_id_is_not_found(provider):
    respx.get(f"{BASE}/esummary.fcgi").mock(
        return_value=httpx.Response(
            200,
            json={"result": {"uids": ["999"], "999": {"uid": "999", "error": "cannot get document summary"}}},
        )
    )
    with pytest.raises(NotFound):
        await provider.record("999")


@respx.mock
async def test_request_carries_ncbi_key_and_email():
    settings = Settings(
        ncbi_api_key="key",
        ncbi_email="me@example.com",
        host_delays={"eutils.ncbi.nlm.nih.gov": 0.0},
    )
    async with PoliteClient(settings) as client:
        provider = GeneProvider(client, settings)
        route = respx.get(f"{BASE}/esearch.fcgi").mock(
            return_value=httpx.Response(200, json=SEARCH)
        )
        respx.get(f"{BASE}/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=SUMMARY)
        )
        await provider.record("TP53")
        params = route.calls.last.request.url.params
        assert params["db"] == "gene"
        assert params["api_key"] == "key"
        assert params["email"] == "me@example.com"
        assert "TP53[gene]" in params["term"]


@respx.mock
async def test_gene_record_ensembl(tools):
    respx.get("https://rest.ensembl.org/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "ENSG00000141510",
                "display_name": "TP53",
                "description": "tumor protein p53",
                "biotype": "protein_coding",
                "species": "homo_sapiens",
                "seq_region_name": "17",
                "start": 7661779,
                "end": 7687546,
                "strand": -1,
                "assembly_name": "GRCh38",
            },
        )
    )
    result = await tools["gene_record"]("TP53", kind="ensembl")
    assert result["source"] == "ensembl"
    assert result["record"]["gene_id"] == "ENSG00000141510"
    assert result["source_url"].startswith("https://www.ensembl.org/Homo_sapiens/Gene/Summary")


async def test_gene_record_ensembl_unsupported_organism(tools):
    result = await tools["gene_record"]("TP53", kind="ensembl", organism=999999)
    assert result["source"] == "ensembl"
    assert "unsupported organism" in result["error"]
