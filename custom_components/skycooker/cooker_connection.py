import asyncio
import logging
import traceback
from time import monotonic

from bleak import BleakClient

from homeassistant.components import bluetooth

from .const import *
from .skycooker import SkyCookerProtocol

_LOGGER = logging.getLogger(__name__)


class CookerConnection(SkyCookerProtocol):
    """Класс для управления соединением с мультиваркой"""
    
    BLE_RECV_TIMEOUT = 1.5
    MAX_TRIES = 3
    TRIES_INTERVAL = 0.5
    STATS_INTERVAL = 15
    TARGET_TTL = 30

    def __init__(self, mac, key, persistent=True, adapter=None, hass=None, model=None):
        super().__init__(model)
        self._device = None
        self._client = None
        self._mac = mac
        self._key = key
        self.persistent = persistent
        self.adapter = adapter
        self.hass = hass
        self._auth_ok = False
        self._sw_version = None
        self._iter = 0
        self._update_lock = asyncio.Lock()
        self._last_set_target = 0
        self._last_get_stats = 0
        self._last_connect_ok = False
        self._last_auth_ok = False
        self._successes = []
        self._target_state = None
        self._status = None
        self._disposed = False
        self._last_data = None

    async def command(self, command, params=[]):
        """Отправка команды устройству"""
        _LOGGER.debug(f"📤 Command: Sending command 0x{command:02X} with params: {[hex(p) for p in params]}")
        
        if self._disposed:
            _LOGGER.error("❌ Command: Connection is disposed")
            raise DisposedError()
        if not self._client or not self._client.is_connected:
            _LOGGER.error("❌ Command: Not connected to device")
            raise IOError("not connected")
        
        self._iter = (self._iter + 1) % 256
        _LOGGER.debug(f"📤 Command: Iteration {self._iter}, writing command 0x{command:02x}")
        
        data = bytes([0x55, self._iter, command] + list(params) + [0xAA])
        _LOGGER.debug(f"📤 Command: Full packet: {' '.join([f'{b:02x}' for b in data])}")
        
        self._last_data = None
        try:
            await self._client.write_gatt_char(self.UUID_TX, data)
            _LOGGER.debug(f"✅ Command: Successfully wrote {len(data)} bytes to device")
        except Exception as e:
            _LOGGER.error(f"❌ Command: Failed to write to device: {e}")
            raise
        
        timeout_time = monotonic() + self.BLE_RECV_TIMEOUT
        _LOGGER.debug(f"📥 Command: Waiting for response with timeout {self.BLE_RECV_TIMEOUT}s")
        
        while True:
            await asyncio.sleep(0.05)
            if self._last_data:
                r = self._last_data
                _LOGGER.debug(f"📥 Command: Received raw data: {' '.join([f'{b:02x}' for b in r])}")
                
                if r[0] != 0x55 or r[-1] != 0xAA:
                    _LOGGER.error(f"❌ Command: Invalid response magic, expected 0x55/0xAA, got 0x{r[0]:02X}/0x{r[-1]:02X}")
                    raise IOError("Invalid response magic")
                if r[1] == self._iter:
                    _LOGGER.debug(f"✅ Command: Response iteration matches {self._iter}")
                    break
                else:
                    _LOGGER.debug(f"⚠️ Command: Iteration mismatch, expected {self._iter}, got {r[1]}, waiting for next packet")
                    self._last_data = None
            if monotonic() >= timeout_time:
                _LOGGER.error(f"❌ Command: Receive timeout after {self.BLE_RECV_TIMEOUT}s")
                raise IOError("Receive timeout")
        
        if r[2] != command:
            _LOGGER.error(f"❌ Command: Invalid response command, expected 0x{command:02X}, got 0x{r[2]:02X}")
            raise IOError("Invalid response command")
        
        clean = bytes(r[3:-1])
        _LOGGER.debug(f"📥 Command: Clean response data: {' '.join([f'{c:02x}' for c in clean])}")
        return clean

    def _rx_callback(self, sender, data):
        """Обработка входящих данных"""
        self._last_data = data

    async def _connect(self):
        """Подключение к устройству"""
        _LOGGER.debug(f"Connect: Starting connection to device {self._mac}")
        
        if self._disposed:
            _LOGGER.error("Connect: Connection is disposed")
            raise DisposedError()
        if self._client and self._client.is_connected:
            _LOGGER.debug("Connect: Already connected")
            return
        
        try:
            self._device = bluetooth.async_ble_device_from_address(self.hass, self._mac)
            _LOGGER.debug(f"Connect: Found BLE device: {self._device}")
            
            self._client = BleakClient(self._device)
            await self._client.connect()
            
            _LOGGER.info(f"Connect: Successfully connected to {self._mac}")
            await self._client.start_notify(self.UUID_RX, self._rx_callback)
            _LOGGER.debug("Connect: Subscribed to RX notifications")
        except Exception as e:
            _LOGGER.error(f"Connect: Failed to connect with error: {e}")
            raise

    async def auth(self):
        """Аутентификация"""
        return super().auth(self._key)

    async def _disconnect(self):
        """Отключение от устройства"""
        _LOGGER.debug("Disconnect: Starting disconnection process")
        try:
            if self._client:
                was_connected = self._client.is_connected
                _LOGGER.debug(f"Disconnect: Client was connected: {was_connected}")
                await self._client.disconnect()
                if was_connected:
                    _LOGGER.info("Disconnect: Successfully disconnected from device")
        except Exception as e:
            _LOGGER.error(f"Disconnect: Error during disconnection: {e}")
        finally:
            self._auth_ok = False
            self._device = None
            self._client = None
            _LOGGER.debug("Disconnect: Connection resources cleared")

    async def disconnect(self):
        """Публичный метод отключения"""
        try:
            await self._disconnect()
        except:
            pass

    async def _connect_if_need(self):
        """Подключение при необходимости"""
        if self._client and not self._client.is_connected:
            _LOGGER.debug("Connection lost")
            await self.disconnect()
        
        if not self._client or not self._client.is_connected:
            try:
                await self._connect()
                self._last_connect_ok = True
            except Exception as ex:
                await self.disconnect()
                self._last_connect_ok = False
                raise ex
        
        if not self._auth_ok:
            auth_result = await self.auth()
            self._last_auth_ok = self._auth_ok = auth_result
            if not self._auth_ok:
                _LOGGER.error(f"Auth failed. You need to enable pairing mode on the cooker.")
                raise AuthError("Auth failed")
            _LOGGER.debug("Auth ok")
            self._sw_version = await self.get_version()
            # Синхронизация времени не требуется для мультиварки

    async def _disconnect_if_need(self):
        """Отключение при необходимости"""
        if not self.persistent:
            await self.disconnect()

    async def update(self, tries=MAX_TRIES, force_stats=False, extra_action=None, commit=False):
        """Обновление состояния устройства"""
        _LOGGER.debug(f"Update: Starting update process (tries={tries}, force_stats={force_stats})")
        
        try:
            async with self._update_lock:
                if self._disposed:
                    _LOGGER.warning("Update: Connection is disposed, skipping update")
                    return False
                
                _LOGGER.debug("Update: Acquired update lock")
                if not self.available:
                    _LOGGER.debug("Update: Device not available, forcing stats update")
                    force_stats = True
                
                await self._connect_if_need()

                if extra_action:
                    _LOGGER.debug("Update: Executing extra action")
                    await extra_action

                # Получение текущего состояния
                _LOGGER.debug("Update: Requesting current status")
                self._status = await self.get_status()
                _LOGGER.debug(f"Update: Status updated successfully")
                
                if commit:
                    # Коммит изменений не требуется для мультиварки
                    _LOGGER.debug("Update: Commit requested but not implemented for cooker")

                await self._disconnect_if_need()
                self.add_stat(True)
                _LOGGER.debug("Update: Update process completed successfully")
                return True

        except Exception as ex:
            _LOGGER.error(f"Update: Exception occurred: {type(ex).__name__}: {str(ex)}")
            await self.disconnect()
            if type(ex) == AuthError:
                _LOGGER.warning("Update: Authentication error, returning without retry")
                return False
            self.add_stat(False)
            if tries > 1 and extra_action == None:
                _LOGGER.debug(f"Update: Retrying ({self.MAX_TRIES - tries + 1}/{self.MAX_TRIES}) after {self.TRIES_INTERVAL}s")
                await asyncio.sleep(self.TRIES_INTERVAL)
                return await self.update(tries=tries-1, force_stats=force_stats, extra_action=extra_action, commit=commit)
            else:
                _LOGGER.error(f"Update: Final attempt failed, {type(ex).__name__}: {str(ex)}")
                _LOGGER.debug(traceback.format_exc())
            return False

    def add_stat(self, value):
        """Добавление статистики"""
        self._successes.append(value)
        if len(self._successes) > 100:
            self._successes = self._successes[-100:]

    @staticmethod
    def limit_temp(temp):
        """Ограничение температуры"""
        if temp is not None and temp > MAX_TEMPERATURE:
            return MAX_TEMPERATURE
        elif temp is not None and temp < MIN_TEMPERATURE:
            return MIN_TEMPERATURE
        else:
            return temp

    @staticmethod
    def get_mode_name(mode_id):
        """Получение имени режима"""
        if mode_id == 0xFF:
            return "Выключено"
        return MODE_NAMES.get(mode_id, f"Режим {mode_id}")

    @property
    def success_rate(self):
        """Процент успешных подключений"""
        if len(self._successes) == 0:
            return 0
        return int(100 * len([s for s in self._successes if s]) / len(self._successes))

    async def _set_target_state(self, target_mode, target_temp=0, target_hours=0, target_minutes=0):
        """Установка целевого состояния"""
        await self.set_main_mode(target_mode, target_temp, target_hours, target_minutes)
        self._last_set_target = monotonic()
        await self.update()

    async def cancel_target(self):
        """Отмена целевого состояния"""
        self._target_state = None

    def stop(self):
        """Остановка соединения"""
        if self._disposed:
            return
        self._disconnect()
        self._disposed = True
        _LOGGER.info("Stopped.")

    @property
    def available(self):
        """Доступность устройства"""
        return self._last_connect_ok and self._last_auth_ok

    @property
    def current_temp(self):
        """Текущая температура"""
        if self._status:
            return self._status.temperature
        return None

    @property
    def current_mode(self):
        """Текущий режим"""
        if self._status and self._status.power:
            return self._status.mode
        return None

    @property
    def target_temp(self):
        """Целевая температура"""
        if self._status:
            return self._status.target_temperature
        return None

    @property
    def target_mode(self):
        """Целевой режим"""
        if self._status and self._status.power:
            return self._status.mode
        return None

    @property
    def target_mode_str(self):
        """Строковое представление целевого режима"""
        return self.get_mode_name(self.target_mode)

    async def set_target_temp(self, target_temp, operation_mode=None):
        """Установка целевой температуры"""
        if target_temp == self.target_temp:
            return
        
        _LOGGER.info(f"Setting target temperature to {target_temp}")
        target_mode = self.target_mode
        
        # Определение режима по имени
        if operation_mode:
            for mode_id, mode_name in MODE_NAMES.items():
                if mode_name == operation_mode:
                    target_mode = mode_id
                    break
        
        # Проверка диапазона температуры
        target_temp = self.limit_temp(target_temp)
        
        if target_mode is None:
            target_mode = MODE_MULTICOOK  # По умолчанию мультиповар
        
        await self._set_target_state(target_mode, target_temp)

    async def set_target_mode(self, operation_mode):
        """Установка целевого режима"""
        if operation_mode == self.target_mode_str:
            return
        
        _LOGGER.info(f"Setting target mode to {operation_mode}")
        
        # Поиск ID режима по имени
        target_mode = None
        for mode_id, mode_name in MODE_NAMES.items():
            if mode_name == operation_mode:
                target_mode = mode_id
                break
        
        if target_mode is None:
            _LOGGER.error(f"Unknown operation mode: {operation_mode}")
            return
        
        # Установка режима
        await self._set_target_state(target_mode)

    @property
    def connected(self):
        """Состояние подключения"""
        return True if self._client and self._client.is_connected else False

    @property
    def auth_ok(self):
        """Состояние аутентификации"""
        return self._auth_ok

    @property
    def sw_version(self):
        """Версия прошивки"""
        return self._sw_version

    @property
    def postheat_enabled(self):
        """Включен ли подогрев"""
        if not self._status:
            return None
        return self._status.postheat

    @property
    def timer_mode(self):
        """Режим таймера"""
        if not self._status:
            return None
        return self._status.timer_mode

    @property
    def cooking_time(self):
        """Время готовки"""
        if not self._status:
            return None
        return self._status.hours, self._status.minutes

    @property
    def delay_time(self):
        """Время отложенного старта"""
        if not self._status:
            return None
        return self._status.wait_hours, self._status.wait_minutes


class AuthError(Exception):
    """Ошибка аутентификации"""
    pass


class DisposedError(Exception):
    """Ошибка использования уничтоженного объекта"""
    pass