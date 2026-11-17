"""Runtime settings.

Everything works without configuration: all five upstream sources are
keyless. ``NCBI_API_KEY`` is optional and only lifts the E-utilities rate
limit from 3 req/s to 10 req/s.
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
}


@dataclass
class Settings:
    ncbi_api_key: str | None = None
    ncbi_email: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    user_agent: str = DEFAULT_USER_AGENT
    host_delays: dict[str, float] = field(default_factory=lambda: dict(HOST_DELAYS))

    def host_delay(self, host: str) -> float:
        return self.host_delays.get(host, 0.1)

    @classmethod
    def from_env(cls) -> Settings:
        key = os.environ.get("NCBI_API_KEY", "").strip() or None
        email = os.environ.get("NCBI_EMAIL", "").strip() or None
        return cls(ncbi_api_key=key, ncbi_email=email)
