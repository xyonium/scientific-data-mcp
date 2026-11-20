"""ChEBI provider via EBI OLS4 (keyless)."""

from __future__ import annotations

import re

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://www.ebi.ac.uk/ols4/api"
_CHEBI_ID = re.compile(r"^CHEBI[:_](\d+)$", re.IGNORECASE)


class ChebiProvider(Provider):
    name = "chebi"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        payload = await self.http.get_json(
            f"{self.base_url}/search",
            params={"q": query, "ontology": "chebi", "rows": limit},
        )
        try:
            docs = payload["response"]["docs"]
        except (KeyError, TypeError) as exc:
            raise UpstreamDrift("ChEBI search response has no docs") from exc
        return [_normalize_search(doc) for doc in docs or []]

    async def term(self, chebi_id: str) -> dict:
        match = _CHEBI_ID.match(chebi_id.strip())
        if not match:
            raise ValueError(f"invalid ChEBI id: {chebi_id!r}")
        number = match.group(1)
        iri = f"http://purl.obolibrary.org/obo/CHEBI_{number}"
        payload = await self.http.get_json(
            f"{self.base_url}/ontologies/chebi/terms", params={"iri": iri}
        )
        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        if not isinstance(embedded, dict):
            raise UpstreamDrift("ChEBI term response has no _embedded object")
        terms = embedded.get("terms")
        if not isinstance(terms, list):
            raise UpstreamDrift("ChEBI term response has no terms list")
        if not terms:
            raise NotFound(f"no ChEBI term for {chebi_id}")
        term = terms[0]
        if not isinstance(term, dict):
            raise UpstreamDrift("ChEBI term entry is not an object")
        return _normalize_term(term)


def _normalize_search(doc: dict) -> dict:
    return omit_none(
        {
            "chebi_id": doc.get("obo_id"),
            "name": doc.get("label"),
            "description": (doc.get("description") or [None])[0],
            "synonyms": doc.get("synonyms") or None,
            "type": doc.get("type"),
        }
    )


def _normalize_term(term: dict) -> dict:
    return omit_none(
        {
            "chebi_id": term.get("obo_id"),
            "name": term.get("label"),
            "description": (term.get("description") or [None])[0],
            "synonyms": term.get("synonyms") or None,
            "is_obsolete": term.get("is_obsolete"),
        }
    )
