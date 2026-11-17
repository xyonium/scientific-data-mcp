"""Tool modules: one per scientific domain."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..runtime import Service
from .chemistry import register as register_chemistry

ToolMap = dict[str, Callable]


def register_all(mcp: FastMCP, service: Service) -> ToolMap:
    tools: ToolMap = {}
    tools.update(register_chemistry(mcp, service))
    return tools
