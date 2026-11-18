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


class UpstreamDrift(ProviderError):
    """The upstream response no longer matches this adapter's contract.

    Not retryable: repeating the same request will not help. Tools surface it
    with ``suspect_drift`` so the model tells the user to contact the
    administrator instead of retrying blindly.
    """

    kind = "upstream_drift"
    retryable = False
    contact_admin = True


DRIFT_HINT = (
    "上游返回与适配器预期不一致（接口可能已漂移）。不要用相同参数重试；"
    "请告知用户联系管理员更新对应 provider。"
)


def tool_error(
    msg: object,
    hint: str | None = None,
    *,
    suspect_drift: bool = False,
    **extra: object,
) -> dict:
    """Build the single error shape every tool returns."""
    out: dict = {"error": str(msg)}
    if hint:
        out["hint"] = hint
    if suspect_drift:
        out["suspect_drift"] = True
        out["action"] = "contact_admin"
    out.update(extra)
    return out


def scrub(text: str, *secrets: str) -> str:
    """Remove known secrets from a message before it reaches the model."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text
