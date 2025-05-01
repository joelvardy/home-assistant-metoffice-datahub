"""API client for the Met Office DataHub integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import aiohttp
from aiohttp import ClientError, ClientResponseError

from .const import BASE_URL, ENDPOINTS

_LOGGER = logging.getLogger(__name__)

ForecastType = Literal["hourly", "three_hourly", "daily"]

class MetOfficeDataHubAPI:
    """API client for Met Office DataHub."""

    def __init__(self, api_key: str, latitude: float, longitude: float) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._latitude = latitude
        self._longitude = longitude
        self._session = aiohttp.ClientSession()

    async def async_get_forecast(self, forecast_type: ForecastType) -> dict[str, Any]:
        """Get forecast data from the API.

        Args:
            forecast_type: Type of forecast to retrieve (hourly, three_hourly, or daily)

        Returns:
            dict: The forecast data from the API

        Raises:
            ClientError: If there is an error communicating with the API
            ValueError: If the forecast type is invalid

        """
        if forecast_type not in ENDPOINTS:
            raise ValueError(f"Invalid forecast type: {forecast_type}")

        endpoint = f"{BASE_URL}{ENDPOINTS[forecast_type]}"
        params = {
            "datasource": "BD1",
            "includeLocationName": "true",
            "latitude": self._latitude,
            "longitude": self._longitude,
            "excludeParameterMetadata": "true"
        }
        headers = {"apikey": self._api_key}

        for attempt in range(3):  # Retry up to 3 times
            try:
                _LOGGER.debug("Making API request for Met Office (DataHub), attempt %d endpoint: %s params: %s", attempt + 1, endpoint, params)
                async with self._session.get(endpoint, params=params, headers=headers) as response:
                    response.raise_for_status()
                    return await response.json()
            except ClientResponseError as err:
                if err.status == 401:
                    _LOGGER.error("Invalid API key for Met Office (DataHub)")
                    raise
                if err.status == 429:
                    if attempt < 2:  # Don't wait on the last attempt
                        _LOGGER.warning("Rate limited by Met Office (DataHub), retrying")
                        await asyncio.sleep(2 ** attempt)
                        continue
                _LOGGER.error("Error fetching Met Office (DataHub) data: %s", err)
                raise
            except ClientError as err:
                if attempt < 2:  # Don't wait on the last attempt
                    _LOGGER.warning("Error communicating with Met Office (DataHub), retrying")
                    await asyncio.sleep(2 ** attempt)
                    continue
                _LOGGER.error("Error communicating with Met Office (DataHub): %s", err)
                raise
        return None

    async def async_close(self) -> None:
        """Close the API client session."""
        await self._session.close()
