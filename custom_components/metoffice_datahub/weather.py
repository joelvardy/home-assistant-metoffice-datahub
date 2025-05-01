"""Weather platform for the Met Office (DataHub) integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .metoffice_datahub_api import MetOfficeDataHubAPI

_LOGGER = logging.getLogger(__name__)

# Map Met Office weather codes to Home Assistant weather conditions
# Based on https://www.metoffice.gov.uk/services/data/datapoint/code-definitions
CONDITION_MAP = {
    0: "clear-night",  # Clear night
    1: "sunny",  # Sunny day
    2: "partlycloudy",  # Partly cloudy (night)
    3: "partlycloudy",  # Partly cloudy (day)
    5: "fog",  # Mist
    6: "fog",  # Fog
    7: "cloudy",  # Cloudy
    8: "cloudy",  # Overcast
    9: "lightning-rainy",  # Light rain shower (night)
    10: "lightning-rainy",  # Light rain shower (day)
    11: "rainy",  # Drizzle
    12: "rainy",  # Light rain
    13: "rainy",  # Heavy rain shower (night)
    14: "rainy",  # Heavy rain shower (day)
    15: "rainy",  # Heavy rain
    16: "snowy-rainy",  # Sleet shower (night)
    17: "snowy-rainy",  # Sleet shower (day)
    18: "snowy-rainy",  # Sleet
    19: "snowy",  # Hail shower (night)
    20: "snowy",  # Hail shower (day)
    21: "snowy",  # Hail
    22: "snowy",  # Light snow shower (night)
    23: "snowy",  # Light snow shower (day)
    24: "snowy",  # Light snow
    25: "snowy",  # Heavy snow shower (night)
    26: "snowy",  # Heavy snow shower (day)
    27: "snowy",  # Heavy snow
    28: "lightning",  # Thunder shower (night)
    29: "lightning",  # Thunder shower (day)
    30: "lightning",  # Thunder
}

# Update interval for the Met Office DataHub API (1 hour)
SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Met Office (DataHub) weather platform."""

    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MetOfficeDataHubWeather(api, entry.title)])


class MetOfficeDataHubWeather(WeatherEntity):
    """Representation of a Met Office (DataHub) weather condition."""

    _attr_attribution = "Data provided by the Met Office"
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit = UnitOfLength.METERS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY
        | WeatherEntityFeature.FORECAST_HOURLY
    )
    _attr_should_poll = True

    def __init__(self, api: MetOfficeDataHubAPI, name: str) -> None:
        """Initialize the Met Office (DataHub) weather platform."""

        self._api = api
        self._attr_name = name
        self._attr_unique_id = f"metoffice_datahub_{self._api._latitude}_{self._api._longitude}"
        self._data = None
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Force an immediate update on startup
        await self.async_update()

    async def async_update(self) -> None:
        """Get the latest data from Met Office (DataHub)."""

        try:
            self._data = await self._api.async_get_forecast("hourly")
            self._attr_available = True
        except Exception as err:
            _LOGGER.error("Error fetching Met Office (DataHub) data: %s", err)
            self._attr_available = False
            return

        if not self._data or "features" not in self._data:
            _LOGGER.error("Invalid data received from Met Office (DataHub)")
            return

        # Get the first feature (should be our location)
        feature = self._data["features"][0]
        if not feature or "properties" not in feature:
            _LOGGER.error("Invalid feature data received from Met Office (DataHub)")
            return

        properties = feature["properties"]
        if not properties or "timeSeries" not in properties:
            _LOGGER.error("Invalid properties data received from Met Office (DataHub)")
            return

        # Get the current conditions (first time series entry)
        current = properties["timeSeries"][0]
        if not current:
            _LOGGER.error("Invalid current conditions data received from Met Office (DataHub)")
            return

        # Update current conditions
        self._attr_native_temperature = current["screenTemperature"]
        self._attr_native_apparent_temperature = current["feelsLikeTemperature"]
        self._attr_native_dew_point = current["screenDewPointTemperature"]
        self._attr_humidity = current["screenRelativeHumidity"]
        self._attr_native_pressure = current["mslp"] / 100  # Convert Pa to hPa
        self._attr_native_visibility = current["visibility"]
        self._attr_native_wind_speed = current["windSpeed10m"]
        self._attr_wind_bearing = current["windDirectionFrom10m"]
        self._attr_uv_index = current["uvIndex"]
        self._attr_condition = CONDITION_MAP.get(
            current["significantWeatherCode"], "unknown"
        )

    async def async_forecast_daily(self) -> list[dict[str, Any]] | None:
        """Return the daily forecast."""
        if not self._data:
            return None

        feature = self._data["features"][0]
        properties = feature["properties"]
        time_series = properties["timeSeries"]

        # Group hourly data into daily forecasts
        daily_forecasts = []
        current_day = None
        daily_data = []

        for entry in time_series:
            timestamp = dt_util.parse_datetime(entry["time"])
            if not timestamp:
                continue

            day = timestamp.date()
            if current_day is None:
                current_day = day
            elif day != current_day:
                # Process the previous day's data
                if daily_data:
                    forecast = self._create_daily_forecast(daily_data)
                    daily_forecasts.append(forecast)
                daily_data = []
                current_day = day

            daily_data.append(entry)

        # Add the last day's forecast
        if daily_data:
            forecast = self._create_daily_forecast(daily_data)
            daily_forecasts.append(forecast)

        return daily_forecasts

    def _create_daily_forecast(self, daily_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Create a daily forecast from hourly data."""
        temps = [entry["screenTemperature"] for entry in daily_data]
        conditions = [entry["significantWeatherCode"] for entry in daily_data]
        wind_speeds = [entry["windSpeed10m"] for entry in daily_data]
        wind_bearings = [entry["windDirectionFrom10m"] for entry in daily_data]
        precip_probs = [entry["probOfPrecipitation"] for entry in daily_data]

        # Get the most common condition for the day
        condition_code = max(set(conditions), key=conditions.count)

        return {
            ATTR_FORECAST_TIME: daily_data[0]["time"],
            ATTR_FORECAST_NATIVE_TEMP: max(temps),
            ATTR_FORECAST_NATIVE_TEMP_LOW: min(temps),
            ATTR_FORECAST_CONDITION: CONDITION_MAP.get(condition_code, "unknown"),
            ATTR_FORECAST_NATIVE_PRECIPITATION: sum(
                entry["precipitationRate"] for entry in daily_data
            ),
            ATTR_FORECAST_PRECIPITATION_PROBABILITY: max(precip_probs),
            ATTR_FORECAST_WIND_SPEED: max(wind_speeds),
            ATTR_FORECAST_WIND_BEARING: sum(wind_bearings) / len(wind_bearings),
        }

    async def async_forecast_hourly(self) -> list[dict[str, Any]] | None:
        """Return the hourly forecast."""
        if not self._data:
            return None

        feature = self._data["features"][0]
        properties = feature["properties"]
        time_series = properties["timeSeries"]

        return [
            {
                ATTR_FORECAST_TIME: entry["time"],
                ATTR_FORECAST_NATIVE_TEMP: entry["screenTemperature"],
                ATTR_FORECAST_CONDITION: CONDITION_MAP.get(
                    entry["significantWeatherCode"], "unknown"
                ),
                ATTR_FORECAST_NATIVE_PRECIPITATION: entry["precipitationRate"],
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: entry["probOfPrecipitation"],
                ATTR_FORECAST_WIND_SPEED: entry["windSpeed10m"],
                ATTR_FORECAST_WIND_BEARING: entry["windDirectionFrom10m"],
            }
            for entry in time_series
        ]
