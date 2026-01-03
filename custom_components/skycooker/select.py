"""SkyCooker selects."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_FRIENDLY_NAME
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)

from .const import *
from .cooker_connection import CookerConnection

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyCooker select entities."""
    async_add_entities([
        SkyCookerModeSelect(hass, entry),
    ])


class SkyCookerSelectBase(SelectEntity):
    """Base class for SkyCooker selects."""

    def __init__(self, hass, entry):
        """Initialize the select."""
        self.hass = hass
        self.entry = entry

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        """Update the select."""
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


class SkyCookerModeSelect(SkyCookerSelectBase):
    """Mode select for SkyCooker."""

    def __init__(self, hass, entry):
        """Initialize the mode select."""
        super().__init__(hass, entry)
        self._attr_name = f"{FRIENDLY_NAME} {entry.data.get(CONF_FRIENDLY_NAME, '')} Режим готовки".strip()
        self._attr_unique_id = entry.entry_id + "_mode"
        self._attr_options = list(MODE_NAMES.values())

    @property
    def current_option(self):
        """Return the current selected option."""
        if self.cooker._status:
            mode = self.cooker._status.mode
            return MODE_NAMES.get(mode, "Неизвестно")
        return "Нет данных"

    async def async_select_option(self, option):
        """Change the selected option."""
        _LOGGER.info(f"⚙️ Setting mode to {option}")
        await self.cooker.set_target_mode(option)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)