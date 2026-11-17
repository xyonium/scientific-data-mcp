from __future__ import annotations

from scientific_data_mcp.server import build_server

EXPECTED_TOOLS = {
    "chem_compound",
    "chem_compound_properties",
    "chem_similar_compounds",
    "chembl_search",
    "chembl_bioactivity",
    "chembl_mechanisms",
    "protein_entry",
    "protein_search",
    "protein_map_ids",
    "protein_structure",
    "protein_structure_search",
    "pubmed_record",
}


async def test_server_exposes_exactly_the_twelve_tools():
    mcp = build_server()
    assert {tool.name for tool in await mcp.list_tools()} == EXPECTED_TOOLS
