"""Runtime settings.

The twenty-three base upstream sources work without configuration; ``NCBI_API_KEY``
and ``OPENFDA_API_KEY`` are optional and only lift rate limits. Materials
Project and BioGRID are key-gated: their providers are only created when
their keys are present (the ``material`` tool appears only with MP; the
shared ``protein_interactions`` tool stays available for STRING).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_USER_AGENT = (
    "scientific-data-mcp/0.1 (+https://github.com/xyonium/scientific-data-mcp)"
)

# Per-host minimum gap between requests. Values follow each API's published
# politeness guidance (NCBI 3/s without a key, PubChem <=5/s, ChEMBL moderate).
HOST_DELAYS: dict[str, float] = {
    "pubchem.ncbi.nlm.nih.gov": 0.2,
    "www.ebi.ac.uk": 0.5,
    "rest.uniprot.org": 0.2,
    "data.rcsb.org": 0.2,
    "search.rcsb.org": 0.5,
    "eutils.ncbi.nlm.nih.gov": 0.34,
    "www.ncbi.nlm.nih.gov": 0.34,
    "api.materialsproject.org": 1.0,
    "ghoapi.azureedge.net": 0.5,
    "webservice.thebiogrid.org": 1.0,
    "string-db.org": 0.5,
    "api.fda.gov": 0.5,
    "clinicaltrials.gov": 0.5,
    "alphafold.ebi.ac.uk": 0.5,
    "api.platform.opentargets.org": 0.5,
    "reactome.org": 0.5,
    "ontology.jax.org": 0.5,
    "rest.kegg.jp": 0.5,
    "dailymed.nlm.nih.gov": 0.5,
    "api.gdc.cancer.gov": 0.5,
    "www.cbioportal.org": 0.5,
    "gtexportal.org": 0.5,
}


@dataclass
class Settings:
    ncbi_api_key: str | None = None
    ncbi_email: str | None = None
    materials_project_api_key: str | None = None
    biogrid_access_key: str | None = None
    openfda_api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 4
    retry_budget: float = 45.0
    user_agent: str = DEFAULT_USER_AGENT
    host_delays: dict[str, float] = field(default_factory=lambda: dict(HOST_DELAYS))

    def __post_init__(self) -> None:
        # NCBI allows 10 req/s with a registered key, 3 req/s without.
        if self.ncbi_api_key:
            self.host_delays["eutils.ncbi.nlm.nih.gov"] = 0.1
            self.host_delays["www.ncbi.nlm.nih.gov"] = 0.1

    def host_delay(self, host: str) -> float:
        return self.host_delays.get(host, 0.1)

    @classmethod
    def from_env(cls) -> Settings:
        key = os.environ.get("NCBI_API_KEY", "").strip() or None
        email = os.environ.get("NCBI_EMAIL", "").strip() or None
        mp_key = os.environ.get("MATERIALS_PROJECT_API_KEY", "").strip() or None
        bg_key = os.environ.get("BIOGRID_ACCESS_KEY", "").strip() or None
        fda_key = os.environ.get("OPENFDA_API_KEY", "").strip() or None
        return cls(
            ncbi_api_key=key,
            ncbi_email=email,
            materials_project_api_key=mp_key,
            biogrid_access_key=bg_key,
            openfda_api_key=fda_key,
        )
