"""Service container: settings, shared HTTP client and provider instances."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import Settings
from .http import PoliteClient
from .providers.alphafold import AlphaFoldProvider
from .providers.base import Provider
from .providers.bindingdb import BindingDbProvider
from .providers.biogrid import BioGridProvider
from .providers.cbioportal import CbioPortalProvider
from .providers.chebi import ChebiProvider
from .providers.chembl import ChemBLProvider
from .providers.clinicaltrials import ClinicalTrialsProvider
from .providers.clinpgx import ClinPgxProvider
from .providers.clinvar import ClinVarProvider
from .providers.cod import CodProvider
from .providers.dailymed import DailyMedProvider
from .providers.ensembl import EnsemblProvider
from .providers.gdc import GdcProvider
from .providers.gene import GeneProvider
from .providers.geo import GeoProvider
from .providers.gtex import GtexProvider
from .providers.gwas import GwasProvider
from .providers.hpo import HpoProvider
from .providers.interpro import InterProProvider
from .providers.kegg import KeggProvider
from .providers.materials_project import MaterialsProjectProvider
from .providers.monarch import MonarchProvider
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
        "hpo": HpoProvider(http, settings),
        "geo": GeoProvider(http, settings),
        "kegg": KeggProvider(http, settings),
        "dailymed": DailyMedProvider(http, settings),
        "gdc": GdcProvider(http, settings),
        "cbioportal": CbioPortalProvider(http, settings),
        "gtex": GtexProvider(http, settings),
        "ensembl": EnsemblProvider(http, settings),
        "chebi": ChebiProvider(http, settings),
        "bindingdb": BindingDbProvider(http, settings),
        "gwas": GwasProvider(http, settings),
        "monarch": MonarchProvider(http, settings),
        "clinpgx": ClinPgxProvider(http, settings),
        "cod": CodProvider(http, settings),
    }
    if settings.materials_project_api_key:
        providers["materials_project"] = MaterialsProjectProvider(http, settings)
    if settings.biogrid_access_key:
        providers["biogrid"] = BioGridProvider(http, settings)
    return Service(settings=settings, http=http, providers=providers)
