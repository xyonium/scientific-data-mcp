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


async def test_guarded_tools_keep_their_input_schema():
    mcp = build_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    props = tools["chem_compound"].inputSchema["properties"]
    assert {"identifier", "id_type"} <= set(props)
    assert tools["chem_compound"].inputSchema["required"] == ["identifier"]
