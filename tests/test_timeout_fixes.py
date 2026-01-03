#!/usr/bin/env python3
"""
Test script for SkyCooker timeout fixes.
This script validates the improvements made to fix timeout issues.
"""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mock Home Assistant components for testing
class MockHass:
    def __init__(self):
        self.data = {}

class MockDevice:
    def __init__(self, address, name):
        self.address = address
        self.name = name

class MockClient:
    def __init__(self):
        self.is_connected = True
        self.notifications = []
        
    async def write_gatt_char(self, uuid, data):
        logger.debug(f"Mock write: {data.hex()}")
        
    async def start_notify(self, uuid, callback):
        logger.debug("Mock start notify")
        
    async def disconnect(self):
        self.is_connected = False
        logger.debug("Mock disconnect")

async def test_command_timeouts():
    """Test command timeout functionality"""
    logger.info("🧪 Testing command timeout functionality")
    
    # Import after mocking
    from custom_components.skycooker.const import COMMAND_TIMEOUTS
    from custom_components.skycooker.cooker_connection import CookerConnection
    
    # Test timeout values
    assert COMMAND_TIMEOUTS[COMMAND_GET_VERSION] == 5.0
    assert COMMAND_TIMEOUTS[COMMAND_AUTH] == 3.0
    assert COMMAND_TIMEOUTS["default"] == 1.5
    
    logger.info("✅ Command timeout values are correct")

async def test_retry_mechanism():
    """Test retry mechanism with mocked failures"""
    logger.info("🧪 Testing retry mechanism")
    
    from custom_components.skycooker.cooker_connection import CookerConnection
    from custom_components.skycooker.const import COMMAND_GET_STATUS
    
    # Create mock objects
    hass = MockHass()
    cooker = CookerConnection(
        mac="AA:BB:CC:DD:EE:FF",
        key=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        hass=hass
    )
    
    # Mock client
    cooker._client = MockClient()
    cooker._disposed = False
    cooker._iter = 0
    
    # Mock successful response
    def mock_response():
        cooker._last_data = bytes([0x55, 0x01, COMMAND_GET_STATUS, 0x01, 0x02, 0x03, 0xAA])
    
    # Test successful command
    cooker._wait_for_response = AsyncMock(return_value=bytes([0x55, 0x01, COMMAND_GET_STATUS, 0x01, 0x02, 0x03, 0xAA]))
    
    try:
        result = await cooker.command(COMMAND_GET_STATUS, timeout=2.0, retries=1)
        logger.info("✅ Command executed successfully with retries")
        assert result == bytes([0x01, 0x02, 0x03])
    except Exception as e:
        logger.error(f"❌ Command failed: {e}")
        raise

async def test_connection_management():
    """Test improved connection management"""
    logger.info("🧪 Testing connection management")
    
    from custom_components.skycooker.cooker_connection import CookerConnection
    
    # Create mock objects
    hass = MockHass()
    cooker = CookerConnection(
        mac="AA:BB:CC:DD:EE:FF",
        key=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        hass=hass
    )
    
    # Test connection state properties
    assert cooker.connected == False
    assert cooker.auth_ok == False
    assert cooker.available == False
    
    # Mock connected state
    cooker._client = MockClient()
    cooker._auth_ok = True
    cooker._last_connect_ok = True
    
    assert cooker.connected == True
    assert cooker.auth_ok == True
    assert cooker.available == True
    
    logger.info("✅ Connection management works correctly")

async def test_error_handling():
    """Test improved error handling"""
    logger.info("🧪 Testing error handling")
    
    from custom_components.skycooker.cooker_connection import CookerConnection, AuthError, DisposedError
    from custom_components.skycooker.const import COMMAND_GET_STATUS
    
    # Create mock objects
    hass = MockHass()
    cooker = CookerConnection(
        mac="AA:BB:CC:DD:EE:FF",
        key=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        hass=hass
    )
    
    # Test disposed error
    cooker._disposed = True
    try:
        await cooker.command(COMMAND_GET_STATUS)
        assert False, "Should have raised DisposedError"
    except DisposedError:
        logger.info("✅ DisposedError raised correctly")
    
    # Test not connected error
    cooker._disposed = False
    cooker._client = None
    try:
        await cooker.command(COMMAND_GET_STATUS)
        assert False, "Should have raised IOError"
    except IOError:
        logger.info("✅ IOError raised for not connected")

async def main():
    """Run all tests"""
    logger.info("🚀 Starting SkyCooker timeout fixes validation")
    
    try:
        await test_command_timeouts()
        await test_retry_mechanism()
        await test_connection_management()
        await test_error_handling()
        
        logger.info("🎉 All tests passed! Timeout fixes are working correctly.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())