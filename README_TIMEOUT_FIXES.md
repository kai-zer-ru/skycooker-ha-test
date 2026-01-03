# SkyCooker Integration - Timeout Fixes and Improvements

## Overview

This document describes the improvements made to fix timeout issues in the SkyCooker Home Assistant integration for Redmond RMC-M40S multicookers.

**Русская версия:** [README_TIMEOUT_FIXES_RU.md](README_TIMEOUT_FIXES_RU.md)

## Problems Identified

### 1. Command Timeout Issues
- **Fixed 1.5s timeout** was too short for some operations
- **No adaptive timeout** based on command type
- **No retry mechanism** for individual commands
- **Race condition** in response handling with 0.05s polling

### 2. Connection Management Problems
- **No connection state validation** before sending commands
- **Inconsistent error handling** between connection and command levels
- **No connection health monitoring**

### 3. Protocol Implementation Issues
- **Missing command constants** in const.py
- **Inconsistent command handling** between base class and connection class
- **No command queuing** for concurrent operations

## Solutions Implemented

### 1. Adaptive Timeout System

Added command-specific timeouts in `const.py`:

```python
COMMAND_TIMEOUTS = {
    COMMAND_AUTH: 3.0,              # Аутентификация может быть медленной
    COMMAND_GET_VERSION: 5.0,       # Получение версии
    COMMAND_GET_STATUS: 2.0,        # Получение статуса
    COMMAND_SET_MAIN_MODE: 3.0,     # Установка режима
    COMMAND_TURN_ON: 2.0,           # Включение
    COMMAND_TURN_OFF: 2.0,          # Выключение
    COMMAND_SET_TEMPERATURE: 2.0,   # Установка температуры
    COMMAND_SET_COOKING_TIME: 2.0,  # Установка времени готовки
    COMMAND_SET_DELAY_TIME: 2.0,    # Установка отложенного старта
    COMMAND_SET_POST_HEAT: 2.0,     # Установка подогрева
    "default": 1.5                  # Стандартный таймаут
}
```

### 2. Enhanced Command Handling

The `command()` method now includes:
- **Adaptive timeouts** based on command type
- **Automatic retries** with exponential backoff
- **Improved error handling** with specific timeout exceptions
- **Adaptive polling** that increases interval over time

### 3. Improved Connection Management

Enhanced `_connect_if_need()` method with:
- **Better logging** for connection states
- **More descriptive error messages**
- **Proper authentication handling**
- **Connection health monitoring**

### 4. Test Connection Function

Added comprehensive testing function `test_connection()` that:
- **Tests all basic commands** (status, version, power)
- **Validates authentication**
- **Tests temperature and mode setting**
- **Provides detailed logging** of results
- **Returns structured results** for analysis

## Usage

### Testing Connection (Development)

To test the connection and commands during development:

1. **Via Home Assistant Service**:
   ```yaml
   # In Home Assistant Developer Tools -> Services
   service: skycooker.test_connection
   ```

2. **Programmatically**:
   ```python
   # In your code
   results = await cooker.test_connection()
   for result in results:
       print(f"{result['test']}: {result['status']} - {result['details']}")
   ```

### Command Timeout Configuration

You can customize timeouts by modifying the `COMMAND_TIMEOUTS` dictionary in `const.py`:

```python
# Increase timeout for specific commands
COMMAND_TIMEOUTS[COMMAND_GET_VERSION] = 10.0  # 10 seconds for version check
```

### Manual Command Testing

For manual testing of specific commands:

```python
# Test with custom timeout and retries
response = await cooker.command(
    COMMAND_GET_STATUS,
    timeout=3.0,  # Custom timeout
    retries=3     # Custom retry count
)
```

## Testing

### Unit Tests

Comprehensive unit tests are located in the `tests/` directory:

```bash
# Run all tests
python -m pytest tests/

# Run timeout-specific tests
python -m pytest tests/test_timeout_fixes.py -v

# Run with coverage
python -m pytest tests/ --cov=custom_components.skycooker
```

## Error Handling

### Timeout Errors

- **TimeoutError**: Raised when command response timeout is exceeded
- **IOError**: Raised for invalid responses or connection issues
- **AuthError**: Raised specifically for authentication failures

### Retry Logic

Commands automatically retry with:
- **Exponential backoff**: 0.2s, 0.4s, 0.6s delays
- **Configurable retry count**: Default 2 retries
- **Smart retry conditions**: Only on timeouts and certain errors

## Logging

Enhanced logging provides detailed information:

```
🧪 Starting connection test
🔌 Testing connection...
✅ Connection: Connected successfully
🔑 Testing authentication...
✅ Authentication: Auth successful
📤 Testing command: Get Status (0x06)
✅ Command Get Status: Response: 0101003c00000000000000000000000000000000
🌡️ Testing temperature setting...
✅ Set Temperature: Temperature set to 60°C
⚙️ Testing mode switching...
✅ Set Mode: Mode set to Выпечка
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**:
   - Ensure pairing mode is enabled on the cooker
   - Check MAC address is correct
   - Verify password/key is correct

2. **Connection Timeout**:
   - Check Bluetooth is enabled on the host
   - Ensure cooker is within range
   - Try increasing timeout values

3. **Command Timeout**:
   - Some commands naturally take longer (like version check)
   - Increase timeout for specific commands if needed
   - Check cooker battery level

### Debug Mode

Enable debug logging in Home Assistant configuration:

```yaml
logger:
  default: info
  logs:
    custom_components.skycooker: debug
```

## Performance Improvements

### Adaptive Polling

The response waiting mechanism now:
- **Starts with fast polling** (50ms intervals)
- **Increases interval over time** (up to 200ms)
- **Reduces CPU usage** during long waits

### Connection Reuse

- **Persistent connections** reduce connection overhead
- **Smart reconnection** only when needed
- **Proper cleanup** of failed connections

## Backward Compatibility

All changes maintain backward compatibility:
- **Existing configurations** continue to work
- **Default timeouts** remain the same for most commands
- **API remains unchanged** for external integrations

## Future Improvements

Potential areas for further enhancement:
1. **Command queuing** for concurrent operations
2. **Connection pooling** for multiple devices
3. **Advanced error recovery** with automatic fallbacks
4. **Performance metrics** collection and reporting