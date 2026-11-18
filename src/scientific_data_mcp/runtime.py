"""Service container: settings, shared HTTP client and provider instances."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import Settings
from .http import PoliteClient
from .providers.base import Provider
from .providers.chembl import ChemBLProvider
from .providers.materials_project import MaterialsProjectProvider
from .providers.pubchem import PubChemProvider
from .providers.pubmed import PubMedProvider
from .providers.rcsb import RcsbProvider
from .providers.uniprot import UniProtProvider


@dataclass
class Service:
    settings: Settings
    http: PoliteClient
    providers: dict[str, Provider] = field(default_factory=dict)

    async def aclose(self) -> None:
        await self.http.aclose()


def build_service(settings: Settings | None = None) -> Service:
    # E-utilities carries NCBI_API_KEY in the query string (its only supported
    # place); httpx's INFO request log would print the full URL, so keep it quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = settings or Settings.from_env()
    http = PoliteClient(settings)
    providers: dict[str, Provider] = {
        "pubchem": PubChemProvider(http, settings),
        "chembl": ChemBLProvider(http, settings),
        "uniprot": UniProtProvider(http, settings),
        "rcsb": RcsbProvider(http, settings),
        "pubmed": PubMedProvider(http, settings),
    }
    if settings.materials_project_api_key:
        providers["materials_project"] = MaterialsProjectProvider(http, settings)
    return Service(settings=settings, http=http, providers=providers)
