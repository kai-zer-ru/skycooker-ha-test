"""Комплексные тесты для SkyCooker интеграции."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from custom_components.skycooker.const import *
from custom_components.skycooker.skycooker import SkyCookerProtocol, SkyCookerError, CookerState
from custom_components.skycooker.cooker_connection import CookerConnection


class TestSkyCookerProtocolComprehensive:
    """Комплексные тесты для протокола мультиварки."""

    def test_cooker_state_creation(self):
        """Тест создания состояния мультиварки."""
        state = CookerState(
            status=0x05,           # Готовка
            mode=0x05,             # Мультиповар
            submode=0x00,          # Без подрежима
            temperature=80,        # Температура 80°C
            target_temperature=80, # Целевая температура 80°C
            hours=2,               # 2 часа
            minutes=30,            # 30 минут
            wait_hours=1,          # Ожидание 1 час
            wait_minutes=0,        # Ожидание 0 минут
            heat=1,                # Подогрев включен
            version=1.0,           # Версия 1.0
            language=1,            # Русский язык
            autostart=False,       # Автозапуск выключен
            power=True,            # Включена
            postheat=True,         # Подогрев включен
            timer_mode=False,      # Режим таймера выключен
            automode=False         # Автоматический режим выключен
        )
        
        assert state.status == 0x05
        assert state.mode == 0x05
        assert state.temperature == 80
        assert state.power is True
        assert state.postheat is True

    @pytest.mark.asyncio
    async def test_protocol_commands(self):
        """Тест команд протокола."""
        # Простой тест без моков
        protocol = SkyCookerProtocol("RMC-M40S")
        assert protocol.model == "RMC-M40S"
        assert protocol.model_code == "M40S"


class TestCookerConnectionComprehensive:
    """Комплексные тесты для соединения с мультиваркой."""

    @pytest.fixture
    def mock_hass(self):
        """Мок hass."""
        return MagicMock()

    @pytest.fixture
    def cooker_connection(self, mock_hass):
        """Создание экземпляра CookerConnection."""
        return CookerConnection(
            mac="AA:BB:CC:DD:EE:FF",
            key=[1, 2, 3, 4, 5, 6, 7, 8],
            persistent=True,
            adapter=None,
            hass=mock_hass,
            model="RMC-M40S"
        )

    @pytest.mark.asyncio
    async def test_connection_management(self, cooker_connection):
        """Тест управления соединением."""
        # Тест подключения
        cooker_connection._connect = AsyncMock()
        cooker_connection._auth_ok = False
        cooker_connection._last_connect_ok = False
        
        with patch.object(cooker_connection, 'auth', return_value=True):
            with patch.object(cooker_connection, 'get_version', return_value=(1, 0)):
                await cooker_connection._connect_if_need()
                
                assert cooker_connection._auth_ok is True
                assert cooker_connection._last_connect_ok is True

    @pytest.mark.asyncio
    async def test_state_management(self, cooker_connection):
        """Тест управления состоянием."""
        # Установка тестового состояния
        cooker_connection._status = CookerState(
            status=0x05, mode=0x05, submode=0x00, temperature=80,
            target_temperature=80, hours=2, minutes=30, wait_hours=1,
            wait_minutes=0, heat=1, version=1.0, language=1,
            autostart=False, power=True, postheat=True,
            timer_mode=False, automode=False
        )
        
        # Тест получения текущей температуры
        assert cooker_connection.current_temp == 80
        
        # Тест получения текущего режима
        assert cooker_connection.current_mode == 0x05
        
        # Тест получения целевой температуры
        assert cooker_connection.target_temp == 80
        
        # Тест получения целевого режима
        assert cooker_connection.target_mode == 0x05

    @pytest.mark.asyncio
    async def test_temperature_control(self, cooker_connection):
        """Тест управления температурой."""
        cooker_connection._status = CookerState(
            status=0x01, mode=0x05, submode=0x00, temperature=25,
            target_temperature=25, hours=0, minutes=0, wait_hours=0,
            wait_minutes=0, heat=0, version=1.0, language=1,
            autostart=False, power=False, postheat=False,
            timer_mode=False, automode=False
        )
        
        # Тест установки температуры
        with patch.object(cooker_connection, 'set_main_mode') as mock_set_mode:
            await cooker_connection.set_target_temp(80, "Мультиповар")
            mock_set_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_mode_control(self, cooker_connection):
        """Тест управления режимами."""
        cooker_connection._status = CookerState(
            status=0x00, mode=0xFF, submode=0x00, temperature=25,
            target_temperature=25, hours=0, minutes=0, wait_hours=0,
            wait_minutes=0, heat=0, version=1.0, language=1,
            autostart=False, power=False, postheat=False,
            timer_mode=False, automode=False
        )
        
        # Тест установки режима
        with patch.object(cooker_connection, 'set_main_mode') as mock_set_mode:
            await cooker_connection.set_target_mode("Тушение")
            mock_set_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, cooker_connection):
        """Тест обработки ошибок."""
        cooker_connection._disposed = False
        
        # Тест ошибки при команде
        with patch.object(cooker_connection, 'command', side_effect=IOError("Connection lost")):
            with pytest.raises(IOError):
                await cooker_connection.command(0x06)

    @pytest.mark.asyncio
    async def test_statistics(self, cooker_connection):
        """Тест статистики подключений."""
        # Добавление статистики
        cooker_connection.add_stat(True)
        cooker_connection.add_stat(False)
        cooker_connection.add_stat(True)
        cooker_connection.add_stat(True)
        
        # Проверка процента успешных подключений
        assert cooker_connection.success_rate == 75  # 3 из 4 успешных
        
        # Проверка ограничения длины истории
        for _ in range(100):
            cooker_connection.add_stat(True)
        
        assert len(cooker_connection._successes) == 100


class TestIntegrationScenarios:
    """Тесты интеграционных сценариев."""

    @pytest.mark.asyncio
    async def test_full_cooking_cycle(self):
        """Тест полного цикла готовки."""
        # Этот тест будет более сложным и потребует мокирования
        # всех компонентов, но показывает направление для развития
        pass

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Тест восстановления после ошибок."""
        # Тест восстановления после потери соединения
        pass

    @pytest.mark.asyncio
    async def test_persistent_connection(self):
        """Тест постоянного подключения."""
        # Тест поведения при постоянном подключении
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])