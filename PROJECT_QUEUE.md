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

## Batch 2 Projects (Session 2)

Continued queue — 6 new facts, 7 new design elements, 8 new projects.

### New Facts Created (Batch 2)

| Title | Domain / Category | File |
|-------|-------------------|------|
| BME280 Combined Pressure, Humidity, and Temperature Sensor | electrical / sensors | `0b202755-…` |
| pH Electrode — Calibration and Millivolt Measurement | electrical / sensors | `d5f217ad-…` |
| Rotary Encoder — Incremental A/B Quadrature Pulse Counting | electrical / user-interface | `b4ccc656-…` |
| MOSFET Linear-Mode Constant-Current Electronic Load | electrical / power-electronics | `f18fd907-…` |
| Aerobic Composting — Temperature, Moisture, and Gas Indicators | general / biology | `a4b4d4c8-…` |
| Color Sensing by Reflectance — TCS3200 Frequency-Mode Operation | electrical / sensors | `edec61cc-…` |

### New Design Elements Created (Batch 2)

| Title | Category | File |
|-------|----------|------|
| BME280 Environmental Sensor Module (I²C) | sensing | `bme280-environmental-sensor-module.json` |
| SX1276 LoRa Radio Module (RFM95W) | communication | `sx1276-lora-radio-module.json` |
| pH Probe BNC Amplifier Interface | sensing | `ph-probe-bnc-amplifier-interface.json` |
| Rotary Encoder User-Interface Navigation | control | `rotary-encoder-user-interface-navigation.json` |
| MAX31865 PT100 RTD Amplifier | sensing | `max31865-pt100-rtd-amplifier.json` |
| MOSFET Constant-Current Load Stage | power | `mosfet-constant-current-load-stage.json` |
| Turbidity NTU Optical Sensor Module | sensing | `turbidity-ntu-optical-sensor-module.json` |

### Projects (Batch 2)

- [x] **Smart Sous-Vide Cooker** (`smart-sous-vide-cooker.json`)
  - Domain: `systems`
  - Facts: RTD PT100 ✓, PID Controller ✓, SSR ✓, Rotary Encoder *(new)*, OLED SSD1306 ✓, DS3231 ✓
  - Elements: MAX31865 RTD *(new)*, SSR Mains ✓, Rotary Encoder UI *(new)*, SSD1306 OLED ✓, DS3231 RTC ✓, Arduino Nano ✓
  - Element interactions: RTD→MCU, Encoder→MCU, RTC→MCU, MCU→SSR, MCU→OLED
  - Integration code: Arduino C++ PID sous-vide with 1-s window duty cycle + cook timer
  - Status: **completed**

- [x] **LoRa Environmental Field Station** (`lora-environmental-field-station.json`)
  - Domain: `systems`
  - Facts: BME280 *(new)*, LoRa ✓, Low-Power Sleep ✓, Solar Panel Sizing ✓, NTP ✓
  - Elements: BME280 Module *(new)*, SX1276 LoRa *(new)*, MCU Deep Sleep ✓, Solar+MPPT ✓, MicroSD Logger ✓, Arduino Pro Mini ✓
  - Element interactions: BME280→MCU, MCU→SD, MCU→LoRa, WDT sleep→MCU
  - Integration code: Arduino C++ AVR WDT deep-sleep + LoRa compact binary payload
  - Status: **completed**

- [x] **Portable Water Quality Monitor v2** (`portable-water-quality-monitor-v2.json`)
  - Domain: `systems`
  - Facts: Water Quality Sensing ✓, pH Electrode *(new)*, Turbidity NTU ✓, ADC Resolution ✓, OLED SSD1306 ✓
  - Elements: pH Probe BNC *(new)*, Turbidity NTU Module *(new)*, SSD1306 OLED ✓, MicroSD Logger ✓, Rotary Encoder UI *(new)*, Arduino Nano ✓
  - Element interactions: pH→MCU, Turbidity→MCU, Encoder→MCU, MCU→OLED, MCU→SD
  - Integration code: Arduino C++ pH + NTU + TDS with EEPROM calibration + auto-save
  - Status: **completed**

- [x] **Automatic Soldering Iron Station** (`automatic-soldering-iron-station.json`)
  - Domain: `electrical`
  - Facts: RTD PT100 ✓, PID ✓, SSR ✓, Rotary Encoder *(new)*, OLED SSD1306 ✓
  - Elements: MAX31865 RTD *(new)*, N-MOSFET ✓, Rotary Encoder UI *(new)*, SSD1306 OLED ✓, Arduino Nano ✓
  - Element interactions: RTD→MCU, Encoder→MCU, MCU→MOSFET, MCU→OLED
  - Integration code: Arduino C++ median-filter PID + auto-sleep on stand reed switch
  - Status: **completed**

- [x] **Smart Compost Monitor** (`smart-compost-monitor.json`)
  - Domain: `systems`
  - Facts: Aerobic Composting *(new)*, DS18B20 ✓, Capacitive Soil Moisture ✓, NDIR CO₂ ✓, MQTT ✓
  - Elements: DS18B20 Probe Array ✓, Capacitive Soil Probe ✓, SCD41 CO₂ Module ✓, SSD1306 OLED ✓, ESP32 MQTT ✓, MQTT Logger ✓
  - Element interactions: DS18B20→ESP32, Soil Probe→ESP32, SCD41→ESP32, ESP32→OLED, ESP32→MQTT Logger
  - Integration code: Arduino C++ (ESP32) WiFi+MQTT with temperature/moisture/CO₂ + phase status
  - Status: **completed**

- [x] **Robotic Color Sorting Conveyor** (`robotic-color-sorting-conveyor.json`)
  - Domain: `systems`
  - Facts: Color Sensing TCS3200 *(new)*, DC Motor PWM ✓, RC Servo PWM ✓, I²C ✓
  - Elements: TCS3200 Color Sensor ✓, DC Gear Motor ✓, RC Servo Joint ✓, Arduino Uno ✓
  - Element interactions: TCS3200→MCU, MCU→DC Motor, MCU→Servo
  - Integration code: Arduino C++ color classify + diverter servo actuation + belt stop-during-read
  - Status: **completed**

- [x] **DIY Electronic Load (Constant Current)** (`diy-electronic-load.json`)
  - Domain: `electrical`
  - Facts: MOSFET CC Load *(new)*, N-MOSFET ✓, Coulomb Counting ✓, OLED SSD1306 ✓, Rotary Encoder *(new)*, Ohm's Law ✓
  - Elements: MOSFET CC Stage *(new)*, INA219 Monitor ✓, SSD1306 OLED ✓, Rotary Encoder UI *(new)*, Arduino Nano ✓
  - Element interactions: Encoder→MCU, MCU→DAC→MOSFET, INA219→MCU, MCU→OLED
  - Integration code: Arduino C++ programmable 0–5 A CC load + OTP protection + energy accumulation
  - Status: **completed**

- [x] **Induction Forge Temperature Controller** (`induction-forge-temperature-controller.json`)
  - Domain: `systems`
  - Facts: Induction Heating IGBT ✓, RTD PT100 ✓, PID ✓, N-MOSFET ✓, Rotary Encoder *(new)*, OLED SSD1306 ✓
  - Elements: IGBT Induction Heating ✓, MAX31865 RTD *(new)*, N-MOSFET ✓, Rotary Encoder UI *(new)*, SSD1306 OLED ✓, Arduino Nano ✓
  - Element interactions: RTD→MCU, Encoder→MCU, MCU→MOSFET→IGBT driver, MCU→OLED
  - Integration code: Arduino C++ median-5 PID + 1250 °C safety cutoff + NC relay interlock
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
| 10 | Smart Sous-Vide Cooker | ✅ Completed |
| 11 | LoRa Environmental Field Station | ✅ Completed |
| 12 | Portable Water Quality Monitor v2 | ✅ Completed |
| 13 | Automatic Soldering Iron Station | ✅ Completed |
| 14 | Smart Compost Monitor | ✅ Completed |
| 15 | Robotic Color Sorting Conveyor | ✅ Completed |
| 16 | DIY Electronic Load (Constant Current) | ✅ Completed |
| 17 | Induction Forge Temperature Controller | ✅ Completed |

**Batch 1:** 8 new facts, 8 new design elements, 9 new projects.
**Batch 2:** 6 new facts, 7 new design elements, 8 new projects.
**Batch 3:** 6 new facts, 5 new design elements, 8 new projects.
**Total added:** 20 new facts, 20 new design elements, **25 new projects** (plus 2 in-design projects completed).
FactDB totals: **136 facts · 118 design elements · 72 projects**.

---

## Batch 3 Projects (Session 3)

### New Facts Created (Batch 3)

| Title | Domain / Category | File |
|-------|-------------------|------|
| MAX6675 K-Type Thermocouple-to-Digital SPI Converter | electrical / thermocouples | `f61f3e4e-…` |
| WS2812B Addressable RGB LED — Single-Wire Protocol and Timing | electrical / lighting | `2c6a7a37-…` |
| HX711 24-Bit ADC for Load Cell and Wheatstone Bridge Amplification | electrical / sensors | `638ad328-…` |
| AC Power Factor and True Power Measurement via Current and Voltage Sensing | electrical / power-electronics | `d758336e-…` |
| Frequency Counter — Gate-Time Pulse Counting Method | electrical / signal-processing | `16e4d8e1-…` |
| Stepper Motor Closed-Loop Control via Magnetic Encoder Feedback | electrical / actuation | `37900aa4-…` |

### New Design Elements Created (Batch 3)

| Title | Category | File |
|-------|----------|------|
| MAX6675 K-Type Thermocouple SPI Module | sensing | `max6675-k-type-thermocouple-spi-module.json` |
| NeoPixel WS2812B Addressable RGB LED Strip Controller | actuation | `neopixel-ws2812b-led-strip-controller.json` |
| HX711 Load Cell Precision Weighing Interface | sensing | `hx711-load-cell-precision-weighing.json` |
| AC Mains Power Meter (ZMPT101B + SCT-013 + EmonLib) | sensing | `ac-mains-power-meter-emonlib.json` |
| Closed-Loop Stepper Motor with AS5600 Magnetic Encoder | actuation | `closed-loop-stepper-as5600-encoder.json` |

### Projects (Batch 3)

- [x] **Smart Reflow Oven Controller** (`smart-reflow-oven-controller.json`)
  - Domain: `electrical`
  - Facts: MAX6675 *(new)*, PID ✓, SSR ✓, Rotary Encoder ✓, OLED SSD1306 ✓
  - Elements: MAX6675 Module *(new)*, SSR ✓, Rotary Encoder UI ✓, SSD1306 OLED ✓, Arduino Nano ✓
  - Integration code: Arduino C++ lead-free reflow state machine (PREHEAT/SOAK/RAMP/REFLOW/COOL)
  - Status: **completed**

- [x] **Automated Precision Scale** (`automated-precision-scale.json`)
  - Domain: `systems`
  - Facts: HX711 *(new)*, Load Cell ✓, ADC Resolution ✓, OLED ✓, Rotary Encoder ✓
  - Elements: HX711 Weighing *(new)*, SSD1306 OLED ✓, Rotary Encoder UI ✓, Arduino Nano ✓
  - Integration code: Arduino C++ 5 kg scale + tare EEPROM + g/oz toggle + auto-sleep
  - Status: **completed**

- [x] **LED Grow Light Controller** (`led-grow-light-controller.json`)
  - Domain: `systems`
  - Facts: WS2812B *(new)*, MQTT ✓, DS3231 ✓, NTP ✓, OLED ✓
  - Elements: NeoPixel WS2812B *(new)*, ESP32 MQTT ✓, DS3231 RTC ✓, SSD1306 OLED ✓, MQTT Logger ✓
  - Integration code: ESP32 Arduino C++ grow light with SEEDLING/VEG/FLOWER spectrum profiles
  - Status: **completed**

- [x] **AC Energy Monitor Dashboard** (`ac-energy-monitor-dashboard.json`)
  - Domain: `electrical`
  - Facts: AC Power Factor *(new)*, CT Clamp RMS ✓, MQTT ✓, NTP ✓, OLED ✓
  - Elements: AC Power Meter EmonLib *(new)*, ESP32 MQTT ✓, SSD1306 OLED ✓, MicroSD Logger ✓, NTP Logger ✓
  - Integration code: ESP32 Arduino C++ EmonLib V/I/P/PF + HTTP API + MQTT + SD CSV log
  - Status: **completed**

- [x] **Closed-Loop CNC Pen Plotter** (`closed-loop-cnc-pen-plotter.json`)
  - Domain: `mechanical`
  - Facts: Stepper Closed-Loop *(new)*, Stepper Drive ✓, G-code ✓, RC Servo ✓, Wheel Encoder ✓
  - Elements: Closed-Loop Stepper AS5600 *(new)*, CoreXY Gantry ✓, GRBL ✓, NEMA17/DRV8825 ✓, RC Servo ✓, Arduino Mega ✓
  - Integration code: Arduino C++ Timer2 1 kHz closed-loop ISR + GRBL + AS5600 TCA9548A mux
  - Status: **completed**

- [x] **Automated Plant Watering System** (`automated-plant-watering-system.json`)
  - Domain: `systems`
  - Facts: Capacitive Soil Moisture ✓, Solenoid Valve ✓, N-MOSFET ✓, MQTT ✓, DS3231 ✓
  - Elements: Capacitive Probe ✓, N-MOSFET ✓, DS3231 RTC ✓, SSD1306 OLED ✓, ESP32 MQTT ✓, MQTT Logger ✓
  - Integration code: ESP32 Arduino C++ 4-zone watering + RTC alarms + MQTT event log
  - Status: **completed**

- [x] **RFID Access Control Logger** (`rfid-access-control-logger.json`)
  - Domain: `systems`
  - Facts: RFID/NFC ✓, N-MOSFET ✓, MQTT ✓, NTP ✓, OTA ✓
  - Elements: MFRC522 RFID ✓, N-MOSFET ✓, SSD1306 OLED ✓, MicroSD Logger ✓, OTA Update ✓, ESP32 MQTT ✓
  - Integration code: ESP32 Arduino C++ RFID auth + door strike + CSV log + MQTT + OTA
  - Status: **completed**

- [x] **Ultrasonic Levitation Demo** (`ultrasonic-levitation-demo.json`)
  - Domain: `systems`
  - Facts: Ultrasonic Piezoelectric ✓, Ultrasonic Distance ✓, DC Motor PWM ✓, Rotary Encoder ✓, OLED ✓
  - Elements: Rotary Encoder UI ✓, SSD1306 OLED ✓, Arduino Uno ✓
  - Integration code: Arduino C++ Timer1 phase-correct PWM 40 kHz push-pull + frequency tuning
  - Status: **completed**

---

## Copilot Continuous Seeder

A self-driving seeder script (`scripts/copilot_seeder.py`) can generate new
projects autonomously by prompting the GitHub Copilot CLI.

**Usage:**
```bash
# Run forever (Ctrl-C to stop):
factdb seed-copilot

# Generate exactly 10 new projects then stop:
factdb seed-copilot --count 10

# Dry-run (inspect prompts without writing files):
factdb seed-copilot --dry-run

# Override Copilot model:
factdb seed-copilot --model gpt-5.2 --count 5

# Verbose output:
factdb seed-copilot --count 3 --verbose
```

**How it works:**
1. Reads all existing fact / element / project titles from `data/` JSON files.
2. Builds a detailed prompt instructing Copilot to invent a novel project,
   filling in any gaps with new facts and design elements.
3. Calls `gh copilot -p "..." --allow-all-tools --autopilot` non-interactively.
4. Parses the JSON envelope from the response.
5. Validates and writes new `.json` files to the appropriate `data/` paths.
6. Appends new relationships to `data/facts/_relationships.json`.
7. Re-seeds the SQLite DB (`factdb seed && factdb seed-projects`).
8. Appends a summary line to this file.
9. Loops back to step 1 (with configurable pause between iterations).

---

## Full Summary

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
| 10 | Smart Sous-Vide Cooker | ✅ Completed |
| 11 | LoRa Environmental Field Station | ✅ Completed |
| 12 | Portable Water Quality Monitor v2 | ✅ Completed |
| 13 | Automatic Soldering Iron Station | ✅ Completed |
| 14 | Smart Compost Monitor | ✅ Completed |
| 15 | Robotic Color Sorting Conveyor | ✅ Completed |
| 16 | DIY Electronic Load (Constant Current) | ✅ Completed |
| 17 | Induction Forge Temperature Controller | ✅ Completed |
| 18 | Smart Reflow Oven Controller | ✅ Completed |
| 19 | Automated Precision Scale | ✅ Completed |
| 20 | LED Grow Light Controller | ✅ Completed |
| 21 | AC Energy Monitor Dashboard | ✅ Completed |
| 22 | Closed-Loop CNC Pen Plotter | ✅ Completed |
| 23 | Automated Plant Watering System | ✅ Completed |
| 24 | RFID Access Control Logger | ✅ Completed |
| 25 | Ultrasonic Levitation Demo | ✅ Completed |
| 26+ | *(future — auto-generated by `factdb seed-copilot`)* | 🤖 Automated |
