"""Service container: settings, shared HTTP client and provider instances."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import Settings
from .http import PoliteClient
from .providers.alphafold import AlphaFoldProvider
from .providers.base import Provider
from .providers.biogrid import BioGridProvider
from .providers.chembl import ChemBLProvider
from .providers.clinicaltrials import ClinicalTrialsProvider
from .providers.clinvar import ClinVarProvider
from .providers.gene import GeneProvider
from .providers.interpro import InterProProvider
from .providers.materials_project import MaterialsProjectProvider
from .providers.openfda import OpenFdaProvider
from .providers.opentargets import OpenTargetsProvider
from .providers.pubchem import PubChemProvider
from .providers.pubmed import PubMedProvider
from .providers.quickgo import QuickGoProvider
from .providers.rcsb import RcsbProvider
from .providers.reactome import ReactomeProvider
from .providers.string_db import StringDbProvider
from .providers.uniprot import UniProtProvider
from .providers.who import WhoProvider


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
        "who": WhoProvider(http, settings),
        "string": StringDbProvider(http, settings),
        "openfda": OpenFdaProvider(http, settings),
        "clinicaltrials": ClinicalTrialsProvider(http, settings),
        "alphafold": AlphaFoldProvider(http, settings),
        "opentargets": OpenTargetsProvider(http, settings),
        "reactome": ReactomeProvider(http, settings),
        "ncbi_gene": GeneProvider(http, settings),
        "clinvar": ClinVarProvider(http, settings),
        "interpro": InterProProvider(http, settings),
        "quickgo": QuickGoProvider(http, settings),
    }
    if settings.materials_project_api_key:
        providers["materials_project"] = MaterialsProjectProvider(http, settings)
    if settings.biogrid_access_key:
        providers["biogrid"] = BioGridProvider(http, settings)
    return Service(settings=settings, http=http, providers=providers)
