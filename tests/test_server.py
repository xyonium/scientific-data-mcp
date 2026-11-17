from __future__ import annotations

from scientific_data_mcp.server import build_server


async def test_server_registers_chemistry_tools():
    mcp = build_server()
    names = {tool.name for tool in await mcp.list_tools()}
    assert {"chem_compound", "chem_compound_properties", "chem_similar_compounds"} <= names
