# Boiler Temperature Monitor

ESP32-based boiler water temperature monitor with Home Assistant integration and smart alerts.

## Features

- Real-time boiler water temperature monitoring
- Fixed alert thresholds: low below 140°F, high above 190°F
- Push notifications via Home Assistant Companion App
- ESPHome integration for easy Home Assistant setup

## Hardware Required

- ESP32-C3 SuperMini dev board
- DS18B20 waterproof temperature sensor
- 4.7kΩ resistor (pull-up for 1-Wire bus)
- Jumper wires

## Wiring Diagram

```
DS18B20          ESP32-C3 SuperMini
───────          ──────────────────
Red    ────────► 3.3V
Black  ────────► GND
Yellow ────────► GPIO4
       │
       └──[4.7kΩ]──► 3.3V  (pull-up resistor)
```

## Alert Thresholds

| Alert | Threshold |
|-------|-----------|
| Low   | below 140°F |
| High  | above 190°F |

Thresholds are fixed and do not depend on outside temperature.

## Installation

### 1. Prerequisites

- Home Assistant with ESPHome add-on installed
- Home Assistant Companion App on your phone

### 2. ESPHome Setup

1. Open ESPHome from the Home Assistant sidebar
2. Click **+ New Device** → name it `boiler-temp` → select **ESP32-C3**
3. Click **Edit** on the new device
4. Replace the contents with `boiler_temp.yaml` from this repo
5. Click **Secrets** and add your credentials (see secrets.yaml for template)

### 3. Configure Secrets

Add these to ESPHome secrets:

```yaml
wifi_ssid: "YourWiFiName"
wifi_password: "YourWiFiPassword"
api_encryption_key: "your-32-byte-base64-key"
ota_password: "your-ota-password"
fallback_password: "your-fallback-password"
```

Generate an API key at: https://esphome.io/components/api.html

### 4. First Flash (USB)

1. Connect ESP32-C3 to your computer via USB
2. In ESPHome, click 3 dots → **Install** → **Plug into this computer**
3. Select the serial port and wait for flashing to complete

### 5. Get Sensor Address

1. After flashing, click **Logs** in ESPHome
2. Find the line: `Found sensors: 0x1234567890ABCDEF`
3. Edit your config and replace `0x0000000000000000` with your sensor's address
4. Re-flash wirelessly via **Install** → **Wirelessly**

### 6. Set Up Notifications

1. Find your phone's notify service:
   - Go to **Developer Tools** → **Services**
   - Search for `notify.mobile_app`
   - Note your device name (e.g., `notify.mobile_app_johns_iphone`)

2. Edit `home_assistant_automation.yaml`:
   - Replace `notify.mobile_app_YOUR_PHONE` with your device name

3. Add automations to Home Assistant:
   - Go to **Settings** → **Automations** → **+ Create Automation**
   - Click 3 dots → **Edit in YAML**
   - Paste each automation block from `home_assistant_automation.yaml`

## Files

| File | Description |
|------|-------------|
| `boiler_temp.yaml` | ESPHome device configuration |
| `secrets.yaml` | Template for credentials (do not commit with real values) |
| `home_assistant_automation.yaml` | Home Assistant notification automations |

## Customization

### Change GPIO Pin

Edit `boiler_temp.yaml` line 35:
```yaml
pin: GPIO4  # Change to your data pin
```

### Adjust Temperature Thresholds

Edit the binary_sensor lambda functions in `boiler_temp.yaml` to change the alert thresholds.

## License

MIT
