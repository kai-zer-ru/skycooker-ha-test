"""SkyCooker sensors."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import (ATTR_TEMPERATURE, CONF_FRIENDLY_NAME, CONF_SCAN_INTERVAL,
                                 UnitOfTemperature, UnitOfTime, PERCENTAGE)
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)
from homeassistant.helpers.entity import EntityCategory

from .const import *
from .skycooker import MODE_NAMES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyCooker sensor entities."""
    async_add_entities([
        SkyCookerStatusSensor(hass, entry),
        SkyCookerTemperatureSensor(hass, entry),
        SkyCookerCookingTimeSensor(hass, entry),
        SkyCookerDelayTimeSensor(hass, entry),
        SkyCookerSuccessRateSensor(hass, entry),
    ])


class SkyCookerSensorBase(SensorEntity):
    """Base class for SkyCooker sensors."""

    def __init__(self, hass, entry):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        """Update the sensor."""
        self.schedule_update_ha_state()

    @property
    def cooker(self):
        """Return the cooker connection."""
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self.entry.entry_id + f"_{self.entity_description.key}"

    @property
    def name(self):
        """Return the name."""
        return f"{FRIENDLY_NAME} {self.entry.data.get(CONF_FRIENDLY_NAME, '')} {self.entity_description.name}".strip()

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


class SkyCookerStatusSensor(SkyCookerSensorBase):
    """Status sensor for SkyCooker."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(MODE_NAMES.values()) + ["Выключено"]
    
    def __init__(self, hass, entry):
        """Initialize the status sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Состояние".strip()
        self._attr_unique_id = entry.entry_id + "_status"

    @property
    def native_value(self):
        """Return the current status."""
        if self.cooker._status:
            status = self.cooker._status.status
            mode = self.cooker._status.mode
            
            if status == 0x00:
                return "Бездействие"
            elif status == 0x01:
                return "Настройка"
            elif status == 0x02:
                return "Ожидание"
            elif status == 0x03:
                return "Нагрев"
            elif status == 0x04:
                return "Помощь"
            elif status == 0x05:
                return "Готовка"
            elif status == 0x06:
                return "Подогрев"
            else:
                return "Неизвестно"
        return "Нет данных"

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self.cooker._status:
            attrs.update({
                "connected": self.cooker.connected,
                "auth_ok": self.cooker.auth_ok,
                "success_rate": self.cooker.success_rate,
                "persistent_connection": self.cooker.persistent,
                "poll_interval": self.entry.data.get(CONF_SCAN_INTERVAL, 0),
                "power": self.cooker._status.power,
                "postheat": self.cooker._status.postheat,
                "timer_mode": self.cooker._status.timer_mode,
                "automode": self.cooker._status.automode,
                "language": self.cooker._status.language,
                "autostart": self.cooker._status.autostart,
            })
        return attrs


class SkyCookerTemperatureSensor(SkyCookerSensorBase):
    """Temperature sensor for SkyCooker."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    
    def __init__(self, hass, entry):
        """Initialize the temperature sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Температура".strip()
        self._attr_unique_id = entry.entry_id + "_temperature"

    @property
    def native_value(self):
        """Return the current temperature."""
        return self.cooker.current_temp

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self.cooker._status:
            attrs.update({
                "target_temperature": self.cooker.target_temp,
                "min_temperature": MIN_TEMPERATURE,
                "max_temperature": MAX_TEMPERATURE,
            })
        return attrs


class SkyCookerCookingTimeSensor(SkyCookerSensorBase):
    """Cooking time sensor for SkyCooker."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    
    def __init__(self, hass, entry):
        """Initialize the cooking time sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время готовки".strip()
        self._attr_unique_id = entry.entry_id + "_cooking_time"

    @property
    def native_value(self):
        """Return the current cooking time in minutes."""
        if self.cooker._status:
            hours, minutes = self.cooker._status.hours, self.cooker._status.minutes
            return hours * 60 + minutes
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self.cooker._status:
            attrs.update({
                "hours": self.cooker._status.hours,
                "minutes": self.cooker._status.minutes,
                "min_time": MIN_COOKING_TIME,
                "max_time": MAX_COOKING_TIME,
            })
        return attrs


class SkyCookerDelayTimeSensor(SkyCookerSensorBase):
    """Delay time sensor for SkyCooker."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    
    def __init__(self, hass, entry):
        """Initialize the delay time sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Время отложенного старта".strip()
        self._attr_unique_id = entry.entry_id + "_delay_time"

    @property
    def native_value(self):
        """Return the current delay time in minutes."""
        if self.cooker._status:
            wait_hours, wait_minutes = self.cooker._status.wait_hours, self.cooker._status.wait_minutes
            if wait_hours != -1 and wait_minutes != -1:
                return wait_hours * 60 + wait_minutes
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self.cooker._status:
            attrs.update({
                "wait_hours": self.cooker._status.wait_hours,
                "wait_minutes": self.cooker._status.wait_minutes,
                "min_delay": MIN_DELAY_TIME,
                "max_delay": MAX_DELAY_TIME,
            })
        return attrs


class SkyCookerSuccessRateSensor(SkyCookerSensorBase):
    """Success rate sensor for SkyCooker."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bluetooth-connect"
    
    def __init__(self, hass, entry):
        """Initialize the success rate sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Процент успешных операций".strip()
        self._attr_unique_id = entry.entry_id + "_success_rate"

    @property
    def native_value(self):
        """Return the success rate percentage."""
        return self.cooker.success_rate

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self.cooker._successes:
            total_attempts = len(self.cooker._successes)
            successful_attempts = len([s for s in self.cooker._successes if s])
            attrs.update({
                "total_attempts": total_attempts,
                "successful_attempts": successful_attempts,
                "failed_attempts": total_attempts - successful_attempts,
                "persistent_connection": self.cooker.persistent,
                "poll_interval": self.entry.data.get(CONF_SCAN_INTERVAL, 0),
            })
        return attrs