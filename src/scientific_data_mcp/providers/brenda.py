"""BRENDA SOAP provider (key-gated; SOAP access requires registration).

BRENDA asks for at most one request per second. The synchronous zeep
client is run in a worker thread and is never retried automatically.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

from ..config import Settings
from ..errors import AuthError, ProviderError, UpstreamError
from ..http import PoliteClient
from .base import Provider

_WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
_ENDPOINT = "https://www.brenda-enzymes.org/soap/brenda_server.php"

_METHODS = {
    "km": ("getKmValue", ("kmValue*", "kmValueMaximum*", "substrate*", "commentary*", "ligandStructureId*", "literature*")),
    "kcat": ("getTurnoverNumber", ("turnoverNumber*", "turnoverNumberMaximum*", "substrate*", "commentary*", "ligandStructureId*", "literature*")),
    "ki": ("getKiValue", ("kiValue*", "kiValueMaximum*", "inhibitor*", "commentary*", "ligandStructureId*", "literature*")),
    "kcat_km": ("getKcatKmValue", ("kcatKmValue*", "kcatKmValueMaximum*", "substrate*", "commentary*", "ligandStructureId*", "literature*")),
    "names": ("getEnzymeNames", ("synonyms*",)),
    "engineering": ("getEngineering", ("engineering*", "commentary*", "literature*")),
}
_SUBSTRATES = (
    "getSubstratesProducts",
    (
        "substrates*", "commentarySubstrates*", "literatureSubstrates*",
        "organismSubstrates*", "products*", "commentaryProducts*",
        "literatureProducts*", "organismProducts*", "reversibility*",
    ),
)


class BrendaProvider(Provider):
    name = "brenda"
    base_url = "https://www.brenda-enzymes.org"

    def __init__(self, http: PoliteClient, settings: Settings, service: Any | None = None):
        super().__init__(http, settings)
        self._email = settings.brenda_email or ""
        self._password_sha = hashlib.sha256((settings.brenda_password or "").encode()).hexdigest()
        self._service = service
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def _get_service(self):
        if self._service is not None:
            return self._service
        async with self._lock:
            if self._service is None:
                from zeep import Client
                from zeep import Settings as ZeepSettings

                client = await asyncio.to_thread(
                    Client, _WSDL, settings=ZeepSettings(strict=False)
                )
                self._service = client.service
        return self._service

    async def _pace(self) -> None:
        now = time.monotonic()
        wait = 1.0 - (now - self._last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()

    async def query(self, kind: str, ec_number: str, organism: str = "") -> list[dict]:
        method, fields = _SUBSTRATES if kind == "substrates" else _METHODS[kind]
        args = [self._email, self._password_sha, f"ecNumber*{ec_number}"]
        args.append(f"organism*{organism}" if organism else "organism*")
        args.extend(fields)
        service = await self._get_service()
        await self._pace()
        try:
            result = await asyncio.to_thread(getattr(service, method), *args)
        except Exception as exc:
            msg = str(exc)
            low = msg.lower()
            if any(x in low for x in ("password", "email", "login", "authenticat")):
                raise AuthError(f"BRENDA authentication failed: {msg}") from exc
            if isinstance(exc, ProviderError):
                raise
            raise UpstreamError(f"BRENDA SOAP error: {msg}") from exc
        plain = _to_plain(result)
        if isinstance(plain, dict):
            for key in (
                method,
                "return",
                "KmValue",
                "TurnoverNumber",
                "KiValue",
                "KcatKmValue",
                "SubstratesProducts",
                "EnzymeNames",
                "Engineering",
                "ArrayOfKmValues",
                "ArrayOfTurnoverNumbers",
                "ArrayOfKiValues",
                "ArrayOfKcatKmValues",
                "ArrayOfSubstratesProducts",
                "ArrayOfEnzymeNames",
                "ArrayOfEngineerings",
            ):
                if key in plain:
                    plain = plain[key]
                    break
        if plain is None:
            return []
        if isinstance(plain, dict):
            return [plain]
        if isinstance(plain, list):
            return [x for x in plain if isinstance(x, dict)]
        return []


def _to_plain(value: Any) -> Any:
    if hasattr(value, "__values__"):
        return {k: _to_plain(v) for k, v in value.__values__.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    return value
