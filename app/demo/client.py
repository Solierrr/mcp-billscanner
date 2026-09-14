"""Adapter determinístico para demonstrar a aplicação sem APIs externas."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..contracts import GeocodingResult


DEMO_LATITUDE = -23.5614
DEMO_LONGITUDE = -46.6559


class DemoApiClient:
    """Fornece dados fictícios sem abrir conexões de rede.

    Este adapter existe somente para validar o fluxo MCP e os cálculos. Seus
    dados não descrevem o endereço ou as coordenadas recebidas e nunca devem
    ser usados em uma decisão de compra ou projeto fotovoltaico.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def geocode_address(self, address: str) -> GeocodingResult:
        return GeocodingResult(
            latitude=DEMO_LATITUDE,
            longitude=DEMO_LONGITUDE,
            formatted_address=(
                f"{address} — coordenadas fictícias do modo demonstração"
            ),
        )

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        del latitude, longitude

        # Potência e dimensões vêm do painel comercial configurado; telhado e
        # produção continuam fictícios. A produção DC linear de ~76,67
        # kWh/mês por painel resulta em ~65,17 kWh/mês após o fator 0,85.
        yearly_dc_per_panel_kwh = 920.0
        panel_counts = (4, 8, 12)
        return {
            "name": "buildings/demo-offline",
            "solarPotential": {
                "maxArrayPanelsCount": 12,
                "panelCapacityWatts": self._settings.panel_power_watts,
                "panelWidthMeters": self._settings.panel_width_meters,
                "panelHeightMeters": self._settings.panel_height_meters,
                "maxSunshineHoursPerYear": 1900.0,
                "solarPanelConfigs": [
                    {
                        "panelsCount": count,
                        "yearlyEnergyDcKwh": yearly_dc_per_panel_kwh * count,
                    }
                    for count in panel_counts
                ],
            },
        }
