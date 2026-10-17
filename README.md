# Basement Hub (boiler water temperature + basement climate + air quality)

ESPHome node for a Seeed XIAO ESP32-C3 (external antenna) that reports to Home Assistant:

- Boiler / circulating water temperature (DS18B20 probe on the boiler water pipe)
- Basement temperature and humidity (AHT21 on the combo board)
- Basement air quality: ENS160 (AQI, TVOC, estimated eCO2) and CCS811 (second opinion)
- Fixed boiler alerts: **low below 140°F, high above 190°F**

> The air-quality sensors estimate eCO2/TVOC. They are NOT a carbon monoxide detector.
> Keep real CO alarms in the basement and near the bedrooms.

## Hardware

- Seeed Studio XIAO ESP32-C3 with the external u.FL antenna attached (attach before power-up)
- DS18B20 waterproof temperature probe
- 4.7kΩ resistor (1-Wire pull-up)
- CCS811 + ENS160 + AHT21 combo board (I2C)
- Jumper wires

## Wiring

```
DS18B20 probe            XIAO ESP32-C3
─────────────            ─────────────
Red     ───────────────► 3V3
Black   ───────────────► GND
Yellow  ───────────────► D2 (GPIO4)
        └──[4.7kΩ]─────► 3V3   (pull-up between data and 3V3)

Combo board (I2C)        XIAO ESP32-C3
─────────────────        ─────────────
VCC     ───────────────► 3V3
GND     ───────────────► GND
SDA     ───────────────► D4 (GPIO6)
SCL     ───────────────► D5 (GPIO7)
```

A second DS18B20 can later share the same three wires (probe red/black/yellow in parallel).
When two probes are present, give each an explicit `address:` and a unique name in `basement_hub.yaml`.
Mount the combo board away from the hot pipe or its temperature reading will be high.

## Alerts

| Alert | Threshold | Must persist | Notification |
|-------|-----------|--------------|--------------|
| Low   | below 140°F | 10 minutes (ignores cold start) | Repeats **hourly** until recovered or paused |
| High  | above 190°F | 1 minute (ignores glitches) | Once |
| Offline | no reading | 10 minutes | Once |

Thresholds are fixed and do not depend on outside temperature. Each alert goes to the Home Assistant
app (phone) and to Telegram through the Hermes watcher `boiler_watch.py`. Pause the hourly low-temp
reminders with the **Pause alerts** button on the notification or by turning on
`input_boolean.boiler_alerts_paused`. The pause clears itself when the boiler returns to normal.

The thresholds apply to wherever the probe is mounted. The loop circulates constantly (the system has no
antifreeze, so the water is kept moving), which means a basement pipe stays close to boiler temperature
whether or not the house is calling for heat. A probe strapped to the outside of a pipe still reads a
little lower than the water, so insulate over it.

**Freeze risk:** the loop is plain water. If the fire dies or the circulation pump stops in winter the
water can freeze and split the boiler and buried lines, so treat the low alert as freeze protection.
Power the node from a generator-backed circuit, because a power outage is exactly when the circulator
stops and the hub would otherwise go dark with it.

## Installation

1. **ESPHome:** add a new device, replace its contents with `basement_hub.yaml`, add the secrets
   (`wifi_ssid`, `wifi_password`, `api_encryption_key`, `ota_password`, `fallback_password`).
2. **First flash over USB**, then watch the log: confirm the I2C scan finds 0x38 (AHT21),
   0x52 or 0x53 (ENS160), 0x5A or 0x5B (CCS811), and that the DS18B20 reports a temperature.
   If an address differs from the config, change `address:` in `basement_hub.yaml`.
3. **Check the entity IDs** in Home Assistant (Developer Tools > States, search `basement_`).
   The automations and watcher assume `sensor.basement_boiler_water_temperature` and
   `binary_sensor.basement_boiler_temperature_low` / `_high` / `_alert`. Fix them if they differ.
4. **Create a Toggle helper** named "Boiler alerts paused" (`input_boolean.boiler_alerts_paused`).
5. **Notifications:** adjust the `notify.mobile_app_...` target in `home_assistant_automation.yaml`
   and paste each automation into Home Assistant (Settings > Automations > Edit in YAML).

## Files

| File | Description |
|------|-------------|
| `basement_hub.yaml` | ESPHome device configuration |
| `home_assistant_automation.yaml` | Home Assistant phone notifications (low repeats hourly, pause button, offline) |
| `secrets.yaml` | NOT in the repo; supply your own credentials |

## License

MIT
