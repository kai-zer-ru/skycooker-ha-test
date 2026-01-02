"""Constants for SkyCooker component."""

DOMAIN = "skycooker"
FRIENDLY_NAME = "SkyCooker"
MANUFACTORER = "Redmond"
SUGGESTED_AREA = "kitchen"

# Debug version for development
DEBUG_VERSION = "0.0.1"

CONF_PERSISTENT_CONNECTION = "persistent_connection"

DEFAULT_SCAN_INTERVAL = 5
DEFAULT_PERSISTENT_CONNECTION = True

DATA_CONNECTION = "connection"
DATA_CANCEL = "cancel"
DATA_WORKING = "working"
DATA_DEVICE_INFO = "device_info"

DISPATCHER_UPDATE = "update"

# Команды протокола
COMMAND_GET_VERSION = 0x01
COMMAND_TURN_ON = 0x03
COMMAND_TURN_OFF = 0x04
COMMAND_SET_MAIN_MODE = 0x05
COMMAND_GET_STATUS = 0x06
COMMAND_SET_TEMPERATURE = 0x0B
COMMAND_SET_COOKING_TIME = 0x0C
COMMAND_SET_DELAY_TIME = 0x14
COMMAND_SET_POST_HEAT = 0x16
COMMAND_AUTH = 0xFF

# Состояния мультиварки
STATUS_HIBERNATION = 0x00
STATUS_SETTING = 0x01
STATUS_WAITING = 0x02
STATUS_HEAT = 0x03
STATUS_ASSISTANCE = 0x04
STATUS_COOKING = 0x05
STATUS_HEATING = 0x06

STATUS_NAMES = {
    STATUS_HIBERNATION: "Бездействие",
    STATUS_SETTING: "Настройка",
    STATUS_WAITING: "Ожидание",
    STATUS_HEAT: "Нагрев",
    STATUS_ASSISTANCE: "Помощь",
    STATUS_COOKING: "Готовка",
    STATUS_HEATING: "Подогрев"
}

# Типы моделей
MODEL_TYPE = {
    "RMC-M40S": "M40S",
    "RMC-M41S": "M41S",
    "RMC-M42S": "M42S",
    "RMC-M43S": "M43S",
    "RMC-M44S": "M44S",
    "RMC-M45S": "M45S",
    "RMC-M46S": "M46S",
    "RMC-M47S": "M47S",
    "RMC-M48S": "M48S",
    "RMC-M49S": "M49S",
}

# Режимы готовки
MODE_SLOW_COOK = 0x00
MODE_STEW = 0x01
MODE_BAKE = 0x02
MODE_STEAM = 0x03
MODE_YOGURT = 0x04
MODE_MULTICOOK = 0x05
MODE_SOUP = 0x06
MODE_PASTA = 0x07
MODE_RICE = 0x08
MODE_BREAD = 0x09
MODE_DESSERT = 0x0A
MODE_KEEP_WARM = 0x0B
MODE_OFF = 0xFF

MODE_NAMES = {
    MODE_SLOW_COOK: "Тушение",
    MODE_STEW: "Варка",
    MODE_BAKE: "Выпечка",
    MODE_STEAM: "На пару",
    MODE_YOGURT: "Йогурт",
    MODE_MULTICOOK: "Мультиповар",
    MODE_SOUP: "Суп",
    MODE_PASTA: "Паста",
    MODE_RICE: "Рис",
    MODE_BREAD: "Хлеб",
    MODE_DESSERT: "Десерт",
    MODE_KEEP_WARM: "Подогрев",
    MODE_OFF: "Выключено"
}

# Диапазоны температур
MIN_TEMPERATURE = 30
MAX_TEMPERATURE = 120

# Диапазоны времени
MIN_COOKING_TIME = 1  # минуты
MAX_COOKING_TIME = 24 * 60  # 24 часа в минутах
MIN_DELAY_TIME = 1  # минуты
MAX_DELAY_TIME = 24 * 60  # 24 часа в минутах

# Типы сенсоров
SENSOR_TYPE_SUCCESS_RATE = "success_rate"

BLE_SCAN_TIME = 3