"""Тесты для SkyCooker интеграции."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from custom_components.skycooker.const import *
from custom_components.skycooker.skycooker import SkyCookerProtocol, SkyCookerError
from custom_components.skycooker.cooker_connection import CookerConnection


class TestSkyCookerProtocol:
    """Тесты для протокола мультиварки."""

    def test_get_model_code(self):
        """Тест определения кода модели."""
        assert SkyCookerProtocol.get_model_code("RMC-M40S") == "M40S"
        assert SkyCookerProtocol.get_model_code("RMC-M41S") == "M40S"
        assert SkyCookerProtocol.get_model_code("Unknown-Model") is None

    def test_init_with_unknown_model(self):
        """Тест инициализации с неизвестной моделью."""
        with pytest.raises(SkyCookerError):
            SkyCookerProtocol("Unknown-Model")


class TestCookerConnection:
    """Тесты для соединения с мультиваркой."""

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
    async def test_limit_temp(self, cooker_connection):
        """Тест ограничения температуры."""
        assert cooker_connection.limit_temp(50) == 50
        assert cooker_connection.limit_temp(MIN_TEMPERATURE - 1) == MIN_TEMPERATURE
        assert cooker_connection.limit_temp(MAX_TEMPERATURE + 1) == MAX_TEMPERATURE
        assert cooker_connection.limit_temp(None) is None

    @pytest.mark.asyncio
    async def test_get_mode_name(self, cooker_connection):
        """Тест получения имени режима."""
        assert cooker_connection.get_mode_name(MODE_MULTICOOK) == "Мультиповар"
        assert cooker_connection.get_mode_name(MODE_OFF) == "Выключено"
        assert cooker_connection.get_mode_name(99) == "Режим 99"

    @pytest.mark.asyncio
    async def test_add_stat(self, cooker_connection):
        """Тест добавления статистики."""
        cooker_connection.add_stat(True)
        cooker_connection.add_stat(False)
        cooker_connection.add_stat(True)
        
        assert len(cooker_connection._successes) == 3
        assert cooker_connection.success_rate == 66  # 2 из 3 успешных

    @pytest.mark.asyncio
    async def test_stop(self, cooker_connection):
        """Тест остановки соединения."""
        cooker_connection._disposed = False
        cooker_connection._disconnect = AsyncMock()
        
        cooker_connection.stop()
        
        assert cooker_connection._disposed is True
        cooker_connection._disconnect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])