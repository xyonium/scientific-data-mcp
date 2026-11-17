from __future__ import annotations

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools.literature import register

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID>
<Article><ArticleTitle>T</ArticleTitle><AuthorList><Author><LastName>Doe</LastName>
<ForeName>Jane</ForeName></Author></AuthorList>
<Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue><Title>J</Title></Journal>
</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""


@pytest.fixture
async def tools():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0})
    service = build_service(settings)
    registered = register(FastMCP("test"), service)
    yield registered
    await service.aclose()


async def test_pubmed_record_requires_exactly_one_identifier(tools):
    both = await tools["pubmed_record"](pmid="1", doi="10.1/x")
    neither = await tools["pubmed_record"]()
    assert "exactly one" in both["error"]
    assert "exactly one" in neither["error"]


@respx.mock
async def test_pubmed_record_envelope(tools):
    respx.get(EFETCH).mock(return_value=httpx.Response(200, text=XML))
    result = await tools["pubmed_record"](pmid="1")
    assert result["source"] == "pubmed"
    assert result["source_url"] == "https://pubmed.ncbi.nlm.nih.gov/1/"
    assert result["record"]["authors"] == ["Doe Jane"]


@respx.mock
async def test_pubmed_record_upstream_error_is_a_dict(tools):
    respx.get(EFETCH).mock(return_value=httpx.Response(500))
    result = await tools["pubmed_record"](pmid="1")
    assert result["source"] == "pubmed"
    assert "unavailable" in result["error"]


@respx.mock
async def test_pubmed_record_unknown_doi_is_not_found(tools):
    respx.get(ESEARCH).mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
    )
    result = await tools["pubmed_record"](doi="10.9999/nope")
    assert "not_found" in result["error"]
