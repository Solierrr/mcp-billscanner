"""Factories determinísticas compartilhadas pelos testes."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.config import Settings


def make_settings(**overrides: Any) -> Settings:
    settings = Settings(
        demo_mode=True,
        google_api_key="",
        solar_api_url=(
            "https://solar.googleapis.com/v1/buildingInsights:findClosest"
        ),
        solar_api_auth_mode="google_api_key",
        geocoding_api_url=(
            "https://maps.googleapis.com/maps/api/geocode/json"
        ),
        request_timeout_seconds=15.0,
        http_max_attempts=3,
        default_tariff_reais_kwh=0.95,
        panel_reference="JA Solar JAM72S30-550/MR",
        panel_power_watts=550.0,
        panel_width_meters=1.134,
        panel_height_meters=2.278,
        panel_module_reference_price_reais=780.0,
        installation_labor_cost_per_panel_reais=632.5,
        other_system_cost_per_panel_reais=387.5,
        fallback_panel_monthly_kwh=65.0,
        system_performance_ratio=0.85,
        annual_panel_degradation_rate=0.0055,
    )
    return replace(settings, **overrides)


def building_insights_fixture() -> dict[str, Any]:
    return {
        "solarPotential": {
            "maxArrayPanelsCount": 12,
            "panelCapacityWatts": 550.0,
            "panelWidthMeters": 1.134,
            "panelHeightMeters": 2.278,
            "maxSunshineHoursPerYear": 1900.0,
            "solarPanelConfigs": [
                {"panelsCount": 4, "yearlyEnergyDcKwh": 3680.0},
                {"panelsCount": 8, "yearlyEnergyDcKwh": 7360.0},
                {"panelsCount": 12, "yearlyEnergyDcKwh": 11040.0},
            ],
        }
    }
