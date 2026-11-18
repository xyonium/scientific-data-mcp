"""Tool registration guard: no exception may escape a tool call."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..errors import DRIFT_HINT, ProviderError, UpstreamDrift, tool_error


def guarded_tool(
    mcp: FastMCP, *, name: str, source: str
) -> Callable[[Callable[..., Awaitable[dict]]], Callable[..., Awaitable[dict]]]:
    """Register ``fn`` as an MCP tool whose every failure becomes an error dict.

    Provider errors keep their kind prefix; validation ValueErrors keep their
    message; anything else is reported as ``unexpected <Type>: <message>``.
    ``asyncio.CancelledError`` is a BaseException and is deliberately not
    caught.
    """

    def decorate(fn: Callable[..., Awaitable[dict]]):
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> dict:
            try:
                return await fn(*args, **kwargs)
            except UpstreamDrift as exc:
                return tool_error(
                    f"{exc.kind}: {exc}",
                    hint=DRIFT_HINT,
                    suspect_drift=True,
                    source=source,
                )
            except ProviderError as exc:
                return tool_error(f"{exc.kind}: {exc}", source=source)
            except ValueError as exc:
                return tool_error(str(exc), source=source)
            except Exception as exc:  # noqa: BLE001 - the whole point of the guard
                # A shape/attribute/type error escaping the adapter usually
                # means the upstream payload changed.
                return tool_error(
                    f"unexpected {type(exc).__name__}: {exc}",
                    hint=DRIFT_HINT,
                    suspect_drift=True,
                    source=source,
                )

        mcp.tool(name=name)(wrapper)
        return wrapper

    return decorate
