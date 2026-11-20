from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound, UpstreamDrift, UpstreamError
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.ensembl import EnsemblProvider

BASE = "https://rest.ensembl.org"
GENE = {
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
    "canonical_transcript": "ENST00000269305.9",
    "version": 20,
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"rest.ensembl.org": 0.0})
    async with PoliteClient(settings) as client:
        yield EnsemblProvider(client, settings)


@respx.mock
async def test_symbol_lookup(provider):
    route = respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(200, json=GENE)
    )
    record = await provider.gene("TP53", "homo_sapiens")
    assert record["gene_id"] == "ENSG00000141510"
    assert record["symbol"] == "TP53"
    assert record["chromosome"] == "17"
    assert route.calls.last.request.headers["accept"] == "application/json"


@respx.mock
async def test_id_lookup_passes_species(provider):
    route = respx.get(f"{BASE}/lookup/id/ENSG00000141510").mock(
        return_value=httpx.Response(200, json=GENE)
    )
    await provider.gene("ENSG00000141510", "homo_sapiens")
    assert route.calls.last.request.url.params["species"] == "homo_sapiens"


@respx.mock
async def test_403_is_unavailable_and_not_retried(provider):
    route = respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(403, text="forbidden")
    )
    with pytest.raises(UpstreamError):
        await provider.gene("TP53", "homo_sapiens")
    assert route.call_count == 1


@respx.mock
async def test_404_is_not_found(provider):
    respx.get(f"{BASE}/lookup/symbol/homo_sapiens/NOPE").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(NotFound):
        await provider.gene("NOPE", "homo_sapiens")


@respx.mock
async def test_non_object_is_drift(provider):
    respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(200, json=["oops"])
    )
    with pytest.raises(UpstreamDrift):
        await provider.gene("TP53", "homo_sapiens")


@respx.mock
async def test_redirect_is_not_followed(provider):
    route = respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(302, headers={"Location": "https://example.org/"})
    )
    with pytest.raises(UpstreamError, match="redirect"):
        await provider.gene("TP53", "homo_sapiens")
    assert route.call_count == 1


@respx.mock
async def test_429_is_unavailable_and_not_retried(provider):
    route = respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(429)
    )
    with pytest.raises(UpstreamError):
        await provider.gene("TP53", "homo_sapiens")
    assert route.call_count == 1


def test_host_delay_is_five_seconds():
    assert Settings().host_delays["rest.ensembl.org"] == 5.0


@respx.mock
async def test_worm_stable_id_uses_lookup_id(provider):
    route = respx.get(f"{BASE}/lookup/id/WBGene00006789").mock(
        return_value=httpx.Response(200, json=GENE)
    )
    await provider.gene("WBGene00006789", "caenorhabditis_elegans")
    assert route.calls.last.request.url.params["species"] == "caenorhabditis_elegans"


@respx.mock
async def test_null_id_is_drift(provider):
    respx.get(f"{BASE}/lookup/symbol/homo_sapiens/TP53").mock(
        return_value=httpx.Response(200, json={"id": None})
    )
    with pytest.raises(UpstreamDrift):
        await provider.gene("TP53", "homo_sapiens")
