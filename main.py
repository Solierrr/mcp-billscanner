"""Ponto de entrada normal do servidor MCP da calculadora solar."""

from __future__ import annotations

import os

# O entrypoint de produção nunca seleciona o adapter com dados fictícios,
# mesmo que uma configuração local antiga ainda contenha DEMO_MODE=true.
os.environ["DEMO_MODE"] = "false"

from app.mcp_server import mcp  # noqa: E402


def main() -> None:
    """Inicia o servidor MCP real usando transporte stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
