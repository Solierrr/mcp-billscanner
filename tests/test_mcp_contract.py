"""Testes do contrato público e autodescritivo das ferramentas MCP."""

from __future__ import annotations

import json
import logging
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from mcp.server.fastmcp.exceptions import ToolError

import app.mcp_server as mcp_server
from app.api_models import GeocodingToolResponse, SolarCalculationToolResponse
from app.demo.client import DemoApiClient
from app.mcp_server import mcp
from app.service import SolarCalculationService
from tests.helpers import make_settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIRECTORY = PROJECT_ROOT / "examples"


class McpContractTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _read_example(filename: str) -> dict[str, Any]:
        with (EXAMPLES_DIRECTORY / filename).open(encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _assert_output_schema_is_descriptive(
        test_case: unittest.TestCase,
        schema: dict[str, Any],
    ) -> None:
        discriminator = schema["discriminator"]
        test_case.assertEqual(discriminator["propertyName"], "sucesso")
        test_case.assertNotIn("mapping", discriminator)
        test_case.assertEqual(len(schema["oneOf"]), 2)

        definitions = schema.get("$defs", {})
        test_case.assertTrue(definitions)
        for definition_name, definition in definitions.items():
            with test_case.subTest(definition=definition_name):
                test_case.assertEqual(definition.get("type"), "object")
                test_case.assertIs(definition.get("additionalProperties"), False)
                test_case.assertTrue(definition.get("description"))
                properties = definition.get("properties", {})
                test_case.assertTrue(properties)
                for property_name, property_schema in properties.items():
                    with test_case.subTest(
                        definition=definition_name,
                        property=property_name,
                    ):
                        test_case.assertTrue(property_schema.get("description"))

    def _demo_dependencies(self) -> tuple[Any, DemoApiClient, SolarCalculationService]:
        settings = make_settings(demo_mode=True)
        return settings, DemoApiClient(settings), SolarCalculationService(settings)

    async def test_tools_publish_self_describing_schemas(self) -> None:
        tools = {
            tool.name: tool.model_dump(mode="json")
            for tool in await mcp.list_tools()
        }

        self.assertEqual(
            set(tools),
            {"calcular_sistema_solar", "geocodificar_endereco"},
        )
        expected_inputs = {
            "geocodificar_endereco": {"endereco"},
            "calcular_sistema_solar": {
                "latitude",
                "longitude",
                "consumo_mensal_kwh",
                "valor_conta_reais",
                "endereco",
            },
        }
        for tool_name, expected_properties in expected_inputs.items():
            with self.subTest(tool=tool_name):
                input_schema = tools[tool_name]["inputSchema"]
                self.assertEqual(
                    set(input_schema["properties"]), expected_properties
                )
                for property_name, property_schema in input_schema[
                    "properties"
                ].items():
                    with self.subTest(tool=tool_name, property=property_name):
                        self.assertTrue(property_schema.get("description"))
                        self.assertTrue(property_schema.get("examples"))

                self._assert_output_schema_is_descriptive(
                    self, tools[tool_name]["outputSchema"]
                )

        self.assertEqual(
            tools["geocodificar_endereco"]["inputSchema"]["required"],
            ["endereco"],
        )
        self.assertNotIn(
            "required", tools["calcular_sistema_solar"]["inputSchema"]
        )

    async def test_demo_examples_validate_and_preserve_exact_json(self) -> None:
        examples = (
            (
                GeocodingToolResponse,
                "geocodificar_endereco.output.demo.json",
            ),
            (
                SolarCalculationToolResponse,
                "calcular_sistema_solar.output.demo.json",
            ),
        )

        for response_model, output_filename in examples:
            with self.subTest(example=output_filename):
                expected = self._read_example(output_filename)
                response = response_model.model_validate(expected)

                self.assertEqual(response.model_dump(mode="json"), expected)

    async def test_call_tool_returns_examples_without_result_wrapper(self) -> None:
        settings, api_client, calculation_service = self._demo_dependencies()
        examples = (
            (
                "geocodificar_endereco",
                "geocodificar_endereco.input.json",
                "geocodificar_endereco.output.demo.json",
            ),
            (
                "calcular_sistema_solar",
                "calcular_sistema_solar.input.json",
                "calcular_sistema_solar.output.demo.json",
            ),
        )

        with (
            patch.object(mcp_server, "settings", settings),
            patch.object(mcp_server, "api_client", api_client),
            patch.object(
                mcp_server, "calculation_service", calculation_service
            ),
        ):
            for tool_name, input_filename, output_filename in examples:
                with self.subTest(tool=tool_name):
                    arguments = self._read_example(input_filename)
                    expected = self._read_example(output_filename)

                    content_blocks, structured_content = await mcp.call_tool(
                        tool_name, arguments
                    )

                    self.assertEqual(structured_content, expected)
                    self.assertNotIn("result", structured_content)
                    self.assertEqual(len(content_blocks), 1)
                    self.assertEqual(
                        json.loads(content_blocks[0].text), expected
                    )

    async def test_error_payload_omits_unavailable_optional_context(self) -> None:
        settings, api_client, calculation_service = self._demo_dependencies()

        with (
            patch.object(mcp_server, "settings", settings),
            patch.object(mcp_server, "api_client", api_client),
            patch.object(
                mcp_server, "calculation_service", calculation_service
            ),
        ):
            _, structured_content = await mcp.call_tool(
                "calcular_sistema_solar", {}
            )

        self.assertEqual(
            set(structured_content),
            {"sucesso", "modo_execucao", "aviso_demonstracao", "erro"},
        )
        self.assertFalse(structured_content["sucesso"])
        self.assertEqual(
            structured_content["erro"]["codigo"], "entrada_invalida"
        )
        self.assertNotIn("servico", structured_content["erro"])
        self.assertNotIn("status_code", structured_content["erro"])

    async def test_schema_type_errors_are_mcp_transport_errors(self) -> None:
        with self.assertRaises(ToolError):
            await mcp.call_tool(
                "geocodificar_endereco", {"endereco": 123}
            )

    async def test_http_client_loggers_do_not_emit_informational_urls(self) -> None:
        self.assertEqual(logging.getLogger("httpx").level, logging.WARNING)
        self.assertEqual(logging.getLogger("httpcore").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
