# Project Queue

Tracks the design queue for FactDB projects. Each project is designed by verifying
all supporting facts and design elements against the FactDB knowledge base — creating
any missing facts or design elements before marking the project complete.

---

## Previously In-Design (now completed)

- [x] **Autonomous Obstacle-Avoidance Rover** (`autonomous-obstacle-avoidance-rover.json`)
  - All 5 supporting facts verified ✓
  - All 7 design elements verified ✓
  - Element interactions added (LiDAR → MCU, Sonar → MCU, nRF24 → MCU, MCU → L298N, L298N → Motors)
  - Integration code added (Arduino C++ obstacle avoidance + A* reactive planner)
  - Status: `in_design` → **completed**

- [x] **Voice-Controlled Home Automation Hub** (`voice-controlled-home-automation-hub.json`)
  - 3 new supporting facts added: `Voice Recognition — Keyword Spotting UART Module (LD3320)`,
    `Solid-State Relay (SSR) Mains Load Switching` *(new)*, `N-Channel MOSFET as a Low-Side Power Switch`
  - All 5 design elements verified ✓
  - Element interactions added (Voice → ESP32, BLE → ESP32, ESP32 → SSR, ESP32 → MQTT Logger)
  - Integration code added (Arduino C++ BLE + UART voice + relay dispatch)
  - Status: `in_design` → **completed**

- [x] **Weather Station Software** (`weather-station-software.json`)
  - Already fully designed in previous session
  - Element interactions and integration code present ✓
  - Status: `in_design` (unchanged — software project already complete)

---

## New Projects Queue

New projects added below. Each required verifying facts and design elements in FactDB
and creating any missing assets before marking complete.

### New Facts Created

| Title | Domain / Category | File |
|-------|-------------------|------|
| Solid-State Relay (SSR) Mains Load Switching | electrical / solid-state-relays | `3e3a7c2d-…` |
| DS18B20 1-Wire Digital Temperature Sensing | electrical / temperature-sensors | `0791d1aa-…` |
| I²C Real-Time Clock — DS3231 Timekeeping and Alarms | electrical / timing | `8598a225-…` |
| Nichrome Resistance Heating Wire Power Calculation | electrical / heating-elements | `57e2ae3d-…` |
| Hall-Effect Speed Sensor for Rotating Machinery | electrical / speed-sensing | `5fefa83e-…` |
| State-of-Charge Estimation via Coulomb Counting | electrical / battery-management | `083551ab-…` |
| Magnetic Reed Switch for Contact/Position Detection | electrical / position-sensing | `7efe63d1-…` |
| OLED SSD1306 Monochrome Display I²C Interface | electrical / display | `8d61cf7d-…` |

### New Design Elements Created

| Title | Category | File |
|-------|----------|------|
| DS18B20 1-Wire Temperature Probe Array | sensing | `ds18b20-1-wire-temperature-probe-array.json` |
| DS3231 RTC Alarm Scheduling Module | control | `ds3231-rtc-alarm-scheduling-module.json` |
| Nichrome Hot Wire Foam Cutter Drive | actuation | `nichrome-hot-wire-foam-cutter-drive.json` |
| Hall-Effect Reed Switch Wheel Speed Sensor | sensing | `hall-effect-wheel-speed-sensor.json` |
| SSD1306 OLED Display UI Module | processing | `ssd1306-oled-display-ui-module.json` |
| INA219 I²C Current and Power Monitor | sensing | `ina219-i2c-current-and-power-monitor.json` |
| Resistive Cell Voltage Sensing Divider Array | sensing | `resistive-cell-voltage-sensing-divider-array.json` |
| Magnetic Reed Switch Door Position Sensor | sensing | `magnetic-reed-switch-door-position-sensor.json` |

### Projects

- [x] **Smart Aquarium Controller** (`smart-aquarium-controller.json`)
  - Domain: `systems`
  - Facts: DS18B20 *(new)*, DS3231 *(new)*, Solenoid Valve ✓, N-MOSFET ✓, PID Controller ✓
  - Elements: DS18B20 Probe *(new)*, DS3231 RTC *(new)*, MOSFET Switch ✓, SSD1306 OLED *(new)*, Arduino Nano ✓
  - Element interactions: Probe → MCU, RTC → MCU, MCU → MOSFET, MCU → OLED
  - Integration code: Arduino C++ aquarium controller (temperature alarm + lighting schedule + top-off pump)
  - Status: **completed**

- [x] **CNC Hot Wire Foam Cutter** (`cnc-hot-wire-foam-cutter.json`)
  - Domain: `mechanical`
  - Facts: G-code ✓, Stepper Motor Drive ✓, Nichrome Wire *(new)*, N-MOSFET ✓, Ohm's Law ✓
  - Elements: CoreXY Gantry ✓, NEMA17/DRV8825 ✓, Nichrome Drive *(new)*, MOSFET Switch ✓, GRBL ✓, Arduino Uno ✓
  - Element interactions: GRBL → Stepper, GRBL → MOSFET, MOSFET → Nichrome, Gantry → Nichrome
  - Integration code: Python G-code sender (`cnc_foam_cutter.py`)
  - Status: **completed**

- [x] **Automated Pill Dispenser** (`automated-pill-dispenser.json`)
  - Domain: `systems`
  - Facts: DS3231 *(new)*, Stepper Motor Drive ✓, Load Cell ✓, SSD1306 OLED *(new)*, PID Controller ✓
  - Elements: DS3231 RTC *(new)*, NEMA17/DRV8825 ✓, SSD1306 OLED *(new)*, Arduino Nano ✓
  - Element interactions: RTC → MCU, MCU → Stepper, MCU → OLED
  - Integration code: Arduino C++ 7-compartment carousel dispenser
  - Status: **completed**

- [x] **Bluetooth Bicycle Speedometer** (`bluetooth-bicycle-speedometer.json`)
  - Domain: `systems`
  - Facts: Hall-Effect Speed Sensor *(new)*, Wheel Encoder Odometry ✓, BLE ✓, SSD1306 OLED *(new)*, ADC Resolution ✓
  - Elements: Hall-Effect Wheel Speed Sensor *(new)*, SSD1306 OLED *(new)*, BLE GATT App Interface ✓, Arduino Nano ✓
  - Element interactions: Hall Sensor → MCU, MCU → OLED, MCU → BLE
  - Integration code: Arduino C++ speed + distance + BLE JSON stream
  - Status: **completed**

- [x] **Smart Battery Management System Monitor** (`smart-bms-monitor.json`)
  - Domain: `electrical`
  - Facts: State-of-Charge Coulomb Counting *(new)*, Li-Ion Battery ✓, KVL ✓, ADC Resolution ✓, SSD1306 OLED *(new)*
  - Elements: Cell Voltage Divider *(new)*, INA219 Monitor *(new)*, SSD1306 OLED *(new)*, Arduino Nano ✓
  - Element interactions: Voltage Dividers → MCU, INA219 → MCU, MCU → OLED
  - Integration code: Arduino C++ Coulomb-counting BMS monitor with EEPROM persistence
  - Status: **completed**

- [x] **Garage Door IoT Controller** (`garage-door-iot-controller.json`)
  - Domain: `systems`
  - Facts: MQTT ✓, OTA Firmware Update ✓, Magnetic Reed Switch *(new)*, PIR HC-SR501 ✓, SSR *(new)*
  - Elements: Reed Switch Door Sensor *(new)*, PIR HC-SR501 ✓, SSR Relay ✓, OTA Update ✓, ESP32 WiFi MQTT ✓, MQTT Logger ✓
  - Element interactions: Reed Switches → ESP32, PIR → ESP32, ESP32 → SSR, ESP32 → MQTT Logger, OTA → ESP32
  - Integration code: Arduino C++ (ESP32) full MQTT + OTA + interrupt-driven door state machine
  - Status: **completed**

---

## Summary

| # | Project | Status |
|---|---------|--------|
| 1 | Autonomous Obstacle-Avoidance Rover | ✅ Completed |
| 2 | Voice-Controlled Home Automation Hub | ✅ Completed |
| 3 | Weather Station Software | ✅ Completed (prior session) |
| 4 | Smart Aquarium Controller | ✅ Completed |
| 5 | CNC Hot Wire Foam Cutter | ✅ Completed |
| 6 | Automated Pill Dispenser | ✅ Completed |
| 7 | Bluetooth Bicycle Speedometer | ✅ Completed |
| 8 | Smart Battery Management System Monitor | ✅ Completed |
| 9 | Garage Door IoT Controller | ✅ Completed |

**8 new facts** and **8 new design elements** were added to support the new projects.
Total FactDB now: ~124 facts, ~106 design elements, **56 projects**.
