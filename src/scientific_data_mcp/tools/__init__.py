"""Tool modules: one per scientific domain."""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..runtime import Service
from .annotations import register as register_annotations
from .biology import register as register_biology
from .chemistry import register as register_chemistry
from .clinical import register as register_clinical
from .datasets import register as register_datasets
from .genomics import register as register_genomics
from .interactions import register as register_interactions
from .literature import register as register_literature
from .materials import register as register_materials
from .ontology import register as register_ontology
from .protein import register as register_protein
from .who import register as register_who

ToolMap = dict[str, Callable]


def register_all(mcp: FastMCP, service: Service) -> ToolMap:
    tools: ToolMap = {}
    tools.update(register_chemistry(mcp, service))
    tools.update(register_protein(mcp, service))
    tools.update(register_literature(mcp, service))
    tools.update(register_materials(mcp, service))
    tools.update(register_interactions(mcp, service))
    tools.update(register_clinical(mcp, service))
    tools.update(register_biology(mcp, service))
    tools.update(register_genomics(mcp, service))
    tools.update(register_annotations(mcp, service))
    tools.update(register_ontology(mcp, service))
    tools.update(register_datasets(mcp, service))
    tools.update(register_who(mcp, service))
    return tools
