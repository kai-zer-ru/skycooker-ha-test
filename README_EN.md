# SkyCooker - HomeAssistant Integration

Integration for managing Redmond Ready4Sky series multicookers (RMC-M40S and other models) via Bluetooth.

## Supported Models

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

## Features

### Cooker Control
- Power on/off
- Cooking mode selection (Slow Cook, Stew, Bake, Steam, Yogurt, Multicook, Soup, Pasta, Rice, Bread, Dessert, Keep Warm)
- Temperature setting (30-120°C)
- Cooking time setting (1 minute - 24 hours)
- Delay start time setting (1 minute - 24 hours)
- Post-cooking heat enable/disable

### State Monitoring
- Current state (Hibernation, Setting, Waiting, Heat, Assistance, Cooking, Heating)
- Current temperature
- Target temperature
- Remaining cooking time
- Remaining delay start time
- Bluetooth signal strength
- Post-heat status
- Timer mode status

## Requirements

- HomeAssistant 2025.12.5 or newer
- Bluetooth adapter
- Python 3.10 or newer

## Installation

1. Copy the `custom_components/skycooker` folder to your HomeAssistant `custom_components` folder
2. Restart HomeAssistant
3. Go to Settings → Integrations → Add Integration
4. Select "SkyCooker"
5. Follow the on-screen instructions

## Configuration

### Pairing Mode
Before the first connection, put the cooker into pairing mode:
1. Make sure the cooker is powered on
2. Press and hold the "Menu" button (or another button depending on the model) for 10 seconds
3. The display should show "PAIR" or a blinking indicator

### Configuration Options
- **Persistent Connection**: Responds faster to changes but is exclusive (you won't be able to use the official app simultaneously)
- **Poll Interval**: How often the integration will request the cooker status (in seconds)

## Entities

The integration creates the following entities:

### Switches
- `switch.skycooker_power` - Cooker power on/off
- `switch.skycooker_postheat` - Post-cooking heat
- `switch.skycooker_timer_mode` - Timer mode (cooking time/delay start)

### Selects
- `select.skycooker_mode` - Cooking mode selection

### Numbers
- `number.skycooker_temperature` - Cooking temperature
- `number.skycooker_cooking_hours` - Cooking time (hours)
- `number.skycooker_cooking_minutes` - Cooking time (minutes)
- `number.skycooker_delay_hours` - Delay start time (hours)
- `number.skycooker_delay_minutes` - Delay start time (minutes)

### Sensors
- `sensor.skycooker_status` - Cooker status
- `sensor.skycooker_temperature` - Current temperature
- `sensor.skycooker_cooking_time` - Cooking time
- `sensor.skycooker_delay_time` - Delay start time
- `sensor.skycooker_signal_strength` - Bluetooth signal strength

## Automation

Example automation for starting cooking:

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
          option: "Multicook"
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

## Support

If you have any problems or questions:
1. Check HomeAssistant logs for errors
2. Make sure the Bluetooth adapter is working correctly
3. Verify that your cooker is supported by the integration
4. Create an issue on GitHub with a problem description and logs

## License

MIT License

## Author

kai-zer-ru

---

**Note**: Russian documentation is available in [README.md](README.md)