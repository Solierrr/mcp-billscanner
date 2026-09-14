"""Testes dos entrypoints e do registro MCP."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import main
import app.mcp_server as mcp_server
from app.mcp_server import mcp
from app.normal.google_client import GoogleApiClient


class MainEntrypointTests(unittest.TestCase):
    def test_main_starts_stdio_transport(self) -> None:
        with patch.object(main.mcp, "run") as run:
            main.main()

        run.assert_called_once_with(transport="stdio")

    def test_main_uses_normal_adapter_only(self) -> None:
        self.assertFalse(mcp_server.settings.demo_mode)
        self.assertIsInstance(mcp_server.api_client, GoogleApiClient)


class McpRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_expected_tools_are_registered(self) -> None:
        tools = sorted(tool.name for tool in await mcp.list_tools())

        self.assertEqual(
            tools,
            ["calcular_sistema_solar", "geocodificar_endereco"],
        )


if __name__ == "__main__":
    unittest.main()
