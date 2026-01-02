# SkyCooker - Интеграция для HomeAssistant

Интеграция для управления мультиварками Redmond серии Ready4Sky (RMC-M40S и другие модели) через Bluetooth.

## Поддерживаемые модели

- RMC-M40S
- RMC-M41S
- RMC-M42S
- RMC-M43S
- RMC-M44S
- RMC-M45S
- RMC-M46S
- RMC-M47S
- RMC-M48S
- RMC-M49S

## Функциональные возможности

### Управление мультиваркой
- Включение и выключение
- Выбор режимов готовки (Тушение, Варка, Выпечка, На пару, Йогурт, Мультиповар, Суп, Паста, Рис, Хлеб, Десерт, Подогрев)
- Установка температуры готовки (30-120°C)
- Установка времени готовки (1 минута - 24 часа)
- Установка времени отложенного старта (1 минута - 24 часа)
- Включение/выключение подогрева после готовки

### Мониторинг состояния
- Текущее состояние (Бездействие, Настройка, Ожидание, Нагрев, Помощь, Готовка, Подогрев)
- Текущая температура
- Целевая температура
- Оставшееся время готовки
- Оставшееся время отложенного старта
- Качество Bluetooth сигнала
- Состояние подогрева
- Режим таймера

## Требования

- HomeAssistant 2025.12.5 или новее
- Bluetooth адаптер
- Python 3.10 или новее

## Установка

1. Скопируйте папку `custom_components/skycooker` в папку `custom_components` вашего HomeAssistant
2. Перезапустите HomeAssistant
3. Перейдите в Настройки → Интеграции → Добавить интеграцию
4. Выберите "SkyCooker"
5. Следуйте инструкциям на экране

## Настройка

### Режим сопряжения
Перед первым подключением переведите мультиварку в режим сопряжения:
1. Убедитесь, что мультиварка включена
2. Зажмите и удерживайте кнопку "Меню" (или другую кнопку в зависимости от модели) 10 секунд
3. На дисплее должна появиться надпись "PAIR" или мигающий индикатор

### Параметры настройки
- **Постоянное подключение**: Быстрее реагирует на изменения, но эксклюзивно (не сможете использовать официальное приложение одновременно)
- **Интервал опроса**: Как часто интеграция будет запрашивать состояние мультиварки (в секундах)

## Сущности

Интеграция создает следующие сущности:

### Переключатели (Switch)
- `switch.skycooker_power` - Включение/выключение мультиварки
- `switch.skycooker_postheat` - Подогрев после готовки
- `switch.skycooker_timer_mode` - Режим таймера (время готовки/отложенный старт)

### Селекторы (Select)
- `select.skycooker_mode` - Выбор режима готовки

### Числовые контролы (Number)
- `number.skycooker_temperature` - Температура готовки
- `number.skycooker_cooking_hours` - Время готовки (часы)
- `number.skycooker_cooking_minutes` - Время готовки (минуты)
- `number.skycooker_delay_hours` - Время отложенного старта (часы)
- `number.skycooker_delay_minutes` - Время отложенного старта (минуты)

### Сенсоры (Sensor)
- `sensor.skycooker_status` - Состояние мультиварки
- `sensor.skycooker_temperature` - Текущая температура
- `sensor.skycooker_cooking_time` - Время готовки
- `sensor.skycooker_delay_time` - Время отложенного старта
- `sensor.skycooker_signal_strength` - Сила сигнала Bluetooth

## Автоматизация

Пример автоматизации для включения мультиварки:

```yaml
automation:
  - alias: "Start cooking"
    trigger:
      - platform: time
        at: "08:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.skycooker_power
      - service: select.select_option
        target:
          entity_id: select.skycooker_mode
        data:
          option: "Мультиповар"
      - service: number.set_value
        target:
          entity_id: number.skycooker_temperature
        data:
          value: 80
      - service: number.set_value
        target:
          entity_id: number.skycooker_cooking_hours
        data:
          value: 2
      - service: number.set_value
        target:
          entity_id: number.skycooker_cooking_minutes
        data:
          value: 0
```

## Поддержка

Если у вас возникли проблемы или вопросы:
1. Проверьте логи HomeAssistant на наличие ошибок
2. Убедитесь, что Bluetooth адаптер работает корректно
3. Проверьте, что мультиварка поддерживается интеграцией
4. Создайте issue на GitHub с описанием проблемы и логами

## Лицензия

MIT License

## Автор

kai-zer-ru