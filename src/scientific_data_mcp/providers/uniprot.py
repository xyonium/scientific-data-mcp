"""UniProt provider (rest.uniprot.org, keyless).

Covers three things the upstream REST API does well: one entry, a cursor-
paginated search, and the asynchronous ID-mapping job.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import parse_qs, quote, urlparse

from ..config import Settings
from ..errors import UpstreamError
from ..http import PoliteClient
from .base import Provider

_BASE = "https://rest.uniprot.org"
_SEARCH_FIELDS = "accession,id,protein_name,gene_names,organism_name,length"
_POLL_INTERVAL = 0.5
_MAPPING_PAGE = 500


class UniProtProvider(Provider):
    name = "uniprot"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def entry(self, accession: str, include_sequence: bool = False) -> dict:
        payload = await self.http.get_json(
            f"{self.base_url}/uniprotkb/{quote(accession, safe='')}.json"
        )
        if not isinstance(payload, dict) or "primaryAccession" not in payload:
            raise UpstreamError(f"unexpected UniProt entry payload for {accession}")
        return _normalize_entry(payload, include_sequence)

    async def search(self, query: str, size: int = 10, cursor: str | None = None) -> dict:
        params: dict = {
            "query": query,
            "size": size,
            "format": "json",
            "fields": _SEARCH_FIELDS,
        }
        if cursor:
            params["cursor"] = cursor
        resp = await self.http.get_response(f"{self.base_url}/uniprotkb/search", params=params)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise UpstreamError(f"non-JSON UniProt search response: {exc}") from exc
        items = [_normalize_summary(row) for row in payload.get("results") or []]
        return {
            "items": items,
            "next_cursor": _next_cursor(resp.headers.get("link", "")),
        }

    async def map_ids(
        self, from_db: str, to_db: str, ids: str, timeout: float = 30.0
    ) -> dict:
        payload = await self.http.post_form(
            f"{self.base_url}/idmapping/run",
            {"from": from_db, "to": to_db, "ids": ids},
        )
        job_id = payload.get("jobId")
        if not job_id:
            raise UpstreamError("UniProt idmapping did not return a jobId")
        deadline = time.monotonic() + timeout
        while True:
            # The status endpoint answers 303 (+ a JSON body) once the job is
            # done; do not follow it, or the jobStatus field is lost.
            status = await self.http.get_json(
                f"{self.base_url}/idmapping/status/{job_id}", follow_redirects=False
            )
            state = status.get("jobStatus")
            if state == "FINISHED" or "results" in status:
                break
            if state in ("ERROR", "FAILED"):
                raise UpstreamError(f"UniProt idmapping job {job_id} failed: {status}")
            if time.monotonic() >= deadline:
                raise UpstreamError(f"UniProt idmapping job {job_id} timed out after {timeout:.0f}s")
            await asyncio.sleep(_POLL_INTERVAL)
        results = await self.http.get_json(
            f"{self.base_url}/idmapping/results/{job_id}", params={"size": _MAPPING_PAGE}
        )
        mappings: dict[str, list[str]] = {}
        for row in results.get("results") or []:
            src = row.get("from")
            dst = row.get("to")
            if src and dst:
                mappings.setdefault(src, []).append(dst)
        return {"job_id": job_id, "mappings": mappings}


def _protein_name(row: dict) -> str | None:
    desc = row.get("proteinDescription") or {}
    recommended = (desc.get("recommendedName") or {}).get("fullName") or {}
    if recommended.get("value"):
        return recommended["value"]
    for submission in desc.get("submissionNames") or []:
        value = (submission.get("fullName") or {}).get("value")
        if value:
            return value
    return None


def _genes(row: dict) -> list[str]:
    names = []
    for gene in row.get("genes") or []:
        name = (gene.get("geneName") or {}).get("value")
        if name:
            names.append(name)
    return names


def _organism(row: dict) -> tuple[str | None, int | None]:
    organism = row.get("organism") or {}
    return organism.get("scientificName"), organism.get("taxonId")


def _sequence_length(row: dict) -> int | None:
    return (row.get("sequence") or {}).get("length")


def _is_reviewed(row: dict) -> bool:
    return str(row.get("entryType", "")).startswith("UniProtKB reviewed")


def _normalize_summary(row: dict) -> dict:
    name, taxid = _organism(row)
    return {
        "accession": row.get("primaryAccession"),
        "entry_name": row.get("uniProtkbId"),
        "protein_name": _protein_name(row),
        "genes": _genes(row),
        "organism": name,
        "taxid": taxid,
        "reviewed": _is_reviewed(row),
        "sequence_length": _sequence_length(row),
    }


def _normalize_entry(row: dict, include_sequence: bool) -> dict:
    out = _normalize_summary(row)
    sequence = row.get("sequence") or {}
    out["sequence_mass"] = sequence.get("molWeight")
    out["function"] = " ".join(
        text["value"]
        for comment in row.get("comments") or []
        if comment.get("commentType") == "FUNCTION"
        for text in comment.get("texts") or []
        if text.get("value")
    ) or None
    out["keywords"] = [
        keyword["name"] for keyword in row.get("keywords") or [] if keyword.get("name")
    ]
    pdb_ids: list[str] = []
    for cross_ref in row.get("uniProtKBCrossReferences") or []:
        if cross_ref.get("database") == "PDB" and cross_ref.get("id"):
            if cross_ref["id"] not in pdb_ids:
                pdb_ids.append(cross_ref["id"])
    out["pdb_ids"] = pdb_ids
    if include_sequence and sequence.get("value"):
        out["sequence"] = sequence["value"]
    return out


def _next_cursor(link_header: str) -> str | None:
    """Extract the cursor from the RFC 5988 ``rel="next"`` link."""
    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        start = part.find("<")
        end = part.find(">", start + 1)
        if start < 0 or end < 0:
            continue
        query = parse_qs(urlparse(part[start + 1 : end]).query)
        cursor = (query.get("cursor") or [None])[0]
        if cursor:
            return cursor
    return None
