"""SkyCooker numbers."""
import logging

from homeassistant.components.number import NumberEntity, NumberDeviceClass, NumberMode
from homeassistant.const import CONF_FRIENDLY_NAME, UnitOfTemperature
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)

from .const import *
from .cooker_connection import CookerConnection

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyCooker number entities."""
    async_add_entities([
        SkyCookerTemperatureNumber(hass, entry),
        SkyCookerCookingTimeHoursNumber(hass, entry),
        SkyCookerCookingTimeMinutesNumber(hass, entry),
        SkyCookerDelayTimeHoursNumber(hass, entry),
        SkyCookerDelayTimeMinutesNumber(hass, entry),
    ])


class SkyCookerNumberBase(NumberEntity):
    """Base class for SkyCooker numbers."""

    def __init__(self, hass, entry):
        """Initialize the number."""
        self.hass = hass
        self.entry = entry

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        """Update the number."""
        self.schedule_update_ha_state()

    @property
    def cooker(self):
        """Return the cooker connection."""
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._attr_unique_id

    @property
    def name(self):
        """Return the name."""
        return self._attr_name

    @property
    def device_info(self):
        """Return device info."""
        return self.hass.data[DOMAIN][DATA_DEVICE_INFO]()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.cooker.available


class SkyCookerTemperatureNumber(SkyCookerNumberBase):
    """Temperature number for SkyCooker."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_TEMPERATURE
    _attr_native_max_value = MAX_TEMPERATURE
    _attr_native_step = 1
    
    def __init__(self, hass, entry):
        """Initialize the temperature number."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Температура".strip()
        self._attr_unique_id = entry.entry_id + "_temperature_number"

    @property
    def native_value(self):
        """Return the current temperature."""
        return self.cooker.target_temp

    async def async_set_native_value(self, value):
        """Set the temperature."""
        _LOGGER.info(f"🌡️ Setting temperature to {value}")
        await self.cooker.set_target_temp(int(value))
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerCookingTimeHoursNumber(SkyCookerNumberBase):
    """Cooking time hours number for SkyCooker."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    
    def __init__(self, hass, entry):
        """Initialize the cooking time hours number."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время готовки (часы)".strip()
        self._attr_unique_id = entry.entry_id + "_cooking_hours"

    @property
    def native_value(self):
        """Return the current cooking time hours."""
        if self.cooker._status:
            return self.cooker._status.hours
        return 0

    async def async_set_native_value(self, value):
        """Set the cooking time hours."""
        _LOGGER.info(f"⏰ Setting cooking time hours to {value}")
        hours, minutes = self.cooker.cooking_time
        await self.cooker.set_cooking_time(int(value), minutes if minutes else 0)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerCookingTimeMinutesNumber(SkyCookerNumberBase):
    """Cooking time minutes number for SkyCooker."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 59
    _attr_native_step = 1
    
    def __init__(self, hass, entry):
        """Initialize the cooking time minutes number."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время готовки (минуты)".strip()
        self._attr_unique_id = entry.entry_id + "_cooking_minutes"

    @property
    def native_value(self):
        """Return the current cooking time minutes."""
        if self.cooker._status:
            return self.cooker._status.minutes
        return 0

    async def async_set_native_value(self, value):
        """Set the cooking time minutes."""
        _LOGGER.info(f"⏰ Setting cooking time minutes to {value}")
        hours, minutes = self.cooker.cooking_time
        await self.cooker.set_cooking_time(hours if hours else 0, int(value))
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerDelayTimeHoursNumber(SkyCookerNumberBase):
    """Delay time hours number for SkyCooker."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    
    def __init__(self, hass, entry):
        """Initialize the delay time hours number."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время отложенного старта (часы)".strip()
        self._attr_unique_id = entry.entry_id + "_delay_hours"

    @property
    def native_value(self):
        """Return the current delay time hours."""
        if self.cooker._status:
            wait_hours = self.cooker._status.wait_hours
            if wait_hours != -1:
                return wait_hours
        return 0

    async def async_set_native_value(self, value):
        """Set the delay time hours."""
        _LOGGER.info(f"Setting delay time hours to {value}")
        wait_hours, wait_minutes = self.cooker.delay_time
        hours, minutes = self.cooker.cooking_time
        await self.cooker.set_delay_time(int(value), wait_minutes if wait_minutes else 0, 
                                       hours if hours else 0, minutes if minutes else 0)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerDelayTimeMinutesNumber(SkyCookerNumberBase):
    """Delay time minutes number for SkyCooker."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 59
    _attr_native_step = 1
    
    def __init__(self, hass, entry):
        """Initialize the delay time minutes number."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время отложенного старта (минуты)".strip()
        self._attr_unique_id = entry.entry_id + "_delay_minutes"

    @property
    def native_value(self):
        """Return the current delay time minutes."""
        if self.cooker._status:
            wait_minutes = self.cooker._status.wait_minutes
            if wait_minutes != -1:
                return wait_minutes
        return 0

    async def async_set_native_value(self, value):
        """Set the delay time minutes."""
        _LOGGER.info(f"Setting delay time minutes to {value}")
        wait_hours, wait_minutes = self.cooker.delay_time
        hours, minutes = self.cooker.cooking_time
        await self.cooker.set_delay_time(wait_hours if wait_hours else 0, int(value),
                                       hours if hours else 0, minutes if minutes else 0)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)