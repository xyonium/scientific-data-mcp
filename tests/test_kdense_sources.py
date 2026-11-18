from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kdense_sources import diff_catalogs, has_set_change, parse_catalog, render_report  # noqa: E402

SAMPLE = '''---
name: database-lookup
metadata:
  version: "1.8"
  last-reviewed: "2026-09-30"
---

## Available Databases

### Chemistry & Drugs
| Database | Reference File | What it covers |
|---|---|---|
| PubChem | `references/pubchem.md` | Compounds |
| ChEMBL | `references/chembl.md` | Bioactivity |

### Materials Science
| Database | Reference File | What it covers |
|---|---|---|
| Materials Project | `references/materials-project.md` | Band gaps |

## Citing
'''


def test_parse_catalog_reads_version_and_rows():
    catalog = parse_catalog(SAMPLE)
    assert catalog["skill_version"] == "1.8"
    assert catalog["last_reviewed"] == "2026-09-30"
    assert [db["reference"] for db in catalog["databases"]] == [
        "references/pubchem.md",
        "references/chembl.md",
        "references/materials-project.md",
    ]
    assert catalog["databases"][0]["category"] == "Chemistry & Drugs"


def test_diff_detects_added_and_removed():
    old = {"skill_version": "1.7", "databases": parse_catalog(SAMPLE)["databases"][:2]}
    new = parse_catalog(SAMPLE)
    diff = diff_catalogs(old, new)
    assert [db["name"] for db in diff["added"]] == ["Materials Project"]
    assert diff["removed"] == []
    assert has_set_change(diff) is True
    report = render_report(diff, "2026-11-18")
    assert "Materials Project" in report
    assert "1.7" in report and "1.8" in report


def test_diff_without_set_change_is_quiet():
    catalog = parse_catalog(SAMPLE)
    diff = diff_catalogs(catalog, catalog)
    assert has_set_change(diff) is False
