"""Testes unitários do adapter demonstrativo offline."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.demo.client import DEMO_LATITUDE, DEMO_LONGITUDE, DemoApiClient
from tests.helpers import make_settings


class DemoApiClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_geocoding_is_explicitly_fictitious(self) -> None:
        client = DemoApiClient(make_settings())

        with patch(
            "httpx.AsyncClient",
            side_effect=AssertionError("O modo demo tentou acessar a rede"),
        ):
            result = await client.geocode_address("Endereço para teste")

        self.assertEqual(result.latitude, DEMO_LATITUDE)
        self.assertEqual(result.longitude, DEMO_LONGITUDE)
        self.assertIn("fictícias", result.formatted_address)

    async def test_building_insights_are_deterministic_and_offline(self) -> None:
        settings = make_settings()
        client = DemoApiClient(settings)

        with patch(
            "httpx.AsyncClient",
            side_effect=AssertionError("O modo demo tentou acessar a rede"),
        ):
            payload = await client.fetch_building_insights(0, 0)

        potential = payload["solarPotential"]
        self.assertEqual(potential["maxArrayPanelsCount"], 12)
        self.assertEqual(potential["panelCapacityWatts"], 550.0)
        self.assertEqual(potential["panelWidthMeters"], 1.134)
        self.assertEqual(potential["panelHeightMeters"], 2.278)
        self.assertEqual(
            [config["panelsCount"] for config in potential["solarPanelConfigs"]],
            [4, 8, 12],
        )


if __name__ == "__main__":
    unittest.main()
