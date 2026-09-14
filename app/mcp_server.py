"""Servidor MCP da calculadora de energia solar."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api_models import (
    BrazilianAddressInput,
    GeocodingToolResponse,
    LatitudeInput,
    LongitudeInput,
    MonthlyBillInput,
    MonthlyConsumptionInput,
    OptionalBrazilianAddressInput,
    SolarCalculationToolResponse,
)
from .config import ConfigurationError, Settings
from .contracts import GeocodingResult, SolarApiClient
from .demo.client import DemoApiClient
from .normal.google_client import ExternalServiceError, GoogleApiClient
from .service import (
    InputValidationError,
    SolarCalculationService,
    SolarDataError,
)


# As APIs Google recebem a chave na query string. Evita que logs informativos
# do cliente HTTP exponham a credencial ao registrar a URL completa.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

mcp = FastMCP("Calculadora Solar")
settings = Settings.from_env()
api_client: SolarApiClient = (
    DemoApiClient(settings) if settings.demo_mode else GoogleApiClient(settings)
)
calculation_service = SolarCalculationService(settings)


@mcp.tool()
async def geocodificar_endereco(
    endereco: BrazilianAddressInput,
) -> GeocodingToolResponse:
    """Converte um endereço brasileiro em coordenadas geográficas.

    Use quando houver um endereço, mas não latitude e longitude. A resposta
    fornece o endereço padronizado e as coordenadas correspondentes. No modo de
    demonstração, as coordenadas são identificadas explicitamente como simuladas.
    """
    try:
        normalized_address = _validate_address(endereco)
        result = await api_client.geocode_address(normalized_address)
        return GeocodingToolResponse.model_validate(
            {
                "sucesso": True,
                **_execution_metadata(),
                "endereco_formatado": result.formatted_address,
                "latitude": round(result.latitude, 7),
                "longitude": round(result.longitude, 7),
            }
        )
    except (InputValidationError, ConfigurationError, ExternalServiceError) as exc:
        return GeocodingToolResponse.model_validate(_error_response(exc))
    except Exception:
        logging.exception("Erro inesperado em ferramenta MCP.")
        return GeocodingToolResponse.model_validate(_unexpected_error_response())


@mcp.tool()
async def calcular_sistema_solar(
    latitude: LatitudeInput = None,
    longitude: LongitudeInput = None,
    consumo_mensal_kwh: MonthlyConsumptionInput = None,
    valor_conta_reais: MonthlyBillInput = None,
    endereco: OptionalBrazilianAddressInput = None,
) -> SolarCalculationToolResponse:
    """Dimensiona um sistema fotovoltaico e estima investimento e retorno.

    Informe latitude e longitude juntas ou somente endereco, nunca os dois
    formatos. Informe também consumo_mensal_kwh, valor_conta_reais ou ambos. A
    ferramenta considera potencial solar, limite do telhado, painel de
    referência, custos configurados e degradação natural para recomendar o
    sistema. Consulte as descrições dos campos da resposta para interpretar as
    unidades, origens e limitações de cada valor.
    """
    try:
        resolved_latitude, resolved_longitude, geocoding = await _resolve_location(
            latitude=latitude,
            longitude=longitude,
            endereco=endereco,
        )

        # Valida a demanda antes de consultar uma API ou os dados demonstrativos.
        calculation_service.resolve_energy_demand(
            consumo_mensal_kwh, valor_conta_reais
        )
        building_insights = await api_client.fetch_building_insights(
            resolved_latitude, resolved_longitude
        )
        result = calculation_service.calculate(
            latitude=resolved_latitude,
            longitude=resolved_longitude,
            consumo_mensal_kwh=consumo_mensal_kwh,
            valor_conta_reais=valor_conta_reais,
            building_insights=building_insights,
        )

        if settings.demo_mode:
            result["fonte_produtividade"] = "dados_ficticios_modo_demonstracao"
            result["metodo_capacidade_telhado"] = (
                "dados_ficticios_modo_demonstracao"
            )
            result["configuracao_google_paineis"] = None
            result["potencia_painel_referencia_google_w"] = None
            result["capacidade_google_paineis_referencia"] = None
            result["observacoes"] = [
                observation
                for observation in result["observacoes"]
                if "energia DC da API" not in observation
            ]
            result["observacoes"].insert(
                0,
                "MODO DEMONSTRAÇÃO: localização, telhado e produção solar são fictícios.",
            )

        response: dict[str, Any] = {
            "sucesso": True,
            **_execution_metadata(),
            **result,
        }
        if geocoding is not None:
            response["endereco_geocodificado"] = geocoding.formatted_address
        return SolarCalculationToolResponse.model_validate(response)
    except (
        InputValidationError,
        SolarDataError,
        ConfigurationError,
        ExternalServiceError,
    ) as exc:
        return SolarCalculationToolResponse.model_validate(_error_response(exc))
    except Exception:
        logging.exception("Erro inesperado em ferramenta MCP.")
        return SolarCalculationToolResponse.model_validate(
            _unexpected_error_response()
        )


async def _resolve_location(
    *,
    latitude: float | None,
    longitude: float | None,
    endereco: str | None,
) -> tuple[float, float, GeocodingResult | None]:
    has_any_coordinate = latitude is not None or longitude is not None
    has_address = endereco is not None and bool(endereco.strip())

    if has_any_coordinate and has_address:
        raise InputValidationError(
            "Informe latitude/longitude ou endereco, não os dois formatos juntos."
        )

    if has_any_coordinate:
        if latitude is None or longitude is None:
            raise InputValidationError(
                "latitude e longitude devem ser informadas juntas."
            )
        validated = calculation_service.validate_location(latitude, longitude)
        return validated[0], validated[1], None

    if has_address:
        result = await api_client.geocode_address(_validate_address(endereco))
        validated = calculation_service.validate_location(
            result.latitude, result.longitude
        )
        return validated[0], validated[1], result

    raise InputValidationError(
        "Informe latitude e longitude ou um endereço para localizar o imóvel."
    )


def _execution_metadata() -> dict[str, Any]:
    if settings.demo_mode:
        return {
            "modo_execucao": "demonstracao_offline",
            "aviso_demonstracao": (
                "Nenhuma API externa foi consultada; localização e potencial "
                "solar são fictícios e servem apenas para testar o software."
            ),
        }
    return {"modo_execucao": "google_apis"}


def _validate_address(address: str | None) -> str:
    if not isinstance(address, str):
        raise InputValidationError("endereco deve ser um texto.")
    normalized = " ".join(address.split())
    if len(normalized) < 5:
        raise InputValidationError("endereco deve ter ao menos 5 caracteres.")
    if len(normalized) > 500:
        raise InputValidationError("endereco deve ter no máximo 500 caracteres.")
    return normalized


def _error_response(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, InputValidationError):
        code = "entrada_invalida"
    elif isinstance(exc, SolarDataError):
        code = "dados_solares_indisponiveis"
    elif isinstance(exc, ConfigurationError):
        code = "configuracao_invalida"
    elif isinstance(exc, ExternalServiceError):
        code = exc.code
    else:
        code = "erro"

    error: dict[str, Any] = {
        "codigo": code,
        "mensagem": str(exc),
    }
    if isinstance(exc, ExternalServiceError):
        error["servico"] = exc.service
        if exc.status_code is not None:
            error["status_code"] = exc.status_code
    return {
        "sucesso": False,
        **_execution_metadata(),
        "erro": error,
    }


def _unexpected_error_response() -> dict[str, Any]:
    return {
        "sucesso": False,
        **_execution_metadata(),
        "erro": {
            "codigo": "erro_interno",
            "mensagem": "Ocorreu um erro interno inesperado na calculadora solar.",
        },
    }
