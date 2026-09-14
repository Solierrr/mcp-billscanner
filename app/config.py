"""Configuração da aplicação carregada do ambiente."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class ConfigurationError(ValueError):
    """Indica uma configuração ausente ou inválida."""


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} deve ser um número.") from exc

    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} deve ser um número finito maior que zero.")
    return value


def _fraction(name: str, default: float) -> float:
    value = _positive_float(name, default)
    if value > 1:
        raise ConfigurationError(f"{name} deve estar no intervalo maior que 0 e até 1.")
    return value


def _non_negative_rate(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} deve ser um número.") from exc

    if not math.isfinite(value) or not 0 <= value < 1:
        raise ConfigurationError(
            f"{name} deve estar no intervalo de 0 (inclusive) a 1 (exclusive)."
        )
    return value


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} deve ser um número inteiro.") from exc

    if value <= 0:
        raise ConfigurationError(f"{name} deve ser maior que zero.")
    return value


def _https_url(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ConfigurationError(
            f"{name} deve ser uma URL HTTPS válida e sem credenciais embutidas."
        )
    return value


def _choice(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default).strip().lower()
    if value not in allowed:
        options = ", ".join(sorted(allowed))
        raise ConfigurationError(f"{name} deve ser um destes valores: {options}.")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "sim", "on"}:
        return True
    if value in {"0", "false", "no", "nao", "não", "off"}:
        return False
    raise ConfigurationError(
        f"{name} deve ser true/false, yes/no, sim/não ou 1/0."
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Parâmetros operacionais e hipóteses financeiras da calculadora."""

    demo_mode: bool
    google_api_key: str
    solar_api_url: str
    solar_api_auth_mode: str
    geocoding_api_url: str
    request_timeout_seconds: float
    http_max_attempts: int
    default_tariff_reais_kwh: float
    panel_reference: str
    panel_power_watts: float
    panel_width_meters: float
    panel_height_meters: float
    panel_module_reference_price_reais: float
    installation_labor_cost_per_panel_reais: float
    other_system_cost_per_panel_reais: float
    fallback_panel_monthly_kwh: float
    system_performance_ratio: float
    annual_panel_degradation_rate: float

    @classmethod
    def from_env(cls) -> "Settings":
        solar_api_url = _https_url(
            "SOLAR_API_URL",
            "https://solar.googleapis.com/v1/buildingInsights:findClosest",
        )
        solar_api_auth_mode = _choice(
            "SOLAR_API_AUTH_MODE", "google_api_key", {"google_api_key", "none"}
        )
        geocoding_api_url = _https_url(
            "GEOCODING_API_URL",
            "https://maps.googleapis.com/maps/api/geocode/json",
        )

        if (
            solar_api_auth_mode == "google_api_key"
            and urlparse(solar_api_url).hostname != "solar.googleapis.com"
        ):
            raise ConfigurationError(
                "SOLAR_API_AUTH_MODE=google_api_key só pode ser usado com "
                "solar.googleapis.com. Use 'none' para um endpoint centralizado "
                "compatível ou implemente autenticação própria no adapter."
            )
        if urlparse(geocoding_api_url).hostname != "maps.googleapis.com":
            raise ConfigurationError(
                "GEOCODING_API_URL deve usar maps.googleapis.com para evitar "
                "encaminhar a chave Google a outro host."
            )

        return cls(
            demo_mode=_boolean("DEMO_MODE", False),
            google_api_key=os.getenv("GOOGLE_SOLAR_API_KEY", "").strip(),
            solar_api_url=solar_api_url,
            solar_api_auth_mode=solar_api_auth_mode,
            geocoding_api_url=geocoding_api_url,
            request_timeout_seconds=_positive_float("REQUEST_TIMEOUT_SECONDS", 15.0),
            http_max_attempts=_positive_int("HTTP_MAX_ATTEMPTS", 3),
            default_tariff_reais_kwh=_positive_float(
                "DEFAULT_TARIFF_REAIS_KWH", 0.95
            ),
            panel_reference=(
                os.getenv("PANEL_REFERENCE", "JA Solar JAM72S30-550/MR").strip()
                or "JA Solar JAM72S30-550/MR"
            ),
            panel_power_watts=_positive_float("PANEL_POWER_WATTS", 550.0),
            panel_width_meters=_positive_float("PANEL_WIDTH_METERS", 1.134),
            panel_height_meters=_positive_float("PANEL_HEIGHT_METERS", 2.278),
            panel_module_reference_price_reais=_positive_float(
                "PANEL_MODULE_REFERENCE_PRICE_REAIS", 780.0
            ),
            installation_labor_cost_per_panel_reais=_positive_float(
                "INSTALLATION_LABOR_COST_PER_PANEL_REAIS", 632.5
            ),
            other_system_cost_per_panel_reais=_positive_float(
                "OTHER_SYSTEM_COST_PER_PANEL_REAIS", 387.5
            ),
            fallback_panel_monthly_kwh=_positive_float(
                "FALLBACK_PANEL_MONTHLY_KWH", 65.0
            ),
            system_performance_ratio=_fraction("SYSTEM_PERFORMANCE_RATIO", 0.85),
            annual_panel_degradation_rate=_non_negative_rate(
                "ANNUAL_PANEL_DEGRADATION_RATE", 0.0055
            ),
        )

    @property
    def estimated_total_cost_per_panel_reais(self) -> float:
        """Soma módulo, mão de obra e demais itens rateados do sistema."""
        return (
            self.panel_module_reference_price_reais
            + self.installation_labor_cost_per_panel_reais
            + self.other_system_cost_per_panel_reais
        )

    def require_google_api_key(self) -> str:
        """Retorna a chave configurada ou falha antes de uma chamada Google."""
        if not self.google_api_key or self.google_api_key == "SUA_CHAVE_AQUI":
            raise ConfigurationError(
                "GOOGLE_SOLAR_API_KEY não foi configurada. "
                "Defina-a no arquivo .env ou no ambiente do cliente MCP."
            )
        return self.google_api_key
