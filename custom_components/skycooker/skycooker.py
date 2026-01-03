import logging
from collections import namedtuple
from struct import pack, unpack
from abc import abstractmethod
from .const import VERSION_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Названия режимов
MODE_NAMES = {
    0x01: "Тушение",
    0x02: "Варка",
    0x03: "Выпечка",
    0x04: "На пару",
    0x05: "Йогурт",
    0x06: "Мультиповар",
    0x07: "Суп",
    0x08: "Паста",
    0x09: "Рис",
    0x0A: "Хлеб",
    0x0B: "Десерт",
    0x0C: "Подогрев",
    0xFF: "Выключено"
}

# Названия состояний
STATUS_NAMES = {
    0x00: "Бездействие",
    0x01: "Настройка",
    0x02: "Ожидание",
    0x03: "Нагрев",
    0x04: "Помощь",
    0x05: "Готовка",
    0x06: "Подогрев"
}

# Структура состояния мультиварки
CookerState = namedtuple("CookerState", [
    "status",           # Состояние (0x00-0x06)
    "mode",             # Режим готовки
    "submode",          # Подрежим (для некоторых режимов)
    "temperature",      # Текущая температура
    "target_temperature", # Целевая температура
    "hours",            # Часы готовки
    "minutes",          # Минуты готовки
    "wait_hours",       # Часы отложенного старта
    "wait_minutes",     # Минуты отложенного старта
    "heat",             # Подогрев после готовки
    "version",          # Версия прошивки
    "language",         # Язык интерфейса
    "autostart",        # Автозапуск
    "power",            # Включена/выключена
    "postheat",         # Подогрев включен
    "timer_mode",       # Режим таймера
    "automode"          # Автоматический режим
])

class SkyCookerProtocol:
    """Протокол для управления мультиваркой Redmond RMC-M40S"""
    
    UUID_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    UUID_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    UUID_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    
    def __init__(self, model):
        self.model = model
        self.model_code = self.get_model_code(model)
        if not self.model_code:
            raise SkyCookerError(f"Unknown cooker model: {model}")
    
    @staticmethod
    def get_model_code(model):
        """Определение кода модели"""
        if model in ["RMC-M40S", "RMC-M41S", "RMC-M42S", "RMC-M43S", "RMC-M44S",
                     "RMC-M45S", "RMC-M46S", "RMC-M47S", "RMC-M48S", "RMC-M49S"]:
            return "M40S"
        elif model in ["RK-M216S", "RK-M215S", "RK-M223S", "RK-G200S", "RK-G211S"]:
            return "M216S"  # Используем протокол от чайников
        return None
    
    @abstractmethod
    async def command(self, command, params=[]):
        """Отправка команды устройству"""
        pass
    
    async def auth(self, key):
        """Аутентификация с устройством"""
        _LOGGER.debug(f"🔑 Auth: Starting authentication with key: {key}")
        try:
            r = await self.command(0xFF, key)
            ok = r[0] != 0
            _LOGGER.debug(f"🔑 Auth: response={r}, ok={ok}")
            return ok
        except Exception as e:
            _LOGGER.error(f"❌ Auth: Authentication failed with error: {e}")
            raise
    
    async def get_version(self):
        """Получение версии прошивки"""
        _LOGGER.debug("📋 Get version: Requesting firmware version")
        # Используем увеличенный таймаут для получения версии
        original_timeout = getattr(self, 'BLE_RECV_TIMEOUT', 1.5)
        self.BLE_RECV_TIMEOUT = VERSION_TIMEOUT
        try:
            r = await self.command(0x01)
            major, minor = unpack("BB", r)
            ver = f"{major}.{minor}"
            _LOGGER.debug(f"📋 Get version: Firmware version {ver} (major={major}, minor={minor})")
            return (major, minor)
        except Exception as e:
            _LOGGER.error(f"❌ Get version: Failed to get version with error: {e}")
            # Для некоторых моделей команда получения версии может не работать
            # Возвращаем заглушку, чтобы не прерывать работу интеграции
            return (0, 0)
        finally:
            self.BLE_RECV_TIMEOUT = original_timeout
    
    async def turn_on(self):
        """Включение мультиварки"""
        _LOGGER.debug("🔌 Turn on: Sending power on command")
        try:
            r = await self.command(0x03)
            if r[0] != 1:
                _LOGGER.error(f"❌ Turn on: Failed to turn on, response: {r}")
                raise SkyCookerError("Can't turn on cooker")
            _LOGGER.info("✅ Turn on: Cooker successfully turned on")
        except Exception as e:
            _LOGGER.error(f"❌ Turn on: Exception occurred: {e}")
            raise
    
    async def turn_off(self):
        """Выключение мультиварки"""
        _LOGGER.debug("🔌 Turn off: Sending power off command")
        try:
            r = await self.command(0x04)
            if r[0] != 1:
                _LOGGER.error(f"❌ Turn off: Failed to turn off, response: {r}")
                raise SkyCookerError("Can't turn off cooker")
            _LOGGER.info("✅ Turn off: Cooker successfully turned off")
        except Exception as e:
            _LOGGER.error(f"❌ Turn off: Exception occurred: {e}")
            raise
    
    async def set_main_mode(self, mode, temperature=0, hours=0, minutes=0):
        """Установка основного режима"""
        _LOGGER.debug(f"⚙️ Set main mode: mode={mode}, temp={temperature}, time={hours}:{minutes}")
        try:
            if mode == 0xFF:  # Выключение
                _LOGGER.debug("⚙️ Set main mode: Mode 0xFF detected, calling turn_off")
                await self.turn_off()
                return
            
            # Формирование данных для команды
            data = pack("BBBBBB", mode, 0, temperature, hours, minutes, 0)
            _LOGGER.debug(f"⚙️ Set main mode: Packed data: {[hex(b) for b in data]}")
            
            r = await self.command(0x05, data)
            if r[0] != 1:
                _LOGGER.error(f"❌ Set main mode: Failed to set mode, response: {r}")
                raise SkyCookerError("Can't set mode")
            
            mode_name = MODE_NAMES.get(mode, f"Unknown({mode})")
            _LOGGER.info(f"✅ Set main mode: Successfully set mode '{mode_name}', temp={temperature}°C, time={hours}:{minutes:02d}")
        except Exception as e:
            _LOGGER.error(f"❌ Set main mode: Exception occurred: {e}")
            raise
    
    async def get_status(self):
        """Получение текущего состояния"""
        _LOGGER.debug("📊 Get status: Requesting current cooker status")
        try:
            r = await self.command(0x06)
            _LOGGER.debug(f"📊 Get status: Raw response: {[hex(b) for b in r]}")
            
            # Разбор ответа
            status = r[11]  # Состояние
            mode = r[3] + 1  # Режим
            submode = r[4]  # Подрежим
            temperature = r[5]  # Температура
            target_temp = r[5]  # Целевая температура
            hours = r[6]  # Часы
            minutes = r[7]  # Минуты
            wait_hours = r[8] - r[6]  # Ожидание часов
            wait_minutes = r[9] - r[7]  # Ожидание минут
            heat = r[10]  # Подогрев
            
            _LOGGER.debug(f"📊 Get status: Parsed values - status={status}, mode={mode}, submode={submode}, "
                         f"temp={temperature}, hours={hours}, minutes={minutes}, "
                         f"wait_hours={wait_hours}, wait_minutes={wait_minutes}, heat={heat}")
            
            cooker_state = CookerState(
                status=status,
                mode=mode,
                submode=submode,
                temperature=temperature,
                target_temperature=target_temp,
                hours=hours,
                minutes=minutes,
                wait_hours=wait_hours,
                wait_minutes=wait_minutes,
                heat=heat,
                version=None,  # Будет установлено позже
                language=1,    # Русский по умолчанию
                autostart=False,
                power=status > 0,
                postheat=heat == 1,
                timer_mode=False,
                automode=False
            )
            
            status_name = STATUS_NAMES.get(status, f"Unknown({status})")
            mode_name = MODE_NAMES.get(mode, f"Unknown({mode})")
            _LOGGER.info(f"✅ Get status: Current state - {status_name}, mode: {mode_name}, "
                        f"temp: {temperature}°C, time: {hours}:{minutes:02d}")
            
            return cooker_state
        except Exception as e:
            _LOGGER.error(f"❌ Get status: Failed to get status with error: {e}")
            raise
    
    async def set_temperature(self, temperature):
        """Установка температуры"""
        data = pack("B", temperature)
        r = await self.command(0x0B, data)
        if r[0] != 1:
            raise SkyCookerError("Can't set temperature")
        _LOGGER.debug(f"Temperature set: {temperature}")
    
    async def set_cooking_time(self, hours, minutes):
        """Установка времени готовки"""
        data = pack("BB", hours, minutes)
        r = await self.command(0x0C, data)
        if r[0] != 1:
            raise SkyCookerError("Can't set cooking time")
        _LOGGER.debug(f"Cooking time set: {hours}:{minutes}")
    
    async def set_delay_time(self, wait_hours, wait_minutes, hours, minutes):
        """Установка времени отложенного старта"""
        total_hours = wait_hours + hours
        total_minutes = wait_minutes + minutes
        if total_minutes >= 60:
            total_hours += 1
            total_minutes -= 60
        
        data = pack("BB", total_hours, total_minutes)
        r = await self.command(0x14, data)
        if r[0] != 1:
            raise SkyCookerError("Can't set delay time")
        _LOGGER.debug(f"Delay time set: {wait_hours}:{wait_minutes}")
    
    async def set_post_heat(self, enabled):
        """Установка подогрева после готовки"""
        data = pack("B", 1 if enabled else 0)
        r = await self.command(0x16, data)
        if r[0] != 1:
            raise SkyCookerError("Can't set post heat")
        _LOGGER.debug(f"Post heat set: {enabled}")


class SkyCookerError(Exception):
    """Исключение для ошибок мультиварки"""
    pass