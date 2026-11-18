"""Tool modules: one per scientific domain."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..runtime import Service
from .chemistry import register as register_chemistry
from .literature import register as register_literature
from .materials import register as register_materials
from .protein import register as register_protein

ToolMap = dict[str, Callable]


def register_all(mcp: FastMCP, service: Service) -> ToolMap:
    tools: ToolMap = {}
    tools.update(register_chemistry(mcp, service))
    tools.update(register_protein(mcp, service))
    tools.update(register_literature(mcp, service))
    tools.update(register_materials(mcp, service))
    return tools
