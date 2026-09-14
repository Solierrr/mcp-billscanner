"""Regras de validação, dimensionamento e estimativa financeira."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .config import Settings


MAX_PAYBACK_MONTHS = 100 * 12


class InputValidationError(ValueError):
    """Indica parâmetros de entrada inválidos."""


class SolarDataError(ValueError):
    """Indica ausência ou inconsistência nos dados solares."""


@dataclass(frozen=True, slots=True)
class EnergyDemand:
    monthly_consumption_kwh: float
    monthly_bill_reais: float | None
    tariff_reais_kwh: float
    tariff_source: str


@dataclass(frozen=True, slots=True)
class RoofCapacity:
    adjusted_max_panels: int
    google_reference_max_panels: int
    method: str
    google_panel_width_meters: float | None
    google_panel_height_meters: float | None


@dataclass(frozen=True, slots=True)
class ProductionEstimate:
    required_panels: int
    recommended_panels: int
    monthly_generation_kwh: float
    monthly_kwh_per_panel: float
    source: str
    google_reference_panel_watts: float | None
    google_config_panels_count: int | None


class SolarCalculationService:
    """Executa cálculos puros sem depender de HTTP ou do protocolo MCP."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def validate_location(latitude: float, longitude: float) -> tuple[float, float]:
        latitude_value = _finite_number(latitude, "latitude")
        longitude_value = _finite_number(longitude, "longitude")

        if not -90 <= latitude_value <= 90:
            raise InputValidationError("latitude deve estar entre -90 e 90.")
        if not -180 <= longitude_value <= 180:
            raise InputValidationError("longitude deve estar entre -180 e 180.")
        return latitude_value, longitude_value

    def resolve_energy_demand(
        self,
        consumo_mensal_kwh: float | None,
        valor_conta_reais: float | None,
    ) -> EnergyDemand:
        if consumo_mensal_kwh is None and valor_conta_reais is None:
            raise InputValidationError(
                "Informe consumo_mensal_kwh ou valor_conta_reais."
            )

        consumption = (
            _positive_number(consumo_mensal_kwh, "consumo_mensal_kwh")
            if consumo_mensal_kwh is not None
            else None
        )
        bill = (
            _positive_number(valor_conta_reais, "valor_conta_reais")
            if valor_conta_reais is not None
            else None
        )

        if consumption is not None and bill is not None:
            tariff = bill / consumption
            source = "tarifa_efetiva_da_conta"
        elif consumption is not None:
            tariff = self._settings.default_tariff_reais_kwh
            source = "tarifa_padrao_configurada"
        else:
            tariff = self._settings.default_tariff_reais_kwh
            consumption = bill / tariff  # type: ignore[operator]
            source = "tarifa_padrao_para_converter_conta"

        return EnergyDemand(consumption, bill, tariff, source)

    def calculate(
        self,
        *,
        latitude: float,
        longitude: float,
        consumo_mensal_kwh: float | None,
        valor_conta_reais: float | None,
        building_insights: dict[str, Any],
    ) -> dict[str, Any]:
        latitude_value, longitude_value = self.validate_location(latitude, longitude)
        demand = self.resolve_energy_demand(consumo_mensal_kwh, valor_conta_reais)
        solar_potential = building_insights.get("solarPotential")
        if not isinstance(solar_potential, dict):
            raise SolarDataError(
                "A API solar não retornou o potencial solar do imóvel."
            )

        roof_capacity = self._derive_roof_capacity(solar_potential)
        production = self._select_production(
            solar_potential,
            demand.monthly_consumption_kwh,
            roof_capacity.adjusted_max_panels,
        )

        compensated_consumption = min(
            demand.monthly_consumption_kwh, production.monthly_generation_kwh
        )
        monthly_savings = compensated_consumption * demand.tariff_reais_kwh
        investment = (
            production.recommended_panels
            * self._settings.estimated_total_cost_per_panel_reais
        )
        payback_years = self._calculate_payback_years_with_degradation(
            investment_reais=investment,
            initial_monthly_generation_kwh=production.monthly_generation_kwh,
            monthly_consumption_kwh=demand.monthly_consumption_kwh,
            tariff_reais_kwh=demand.tariff_reais_kwh,
        )
        coverage_percent = (
            compensated_consumption / demand.monthly_consumption_kwh * 100
        )
        roof_limited = (
            production.monthly_generation_kwh < demand.monthly_consumption_kwh
        )

        observations = [
            "Estimativa indicativa; confirme projeto, sombreamento, perdas, tarifa e orçamento com profissionais habilitados."
        ]
        if roof_limited:
            observations.append(
                "O telhado limita o sistema antes de compensar todo o consumo informado."
            )
        if production.source == "estimativa_padrao_configurada":
            observations.append(
                "A API não retornou configuração energética compatível; foi aplicada a produtividade mensal de fallback."
            )
        else:
            observations.append(
                "A energia DC da API foi convertida por um fator de desempenho antes do cálculo financeiro."
            )
        if roof_capacity.method == "contagem_google_sem_dimensoes_referencia":
            observations.append(
                "A API não informou dimensões do painel de referência; o limite físico é aproximado."
            )
        observations.append(
            "Módulo, mão de obra e demais itens são referências de mercado "
            "configuráveis; os valores reais dependem do imóvel e da região."
        )
        observations.append(
            "O payback considera somente a redução linear anual de potência "
            f"dos painéis ({self._settings.annual_panel_degradation_rate * 100:.2f}%), "
            "pressupondo instalação e uso adequados."
        )
        observations.append(
            "Para um orçamento detalhado e adequado ao imóvel, consulte um "
            "técnico ou uma empresa especializada em energia solar."
        )

        max_sunshine_hours = _optional_positive_number(
            solar_potential.get("maxSunshineHoursPerYear")
        )

        return {
            "localizacao": {
                "latitude": round(latitude_value, 7),
                "longitude": round(longitude_value, 7),
            },
            "consumo_mensal_kwh": round(demand.monthly_consumption_kwh, 2),
            "valor_conta_informado_reais": (
                round(demand.monthly_bill_reais, 2)
                if demand.monthly_bill_reais is not None
                else None
            ),
            "tarifa_aplicada_reais_kwh": round(demand.tariff_reais_kwh, 4),
            "fonte_tarifa": demand.tariff_source,
            "painel_referencia": self._settings.panel_reference,
            "potencia_painel_w": round(self._settings.panel_power_watts, 1),
            "largura_painel_m": round(self._settings.panel_width_meters, 3),
            "altura_painel_m": round(self._settings.panel_height_meters, 3),
            "preco_referencia_modulo_reais": round(
                self._settings.panel_module_reference_price_reais, 2
            ),
            "mao_de_obra_instalacao_por_painel_reais": round(
                self._settings.installation_labor_cost_per_panel_reais, 2
            ),
            "outros_custos_sistema_por_painel_reais": round(
                self._settings.other_system_cost_per_panel_reais, 2
            ),
            "fator_desempenho_sistema": round(
                self._settings.system_performance_ratio, 3
            ),
            "produtividade_mensal_por_painel_kwh": round(
                production.monthly_kwh_per_panel, 2
            ),
            "fonte_produtividade": production.source,
            "configuracao_google_paineis": production.google_config_panels_count,
            "potencia_painel_referencia_google_w": (
                round(production.google_reference_panel_watts, 1)
                if production.google_reference_panel_watts is not None
                else None
            ),
            "horas_sol_maximas_ano": (
                round(max_sunshine_hours, 2)
                if max_sunshine_hours is not None
                else None
            ),
            "paineis_recomendados": production.recommended_panels,
            "capacidade_google_paineis_referencia": (
                roof_capacity.google_reference_max_panels
            ),
            "metodo_capacidade_telhado": roof_capacity.method,
            "limitado_pelo_telhado": roof_limited,
            "geracao_mensal_estimada_kwh": round(
                production.monthly_generation_kwh, 2
            ),
            "consumo_mensal_compensado_kwh": round(compensated_consumption, 2),
            "percentual_consumo_compensado": round(coverage_percent, 1),
            "investimento_estimado_reais": round(investment, 2),
            "economia_mensal_estimada_reais": round(monthly_savings, 2),
            "payback_estimado_anos": (
                round(payback_years, 1) if payback_years is not None else None
            ),
            "observacoes": observations,
        }

    def _calculate_payback_years_with_degradation(
        self,
        *,
        investment_reais: float,
        initial_monthly_generation_kwh: float,
        monthly_consumption_kwh: float,
        tariff_reais_kwh: float,
    ) -> float | None:
        """Acumula economia mensal com redução linear de potência."""
        if investment_reais <= 0:
            return 0.0

        accumulated_savings = 0.0

        for month_index in range(MAX_PAYBACK_MONTHS):
            elapsed_years = month_index / 12
            power_retention = max(
                0.0,
                1
                - self._settings.annual_panel_degradation_rate
                * elapsed_years,
            )
            degraded_generation = (
                initial_monthly_generation_kwh * power_retention
            )
            compensated_consumption = min(
                monthly_consumption_kwh, degraded_generation
            )
            accumulated_savings += compensated_consumption * tariff_reais_kwh

            if accumulated_savings >= investment_reais:
                completed_months = month_index + 1
                return round(completed_months / 12, 1)

        return None

    def _derive_roof_capacity(
        self, solar_potential: dict[str, Any]
    ) -> RoofCapacity:
        google_max = _positive_integer(
            solar_potential.get("maxArrayPanelsCount"),
            "maxArrayPanelsCount",
        )
        google_width = _optional_positive_number(
            solar_potential.get("panelWidthMeters")
        )
        google_height = _optional_positive_number(
            solar_potential.get("panelHeightMeters")
        )

        if google_width is None or google_height is None:
            return RoofCapacity(
                google_max,
                google_max,
                "contagem_google_sem_dimensoes_referencia",
                google_width,
                google_height,
            )

        google_panel_area = google_width * google_height
        configured_panel_area = (
            self._settings.panel_width_meters * self._settings.panel_height_meters
        )
        area_adjusted_max = math.floor(
            google_max * google_panel_area / configured_panel_area
        )
        # O cálculo por área não prova que painéis extras cabem no layout. Por
        # isso, só reduzimos a contagem original; nunca a aumentamos.
        adjusted_max = min(google_max, area_adjusted_max)
        if adjusted_max <= 0:
            raise SolarDataError(
                "As dimensões configuradas do painel não cabem na área útil estimada."
            )
        return RoofCapacity(
            adjusted_max,
            google_max,
            "contagem_google_ajustada_conservadoramente_por_area",
            google_width,
            google_height,
        )

    def _select_production(
        self,
        solar_potential: dict[str, Any],
        monthly_consumption_kwh: float,
        max_panels: int,
    ) -> ProductionEstimate:
        reference_watts = _optional_positive_number(
            solar_potential.get("panelCapacityWatts")
        )
        configs = solar_potential.get("solarPanelConfigs")
        candidates: list[tuple[int, float]] = []

        if reference_watts is not None and isinstance(configs, list):
            power_ratio = self._settings.panel_power_watts / reference_watts
            for config in configs:
                if not isinstance(config, dict):
                    continue
                try:
                    panels_count = _positive_integer(
                        config.get("panelsCount"), "panelsCount"
                    )
                    yearly_dc_energy = _positive_number(
                        config.get("yearlyEnergyDcKwh"), "yearlyEnergyDcKwh"
                    )
                except (InputValidationError, SolarDataError):
                    continue
                if panels_count > max_panels:
                    continue
                monthly_ac_energy = (
                    yearly_dc_energy
                    / 12
                    * power_ratio
                    * self._settings.system_performance_ratio
                )
                candidates.append((panels_count, monthly_ac_energy))

        if not candidates:
            monthly_per_panel = self._settings.fallback_panel_monthly_kwh
            required = math.ceil(monthly_consumption_kwh / monthly_per_panel)
            recommended = min(required, max_panels)
            return ProductionEstimate(
                required,
                recommended,
                recommended * monthly_per_panel,
                monthly_per_panel,
                "estimativa_padrao_configurada",
                None,
                None,
            )

        candidates.sort(key=lambda item: item[0])
        satisfying = next(
            (
                candidate
                for candidate in candidates
                if candidate[1] >= monthly_consumption_kwh
            ),
            None,
        )
        selected_panels, selected_monthly_energy = satisfying or candidates[-1]
        selected_yield = selected_monthly_energy / selected_panels
        required = (
            selected_panels
            if satisfying is not None
            else math.ceil(monthly_consumption_kwh / selected_yield)
        )

        return ProductionEstimate(
            required,
            selected_panels,
            selected_monthly_energy,
            selected_yield,
            "configuracao_google_ajustada_para_potencia_e_desempenho",
            reference_watts,
            selected_panels,
        )


def _finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise InputValidationError(f"{field_name} deve ser um número.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{field_name} deve ser um número.") from exc
    if not math.isfinite(number):
        raise InputValidationError(f"{field_name} deve ser um número finito.")
    return number


def _positive_number(value: Any, field_name: str) -> float:
    number = _finite_number(value, field_name)
    if number <= 0:
        raise InputValidationError(f"{field_name} deve ser maior que zero.")
    return number


def _positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise SolarDataError(f"{field_name} deve ser um inteiro positivo.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise SolarDataError(f"{field_name} não foi informado corretamente.") from exc
    if not math.isfinite(numeric) or not numeric.is_integer() or numeric <= 0:
        raise SolarDataError(f"{field_name} deve ser um inteiro positivo.")
    return int(numeric)


def _optional_positive_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number
