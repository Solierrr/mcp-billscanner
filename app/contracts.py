"""Contratos compartilhados entre os adapters da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GeocodingResult:
    """Coordenadas resolvidas por um adapter real ou demonstrativo."""

    latitude: float
    longitude: float
    formatted_address: str


class SolarApiClient(Protocol):
    """Interface assíncrona exigida pelo servidor MCP."""

    async def geocode_address(self, address: str) -> GeocodingResult: ...

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]: ...
