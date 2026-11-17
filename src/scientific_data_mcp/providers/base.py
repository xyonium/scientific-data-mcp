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
