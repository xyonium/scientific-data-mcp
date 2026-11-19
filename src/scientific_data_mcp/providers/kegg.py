"""KEGG provider (keyless for academic use; commercial use needs a license)."""

from __future__ import annotations

import re
from urllib.parse import quote

from ..config import Settings
from ..errors import NotFound, UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://rest.kegg.jp"
_COMPOUND_ID = re.compile(r"^C\d{5}$")
_PATHWAY = re.compile(r"^((?:map|hsa|mmu|rno|dme|cel|sce|ath)\d+)\s+(.+)$")


class KeggProvider(Provider):
    name = "kegg"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def compound(self, query: str, limit: int = 3) -> list[dict]:
        if _COMPOUND_ID.match(query):
            entries = [query]
        else:
            entries = await self._find(query, limit)
            if not entries:
                return []
        results = []
        for entry in entries:
            text = await self.http.get_text(f"{self.base_url}/get/cpd:{entry}")
            if not text.strip():
                raise NotFound(f"no KEGG compound record for {entry}")
            results.append(_parse_compound(text))
        return results

    async def _find(self, query: str, limit: int) -> list[str]:
        text = await self.http.get_text(
            f"{self.base_url}/find/compound/{quote(query, safe='')}"
        )
        if not text.strip():
            return []
        entries = []
        for line in text.splitlines():
            if not line.strip():
                continue
            if "\t" not in line:
                raise UpstreamDrift(f"unexpected KEGG find line: {line[:80]!r}")
            entry = line.split("\t", 1)[0].strip()
            if not _COMPOUND_ID.match(entry):
                raise UpstreamDrift(f"unexpected KEGG compound id: {entry!r}")
            entries.append(entry)
            if len(entries) >= limit:
                break
        return entries


def _parse_compound(text: str) -> dict:
    blocks = [block for block in text.split("///") if block.strip()]
    if len(blocks) != 1:
        raise UpstreamDrift(
            f"KEGG compound response has {len(blocks)} records, expected 1"
        )
    text = blocks[0]
    fields: dict[str, list[str]] = {}
    pathways_raw: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith(" "):
            if current == "PATHWAY":
                pathways_raw.append(line.strip())
            elif current:
                fields[current][-1] += " " + line.strip()
            continue
        key = line[:12].strip()
        value = line[12:].strip()
        if not key:
            continue
        current = key
        fields.setdefault(key, []).append(value)
        if key == "PATHWAY":
            pathways_raw.append(value)
    if "ENTRY" not in fields:
        raise UpstreamDrift("KEGG compound response has no ENTRY")
    entry = fields["ENTRY"][0].split()[0]
    names: list[str] = []
    for value in fields.get("NAME", []):
        names.extend(part.strip() for part in value.split(";") if part.strip())
    pathways = []
    for value in pathways_raw:
        match = _PATHWAY.match(value)
        if match:
            pathways.append({"id": match.group(1), "name": match.group(2)})
    return omit_none(
        {
            "entry": entry,
            "names": names or None,
            "formula": fields.get("FORMULA", [None])[0],
            "exact_mass": fields.get("EXACT_MASS", [None])[0],
            "mol_weight": fields.get("MOL_WEIGHT", [None])[0],
            "pathways": pathways or None,
        }
    )
