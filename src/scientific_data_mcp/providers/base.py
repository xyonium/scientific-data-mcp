"""Provider protocol: one instance per upstream source."""

from __future__ import annotations

from ..config import Settings
from ..http import PoliteClient


class Provider:
    name: str = "base"
    base_url: str = ""

    def __init__(self, http: PoliteClient, settings: Settings):
        self.http = http
        self.settings = settings

    def available(self) -> bool:
        return True


def omit_none(data: dict) -> dict:
    """Drop only None values; keep real empty lists, 0 and False."""
    return {key: value for key, value in data.items() if value is not None}
