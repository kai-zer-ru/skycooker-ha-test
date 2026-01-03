"""SkyCooker switches."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_FRIENDLY_NAME
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)

from .const import *
from .cooker_connection import CookerConnection

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyCooker switch entities."""
    async_add_entities([
        SkyCookerPowerSwitch(hass, entry),
        SkyCookerPostHeatSwitch(hass, entry),
        SkyCookerTimerModeSwitch(hass, entry),
    ])


class SkyCookerSwitchBase(SwitchEntity):
    """Base class for SkyCooker switches."""

    def __init__(self, hass, entry):
        """Initialize the switch."""
        self.hass = hass
        self.entry = entry

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        """Update the switch."""
        self.schedule_update_ha_state()

    @property
    def cooker(self):
        """Return the cooker connection."""
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self.entry.entry_id + f"_{self._attr_unique_id.split('_')[-1]}"

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


class SkyCookerPowerSwitch(SkyCookerSwitchBase):
    """Power switch for SkyCooker."""

    def __init__(self, hass, entry):
        """Initialize the power switch."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Питание".strip()
        self._attr_unique_id = entry.entry_id + "_power"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.cooker.target_mode is not None

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        # Для включения нужно выбрать режим
        # По умолчанию включаем режим "Мультиповар"
        _LOGGER.info("🔌 Power switch: Turning on cooker")
        await self.cooker.set_target_mode("Мультиповар")
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.info("🔌 Power switch: Turning off cooker")
        await self.cooker.set_target_mode("Выключено")
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerPostHeatSwitch(SkyCookerSwitchBase):
    """Post-heat switch for SkyCooker."""

    def __init__(self, hass, entry):
        """Initialize the post-heat switch."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Подогрев".strip()
        self._attr_unique_id = entry.entry_id + "_postheat"

    @property
    def is_on(self):
        """Return true if post-heat is on."""
        return self.cooker.postheat_enabled

    async def async_turn_on(self, **kwargs):
        """Turn post-heat on."""
        _LOGGER.info("🔥 Post-heat switch: Turning on post-heat")
        await self.cooker.set_post_heat(True)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn post-heat off."""
        _LOGGER.info("🔥 Post-heat switch: Turning off post-heat")
        await self.cooker.set_post_heat(False)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)


class SkyCookerTimerModeSwitch(SkyCookerSwitchBase):
    """Timer mode switch for SkyCooker."""

    def __init__(self, hass, entry):
        """Initialize the timer mode switch."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Режим таймера".strip()
        self._attr_unique_id = entry.entry_id + "_timer_mode"

    @property
    def is_on(self):
        """Return true if timer mode is on."""
        return self.cooker.timer_mode

    async def async_turn_on(self, **kwargs):
        """Turn timer mode on."""
        # Переключение в режим установки времени отложенного старта
        # Это логическое переключение, не требующее команды устройству
        _LOGGER.info("⏰ Timer mode switch: Turning on timer mode")
        self.cooker.timer_mode = True
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn timer mode off."""
        # Переключение в режим установки времени готовки
        _LOGGER.info("⏰ Timer mode switch: Turning off timer mode")
        self.cooker.timer_mode = False
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)