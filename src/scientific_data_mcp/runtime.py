"""Service container: settings, shared HTTP client and provider instances."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .http import PoliteClient
from .providers.base import Provider
from .providers.pubchem import PubChemProvider


@dataclass
class Service:
    settings: Settings
    http: PoliteClient
    providers: dict[str, Provider] = field(default_factory=dict)

    async def aclose(self) -> None:
        await self.http.aclose()


def build_service(settings: Settings | None = None) -> Service:
    settings = settings or Settings.from_env()
    http = PoliteClient(settings)
    providers: dict[str, Provider] = {
        "pubchem": PubChemProvider(http, settings),
    }
    return Service(settings=settings, http=http, providers=providers)
