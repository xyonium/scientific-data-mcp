from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.pubmed import PubMedProvider, parse_article

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

ARTICLE_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>23903748</PMID>
      <Article>
        <ArticleTitle>Nanometre-scale thermometry in a <i>living</i> cell.</ArticleTitle>
        <Abstract>
          <AbstractText Label="Background">Sensitive probing of temperature.</AbstractText>
          <AbstractText>We demonstrate a new approach.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Kucsko</LastName><ForeName>G</ForeName></Author>
          <Author><CollectiveName>Thermo Consortium</CollectiveName></Author>
        </AuthorList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2013</Year></PubDate>
            <Volume>500</Volume>
            <Issue>7460</Issue>
          </JournalIssue>
          <Title>Nature</Title>
        </Journal>
        <Pagination><MedlinePgn>54-8</MedlinePgn></Pagination>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">23903748</ArticleId>
        <ArticleId IdType="doi">10.1038/nature12373</ArticleId>
        <ArticleId IdType="pmc">PMC4221854</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"eutils.ncbi.nlm.nih.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield PubMedProvider(client, settings)


def test_parse_article_extracts_scoped_identifiers():
    record = parse_article(ARTICLE_XML, "23903748")
    assert record["doi"] == "10.1038/nature12373"
    assert record["pmcid"] == "PMC4221854"
    assert record["authors"] == ["Kucsko G", "Thermo Consortium"]
    assert record["abstract"] == (
        "Background: Sensitive probing of temperature. We demonstrate a new approach."
    )
    assert record["title"] == "Nanometre-scale thermometry in a living cell."
    assert record["year"] == "2013"
    assert record["pages"] == "54-8"


def test_parse_article_without_record_raises_not_found():
    with pytest.raises(NotFound):
        parse_article("<PubmedArticleSet/>", "999")


@respx.mock
async def test_by_pmid_requests_xml(provider):
    route = respx.get(EFETCH).mock(return_value=httpx.Response(200, text=ARTICLE_XML))
    record = await provider.by_pmid("23903748")
    assert record["pmid"] == "23903748"
    assert route.calls.last.request.url.params["retmode"] == "xml"
    assert route.calls.last.request.url.params["db"] == "pubmed"


@respx.mock
async def test_by_doi_resolves_through_esearch(provider):
    respx.get(ESEARCH).mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": ["23903748"]}})
    )
    respx.get(EFETCH).mock(return_value=httpx.Response(200, text=ARTICLE_XML))
    record = await provider.by_doi("10.1038/nature12373")
    assert record["pmid"] == "23903748"


@respx.mock
async def test_unknown_doi_raises_not_found(provider):
    respx.get(ESEARCH).mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    with pytest.raises(NotFound):
        await provider.by_doi("10.9999/nope.9999")


@respx.mock
async def test_api_key_is_sent_when_configured():
    settings = Settings(
        ncbi_api_key="secret", host_delays={"eutils.ncbi.nlm.nih.gov": 0.0}
    )
    async with PoliteClient(settings) as client:
        provider = PubMedProvider(client, settings)
        route = respx.get(EFETCH).mock(return_value=httpx.Response(200, text=ARTICLE_XML))
        await provider.by_pmid("23903748")
        assert route.calls.last.request.url.params["api_key"] == "secret"


@respx.mock
async def test_email_is_sent_when_configured():
    settings = Settings(
        ncbi_email="eli@example.com", host_delays={"eutils.ncbi.nlm.nih.gov": 0.0}
    )
    async with PoliteClient(settings) as client:
        provider = PubMedProvider(client, settings)
        route = respx.get(EFETCH).mock(return_value=httpx.Response(200, text=ARTICLE_XML))
        await provider.by_pmid("23903748")
        assert route.calls.last.request.url.params["email"] == "eli@example.com"
