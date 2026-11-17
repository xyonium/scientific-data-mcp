"""PubMed provider via NCBI E-utilities (keyless; optional NCBI_API_KEY).

Only entity-level record lookup: pmid/doi -> one structured record. This
module deliberately offers no cross-source literature search (that is
paper-search's job).

Note: DOI resolution goes through E-utilities ``esearch`` on the same
``eutils.ncbi.nlm.nih.gov`` host rather than the PMC ID converter on
``www.ncbi.nlm.nih.gov``, which was observed timing out from this network.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..config import Settings
from ..errors import NotFound, UpstreamError
from ..http import PoliteClient
from .base import Provider, omit_none

_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_TOOL = "scientific-data-mcp"


class PubMedProvider(Provider):
    name = "pubmed"
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    def _base_params(self) -> dict:
        params: dict = {"tool": _TOOL}
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        if self.settings.ncbi_email:
            params["email"] = self.settings.ncbi_email
        return params

    async def by_pmid(self, pmid: str) -> dict:
        params = {**self._base_params(), "db": "pubmed", "id": pmid, "retmode": "xml"}
        xml = await self.http.get_text(_EFETCH, params=params)
        return parse_article(xml, pmid)

    async def by_doi(self, doi: str) -> dict:
        params = {
            **self._base_params(),
            "db": "pubmed",
            "term": f"{doi}[doi]",
            "retmode": "json",
        }
        payload = await self.http.get_json(_ESEARCH, params=params)
        ids = ((payload.get("esearchresult") or {}).get("idlist")) or []
        if not ids:
            raise NotFound(f"no PubMed record for DOI {doi!r}")
        return await self.by_pmid(str(ids[0]))


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = "".join(node.itertext()).strip()
    return value or None


def parse_article(xml: str, requested_id: str) -> dict:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise UpstreamError(f"unparseable PubMed XML: {exc}") from exc
    article = root.find(".//PubmedArticle")
    if article is None:
        raise NotFound(f"no PubMed record for {requested_id!r}")
    citation = article.find("MedlineCitation")
    if citation is None:
        raise NotFound(f"no PubMed record for {requested_id!r}")
    body = citation.find("Article")
    if body is None:
        raise NotFound(f"no PubMed record for {requested_id!r}")

    identifiers = {
        (node.get("IdType") or "").lower(): (node.text or "").strip()
        for node in article.findall("PubmedData/ArticleIdList/ArticleId")
    }
    abstract_parts = []
    for part in body.findall(".//Abstract/AbstractText"):
        text = _text(part)
        if not text:
            continue
        label = part.get("Label")
        abstract_parts.append(f"{label}: {text}" if label else text)

    authors: list[str] = []
    for author in body.findall(".//AuthorList/Author"):
        collective = author.findtext("CollectiveName")
        if collective:
            authors.append(collective.strip())
            continue
        last = (author.findtext("LastName") or "").strip()
        fore = (author.findtext("ForeName") or "").strip()
        name = " ".join(part for part in (last, fore) if part)
        if name:
            authors.append(name)

    pub_date = body.find("Journal/JournalIssue/PubDate")
    year = None
    if pub_date is not None:
        year = (pub_date.findtext("Year") or "").strip() or None
        if not year:
            medline_date = (pub_date.findtext("MedlineDate") or "").strip()
            year = medline_date[:4] if medline_date[:4].isdigit() else None

    return omit_none({
        "pmid": (citation.findtext("PMID") or requested_id).strip(),
        "doi": identifiers.get("doi") or None,
        "pmcid": identifiers.get("pmc") or None,
        "title": _text(body.find("ArticleTitle")),
        "authors": authors,
        "journal": (body.findtext("Journal/Title") or "").strip() or None,
        "year": year,
        "volume": (body.findtext("Journal/JournalIssue/Volume") or "").strip() or None,
        "issue": (body.findtext("Journal/JournalIssue/Issue") or "").strip() or None,
        "pages": (body.findtext("Pagination/MedlinePgn") or "").strip() or None,
        "abstract": " ".join(abstract_parts) or None,
    })
