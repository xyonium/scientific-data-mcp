from __future__ import annotations

from scientific_data_mcp.server import build_server

EXPECTED_TOOLS = {
    "chem_compound",
    "chem_similar_compounds",
    "chembl_data",
    "protein_record",
    "protein_search",
    "protein_map_ids",
    "pubmed_record",
    "who_data",
    "protein_interactions",
    "openfda",
    "clinical_trials",
    "opentargets",
    "pathways",
}


MATERIALS_TOOLS = {"material"}


async def test_server_exposes_exactly_the_base_tools():
    mcp = build_server()
    assert {tool.name for tool in await mcp.list_tools()} == EXPECTED_TOOLS


async def test_server_adds_materials_tools_when_a_key_is_configured():
    from scientific_data_mcp.config import Settings
    from scientific_data_mcp.runtime import build_service

    mcp = build_server(build_service(Settings(materials_project_api_key="k")))
    names = {tool.name for tool in await mcp.list_tools()}
    assert names == EXPECTED_TOOLS | MATERIALS_TOOLS


async def test_guarded_tools_keep_their_input_schema():
    mcp = build_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    props = tools["chem_compound"].inputSchema["properties"]
    assert {"identifier", "id_type"} <= set(props)
    assert tools["chem_compound"].inputSchema["required"] == ["identifier"]


async def test_biogrid_key_does_not_add_a_tool():
    from scientific_data_mcp.config import Settings
    from scientific_data_mcp.runtime import build_service

    mcp = build_server(build_service(Settings(biogrid_access_key="k")))
    assert {tool.name for tool in await mcp.list_tools()} == EXPECTED_TOOLS


async def test_server_adds_both_key_gated_tools():
    from scientific_data_mcp.config import Settings
    from scientific_data_mcp.runtime import build_service

    service = build_service(
        Settings(materials_project_api_key="m", biogrid_access_key="b")
    )
    names = {tool.name for tool in await build_server(service).list_tools()}
    assert names == EXPECTED_TOOLS | MATERIALS_TOOLS


async def test_openfda_key_does_not_add_a_tool():
    from scientific_data_mcp.config import Settings
    from scientific_data_mcp.runtime import build_service

    mcp = build_server(build_service(Settings(openfda_api_key="k")))
    assert {tool.name for tool in await mcp.list_tools()} == EXPECTED_TOOLS
