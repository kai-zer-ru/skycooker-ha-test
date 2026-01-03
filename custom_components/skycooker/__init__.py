"""Support for SkyCooker."""
import logging
import voluptuous as vol
from datetime import timedelta

import homeassistant.helpers.event as ev
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ATTR_SW_VERSION, CONF_DEVICE,
                                 CONF_FRIENDLY_NAME, CONF_MAC, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, Platform)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import *
from .cooker_connection import CookerConnection

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Sky Cooker integration from a config entry."""
    _LOGGER.info(f"Setting up SkyCooker integration for {entry.data.get(CONF_FRIENDLY_NAME, entry.data[CONF_MAC])}")
    
    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.debug("Init: Created domain data structure")
    if entry.entry_id not in hass.data:
        hass.data[DOMAIN][entry.entry_id] = {}
        _LOGGER.debug(f"Init: Created entry data for {entry.entry_id}")

    cooker = CookerConnection(
        mac=entry.data[CONF_MAC],
        key=entry.data[CONF_PASSWORD],
        persistent=entry.data[CONF_PERSISTENT_CONNECTION],
        adapter=entry.data.get(CONF_DEVICE, None),
        hass=hass,
        model=entry.data.get(CONF_FRIENDLY_NAME, None)
    )
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = cooker
    _LOGGER.info(f"Init: Created cooker connection for {entry.data[CONF_MAC]}")

    async def poll(now, **kwargs) -> None:
        """Polling function for device updates"""
        _LOGGER.debug("Poll: Starting periodic update")
        try:
            await cooker.update()
            await hass.async_add_executor_job(dispatcher_send, hass, DISPATCHER_UPDATE)
            if hass.data[DOMAIN][DATA_WORKING]:
                _LOGGER.debug(f"Poll: Scheduling next poll in {entry.data[CONF_SCAN_INTERVAL]}s")
                schedule_poll(timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]))
            else:
                _LOGGER.info("Poll: Stopping polling, integration not working")
        except Exception as e:
            _LOGGER.error(f"Poll: Error during update: {e}")

    def schedule_poll(td):
        """Schedule next polling"""
        _LOGGER.debug(f"Schedule: Next poll in {td.total_seconds()} seconds")
        hass.data[DOMAIN][DATA_CANCEL] = ev.async_call_later(hass, td, poll)

    # Регистрация сервиса для тестирования соединения
    async def test_connection_service(call):
        """Сервис для тестирования соединения"""
        _LOGGER.info("🔧 Test connection service called")
        try:
            results = await cooker.test_connection()
            _LOGGER.info(f"🔧 Test connection completed with {len(results)} results")
            
            # Логирование результатов в HA log
            for result in results:
                status_icon = "✅" if result["status"] == "OK" else "❌" if result["status"] == "FAIL" else "ℹ️"
                _LOGGER.info(f"  {status_icon} {result['test']}: {result['status']} - {result['details']}")
            
            # Можно добавить уведомление в HA
            hass.bus.fire(f"{DOMAIN}_test_results", {
                "entry_id": entry.entry_id,
                "results": results
            })
            
        except Exception as e:
            _LOGGER.error(f"🔧 Test connection service failed: {e}")
            hass.bus.fire(f"{DOMAIN}_test_error", {
                "entry_id": entry.entry_id,
                "error": str(e)
            })

    # Регистрация сервиса
    hass.services.async_register(
        DOMAIN,
        "test_connection",
        test_connection_service,
        schema={
            vol.Optional("entry_id"): str,
        }
    )

    hass.data[DOMAIN][DATA_WORKING] = True
    hass.data[DOMAIN][DATA_DEVICE_INFO] = lambda: device_info(entry)
    _LOGGER.debug("Init: Set up device info callback")

    # Логирование версии интеграции
    _LOGGER.info(f"🔧 Init: SkyCooker integration version {DEBUG_VERSION}")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(f"🔧 Init: Set up {len(PLATFORMS)} platforms")

    schedule_poll(timedelta(seconds=3))
    _LOGGER.info("Init: Started initial polling")

    return True

def device_info(entry):
    """Информация об устройстве"""
    return DeviceInfo(
        name=(FRIENDLY_NAME + " " + entry.data.get(CONF_FRIENDLY_NAME, "")).strip(),
        manufacturer=MANUFACTORER,
        model=entry.data.get(CONF_FRIENDLY_NAME, None),
        sw_version=entry.data.get(ATTR_SW_VERSION, None),
        identifiers={
            (DOMAIN, entry.data[CONF_MAC])
        },
        connections={
            ("mac", entry.data[CONF_MAC])
        }
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("🔧 Unloading")
    hass.data[DOMAIN][DATA_WORKING] = False
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(entry, component)
        )
    hass.data[DOMAIN][DATA_CANCEL]()
    await hass.async_add_executor_job(hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].stop)
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = None
    _LOGGER.debug("🔧 Entry unloaded")
    return True

async def entry_update_listener(hass, entry):
    """Handle options update."""
    cooker = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION]
    cooker.persistent = entry.data.get(CONF_PERSISTENT_CONNECTION)
    _LOGGER.debug("🔧 Options updated")