"""This module provides a Weather Entity for WeatherFlow."""
from __future__ import annotations

import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    Forecast,
    WeatherEntity,
    WeatherEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utc_from_timestamp

from pyweatherflowrest.data import (
    ForecastDailyDescription,
    ForecastHourlyDescription,
)

from .const import (
    ATTR_FORECAST_FEELS_LIKE,
    ATTR_FORECAST_SUNRISE,
    ATTR_FORECAST_SUNSET,
    ATTR_FORECAST_WIND_GUST,
    ATTR_FORECAST_UV,
    CONDITION_CLASSES,
    DOMAIN,
)
from .entity import WeatherFlowEntity
from .models import WeatherFlowEntryData

_WEATHER_DAILY = "weather_daily"
_WEATHER_HOURLY = "weather_hourly"

_LOGGER = logging.getLogger(__name__)

WEATHER_TYPES: tuple[WeatherEntityDescription, ...] = (
    WeatherEntityDescription(
        key=_WEATHER_DAILY,
        name="Day based Forecast",
    ),
    WeatherEntityDescription(
        key=_WEATHER_HOURLY,
        name="Hourly based Forecast",
    ),
)


def format_condition(condition: str):
    """Map the conditions provided by the weather API to those supported by the frontend."""
    return next(
        (k for k, v in CONDITION_CLASSES.items() if condition in v),
        None,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Add a weather entity from a config_entry."""
    entry_data: WeatherFlowEntryData = hass.data[DOMAIN][entry.entry_id]
    weatherflowapi = entry_data.weatherflowapi
    coordinator = entry_data.coordinator
    forecast_coordinator = entry_data.forecast_coordinator
    station_data = entry_data.station_data

    entities = []
    for description in WEATHER_TYPES:
        entities.append(
            WeatherFlowWeatherEntity(
                weatherflowapi,
                coordinator,
                forecast_coordinator,
                station_data,
                description,
                entry,
                hass.config.units.is_metric,
            )
        )

        _LOGGER.debug(
            "Adding weather entity %s",
            description.name,
        )

    async_add_entities(entities)


class WeatherFlowWeatherEntity(WeatherFlowEntity, WeatherEntity):
    """A WeatherFlow Weather Entity."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # Eight is reasonable in this case.

    def __init__(
        self,
        weatherflowapi,
        coordinator,
        forecast_coordinator,
        station_data,
        description,
        entries: ConfigEntry,
        is_metric: bool,
    ):
        """Initialize an WeatherFlow sensor."""
        super().__init__(
            weatherflowapi,
            coordinator,
            forecast_coordinator,
            station_data,
            description,
            entries,
        )
        self._attr_available = self.forecast_coordinator.last_update_success
        self.daily_forecast = self.entity_description.key in _WEATHER_DAILY
        self._is_metric = is_metric

    @property
    def condition(self):
        """Return the current condition."""
        return format_condition(getattr(self.forecast_coordinator.data, "icon"))

    @property
    def temperature(self):
        """Return the temperature."""
        return getattr(self.coordinator.data, "air_temperature")

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def humidity(self):
        """Return the humidity."""
        return getattr(self.coordinator.data, "relative_humidity")

    @property
    def pressure(self):
        """Return the pressure."""
        return getattr(self.coordinator.data, "sea_level_pressure")

    @property
    def wind_speed(self):
        """Return the wind speed."""
        if getattr(self.coordinator.data, "wind_avg") is None:
            return None

        if self._is_metric:
            return int(round(getattr(self.coordinator.data, "wind_avg") * 3.6))

        return int(round(getattr(self.coordinator.data, "wind_avg")))

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return getattr(self.coordinator.data, "wind_direction")

    @property
    def visibility(self):
        """Return the visibility."""
        return getattr(self.coordinator.data, "visibility")

    @property
    def forecast(self):
        """Return the forecast array."""
        data: Forecast = []
        if self.daily_forecast:
            forecast_data_daily: ForecastDailyDescription = getattr(
                self.forecast_coordinator.data, "forecast_daily"
            )
            for item in forecast_data_daily:
                data.append(
                    {
                        ATTR_FORECAST_TIME: item.utc_time,
                        ATTR_FORECAST_TEMP: item.air_temp_high,
                        ATTR_FORECAST_TEMP_LOW: item.air_temp_low,
                        ATTR_FORECAST_PRECIPITATION: item.precip,
                        ATTR_FORECAST_PRECIPITATION_PROBABILITY: item.precip_probability,
                        ATTR_FORECAST_CONDITION: format_condition(item.icon),
                        ATTR_FORECAST_WIND_SPEED: item.wind_avg,
                        ATTR_FORECAST_WIND_BEARING: item.wind_direction,
                        ATTR_FORECAST_SUNRISE: utc_from_timestamp(item.sunrise),
                        ATTR_FORECAST_SUNSET: utc_from_timestamp(item.sunset),
                    }
                )
            return data

        data: Forecast = []
        forecast_data_hourly: ForecastHourlyDescription = getattr(
            self.forecast_coordinator.data, "forecast_hourly"
        )
        for item in forecast_data_hourly:
            data.append(
                {
                    ATTR_FORECAST_TIME: item.utc_time,
                    ATTR_FORECAST_TEMP: item.air_temperature,
                    ATTR_FORECAST_PRECIPITATION: item.precip,
                    ATTR_FORECAST_PRECIPITATION_PROBABILITY: item.precip_probability,
                    ATTR_FORECAST_CONDITION: format_condition(item.icon),
                    ATTR_FORECAST_WIND_SPEED: item.wind_avg,
                    ATTR_FORECAST_WIND_GUST: item.wind_gust,
                    ATTR_FORECAST_WIND_BEARING: item.wind_direction,
                    ATTR_FORECAST_FEELS_LIKE: item.feels_like,
                    ATTR_FORECAST_UV: item.uv,
                }
            )
        return data
