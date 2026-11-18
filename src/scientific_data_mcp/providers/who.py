"""WHO Global Health Observatory (GHO) provider.

Keyless OData v4. Only the observation endpoint is used: the ``/Indicator``
catalogue endpoint is large and was returning 504 from this network, so the
tool takes an explicit indicator code instead of pretending to search a
catalogue it cannot reliably load.
"""

from __future__ import annotations

from urllib.parse import quote

from ..config import Settings
from ..errors import UpstreamDrift
from ..http import PoliteClient
from .base import Provider, omit_none

_BASE = "https://ghoapi.azureedge.net/api"


class WhoProvider(Provider):
    name = "who"
    base_url = _BASE

    def __init__(self, http: PoliteClient, settings: Settings):
        super().__init__(http, settings)

    async def data(
        self,
        indicator: str,
        country: str | None = None,
        year: int | None = None,
        sex: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        filters = []
        if country:
            filters.append(f"SpatialDim eq '{country.upper()}'")
        if year is not None:
            filters.append(f"TimeDim eq {int(year)}")
        if sex:
            filters.append(f"Dim1 eq '{sex.upper()}'")
        params: dict = {"$top": limit}
        if filters:
            params["$filter"] = " and ".join(filters)
        payload = await self.http.get_json(
            f"{self.base_url}/{quote(indicator.upper(), safe='')}", params=params
        )
        if not isinstance(payload, dict) or "value" not in payload:
            raise UpstreamDrift(
                "WHO GHO response has no 'value' list "
                f"(got {type(payload).__name__})"
            )
        return [_normalize(row) for row in payload["value"] or []]


def _normalize(row: dict) -> dict:
    return omit_none(
        {
            "indicator": row.get("IndicatorCode"),
            "country": row.get("SpatialDim"),
            "country_type": row.get("SpatialDimType"),
            "year": row.get("TimeDim"),
            "sex": row.get("Dim1"),
            "value": row.get("NumericValue"),
            "value_text": row.get("Value"),
            "low": row.get("Low"),
            "high": row.get("High"),
        }
    )
