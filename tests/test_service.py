"""Testes unitários das regras de dimensionamento e finanças."""

from __future__ import annotations

import unittest

from app.service import InputValidationError, SolarCalculationService
from tests.helpers import building_insights_fixture, make_settings


class SolarCalculationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SolarCalculationService(make_settings())

    def test_effective_tariff_uses_bill_and_consumption(self) -> None:
        demand = self.service.resolve_energy_demand(520, 494)

        self.assertEqual(demand.monthly_consumption_kwh, 520)
        self.assertEqual(demand.tariff_reais_kwh, 0.95)
        self.assertEqual(demand.tariff_source, "tarifa_efetiva_da_conta")

    def test_bill_only_is_converted_with_default_tariff(self) -> None:
        demand = self.service.resolve_energy_demand(None, 95)

        self.assertEqual(demand.monthly_consumption_kwh, 100)
        self.assertEqual(
            demand.tariff_source,
            "tarifa_padrao_para_converter_conta",
        )

    def test_missing_or_invalid_demand_is_rejected(self) -> None:
        with self.assertRaises(InputValidationError):
            self.service.resolve_energy_demand(None, None)
        with self.assertRaises(InputValidationError):
            self.service.resolve_energy_demand(-1, None)

    def test_location_ranges_are_validated(self) -> None:
        self.assertEqual(self.service.validate_location(-90, 180), (-90.0, 180.0))
        with self.assertRaisesRegex(InputValidationError, "latitude"):
            self.service.validate_location(91, 0)
        with self.assertRaisesRegex(InputValidationError, "longitude"):
            self.service.validate_location(0, -181)

    def test_configuration_matching_demand_is_selected(self) -> None:
        result = self.service.calculate(
            latitude=-23.5614,
            longitude=-46.6559,
            consumo_mensal_kwh=520,
            valor_conta_reais=494,
            building_insights=building_insights_fixture(),
        )

        self.assertEqual(result["painel_referencia"], "JA Solar JAM72S30-550/MR")
        self.assertEqual(result["preco_referencia_modulo_reais"], 780.0)
        self.assertEqual(
            result["mao_de_obra_instalacao_por_painel_reais"], 632.5
        )
        self.assertEqual(
            result["outros_custos_sistema_por_painel_reais"], 387.5
        )
        self.assertEqual(result["paineis_recomendados"], 8)
        self.assertEqual(result["geracao_mensal_estimada_kwh"], 521.33)
        self.assertEqual(result["investimento_estimado_reais"], 14400.0)
        self.assertEqual(result["economia_mensal_estimada_reais"], 494.0)
        self.assertEqual(result["payback_estimado_anos"], 2.5)
        self.assertFalse(result["limitado_pelo_telhado"])
        self.assertTrue(
            any(
                "consulte um técnico" in observation
                for observation in result["observacoes"]
            )
        )

    def test_linear_natural_degradation_delays_long_payback(self) -> None:
        common_arguments = {
            "latitude": -23.5614,
            "longitude": -46.6559,
            "consumo_mensal_kwh": 520,
            "valor_conta_reais": 494,
            "building_insights": building_insights_fixture(),
        }
        without_degradation = SolarCalculationService(
            make_settings(
                annual_panel_degradation_rate=0.0,
                other_system_cost_per_panel_reais=8587.5,
            )
        ).calculate(**common_arguments)
        with_natural_degradation = SolarCalculationService(
            make_settings(
                annual_panel_degradation_rate=0.0055,
                other_system_cost_per_panel_reais=8587.5,
            )
        ).calculate(**common_arguments)

        self.assertGreater(
            with_natural_degradation["payback_estimado_anos"],
            without_degradation["payback_estimado_anos"],
        )
        self.assertTrue(
            any(
                "redução linear anual de potência" in observation
                for observation in with_natural_degradation["observacoes"]
            )
        )

    def test_fallback_generation_respects_roof_limit(self) -> None:
        result = self.service.calculate(
            latitude=-23.5614,
            longitude=-46.6559,
            consumo_mensal_kwh=650,
            valor_conta_reais=617.5,
            building_insights={
                "solarPotential": {"maxArrayPanelsCount": 5}
            },
        )

        self.assertNotIn("paineis_necessarios_para_demanda", result)
        self.assertEqual(result["paineis_recomendados"], 5)
        self.assertEqual(result["geracao_mensal_estimada_kwh"], 325.0)
        self.assertEqual(result["percentual_consumo_compensado"], 50.0)
        self.assertTrue(result["limitado_pelo_telhado"])


if __name__ == "__main__":
    unittest.main()
