import asyncio
import logging
import traceback
from time import monotonic

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

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

    async def test_connection(self, test_commands=None):
        """Тестирование соединения и команд для разработки"""
        _LOGGER.info("🧪 Starting connection test")
        
        if test_commands is None:
            test_commands = [
                {"cmd": COMMAND_GET_STATUS, "name": "Get Status"},
                {"cmd": COMMAND_GET_VERSION, "name": "Get Version", "timeout": 5.0},
                {"cmd": COMMAND_TURN_OFF, "name": "Turn Off", "params": []},
            ]
        
        results = []
        
        try:
            # Проверка подключения
            _LOGGER.info("🔌 Testing connection...")
            await self._connect_if_need()
            results.append({"test": "Connection", "status": "OK", "details": "Connected successfully"})
            
            # Проверка аутентификации
            _LOGGER.info("🔑 Testing authentication...")
            if not self._auth_ok:
                auth_result = await self.auth()
                if auth_result:
                    results.append({"test": "Authentication", "status": "OK", "details": "Auth successful"})
                else:
                    results.append({"test": "Authentication", "status": "FAIL", "details": "Auth failed"})
                    return results
            else:
                results.append({"test": "Authentication", "status": "OK", "details": "Already authenticated"})
            
            # Тестирование команд
            for test_cmd in test_commands:
                cmd = test_cmd["cmd"]
                name = test_cmd["name"]
                params = test_cmd.get("params", [])
                timeout = test_cmd.get("timeout", None)
                
                _LOGGER.info(f"📤 Testing command: {name} (0x{cmd:02X})")
                
                try:
                    response = await self.command(cmd, params, timeout=timeout, retries=1)
                    results.append({
                        "test": f"Command {name}",
                        "status": "OK",
                        "details": f"Response: {response.hex() if response else 'No response'}"
                    })
                    _LOGGER.info(f"✅ Command {name} successful")
                except Exception as e:
                    results.append({
                        "test": f"Command {name}",
                        "status": "FAIL",
                        "details": f"Error: {type(e).__name__}: {str(e)}"
                    })
                    _LOGGER.error(f"❌ Command {name} failed: {e}")
            
            # Тестирование установки температуры
            _LOGGER.info("🌡️ Testing temperature setting...")
            try:
                await self.set_target_temp(60, "Тушение")
                results.append({"test": "Set Temperature", "status": "OK", "details": "Temperature set to 60°C"})
                _LOGGER.info("✅ Temperature setting successful")
            except Exception as e:
                results.append({"test": "Set Temperature", "status": "FAIL", "details": f"Error: {type(e).__name__}: {str(e)}"})
                _LOGGER.error(f"❌ Temperature setting failed: {e}")
            
            # Тестирование режимов
            _LOGGER.info("⚙️ Testing mode switching...")
            try:
                await self.set_target_mode("Выпечка")
                results.append({"test": "Set Mode", "status": "OK", "details": "Mode set to Выпечка"})
                _LOGGER.info("✅ Mode switching successful")
            except Exception as e:
                results.append({"test": "Set Mode", "status": "FAIL", "details": f"Error: {type(e).__name__}: {str(e)}"})
                _LOGGER.error(f"❌ Mode switching failed: {e}")
            
            # Получение статистики
            results.append({
                "test": "Connection Stats",
                "status": "INFO",
                "details": f"Success rate: {self.success_rate}%, Connected: {self.connected}, Auth: {self.auth_ok}"
            })
            
        except Exception as e:
            results.append({
                "test": "Overall Test",
                "status": "FAIL",
                "details": f"Critical error: {type(e).__name__}: {str(e)}"
            })
            _LOGGER.error(f"❌ Critical error during test: {e}")
        finally:
            # Отключение если не persistent
            if not self.persistent:
                await self.disconnect()
        
        # Логирование результатов
        _LOGGER.info("🧪 Connection test completed:")
        for result in results:
            status_icon = "✅" if result["status"] == "OK" else "❌" if result["status"] == "FAIL" else "ℹ️"
            _LOGGER.info(f"  {status_icon} {result['test']}: {result['status']} - {result['details']}")
        
        return results

    async def command(self, command, params=[], timeout=None, retries=2):
        """Отправка команды устройству с улучшенной обработкой"""
        _LOGGER.debug(f"📤 Command: Sending command 0x{command:02X} with params: {[hex(p) for p in params]}")
        
        if self._disposed:
            _LOGGER.error("❌ Command: Connection is disposed")
            raise DisposedError()
        if not self._client or not self._client.is_connected:
            _LOGGER.error("❌ Command: Not connected to device")
            raise IOError("not connected")
        
        # Определение таймаута для команды
        if timeout is None:
            timeout = COMMAND_TIMEOUTS.get(command, COMMAND_TIMEOUTS["default"])
        
        self._iter = (self._iter + 1) % 256
        _LOGGER.debug(f"📤 Command: Iteration {self._iter}, writing command 0x{command:02x}, timeout: {timeout}s")
        
        data = bytes([0x55, self._iter, command] + list(params) + [0xAA])
        _LOGGER.debug(f"📤 Command: Full packet: {' '.join([f'{b:02x}' for b in data])}")
        
        attempt = 0
        while attempt <= retries:
            attempt += 1
            self._last_data = None
            
            try:
                # Отправка команды
                await self._client.write_gatt_char(self.UUID_TX, data)
                _LOGGER.debug(f"✅ Command: Successfully wrote {len(data)} bytes to device (attempt {attempt})")
                
                # Ожидание ответа с адаптивным polling
                response = await self._wait_for_response(timeout)
                
                # Проверка ответа
                if response[2] != command:
                    _LOGGER.error(f"❌ Command: Invalid response command, expected 0x{command:02X}, got 0x{response[2]:02X}")
                    if attempt <= retries:
                        _LOGGER.debug(f"📤 Command: Retrying command (attempt {attempt}/{retries})")
                        await asyncio.sleep(0.2 * attempt)  # Экспоненциальная задержка
                        continue
                    raise IOError("Invalid response command")
                
                clean = bytes(response[3:-1])
                _LOGGER.debug(f"📥 Command: Clean response data: {' '.join([f'{c:02x}' for c in clean])}")
                return clean
                
            except TimeoutError as e:
                _LOGGER.error(f"❌ Command: Timeout after {timeout}s (attempt {attempt}/{retries})")
                if attempt <= retries:
                    _LOGGER.debug(f"📤 Command: Retrying command after timeout (attempt {attempt}/{retries})")
                    await asyncio.sleep(0.5 * attempt)
                    continue
                raise
            except Exception as e:
                _LOGGER.error(f"❌ Command: Error during command execution: {e}")
                if attempt <= retries:
                    _LOGGER.debug(f"📤 Command: Retrying command after error (attempt {attempt}/{retries})")
                    await asyncio.sleep(0.3 * attempt)
                    continue
                raise
        
        raise IOError(f"Command failed after {retries + 1} attempts")

    async def _wait_for_response(self, timeout):
        """Ожидание ответа с адаптивным polling"""
        timeout_time = monotonic() + timeout
        poll_interval = 0.05  # Начальный интервал polling
        
        while True:
            await asyncio.sleep(poll_interval)
            
            if self._last_data:
                r = self._last_data
                _LOGGER.debug(f"📥 Command: Received raw data: {' '.join([f'{b:02x}' for b in r])}")
                
                # Проверка magic bytes
                if r[0] != 0x55 or r[-1] != 0xAA:
                    _LOGGER.error(f"❌ Command: Invalid response magic, expected 0x55/0xAA, got 0x{r[0]:02X}/0x{r[-1]:02X}")
                    raise IOError("Invalid response magic")
                
                # Проверка iteration
                if r[1] == self._iter:
                    _LOGGER.debug(f"✅ Command: Response iteration matches {self._iter}")
                    return r
                else:
                    _LOGGER.debug(f"⚠️ Command: Iteration mismatch, expected {self._iter}, got {r[1]}, waiting for next packet")
                    self._last_data = None
            
            # Адаптивный polling - увеличиваем интервал со временем
            current_elapsed = monotonic() - (timeout_time - timeout)
            if current_elapsed > timeout * 0.5:  # После половины таймаута увеличиваем интервал
                poll_interval = min(0.2, poll_interval * 1.5)
            
            if monotonic() >= timeout_time:
                _LOGGER.error(f"❌ Command: Receive timeout after {timeout}s")
                raise TimeoutError("Receive timeout")

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
            
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self._device.name or "Unknown Device",
                max_attempts=3
            )
            
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
        """Подключение при необходимости с улучшенной обработкой"""
        # Проверка состояния соединения
        if self._client and not self._client.is_connected:
            _LOGGER.warning("⚠️ Connection lost, attempting to reconnect")
            await self.disconnect()
        
        if not self._client or not self._client.is_connected:
            try:
                _LOGGER.info("🔌 Attempting to connect to cooker")
                await self._connect()
                self._last_connect_ok = True
                _LOGGER.info("✅ Successfully connected to cooker")
            except Exception as ex:
                _LOGGER.error(f"❌ Failed to connect to cooker: {ex}")
                await self.disconnect()
                self._last_connect_ok = False
                raise ex
        
        # Проверка аутентификации
        if not self._auth_ok:
            try:
                _LOGGER.info("🔑 Attempting authentication")
                auth_result = await self.auth()
                self._last_auth_ok = self._auth_ok = auth_result
                if not self._auth_ok:
                    _LOGGER.error("❌ Authentication failed. Please enable pairing mode on the cooker.")
                    raise AuthError("Authentication failed - pairing mode required")
                _LOGGER.info("✅ Authentication successful")
            except AuthError:
                raise
            except Exception as e:
                _LOGGER.error(f"❌ Authentication error: {e}")
                raise AuthError(f"Authentication failed: {e}")
        
        # Получение состояния устройства (если еще не получено)
        if self._status is None:
            try:
                _LOGGER.info("📊 Requesting current cooker status")
                self._status = await self.get_status()
                _LOGGER.info(f"✅ Status retrieved: {self._status}")
            except Exception as e:
                _LOGGER.error(f"❌ Failed to get status: {e}")
                raise

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