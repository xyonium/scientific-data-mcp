"""Live smoke test: one real call per tool against the upstream APIs.

Not part of CI and not run by pytest (it makes real network calls). Run it
manually, ideally once or twice per session:

    python scripts/live_smoke.py

Exit code 0 only when every enabled tool returns a payload without an "error" key.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools import register_all

CASES: list[tuple[str, dict, str]] = [
    ("chem_compound", {"identifier": "aspirin"}, "record"),
    (
        "chem_compound",
        {"identifier": "aspirin", "properties": ["MolecularFormula", "XLogP"]},
        "record",
    ),
    (
        "chem_similar_compounds",
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "threshold": 95, "max_records": 3},
        "count",
    ),
    ("chembl_data", {"kind": "search", "query": "imatinib", "limit": 2}, "count"),
    ("chembl_data", {"kind": "activities", "chembl_id": "CHEMBL941", "limit": 2}, "count"),
    ("chembl_data", {"kind": "mechanisms", "chembl_id": "CHEMBL1642"}, "count"),
    ("protein_record", {"kind": "uniprot", "identifier": "P05067"}, "record"),
    ("protein_record", {"kind": "pdb", "identifier": "4HHB"}, "record"),
    ("protein_search", {"kind": "uniprot", "query": "gene:APP AND organism_id:9606", "size": 2}, "count"),
    ("protein_search", {"kind": "pdb", "query": "hemoglobin", "size": 2}, "count"),
    ("protein_map_ids", {"from_db": "UniProtKB_AC-ID", "to_db": "PDB", "ids": "P04637"}, "count"),
    ("pubmed_record", {"pmid": "23903748"}, "record"),
    ("who_data", {"indicator": "WHOSIS_000001", "country": "CHN", "year": 2022, "limit": 2}, "count"),
    ("protein_interactions", {"genes": "TP53", "source": "string", "limit": 2}, "count"),
    ("openfda", {"query": 'openfda.brand_name:"advil"', "limit": 1}, "count"),
    ("clinical_trials", {"query": "pembrolizumab", "limit": 1}, "count"),
    ("protein_record", {"kind": "alphafold", "identifier": "P04637"}, "record"),
    ("opentargets", {"query": "TP53", "entity": "target", "limit": 2}, "count"),
    ("pathways", {"query": "TP53", "limit": 2}, "count"),
]

if os.environ.get("BIOGRID_ACCESS_KEY", "").strip():
    CASES += [
        ("protein_interactions", {"genes": "TP53", "source": "biogrid", "limit": 2}, "count")
    ]

if os.environ.get("MATERIALS_PROJECT_API_KEY", "").strip():
    CASES += [
        ("material", {"by": "id", "query": "mp-149"}, "count"),
        ("material", {"by": "formula", "query": "SiO2", "limit": 2}, "count"),
    ]


def _summarize(result: dict) -> str:
    if "error" in result:
        return f"ERROR: {result['error']}"
    if "record" in result:
        keys = ", ".join(list(result["record"])[:5])
        return f"record[{keys}]"
    if "count" in result:
        return f"count={result['count']}"
    if "total" in result:
        return f"total={result['total']}"
    return "ok"


async def main() -> int:
    service = build_service(Settings.from_env())
    tools = register_all(FastMCP("live-smoke"), service)
    failures = 0
    try:
        for name, kwargs, _ in CASES:
            started = time.monotonic()
            try:
                result = await tools[name](**kwargs)
            except Exception as exc:  # noqa: BLE001 - smoke harness must keep going
                result = {"error": f"{type(exc).__name__}: {exc}"}
            elapsed = time.monotonic() - started
            status = "FAIL" if "error" in result else "PASS"
            if status == "FAIL":
                failures += 1
            print(f"{status}  {name:<28} {elapsed:6.2f}s  {_summarize(result)}")
    finally:
        await service.aclose()
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
