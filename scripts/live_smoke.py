"""Live smoke test: one real call per tool against the five upstream APIs.

Not part of CI and not run by pytest (it makes real network calls). Run it
manually, ideally once or twice per session:

    python scripts/live_smoke.py

Exit code 0 only when all 12 tools return a payload without an "error" key.
"""

from __future__ import annotations

import asyncio
import sys
import time

from mcp.server.fastmcp import FastMCP

from scientific_data_mcp.config import Settings
from scientific_data_mcp.runtime import build_service
from scientific_data_mcp.tools import register_all

CASES: list[tuple[str, dict, str]] = [
    ("chem_compound", {"identifier": "aspirin"}, "record"),
    ("chem_compound_properties", {"cid": 2244, "properties": ["MolecularFormula", "XLogP"]}, "record"),
    (
        "chem_similar_compounds",
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "threshold": 95, "max_records": 3},
        "count",
    ),
    ("chembl_search", {"query": "imatinib", "resource": "molecule", "limit": 2}, "count"),
    ("chembl_bioactivity", {"chembl_id": "CHEMBL941", "limit": 2}, "count"),
    ("chembl_mechanisms", {"chembl_id": "CHEMBL1642"}, "count"),
    ("protein_entry", {"accession": "P05067"}, "record"),
    ("protein_search", {"query": "gene:APP AND organism_id:9606", "size": 2}, "count"),
    ("protein_map_ids", {"from_db": "UniProtKB_AC-ID", "to_db": "PDB", "ids": "P04637"}, "count"),
    ("protein_structure", {"pdb_id": "4HHB"}, "record"),
    ("protein_structure_search", {"query": "hemoglobin", "rows": 2}, "total"),
    ("pubmed_record", {"pmid": "23903748"}, "record"),
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
