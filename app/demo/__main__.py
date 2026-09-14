"""Executa uma demonstração local sem Google Cloud, cartão ou chave de API."""

from __future__ import annotations

import asyncio
import json
import os

# Precisa ser definido antes de importar o servidor, que carrega a configuração.
os.environ["DEMO_MODE"] = "true"

from app.mcp_server import (  # noqa: E402
    calcular_sistema_solar,
    geocodificar_endereco,
)


async def main() -> None:
    geocoding = await geocodificar_endereco(
        "Avenida Paulista, 1000, São Paulo, SP"
    )
    calculation = await calcular_sistema_solar(
        latitude=-23.5614,
        longitude=-46.6559,
        consumo_mensal_kwh=520,
        valor_conta_reais=494,
    )

    print("=== GEOCODIFICAÇÃO FICTÍCIA ===")
    print(json.dumps(geocoding, ensure_ascii=False, indent=2))
    print("\n=== CÁLCULO SOLAR FICTÍCIO ===")
    print(json.dumps(calculation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
