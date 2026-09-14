"""Testes unitários da configuração por ambiente."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import ConfigurationError, PROJECT_ROOT, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid_without_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

        self.assertFalse(settings.demo_mode)
        self.assertEqual(settings.default_tariff_reais_kwh, 0.95)
        self.assertEqual(settings.panel_reference, "JA Solar JAM72S30-550/MR")
        self.assertEqual(settings.panel_power_watts, 550.0)
        self.assertEqual(settings.panel_width_meters, 1.134)
        self.assertEqual(settings.panel_height_meters, 2.278)
        self.assertEqual(settings.panel_module_reference_price_reais, 780.0)
        self.assertEqual(
            settings.installation_labor_cost_per_panel_reais, 632.5
        )
        self.assertEqual(settings.other_system_cost_per_panel_reais, 387.5)
        self.assertEqual(settings.estimated_total_cost_per_panel_reais, 1800.0)
        self.assertEqual(settings.annual_panel_degradation_rate, 0.0055)
        self.assertEqual(PROJECT_ROOT.name, "ai-billscanner")

    def test_demo_mode_accepts_portuguese_boolean(self) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": "sim"}, clear=True):
            settings = Settings.from_env()

        self.assertTrue(settings.demo_mode)

    def test_invalid_boolean_is_rejected(self) -> None:
        with patch.dict(os.environ, {"DEMO_MODE": "talvez"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "DEMO_MODE"):
                Settings.from_env()

    def test_non_finite_numeric_value_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {"PANEL_POWER_WATTS": "NaN"},
            clear=True,
        ):
            with self.assertRaisesRegex(ConfigurationError, "número finito"):
                Settings.from_env()

    def test_degradation_rate_accepts_zero_and_rejects_one(self) -> None:
        with patch.dict(
            os.environ,
            {"ANNUAL_PANEL_DEGRADATION_RATE": "0"},
            clear=True,
        ):
            self.assertEqual(Settings.from_env().annual_panel_degradation_rate, 0)

        with patch.dict(
            os.environ,
            {"ANNUAL_PANEL_DEGRADATION_RATE": "1"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                ConfigurationError, "ANNUAL_PANEL_DEGRADATION_RATE"
            ):
                Settings.from_env()

    def test_missing_google_key_is_reported_only_when_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

        with self.assertRaisesRegex(ConfigurationError, "GOOGLE_SOLAR_API_KEY"):
            settings.require_google_api_key()


if __name__ == "__main__":
    unittest.main()
