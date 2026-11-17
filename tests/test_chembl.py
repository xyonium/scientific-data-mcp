from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.chembl import ChemBLProvider

BASE = "https://www.ebi.ac.uk/chembl/api/data"

MOLECULE = {
    "molecule_chembl_id": "CHEMBL25",
    "pref_name": "ASPIRIN",
    "molecule_type": "Small molecule",
    "max_phase": 4.0,
    "molecule_structures": {
        "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "isomeric_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    },
    "molecule_properties": {"mw_freebase": 180.16, "alogp": 1.31, "hba": 4, "hbd": 1},
}


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"www.ebi.ac.uk": 0.0})
    async with PoliteClient(settings) as client:
        yield ChemBLProvider(client, settings)


@respx.mock
async def test_molecule_normalizes_structures_and_properties(provider):
    respx.get(f"{BASE}/molecule/CHEMBL25.json").mock(return_value=httpx.Response(200, json=MOLECULE))
    record = await provider.molecule("CHEMBL25")
    assert record["pref_name"] == "ASPIRIN"
    assert record["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert record["mw_freebase"] == 180.16
    assert "first_approval" not in record


@respx.mock
async def test_search_uses_documented_search_endpoint(provider):
    route = respx.get(f"{BASE}/molecule/search.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "molecules": [MOLECULE],
                "page_meta": {"limit": 2, "offset": 0, "total_count": 5, "next": None},
            },
        )
    )
    page = await provider.search("molecule", "imatinib", limit=2, offset=0)
    assert route.calls.last.request.url.params["q"] == "imatinib"
    assert page["total"] == 5
    assert page["next_offset"] is None
    assert page["items"][0]["molecule_chembl_id"] == "CHEMBL25"


@respx.mock
async def test_search_next_offset_when_more_pages(provider):
    respx.get(f"{BASE}/target/search.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "targets": [{"target_chembl_id": "CHEMBL1862", "pref_name": "ABL1"}],
                "page_meta": {"limit": 1, "offset": 0, "total_count": 9, "next": "x"},
            },
        )
    )
    page = await provider.search("target", "ABL1", limit=1, offset=0)
    assert page["next_offset"] == 1


@respx.mock
async def test_activities_filter_by_molecule(provider):
    route = respx.get(f"{BASE}/activity.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "activities": [
                    {
                        "activity_id": 1,
                        "molecule_chembl_id": "CHEMBL941",
                        "target_chembl_id": "CHEMBL1862",
                        "standard_type": "IC50",
                        "standard_value": 40.0,
                        "standard_units": "nM",
                        "pchembl_value": 7.4,
                    }
                ],
                "page_meta": {"limit": 20, "offset": 0, "total_count": 1, "next": None},
            },
        )
    )
    page = await provider.activities("CHEMBL941", None, limit=20, offset=0)
    assert route.calls.last.request.url.params["molecule_chembl_id"] == "CHEMBL941"
    assert "target_chembl_id" not in route.calls.last.request.url.params
    assert page["items"][0]["pchembl_value"] == 7.4


@respx.mock
async def test_mechanisms_are_trimmed(provider):
    respx.get(f"{BASE}/mechanism.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "mechanisms": [
                    {
                        "molecule_chembl_id": "CHEMBL1642",
                        "target_chembl_id": "CHEMBL1862",
                        "mechanism_of_action": "Tyrosine-protein kinase ABL inhibitor",
                        "action_type": "INHIBITOR",
                        "direct_interaction": True,
                        "molecule_name": "IMATINIB MESYLATE",
                    }
                ]
            },
        )
    )
    rows = await provider.mechanisms("CHEMBL1642")
    assert rows == [
        {
            "molecule_chembl_id": "CHEMBL1642",
            "target_chembl_id": "CHEMBL1862",
            "mechanism_of_action": "Tyrosine-protein kinase ABL inhibitor",
            "action_type": "INHIBITOR",
            "direct_interaction": True,
        }
    ]


@respx.mock
async def test_mechanisms_follow_all_pages(provider):
    route = respx.get(f"{BASE}/mechanism.json").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "mechanisms": [{"molecule_chembl_id": "M1", "mechanism_of_action": "a"}],
                    "page_meta": {"limit": 1000, "offset": 0, "total_count": 2, "next": "x"},
                },
            ),
            httpx.Response(
                200,
                json={
                    "mechanisms": [{"molecule_chembl_id": "M1", "mechanism_of_action": "b"}],
                    "page_meta": {"limit": 1000, "offset": 1, "total_count": 2, "next": None},
                },
            ),
        ]
    )
    rows = await provider.mechanisms("CHEMBL1")
    assert [r["mechanism_of_action"] for r in rows] == ["a", "b"]
    assert route.call_count == 2
