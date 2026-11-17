"""Error taxonomy and the never-raise tool-error dict.

Tools never raise: every provider failure is translated here into
``{"error": ..., "source": ..., "hint"?: ...}`` so one bad upstream call
cannot abort an agent turn.
"""

from __future__ import annotations


class ProviderError(Exception):
    kind = "error"
    retryable = False


class RateLimited(ProviderError):
    kind = "rate_limited"
    retryable = True


class AuthError(ProviderError):
    kind = "auth"


class NotFound(ProviderError):
    kind = "not_found"


class UpstreamError(ProviderError):
    kind = "unavailable"
    retryable = True


def tool_error(msg: object, hint: str | None = None, **extra: object) -> dict:
    """Build the single error shape every tool returns."""
    out: dict = {"error": str(msg)}
    if hint:
        out["hint"] = hint
    out.update(extra)
    return out


def scrub(text: str, *secrets: str) -> str:
    """Remove known secrets from a message before it reaches the model."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text
