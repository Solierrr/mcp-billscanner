"""Clientes assíncronos para Google Solar API e Google Geocoding API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx

from ..config import Settings
from ..contracts import GeocodingResult


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_DELAY_SECONDS = 30.0


class ExternalServiceError(RuntimeError):
    """Erro seguro e estruturado de uma API externa."""

    def __init__(
        self,
        message: str,
        *,
        service: str,
        code: str = "external_service_error",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.service = service
        self.code = code
        self.status_code = status_code


class GoogleApiClient:
    """Isola HTTP, autenticação e parsing das APIs externas."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _get_json(
        self,
        url: str,
        params: dict[str, Any],
        *,
        service: str,
        retry_when: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(self._settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, self._settings.http_max_attempts + 1):
                try:
                    response = await client.get(url, params=params)
                except httpx.TimeoutException as exc:
                    if attempt < self._settings.http_max_attempts:
                        await asyncio.sleep(_backoff_delay(attempt))
                        continue
                    raise ExternalServiceError(
                        f"Tempo limite excedido ao consultar {service}.",
                        service=service,
                        code="timeout",
                    ) from exc
                except httpx.RequestError as exc:
                    if attempt < self._settings.http_max_attempts:
                        await asyncio.sleep(_backoff_delay(attempt))
                        continue
                    raise ExternalServiceError(
                        f"Falha de rede ao consultar {service}.",
                        service=service,
                        code="network_error",
                    ) from exc

                if (
                    response.status_code in RETRYABLE_STATUS_CODES
                    and attempt < self._settings.http_max_attempts
                ):
                    await asyncio.sleep(_response_retry_delay(response, attempt))
                    continue

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ExternalServiceError(
                        f"{service} retornou uma resposta inválida.",
                        service=service,
                        code="invalid_json",
                        status_code=response.status_code,
                    ) from exc

                if response.status_code >= 400:
                    message = _extract_api_error(payload) or (
                        f"{service} retornou HTTP {response.status_code}."
                    )
                    raise ExternalServiceError(
                        message,
                        service=service,
                        code="http_error",
                        status_code=response.status_code,
                    )

                if not isinstance(payload, dict):
                    raise ExternalServiceError(
                        f"{service} retornou um formato inesperado.",
                        service=service,
                        code="invalid_payload",
                        status_code=response.status_code,
                    )

                if (
                    retry_when is not None
                    and retry_when(payload)
                    and attempt < self._settings.http_max_attempts
                ):
                    await asyncio.sleep(_backoff_delay(attempt))
                    continue
                return payload

        raise ExternalServiceError(
            f"Não foi possível consultar {service}.",
            service=service,
        )

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "location.latitude": latitude,
            "location.longitude": longitude,
            "requiredQuality": "MEDIUM",
        }
        if self._settings.solar_api_auth_mode == "google_api_key":
            params["key"] = self._settings.require_google_api_key()

        return await self._get_json(
            self._settings.solar_api_url,
            params,
            service="serviço de potencial solar",
        )

    async def geocode_address(self, address: str) -> GeocodingResult:
        api_key = self._settings.require_google_api_key()
        payload = await self._get_json(
            self._settings.geocoding_api_url,
            {
                "address": address,
                "components": "country:BR",
                "region": "br",
                "language": "pt-BR",
                "key": api_key,
            },
            service="Google Geocoding API",
            retry_when=lambda data: data.get("status") == "UNKNOWN_ERROR",
        )

        status = payload.get("status")
        if status != "OK":
            status_messages = {
                "ZERO_RESULTS": "Nenhuma coordenada foi encontrada para o endereço no Brasil.",
                "OVER_QUERY_LIMIT": "A cota da Google Geocoding API foi excedida.",
                "REQUEST_DENIED": "A Google Geocoding API recusou a requisição.",
                "INVALID_REQUEST": "O endereço enviado para geocodificação é inválido.",
                "UNKNOWN_ERROR": "A Google Geocoding API apresentou um erro temporário.",
            }
            message = payload.get("error_message") or status_messages.get(
                str(status), "Não foi possível geocodificar o endereço."
            )
            raise ExternalServiceError(
                str(message),
                service="Google Geocoding API",
                code=str(status or "geocoding_error").lower(),
            )

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise ExternalServiceError(
                "A Google Geocoding API não retornou resultados.",
                service="Google Geocoding API",
                code="zero_results",
            )

        first_result = results[0]
        if not _is_brazilian_result(first_result):
            raise ExternalServiceError(
                "O resultado da geocodificação não pôde ser confirmado como brasileiro.",
                service="Google Geocoding API",
                code="country_mismatch",
            )

        try:
            from math import isfinite

            location = first_result["geometry"]["location"]
            latitude = float(location["lat"])
            longitude = float(location["lng"])
            formatted_address = str(first_result["formatted_address"])
            if (
                not isfinite(latitude)
                or not isfinite(longitude)
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
            ):
                raise ValueError("coordenadas não finitas ou fora da faixa")
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError(
                "A Google Geocoding API retornou dados incompletos.",
                service="Google Geocoding API",
                code="invalid_payload",
            ) from exc

        return GeocodingResult(latitude, longitude, formatted_address)


def _backoff_delay(attempt: int) -> float:
    return min(0.25 * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)


def _response_retry_delay(response: httpx.Response, attempt: int) -> float:
    from datetime import datetime, timezone
    from email.utils import parsedate_to_datetime
    from math import isfinite

    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            seconds = float(retry_after)
            if isfinite(seconds):
                return min(max(seconds, 0.0), MAX_RETRY_DELAY_SECONDS)
        except ValueError:
            pass

        try:
            retry_at = parsedate_to_datetime(retry_after)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
            if isfinite(seconds):
                return min(max(seconds, 0.0), MAX_RETRY_DELAY_SECONDS)
        except (TypeError, ValueError, OverflowError):
            pass

    return _backoff_delay(attempt)


def _is_brazilian_result(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    components = result.get("address_components")
    if not isinstance(components, list):
        return False
    for component in components:
        if not isinstance(component, dict):
            continue
        types = component.get("types")
        if isinstance(types, list) and "country" in types:
            return component.get("short_name") == "BR"
    return False


def _extract_api_error(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    if payload.get("error_message"):
        return str(payload["error_message"])
    return None
