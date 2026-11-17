"""scientific-data-mcp — free, keyless scientific entity data over MCP."""

from __future__ import annotations

__all__ = ["__version__"]

try:  # installed package metadata (hatch-vcs derives it from the git tag)
    from importlib.metadata import version as _version

    __version__ = _version("scientific-data-mcp")
except Exception:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"
