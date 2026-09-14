"""Testes unitários de proteção do adapter Google."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import ConfigurationError
from app.normal.google_client import GoogleApiClient
from tests.helpers import make_settings


class GoogleApiClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_fails_before_opening_network_client(self) -> None:
        client = GoogleApiClient(
            make_settings(demo_mode=False, google_api_key="")
        )

        with patch(
            "httpx.AsyncClient",
            side_effect=AssertionError("A rede não deveria ser acessada"),
        ):
            with self.assertRaisesRegex(
                ConfigurationError, "GOOGLE_SOLAR_API_KEY"
            ):
                await client.fetch_building_insights(-23.5, -46.6)


if __name__ == "__main__":
    unittest.main()
