from __future__ import annotations

import httpx
import pytest
import respx

from scientific_data_mcp.config import Settings
from scientific_data_mcp.errors import NotFound
from scientific_data_mcp.http import PoliteClient
from scientific_data_mcp.providers.pubchem import PubChemProvider

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPS = (
    "MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES,IsomericSMILES,"
    "InChIKey,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,"
    "HeavyAtomCount,Charge,Complexity"
)


@pytest.fixture
async def provider():
    settings = Settings(host_delays={"pubchem.ncbi.nlm.nih.gov": 0.0})
    async with PoliteClient(settings) as client:
        yield PubChemProvider(client, settings)


@respx.mock
async def test_resolve_cid_by_name(provider):
    respx.get(f"{BASE}/compound/name/aspirin/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [2244]}})
    )
    assert await provider.resolve_cid("aspirin", "name") == 2244


@respx.mock
async def test_resolve_cid_by_smiles_uses_post_form(provider):
    route = respx.post(f"{BASE}/compound/smiles/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [2244]}})
    )
    assert await provider.resolve_cid("CC(=O)Oc1ccccc1C(=O)O", "smiles") == 2244
    assert b"smiles=CC%28%3DO%29Oc1ccccc1C%28%3DO%29O" in route.calls.last.request.content


@respx.mock
async def test_properties_normalizes_and_omits_missing(provider):
    respx.get(f"{BASE}/compound/cid/2244/property/{PROPS}/JSON").mock(
        return_value=httpx.Response(
            200,
            json={
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 2244,
                            "MolecularFormula": "C9H8O4",
                            "MolecularWeight": "180.16",
                            "XLogP": 1.2,
                        }
                    ]
                }
            },
        )
    )
    props = await provider.properties(2244)
    assert props == {
        "molecular_formula": "C9H8O4",
        "molecular_weight": "180.16",
        "xlogp": 1.2,
    }


@respx.mock
async def test_synonyms_are_capped(provider):
    respx.get(f"{BASE}/compound/cid/2244/synonyms/JSON").mock(
        return_value=httpx.Response(
            200,
            json={
                "InformationList": {
                    "Information": [{"CID": 2244, "Synonym": ["ASPIRIN", "ACETYLSALICYLIC ACID"]}]
                }
            },
        )
    )
    assert await provider.synonyms(2244, limit=1) == ["ASPIRIN"]


@respx.mock
async def test_unknown_name_raises_not_found(provider):
    respx.get(f"{BASE}/compound/name/nope/cids/JSON").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFound):
        await provider.resolve_cid("nope", "name")


@respx.mock
async def test_similarity_polls_listkey(provider):
    respx.post(f"{BASE}/compound/similarity/smiles/JSON").mock(
        return_value=httpx.Response(202, json={"Waiting": {"ListKey": "k1"}})
    )
    respx.get(f"{BASE}/compound/listkey/k1/cids/JSON").mock(
        return_value=httpx.Response(200, json={"IdentifierList": {"CID": [2244, 4133]}})
    )
    cids = await provider.similar_cids("CC(=O)Oc1ccccc1C(=O)O", threshold=95, max_records=5)
    assert cids == [2244, 4133]


async def test_unknown_id_type_raises_value_error(provider):
    with pytest.raises(ValueError, match="id_type"):
        await provider.resolve_cid("x", "foo")
