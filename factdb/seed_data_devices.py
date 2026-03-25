"""
Device design seed data — engineering facts for FactDB.

Covers the two embedded/IoT product domains:
  • Weather Station — sensors, power, communications, enclosure, calibration
  • Robot Vacuum Cleaner — navigation, drive, suction, power, software

Facts are structured identically to ``seed_data.py`` so they can be loaded
by the same seeder machinery.
"""

from __future__ import annotations

DEVICE_FACTS: list[dict] = [
    # ================================================================
    # WEATHER STATION
    # ================================================================

    # ----------------------------------------------------------------
    # Sensors — Temperature
    # ----------------------------------------------------------------
    {
        "title": "NTC Thermistor Temperature Sensing",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "temperature sensing",
        "detail_level": "intermediate",
        "content": (
            "A Negative Temperature Coefficient (NTC) thermistor decreases in "
            "resistance as temperature rises.  Its resistance–temperature "
            "relationship is described by the Steinhart–Hart equation: "
            "1/T = A + B·ln(R) + C·(ln(R))³."
        ),
        "extended_content": (
            "NTC thermistors offer high sensitivity (~4%/°C) and low cost, making "
            "them the dominant choice for weather-station air-temperature measurement. "
            "Typical range: −40 °C to +125 °C; accuracy ±0.1–0.5 °C after calibration. "
            "A voltage-divider circuit with a precision resistor converts resistance "
            "to a voltage suitable for an ADC input.  Self-heating error (I²R) must "
            "be minimised by keeping excitation current below 100 µA."
        ),
        "formula": "1/T = A + B·ln(R) + C·(ln(R))³",
        "units": "T: K, R: Ω",
        "source": "Steinhart & Hart, Deep-Sea Research, 1968; Measurement Specialties NTC Application Note",
        "confidence_score": 0.98,
        "tags": ["temperature", "thermistor", "NTC", "sensor", "weather-station", "electrical"],
    },
    {
        "title": "RTD (PT100/PT1000) Temperature Measurement",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "temperature sensing",
        "detail_level": "intermediate",
        "content": (
            "A Resistance Temperature Detector (RTD) uses the predictable increase "
            "of metal resistance with temperature.  For platinum: "
            "R(T) = R₀ · (1 + A·T + B·T²) over the range −200 °C to +850 °C."
        ),
        "extended_content": (
            "PT100 (R₀ = 100 Ω at 0 °C) and PT1000 (R₀ = 1000 Ω) are the most "
            "common variants.  Callendar–Van Dusen coefficients: A = 3.9083×10⁻³ /°C, "
            "B = −5.775×10⁻⁷ /°C².  RTDs are more accurate and stable than "
            "thermistors (±0.03–0.1 °C) but require a precision 4-wire circuit or "
            "dedicated AFE to eliminate lead resistance errors.  Used in "
            "meteorological reference instruments (WMO Class-1 stations)."
        ),
        "formula": "R(T) = R₀(1 + A·T + B·T²)",
        "units": "R: Ω, T: °C",
        "source": "IEC 60751:2022, Industrial platinum resistance thermometers",
        "confidence_score": 0.99,
        "tags": ["temperature", "RTD", "PT100", "sensor", "weather-station", "electrical"],
    },

    # ----------------------------------------------------------------
    # Sensors — Humidity
    # ----------------------------------------------------------------
    {
        "title": "Capacitive Relative Humidity Sensing",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "humidity sensing",
        "detail_level": "intermediate",
        "content": (
            "Capacitive humidity sensors measure relative humidity (RH) by "
            "detecting the change in dielectric permittivity of a hygroscopic "
            "polymer film placed between two electrodes as it absorbs water vapour."
        ),
        "extended_content": (
            "Sensor capacitance increases approximately linearly with RH "
            "(∼0.2–0.5 pF / %RH for a 100 pF baseline).  Integrated modules "
            "(e.g., Sensirion SHT4x, Honeywell HIH) combine a capacitive RH "
            "element with an on-chip temperature sensor and a 16-bit sigma–delta "
            "ADC, delivering ±1.8 %RH accuracy over 0–100 %RH.  Hysteresis is "
            "typically <1 %RH and response time 4–8 s (1/e, 63% step response). "
            "The sensor element must be protected from condensation, dust, and "
            "chemical contaminants while remaining exposed to ambient air via a "
            "filter membrane."
        ),
        "units": "% RH (relative humidity)",
        "source": "Sensirion SHT4x Datasheet; WMO-No.8 Guide to Instruments and Methods of Observation",
        "confidence_score": 0.97,
        "tags": ["humidity", "capacitive", "RH", "sensor", "weather-station", "electrical"],
    },

    # ----------------------------------------------------------------
    # Sensors — Pressure
    # ----------------------------------------------------------------
    {
        "title": "MEMS Barometric Pressure Sensor",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "pressure sensing",
        "detail_level": "intermediate",
        "content": (
            "Micro-Electro-Mechanical Systems (MEMS) barometric sensors measure "
            "absolute atmospheric pressure by detecting the deflection of a "
            "micro-machined silicon membrane using piezoresistive or capacitive "
            "techniques."
        ),
        "extended_content": (
            "Typical range: 300–1100 hPa (equivalent to altitudes from +9000 m "
            "to −500 m).  Resolution: ±0.06 hPa (Bosch BMP390), equivalent to "
            "±0.5 m altitude.  Temperature compensation is required: most devices "
            "include an on-chip temperature sensor and compensation coefficients "
            "stored in OTP memory.  Output is via SPI or I²C at sample rates up "
            "to 200 Hz.  For sea-level pressure reduction (QNH), apply: "
            "P_SL = P_stn × exp(g·h / (R_d·T_virt)), where h is station elevation."
        ),
        "formula": "P_SL = P_stn · exp(g · h / (R_d · T_virt))",
        "units": "hPa (hectopascal)",
        "source": "Bosch BMP390 Datasheet; WMO Technical Note No.61",
        "confidence_score": 0.97,
        "tags": ["pressure", "barometric", "MEMS", "sensor", "weather-station", "electrical"],
    },

    # ----------------------------------------------------------------
    # Sensors — Wind
    # ----------------------------------------------------------------
    {
        "title": "Cup Anemometer — Wind Speed Measurement",
        "domain": "mechanical",
        "category": "meteorological instruments",
        "subcategory": "wind measurement",
        "detail_level": "intermediate",
        "content": (
            "A three-cup anemometer converts wind speed to a rotational frequency. "
            "Wind speed is proportional to rotation rate: V = k · f, where k is "
            "the instrument calibration factor and f is the rotation frequency."
        ),
        "extended_content": (
            "Typical calibration factors: k ≈ 0.75–1.0 m/s per Hz for a standard "
            "100 mm cup set.  A reed switch or Hall-effect sensor generates one or "
            "more pulses per revolution, counted by a microcontroller.  Starting "
            "threshold ('threshold wind speed') is typically 0.3–0.5 m/s.  "
            "WMO specification requires measurement range 0.2–75 m/s with ±0.5 m/s "
            "accuracy below 5 m/s and ±10% above.  Ultrasonic anemometers have no "
            "moving parts and better low-wind response."
        ),
        "formula": "V_wind = k · f_rotation",
        "units": "V: m/s, f: Hz",
        "source": "WMO-No.8 Guide to Instruments, Ch.5; R.M. Young 05103 Manual",
        "confidence_score": 0.97,
        "tags": ["wind-speed", "anemometer", "meteorology", "mechanical", "weather-station"],
    },
    {
        "title": "Wind Vane — Wind Direction Measurement",
        "domain": "mechanical",
        "category": "meteorological instruments",
        "subcategory": "wind measurement",
        "detail_level": "fundamental",
        "content": (
            "A wind vane aligns with the wind direction; a potentiometer or "
            "resistor array converts the vane angle to a voltage or resistance "
            "that is read by an ADC to determine direction (0–360°)."
        ),
        "extended_content": (
            "Precision potentiometer vanes provide continuous 360° output "
            "(excluding a small dead band at the electrical stop).  Reed-switch "
            "and resistor-ladder designs encode direction as a discrete voltage "
            "selected from 8 or 16 positions (45° or 22.5° resolution).  Accuracy "
            "requirement (WMO): ±5° for the direction and ±0.5 m/s for speed.  "
            "Vane inertia should be minimised for response to wind gusts (distance "
            "constant < 2 m).  True north correction must be applied during "
            "installation using a compass bearing."
        ),
        "units": "degrees (0–360°, meteorological convention: from North, clockwise)",
        "source": "WMO-No.8 Guide to Instruments, Ch.5",
        "confidence_score": 0.97,
        "tags": ["wind-direction", "vane", "potentiometer", "meteorology", "weather-station"],
    },

    # ----------------------------------------------------------------
    # Sensors — Precipitation
    # ----------------------------------------------------------------
    {
        "title": "Tipping Bucket Rain Gauge",
        "domain": "mechanical",
        "category": "meteorological instruments",
        "subcategory": "precipitation measurement",
        "detail_level": "fundamental",
        "content": (
            "A tipping bucket rain gauge funnels rainfall into a small, balanced "
            "seesaw bucket that tips (generating a switch closure) each time it "
            "collects a fixed volume of water, typically 0.2 mm of precipitation."
        ),
        "extended_content": (
            "Each tip is detected by a reed switch and counted by the data logger. "
            "Total rainfall (mm) = tip count × bucket resolution.  Common "
            "resolutions: 0.1, 0.2, or 0.5 mm per tip.  High-intensity rain "
            "causes under-counting because water continues to fall while the bucket "
            "is tipping (dead time ≈ 150 ms); correction algorithms exist.  The "
            "funnel orifice diameter (typically 200 mm) must be kept free of "
            "debris and insects.  In freezing conditions, a heating element prevents "
            "ice blockage."
        ),
        "formula": "Rainfall (mm) = N_tips × resolution_per_tip",
        "units": "mm (precipitation depth)",
        "source": "WMO-No.8 Guide to Instruments, Ch.6",
        "confidence_score": 0.98,
        "tags": ["rainfall", "precipitation", "tipping-bucket", "gauge", "weather-station"],
    },

    # ----------------------------------------------------------------
    # Signal Processing — ADC and Sampling
    # ----------------------------------------------------------------
    {
        "title": "ADC Resolution and Measurement Precision",
        "domain": "electrical",
        "category": "signal processing",
        "subcategory": "analog-to-digital conversion",
        "detail_level": "intermediate",
        "content": (
            "The resolution of an n-bit ADC divides the full-scale input range "
            "into 2ⁿ discrete steps.  The minimum detectable voltage change "
            "(1 LSB) is: ΔVLSB = V_FS / 2ⁿ."
        ),
        "extended_content": (
            "For a 12-bit ADC with 3.3 V full-scale: ΔVLSB = 3.3 / 4096 ≈ 0.81 mV. "
            "Effective Number of Bits (ENOB) accounts for real-world noise and "
            "nonlinearity: ENOB = (SINAD − 1.76) / 6.02.  For weather-station "
            "temperature reading a 16-bit ADC provides ≈ 50 µV resolution, "
            "corresponding to ≈ 0.01 °C with a typical thermistor slope.  "
            "Anti-aliasing filter cut-off must satisfy the Nyquist criterion: "
            "f_c < f_s / 2."
        ),
        "formula": "ΔV_LSB = V_FS / 2ⁿ",
        "units": "V (volts per LSB)",
        "source": "Kester, The Data Conversion Handbook, Analog Devices, 2005",
        "confidence_score": 0.99,
        "tags": ["ADC", "resolution", "signal-processing", "sensor", "weather-station", "electrical"],
    },
    {
        "title": "Nyquist–Shannon Sampling Theorem",
        "domain": "systems",
        "category": "signal processing",
        "subcategory": "sampling theory",
        "detail_level": "fundamental",
        "content": (
            "To perfectly reconstruct a band-limited signal, the sampling "
            "frequency must be at least twice the signal's highest frequency "
            "component: f_s ≥ 2 · f_max (Nyquist rate)."
        ),
        "extended_content": (
            "Sampling below the Nyquist rate causes aliasing — high-frequency "
            "components appear as spurious lower-frequency components.  In "
            "weather-station design, atmospheric temperature changes slowly "
            "(< 0.01 Hz), so 1 Hz sampling is far above Nyquist; wind gusts "
            "contain energy up to ≈ 10 Hz requiring at least 20 Hz sampling "
            "for gust analysis.  An anti-aliasing low-pass filter with cut-off "
            "below f_s/2 must precede the ADC."
        ),
        "formula": "f_s ≥ 2 · f_max",
        "units": "Hz",
        "source": "Shannon, C.E. (1949). Communication in the Presence of Noise. Proc. IRE.",
        "confidence_score": 1.0,
        "tags": ["sampling", "Nyquist", "signal-processing", "aliasing", "weather-station", "systems"],
    },

    # ----------------------------------------------------------------
    # Power — Solar and Battery
    # ----------------------------------------------------------------
    {
        "title": "Solar Panel Sizing for Remote IoT Stations",
        "domain": "electrical",
        "category": "power systems",
        "subcategory": "renewable energy",
        "detail_level": "intermediate",
        "content": (
            "The required solar panel peak power is P_panel = "
            "(E_daily / η_total) / PSH, where E_daily is daily energy "
            "consumption, η_total is system efficiency, and PSH is Peak Sun Hours."
        ),
        "extended_content": (
            "Peak Sun Hours (PSH) represents equivalent hours of 1000 W/m² "
            "irradiance per day; typical values: 2–3 h (UK winter), 4–5 h (mid-"
            "latitude summer), 5–7 h (desert).  System efficiency η includes "
            "panel derating (temperature, soiling ≈ 0.8), charge-controller "
            "efficiency (MPPT ≈ 0.95), and battery charge/discharge efficiency "
            "(Li-ion ≈ 0.95).  Battery capacity should cover ≥ 5 days of "
            "autonomy (no sun) at 50% depth-of-discharge (DoD)."
        ),
        "formula": "P_panel = E_daily / (η_total · PSH)",
        "units": "P: W, E_daily: Wh, PSH: hours",
        "source": "Perez-Aparicio et al., Solar Energy Systems Design, 2019",
        "confidence_score": 0.96,
        "tags": ["solar", "power", "IoT", "remote", "battery", "weather-station", "electrical"],
    },
    {
        "title": "Li-Ion Battery Capacity and Energy Calculation",
        "domain": "electrical",
        "category": "power systems",
        "subcategory": "energy storage",
        "detail_level": "fundamental",
        "content": (
            "Battery usable energy is: E_usable = V_nominal × C_Ah × DoD, "
            "where C_Ah is the rated capacity in amp-hours and DoD is the "
            "permitted depth of discharge."
        ),
        "extended_content": (
            "Li-ion (LiCoO₂): 3.6–3.7 V nominal, 150–250 Wh/kg, recommended "
            "DoD 80%.  LiFePO₄: 3.2–3.3 V nominal, 90–140 Wh/kg, DoD 90%, "
            "superior cycle life (2000–4000 cycles vs 500–1000 for LiCoO₂) and "
            "safer thermal runaway profile — preferred for outdoor, unattended "
            "weather-station installations.  Temperature derating: capacity "
            "reduces ≈ 20–30% at −20 °C, requiring a larger battery or insulated "
            "enclosure at high-latitude sites."
        ),
        "formula": "E_usable (Wh) = V_nom × C_Ah × DoD",
        "units": "Wh (watt-hours), Ah (amp-hours)",
        "source": "Linden & Reddy, Handbook of Batteries, 4th ed., McGraw-Hill",
        "confidence_score": 0.97,
        "tags": ["battery", "Li-ion", "LiFePO4", "energy", "power", "weather-station", "electrical"],
    },
    {
        "title": "Low-Power Microcontroller Sleep Modes",
        "domain": "electrical",
        "category": "embedded systems",
        "subcategory": "power management",
        "detail_level": "intermediate",
        "content": (
            "Modern microcontrollers offer multiple sleep modes that reduce current "
            "consumption from milliamps (active) to microamps (deep sleep) while "
            "retaining register state and waking on timers or external interrupts."
        ),
        "extended_content": (
            "Typical current: active 10–50 mA, sleep 1–100 µA, deep sleep "
            "0.1–5 µA.  Average current for a duty-cycled sensor node: "
            "I_avg = I_active × t_active/(t_active + t_sleep) + I_sleep.  "
            "For a weather station sampling every 60 s with 100 ms active burst: "
            "I_avg ≈ 25 mA × (0.1/60) + 5 µA ≈ 46 µA.  Peripheral power gating "
            "(sensor VCC via GPIO MOSFET) further reduces quiescent current.  "
            "ARM Cortex-M0+ (e.g., SAMD21) and Nordic nRF52 offer excellent "
            "sleep performance for weather-station applications."
        ),
        "formula": "I_avg = I_active · (t_on / T_period) + I_sleep",
        "units": "µA (microamperes)",
        "source": "ARM Cortex-M0+ TRM; Nordic nRF52840 Product Specification",
        "confidence_score": 0.96,
        "tags": ["microcontroller", "sleep-mode", "power", "embedded", "IoT", "weather-station"],
    },

    # ----------------------------------------------------------------
    # Enclosure and Mechanical
    # ----------------------------------------------------------------
    {
        "title": "IP (Ingress Protection) Rating — IEC 60529",
        "domain": "systems",
        "category": "enclosure design",
        "subcategory": "environmental protection",
        "detail_level": "fundamental",
        "content": (
            "The IP Code (IEC 60529) classifies the degree of protection an "
            "enclosure provides against solid particles and liquids using two "
            "digits: IP XY, where X = solid (0–6) and Y = liquid (0–8/9K)."
        ),
        "extended_content": (
            "Key levels for weather-station electronics: IP54 — dust protected, "
            "splash proof; IP65 — dust tight, low-pressure water jet; IP67 — "
            "dust tight, temporary immersion (1 m / 30 min); IP68 — dust tight, "
            "continuous immersion (manufacturer-specified depth).  Cable glands "
            "and connectors must match or exceed the enclosure IP rating.  Thermal "
            "management (ventilation or thermal mass) must not compromise the IP "
            "rating; Gore-Tex vent membranes allow pressure equalisation while "
            "maintaining IP67."
        ),
        "source": "IEC 60529:2013+AMD1:2013, Degrees of protection provided by enclosures",
        "confidence_score": 0.99,
        "tags": ["IP-rating", "enclosure", "weatherproofing", "IEC60529", "weather-station", "systems"],
    },
    {
        "title": "Radiation Shield for Meteorological Temperature Sensors",
        "domain": "mechanical",
        "category": "meteorological instruments",
        "subcategory": "sensor housing",
        "detail_level": "intermediate",
        "content": (
            "A radiation shield (Stevenson screen or solar radiation shield) "
            "encloses a temperature or humidity sensor to prevent solar radiation "
            "heating errors while allowing free airflow for accurate ambient "
            "measurements."
        ),
        "extended_content": (
            "Solar heating can cause temperature errors of +5 to +30 °C without "
            "shielding.  A WMO-standard naturally-ventilated radiation shield "
            "(e.g., Gill multi-plate shield) reduces daytime radiation error to "
            "<0.5 °C at wind speeds > 1 m/s.  Forced-ventilation shields achieve "
            "<0.1 °C error but consume power (≈ 0.5–2 W fan).  Shield material "
            "should have high solar reflectivity (white UV-resistant ABS or "
            "polycarbonate, albedo > 0.85) and low thermal mass.  WMO height "
            "specification: sensor at 1.25–2 m above short grass."
        ),
        "source": "WMO-No.8 Guide to Instruments, Ch.2; Richardson et al., 2009",
        "confidence_score": 0.98,
        "tags": ["radiation-shield", "temperature", "Stevenson-screen", "meteorology", "weather-station"],
    },
    {
        "title": "Wind Loading on Structures (ASCE 7)",
        "domain": "mechanical",
        "category": "structural",
        "subcategory": "environmental loads",
        "detail_level": "intermediate",
        "content": (
            "The design wind pressure on a structure is: p = q_z · G · C_f, "
            "where q_z is the velocity pressure at height z, G is the gust "
            "factor, and C_f is the net force coefficient."
        ),
        "extended_content": (
            "Velocity pressure: q_z = 0.613 · K_z · K_zt · K_d · V² (Pa), "
            "where V is the 3-second gust design wind speed (m/s) and K factors "
            "account for terrain, topography, and directionality.  For a "
            "weather-station mast at 10 m in open terrain (Exposure C): "
            "K_z ≈ 1.0.  A 10 m mast must withstand a ±50 m/s gust in many "
            "climates.  Guy wires reduce bending moment significantly; base "
            "moments must include dynamic amplification for slender masts."
        ),
        "formula": "p = q_z · G · C_f ;  q_z = 0.613 · K_z · K_zt · K_d · V²",
        "units": "p: Pa, q_z: Pa, V: m/s",
        "source": "ASCE 7-22, Minimum Design Loads for Buildings and Other Structures",
        "confidence_score": 0.96,
        "tags": ["wind-load", "structural", "mast", "mechanical", "weather-station"],
    },

    # ----------------------------------------------------------------
    # Communications
    # ----------------------------------------------------------------
    {
        "title": "LoRa / LoRaWAN — LPWAN for Remote Telemetry",
        "domain": "electrical",
        "category": "wireless communication",
        "subcategory": "LPWAN",
        "detail_level": "intermediate",
        "content": (
            "LoRa (Long Range) is a chirp spread-spectrum modulation technique "
            "enabling data rates of 0.3–50 kbps over distances of 2–15 km "
            "(urban–rural) with sub-milliwatt receiver sensitivity (−137 dBm)."
        ),
        "extended_content": (
            "LoRaWAN defines the network layer; frequency bands: 868 MHz "
            "(Europe), 915 MHz (Americas), 923 MHz (Asia-Pacific); duty-cycle "
            "restrictions apply (1% in EU).  Link budget: EIRP + path gain − "
            "noise = SNR margin.  Spreading factor (SF7–SF12) trades data rate "
            "for range: SF12 gives maximum range but reduces throughput to "
            "250 bps.  Ideal for battery-powered weather stations transmitting "
            "small payloads (< 50 bytes) every few minutes; a 2 Ah battery can "
            "last >2 years with daily uploads."
        ),
        "source": "LoRa Alliance LoRaWAN Specification v1.0.4; Semtech SX1276 Datasheet",
        "confidence_score": 0.96,
        "tags": ["LoRa", "LoRaWAN", "LPWAN", "wireless", "IoT", "weather-station", "electrical"],
    },
    {
        "title": "MQTT Protocol for IoT Sensor Data",
        "domain": "software",
        "category": "communication protocols",
        "subcategory": "IoT messaging",
        "detail_level": "intermediate",
        "content": (
            "MQTT (Message Queuing Telemetry Transport) is a lightweight, "
            "publish–subscribe messaging protocol designed for constrained IoT "
            "devices over low-bandwidth, high-latency networks."
        ),
        "extended_content": (
            "MQTT v3.1.1 / v5.0 uses a central broker (e.g., Mosquitto, AWS IoT "
            "Core).  Clients publish to topics (e.g., 'station/01/temperature'); "
            "subscribers receive matching messages.  QoS levels: 0 (at most once), "
            "1 (at least once), 2 (exactly once).  Minimum header overhead is "
            "2 bytes.  TLS encryption adds ≈ 5–10 kB of code on constrained MCUs. "
            "For weather stations, MQTT over LoRaWAN gateways or WiFi is common; "
            "last-will messages notify subscribers of connection loss."
        ),
        "source": "MQTT v3.1.1 OASIS Standard (2014); MQTT v5.0 OASIS Standard (2019)",
        "confidence_score": 0.98,
        "tags": ["MQTT", "IoT", "protocol", "publish-subscribe", "weather-station", "software"],
    },
    {
        "title": "I²C Serial Communication Protocol",
        "domain": "electrical",
        "category": "digital interfaces",
        "subcategory": "serial communication",
        "detail_level": "intermediate",
        "content": (
            "I²C (Inter-Integrated Circuit) is a two-wire synchronous serial "
            "bus (SDA + SCL) that allows multiple master and slave devices to "
            "communicate over short distances using 7-bit (or 10-bit) addresses."
        ),
        "extended_content": (
            "Standard mode: 100 kbps; Fast mode: 400 kbps; Fast-plus: 1 Mbps; "
            "High-speed: 3.4 Mbps.  Open-drain bus requires pull-up resistors "
            "(typically 4.7 kΩ at 100 kHz, 2.2 kΩ at 400 kHz).  In a "
            "weather-station design, I²C connects MCU to pressure sensors "
            "(BMP390), RH/T sensors (SHT4x), real-time clocks, and EEPROM on "
            "a single bus.  Bus capacitance limit: 400 pF (cable length ≈ 1 m). "
            "Address conflicts between sensors of the same type are resolved with "
            "ADDR select pins or I²C multiplexers (PCA9548)."
        ),
        "source": "NXP I²C-bus Specification and User Manual Rev. 7 (2021)",
        "confidence_score": 0.99,
        "tags": ["I2C", "serial", "bus", "interface", "embedded", "weather-station", "electrical"],
    },
    {
        "title": "NTP Time Synchronisation for Data Logging",
        "domain": "software",
        "category": "embedded systems",
        "subcategory": "time management",
        "detail_level": "intermediate",
        "content": (
            "Network Time Protocol (NTP) synchronises clocks over a packet-"
            "switched network to within milliseconds of Coordinated Universal "
            "Time (UTC), ensuring accurate timestamps on logged sensor data."
        ),
        "extended_content": (
            "NTP uses a hierarchy of time servers (stratum 0–15).  For a "
            "weather station with cellular or WiFi connectivity, SNTP (Simple "
            "NTP, RFC 4330) over UDP port 123 is sufficient; accuracy ≈ 1–50 ms. "
            "An on-board RTC (e.g., DS3231, ±2 ppm = ±172 ms/day) maintains "
            "time during network outages.  UTC timestamps must be stored with "
            "observations; local-time conversion is applied in post-processing. "
            "WMO requires clock accuracy better than ±1 s for standard "
            "synoptic observations."
        ),
        "source": "RFC 5905 (NTPv4); RFC 4330 (SNTPv4); WMO-No.8 Ch.1",
        "confidence_score": 0.98,
        "tags": ["NTP", "time-sync", "UTC", "data-logging", "IoT", "weather-station", "software"],
    },

    # ----------------------------------------------------------------
    # Calibration
    # ----------------------------------------------------------------
    {
        "title": "Sensor Calibration and Traceability to SI",
        "domain": "systems",
        "category": "metrology",
        "subcategory": "calibration",
        "detail_level": "intermediate",
        "content": (
            "Sensor calibration establishes the relationship between an "
            "instrument's output and a reference standard, providing an "
            "uncertainty chain traceable to SI units via national metrology "
            "institutes."
        ),
        "extended_content": (
            "ISO/IEC 17025 governs calibration laboratory competence.  For "
            "weather-station sensors: temperature traceable to ITS-90 (triple "
            "point of water = 273.16 K), pressure to primary pressure standards "
            "(U < 0.1 hPa), RH to gravimetric hygrometers (U < 0.5 %RH). "
            "Field calibration intervals recommended by WMO: temperature 1–2 yr, "
            "pressure 1–2 yr, RH 6–12 months.  Calibration certificates must "
            "include measurement uncertainty at 95% confidence (coverage factor "
            "k = 2) and environmental conditions during calibration."
        ),
        "source": "WMO-No.49 Technical Regulations Vol.I; ISO/IEC 17025:2017",
        "confidence_score": 0.99,
        "tags": ["calibration", "metrology", "traceability", "uncertainty", "weather-station", "systems"],
    },

    # ================================================================
    # ROBOT VACUUM CLEANER
    # ================================================================

    # ----------------------------------------------------------------
    # Navigation — SLAM and Sensors
    # ----------------------------------------------------------------
    {
        "title": "SLAM — Simultaneous Localisation and Mapping",
        "domain": "software",
        "category": "robotics",
        "subcategory": "navigation",
        "detail_level": "advanced",
        "content": (
            "SLAM is the computational problem of building a map of an unknown "
            "environment while simultaneously tracking the robot's location "
            "within that map, using sensor data without prior maps."
        ),
        "extended_content": (
            "SLAM methods include: Extended Kalman Filter (EKF-SLAM) — linearises "
            "nonlinear motion/measurement models; Particle Filter (FastSLAM) — "
            "represents the posterior with weighted samples; Graph SLAM / "
            "pose-graph optimisation — poses as nodes, constraints as edges, "
            "solved via Gauss-Newton or Levenberg-Marquardt.  Robot vacuum "
            "cleaners typically use LiDAR-based SLAM (e.g., GMapping, Cartographer) "
            "or optical flow + IMU fusion.  Computational cost: EKF O(n²) per "
            "step where n = landmark count; particle SLAM O(M·n) per step "
            "where M = particle count.  Map resolution typically 1–5 cm/cell."
        ),
        "source": "Thrun, Burgard & Fox, Probabilistic Robotics, MIT Press, 2005",
        "confidence_score": 0.97,
        "tags": ["SLAM", "mapping", "localisation", "robotics", "navigation", "robot-vacuum", "software"],
    },
    {
        "title": "2D LiDAR Distance Measurement Principle",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "distance measurement",
        "detail_level": "intermediate",
        "content": (
            "A 2D LiDAR (Light Detection and Ranging) sensor emits a rotating "
            "laser beam and measures distance via time-of-flight (ToF): "
            "d = c · t_ToF / 2, where c is the speed of light."
        ),
        "extended_content": (
            "Typical robot-vacuum LiDAR (e.g., RPLIDAR A1): range 0.15–12 m, "
            "angular resolution 1°, 360° scan, 2000–8000 samples/s.  Uncertainty "
            "±1–2 cm at <6 m; degrades on dark/absorptive surfaces.  Phase-"
            "modulation (FMCW) LiDAR is an alternative that uses frequency shift "
            "instead of pulse timing.  The rotating mirror or MEMS mirror adds a "
            "mechanical wear concern; solid-state alternatives (e.g., VCSEL array "
            "+ SPAD) are emerging.  LiDAR point clouds feed occupancy grid maps "
            "in the SLAM algorithm."
        ),
        "formula": "d = c · t_ToF / 2",
        "units": "d: m, t_ToF: s, c: 3×10⁸ m/s",
        "source": "Siciliano et al., Robotics: Modelling, Planning and Control, Springer; RPLIDAR A1 Datasheet",
        "confidence_score": 0.97,
        "tags": ["LiDAR", "ToF", "distance", "sensor", "navigation", "robot-vacuum", "electrical"],
    },
    {
        "title": "Ultrasonic Proximity Sensor — ToF Distance Measurement",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "proximity sensing",
        "detail_level": "fundamental",
        "content": (
            "Ultrasonic sensors emit a 40 kHz sound pulse and measure the "
            "round-trip travel time to an obstacle: d = v_sound · t / 2, "
            "where v_sound ≈ 343 m/s at 20 °C."
        ),
        "extended_content": (
            "Effective range: 2 cm – 4 m (HC-SR04 type); beam angle ≈ 15°. "
            "Speed of sound varies with temperature: v = 331.4 + 0.606·T (m/s, "
            "T in °C).  Ultrasonic sensors complement LiDAR in robot vacuums for "
            "close-range obstacle detection and furniture legs (thin vertical "
            "objects that LiDAR may miss).  Minimum dead zone (≈ 2–4 cm) "
            "prevents measurement during pulse emission."
        ),
        "formula": "d = v_sound · t_echo / 2 ;  v_sound ≈ 331.4 + 0.606·T",
        "units": "d: m, v: m/s, T: °C",
        "source": "Maxbotix Inc., Ultrasonic Sensor Selection Guide; Sick AG, Ultrasonic Technology Overview",
        "confidence_score": 0.97,
        "tags": ["ultrasonic", "proximity", "distance", "ToF", "sensor", "robot-vacuum", "electrical"],
    },
    {
        "title": "Infrared Cliff Detection for Robot Vacuums",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "safety sensing",
        "detail_level": "fundamental",
        "content": (
            "Downward-facing infrared (IR) emitter–detector pairs detect floor "
            "discontinuities (stairs, drops) by measuring the drop in reflected "
            "IR intensity when the floor surface is absent or far away."
        ),
        "extended_content": (
            "Each cliff sensor consists of an IR LED and a phototransistor or "
            "photodiode angled at ≈ 15–45° from vertical.  Floor proximity: "
            "reflected signal is strong; cliff detected: reflected signal falls "
            "below threshold.  A typical robot vacuum has 4 cliff sensors "
            "(corners) operating at 38 kHz modulation to reject ambient light. "
            "Failure mode: dark or highly absorptive carpet reduces reflectance; "
            "threshold calibration per floor type is required.  Cliff detection "
            "triggers immediate motor stop and reverse within ≈ 20 ms "
            "(safety requirement)."
        ),
        "source": "iRobot Open Interface Specification; Neato Robotics Technical Docs",
        "confidence_score": 0.96,
        "tags": ["cliff-detection", "IR", "safety", "sensor", "robot-vacuum", "electrical"],
    },

    # ----------------------------------------------------------------
    # Drive System
    # ----------------------------------------------------------------
    {
        "title": "Differential Drive Robot Kinematics",
        "domain": "mechanical",
        "category": "robotics",
        "subcategory": "motion kinematics",
        "detail_level": "intermediate",
        "content": (
            "A differential-drive robot controls heading and speed using two "
            "independently driven wheels.  Forward speed: v = (v_R + v_L) / 2; "
            "angular rate: ω = (v_R − v_L) / L, where L is the wheelbase."
        ),
        "extended_content": (
            "Dead-reckoning pose update: x(t+dt) = x(t) + v·cos(θ)·dt, "
            "y(t+dt) = y(t) + v·sin(θ)·dt, θ(t+dt) = θ(t) + ω·dt. "
            "Odometry error accumulates due to wheel slip, floor irregularities, "
            "and encoder resolution.  Typical robot-vacuum wheelbase L = 150–200 mm, "
            "wheel diameter 60–80 mm, wheel encoder 360–1200 CPR.  Angular position "
            "precision: Δθ = (ΔN_L − ΔN_R) · π · D / (CPR · L) radians.  Fusion "
            "with LiDAR SLAM corrects accumulated odometry error."
        ),
        "formula": "v = (v_R + v_L)/2 ;  ω = (v_R − v_L)/L",
        "units": "v: m/s, ω: rad/s, L: m",
        "source": "Siegwart, Nourbakhsh & Scaramuzza, Introduction to Autonomous Mobile Robots, MIT Press, 2011",
        "confidence_score": 0.98,
        "tags": ["differential-drive", "kinematics", "odometry", "robotics", "robot-vacuum", "mechanical"],
    },
    {
        "title": "Wheel Encoder Odometry",
        "domain": "systems",
        "category": "robotics",
        "subcategory": "position estimation",
        "detail_level": "intermediate",
        "content": (
            "Quadrature encoders attached to drive wheels count pulses to "
            "measure wheel rotation.  Distance per pulse: Δd = π · D_wheel / CPR, "
            "where D_wheel is wheel diameter and CPR is counts per revolution."
        ),
        "extended_content": (
            "Quadrature encoding uses two phase-offset signals (A and B) to "
            "determine both direction and count, giving 4× resolution per "
            "physical slot (4·CPR effective resolution).  Typical robot-vacuum "
            "encoder: 600 CPR magnetic or optical; effective resolution ≈ 0.1 mm "
            "per count for a 75 mm wheel.  Slip detection: if commanded motor "
            "speed and encoder-measured speed diverge beyond a threshold, the "
            "robot slows down or triggers a stuck condition.  Cumulative "
            "odometry error typically 1–3% of path length."
        ),
        "formula": "Δd = π · D_wheel / (4 · CPR_physical)",
        "units": "m (metres per count)",
        "source": "Borenstein, Everett & Feng, Navigating Mobile Robots, A.K. Peters, 1996",
        "confidence_score": 0.97,
        "tags": ["encoder", "odometry", "wheel", "position", "robotics", "robot-vacuum", "systems"],
    },
    {
        "title": "H-Bridge Motor Driver Circuit",
        "domain": "electrical",
        "category": "power electronics",
        "subcategory": "motor drive",
        "detail_level": "intermediate",
        "content": (
            "An H-bridge uses four switching transistors (MOSFETs or BJTs) to "
            "control the polarity of voltage applied to a DC motor, enabling "
            "forward, reverse, and braking operation with PWM speed control."
        ),
        "extended_content": (
            "Four MOSFETs arranged in a full-bridge: Q1–Q4.  Forward: Q1+Q4 ON; "
            "Reverse: Q2+Q3 ON; Coast (free-wheel): Q1+Q3 or Q2+Q4 ON (low-side "
            "recirculation); Brake: Q1+Q3 ON (high-side shoot-through — avoid). "
            "PWM frequency: 20–50 kHz for quiet operation (above audible range). "
            "Dead-time insertion (50–200 ns) prevents shoot-through.  "
            "Integrated drivers (e.g., DRV8833, TB6612FNG) include protection "
            "(overcurrent, thermal shutdown) and are preferred for robot-vacuum "
            "wheel motors (typically 100–500 mA stall, 5–12 V)."
        ),
        "source": "Mohan, Undeland & Robbins, Power Electronics, 3rd ed.; Texas Instruments DRV8833 Datasheet",
        "confidence_score": 0.97,
        "tags": ["H-bridge", "motor-driver", "PWM", "MOSFET", "DC-motor", "robot-vacuum", "electrical"],
    },
    {
        "title": "DC Motor Speed Control via PWM",
        "domain": "electrical",
        "category": "power electronics",
        "subcategory": "motor control",
        "detail_level": "intermediate",
        "content": (
            "Pulse-Width Modulation (PWM) controls the average voltage applied "
            "to a DC motor by varying the duty cycle D: V_avg = D · V_supply, "
            "where D ∈ [0, 1]."
        ),
        "extended_content": (
            "Motor speed is approximately proportional to average terminal "
            "voltage (for a given load).  The motor's electrical time constant "
            "τ_e = L/R (typically 1–10 ms) filters the PWM ripple; mechanical "
            "time constant τ_m = J·R/K²_t (typically 50–500 ms) determines "
            "speed response.  PWM frequency must be >> 1/τ_e for effective "
            "smoothing (10× rule: f_PWM > 10/τ_e).  Closed-loop speed control "
            "uses encoder feedback with a PI or PID controller.  Typical "
            "robot-vacuum wheel motor: 6–12 V, 0.5–2 A stall, 100–300 RPM at "
            "no-load."
        ),
        "formula": "V_avg = D · V_supply ;  n_motor ∝ V_avg − I·R_a",
        "units": "V (Volts), D (dimensionless 0–1)",
        "source": "Chapman, Electric Machinery Fundamentals, 5th ed.; Mohan, Power Electronics",
        "confidence_score": 0.97,
        "tags": ["PWM", "DC-motor", "speed-control", "duty-cycle", "robot-vacuum", "electrical"],
    },

    # ----------------------------------------------------------------
    # Suction / Cleaning System
    # ----------------------------------------------------------------
    {
        "title": "Brushless DC (BLDC) Motor for Suction Fan",
        "domain": "electrical",
        "category": "motors",
        "subcategory": "BLDC motor",
        "detail_level": "intermediate",
        "content": (
            "A brushless DC motor eliminates carbon brushes by using electronic "
            "commutation via Hall sensors or back-EMF detection, providing higher "
            "efficiency, longer life, and higher speed than brushed motors."
        ),
        "extended_content": (
            "Robot-vacuum suction fans use BLDC motors running 15,000–120,000 RPM "
            "to generate airflow.  Back-EMF constant K_e relates speed to back-"
            "EMF: V_bemf = K_e · ω.  Three-phase electronic commutation (6-step "
            "or sinusoidal) is driven by a dedicated BLDC controller (e.g., "
            "DRV10987).  Efficiency: 80–95% vs 60–75% for brushed equivalent. "
            "Acoustic noise is controlled by minimising cogging torque (fractional "
            "slot winding) and running above 20 kHz PWM switching frequency. "
            "For a 20 W suction motor at 120,000 RPM: tip speed of the impeller "
            "≈ 120 m/s requiring precision-balanced aluminium or PEEK impellers."
        ),
        "formula": "V_bemf = K_e · ω",
        "units": "V: Volts, K_e: V·s/rad, ω: rad/s",
        "source": "Gieras & Wing, Permanent Magnet Motor Technology, 3rd ed., CRC Press",
        "confidence_score": 0.96,
        "tags": ["BLDC", "motor", "suction", "fan", "robot-vacuum", "electrical"],
    },
    {
        "title": "Suction Pressure and Airflow in Vacuum Systems",
        "domain": "mechanical",
        "category": "fluid mechanics",
        "subcategory": "suction performance",
        "detail_level": "intermediate",
        "content": (
            "Vacuum cleaner performance is characterised by sealed suction "
            "(maximum pressure difference at zero flow, Pa) and airflow "
            "(maximum flow at zero pressure, m³/s), and is traded off along "
            "the fan's performance curve."
        ),
        "extended_content": (
            "Bernoulli's principle and the fan affinity laws govern the "
            "suction-airflow curve.  Airflow (volumetric) Q and pressure "
            "drop ΔP relate to particle pickup: heavy particles (sand, crumbs) "
            "require high ΔP; light particles (dust, hair) require high Q. "
            "Robot vacuums: typical sealed suction 1000–4000 Pa, airflow "
            "5–20 L/s.  Suction power P_air = ΔP × Q (watts).  HEPA filter "
            "reduces Q by 15–30% at the same motor speed; system losses include "
            "cyclone separator, duct bends, and brush roll.  Fan affinity: "
            "Q ∝ N, ΔP ∝ N², P ∝ N³ where N = rotational speed."
        ),
        "formula": "P_air = ΔP · Q ;  Q ∝ N,  ΔP ∝ N²,  P ∝ N³",
        "units": "ΔP: Pa, Q: m³/s (or L/s), P_air: W",
        "source": "Çengel & Cimbala, Fluid Mechanics, 3rd ed.; IEC 62885 Vacuum Cleaner Test Standards",
        "confidence_score": 0.96,
        "tags": ["suction", "airflow", "vacuum", "fan", "fluid-mechanics", "robot-vacuum", "mechanical"],
    },
    {
        "title": "HEPA Filter Efficiency and Filtration Grade",
        "domain": "mechanical",
        "category": "filtration",
        "subcategory": "air quality",
        "detail_level": "fundamental",
        "content": (
            "A HEPA (High-Efficiency Particulate Air) filter must capture ≥ 99.97% "
            "of particles ≥ 0.3 µm in diameter (the most penetrating particle "
            "size, MPPS) to meet the H13 or H14 standard."
        ),
        "extended_content": (
            "Filtration grades per EN 1822: H13 ≥ 99.95% efficiency, H14 ≥ 99.995% "
            "at MPPS.  Mechanisms: inertial impaction (large particles), "
            "interception, Brownian diffusion (sub-0.1 µm).  HEPA filters are "
            "pleated to maximise surface area (0.5–1.0 m²) in a small volume. "
            "Robot-vacuum HEPA filters require periodic replacement (every "
            "2–4 months); clogging increases pressure drop, reduces airflow, and "
            "increases motor load.  Washable versions lose efficiency after "
            "multiple washes.  For allergy applications, filter efficiency ≥ H13 "
            "is recommended."
        ),
        "source": "EN 1822:2019 High-efficiency air filters; EPA HEPA Guide; IEC 62885",
        "confidence_score": 0.99,
        "tags": ["HEPA", "filter", "air-quality", "filtration", "robot-vacuum", "mechanical"],
    },

    # ----------------------------------------------------------------
    # Power — Battery and Charging
    # ----------------------------------------------------------------
    {
        "title": "Robot Runtime Estimation from Battery Capacity",
        "domain": "systems",
        "category": "power management",
        "subcategory": "runtime estimation",
        "detail_level": "fundamental",
        "content": (
            "Estimated robot operating time is: t_run = (C_Ah × V_nom × DoD) "
            "/ P_avg, where P_avg is the average power draw during operation."
        ),
        "extended_content": (
            "Typical robot-vacuum power budget: suction motor 15–25 W, drive "
            "motors 2×1.5 W, main brush motor 2 W, computing/sensing 2–5 W; "
            "total ≈ 23–37 W.  A 2600 mAh 14.4 V Li-ion pack (37.4 Wh × 0.85 DoD "
            "= 31.8 Wh usable) gives: t = 31.8 / 30 ≈ 63 minutes — consistent "
            "with typical 60–90 min claims.  Battery life decreases with carpet "
            "type (higher suction needed) and charging temperature (charge above "
            "10 °C and below 45 °C for Li-ion longevity)."
        ),
        "formula": "t_run = (C_Ah · V_nom · DoD) / P_avg",
        "units": "t: hours, C: Ah, V: V, P: W",
        "source": "Linden & Reddy, Handbook of Batteries, 4th ed.; Dyson V7 Technical Documentation",
        "confidence_score": 0.96,
        "tags": ["battery", "runtime", "power", "Li-ion", "robot-vacuum", "systems"],
    },
    {
        "title": "Automatic Charging Dock — IR Beacon Homing",
        "domain": "electrical",
        "category": "control systems",
        "subcategory": "docking navigation",
        "detail_level": "intermediate",
        "content": (
            "Robot vacuums locate their charging dock using modulated infrared "
            "beacons emitted by the dock.  The robot's IR receivers detect "
            "signal strength and bearing to navigate back to the dock for "
            "autonomous recharging."
        ),
        "extended_content": (
            "The dock typically emits three overlapping IR beams at different "
            "modulation frequencies or codes: a wide 'home' beam (≈ 180°) for "
            "initial acquisition, a narrow 'force field' beam (≈ 20°) to guide "
            "final approach, and a 'virtual wall' beam.  Robot IR receivers "
            "(two or more) decode beam identity and compare signal amplitudes for "
            "bearing estimation.  Docking accuracy: ±5–15 mm lateral, ±3° "
            "angular.  Fail-safe: if docking attempt fails after N tries, the "
            "robot returns to its last known position and retries."
        ),
        "source": "iRobot Open Interface Specification v2; Neato Robotics Design Patent US8739355",
        "confidence_score": 0.95,
        "tags": ["docking", "IR", "charging", "navigation", "robot-vacuum", "electrical"],
    },

    # ----------------------------------------------------------------
    # Software / Algorithms
    # ----------------------------------------------------------------
    {
        "title": "Coverage Path Planning — Boustrophedon (Lawnmower) Algorithm",
        "domain": "software",
        "category": "robotics",
        "subcategory": "path planning",
        "detail_level": "intermediate",
        "content": (
            "Boustrophedon coverage path planning sweeps a robot back and forth "
            "in parallel lanes (like ploughing a field) to guarantee complete "
            "area coverage with minimal overlap, maximising cleaning efficiency."
        ),
        "extended_content": (
            "The working width w equals the effective brush or suction width. "
            "Step between lanes = w × (1 − overlap_fraction); 10–20% overlap "
            "compensates for odometry error.  Total path length ≈ A / w, where "
            "A is area.  Cellular decomposition variants divide the map into "
            "convex cells (using critical points of obstacle boundary), each "
            "swept independently.  Robot vacuums combine boustrophedon (for open "
            "areas) with wall-following (perimeter first) and spot-clean (spiral) "
            "modes.  Coverage fraction > 98% achievable in obstacle-free rooms; "
            "drops with higher obstacle density."
        ),
        "formula": "Path length ≈ A / (w · (1 − overlap))",
        "units": "m (path), m² (area A), m (width w)",
        "source": "Choset et al., Principles of Robot Motion, MIT Press, 2005; Zelinsky et al. (1993)",
        "confidence_score": 0.96,
        "tags": ["coverage", "path-planning", "boustrophedon", "algorithm", "robot-vacuum", "software"],
    },
    {
        "title": "Particle Filter Algorithm for Robot Localisation (Monte Carlo)",
        "domain": "software",
        "category": "robotics",
        "subcategory": "probabilistic localisation",
        "detail_level": "advanced",
        "content": (
            "A particle filter (Monte Carlo Localisation, MCL) represents the "
            "robot's posterior belief over pose as a set of M weighted samples "
            "(particles) and updates them with motion and sensor models."
        ),
        "extended_content": (
            "Algorithm: (1) Predict — propagate each particle through the motion "
            "model with noise; (2) Update — weight each particle by the "
            "likelihood of the sensor observation given that pose; "
            "(3) Resample — draw M new particles with replacement proportional "
            "to weights.  Computational cost: O(M) per step.  Typical M = "
            "200–2000 particles for a 10×10 m room.  Kidnapped-robot problem "
            "(sudden relocation) handled by injecting random particles.  MCL "
            "converges after ≈ 5–30 pose updates.  Adaptive MCL (AMCL) adjusts "
            "M dynamically for efficiency."
        ),
        "source": "Thrun, Burgard & Fox, Probabilistic Robotics, MIT Press, 2005, Ch.4–8",
        "confidence_score": 0.97,
        "tags": ["particle-filter", "MCL", "localisation", "probabilistic", "robotics", "robot-vacuum", "software"],
    },
    {
        "title": "A* Pathfinding Algorithm",
        "domain": "software",
        "category": "algorithms",
        "subcategory": "graph search",
        "detail_level": "intermediate",
        "content": (
            "A* finds the lowest-cost path between two nodes in a weighted graph "
            "by evaluating f(n) = g(n) + h(n), where g(n) is the cost from start "
            "to node n and h(n) is an admissible heuristic estimating cost to goal."
        ),
        "extended_content": (
            "A* is complete and optimal when h(n) is admissible (never overestimates "
            "true cost) and consistent (h(n) ≤ c(n,n') + h(n') for edge n→n'). "
            "In robot-vacuum grid maps, each cell is a node; edge cost = 1 "
            "(4-connected) or √2 (diagonal); h(n) = Euclidean or Manhattan "
            "distance to goal.  Time complexity O(b^d) in worst case (b = branching "
            "factor, d = depth); in practice, the heuristic reduces nodes explored "
            "dramatically.  Robot vacuums use A* for goal-directed navigation "
            "(return to dock, navigate around furniture) and D* Lite for dynamic "
            "replanning when new obstacles are discovered."
        ),
        "formula": "f(n) = g(n) + h(n)",
        "source": "Hart, Nilsson & Raphael (1968), IEEE Trans. SSC; Cormen et al., Introduction to Algorithms",
        "confidence_score": 0.99,
        "tags": ["A-star", "pathfinding", "graph-search", "algorithm", "robotics", "robot-vacuum", "software"],
    },

    # ----------------------------------------------------------------
    # Wireless Communication
    # ----------------------------------------------------------------
    {
        "title": "Bluetooth Low Energy (BLE) for App Control",
        "domain": "electrical",
        "category": "wireless communication",
        "subcategory": "short-range",
        "detail_level": "intermediate",
        "content": (
            "BLE (Bluetooth Low Energy, Bluetooth 4.0+) provides short-range "
            "wireless connectivity (10–100 m) at very low energy consumption, "
            "making it suitable for mobile-app control of robot vacuums."
        ),
        "extended_content": (
            "BLE operates in the 2.4 GHz ISM band using 40 channels (3 "
            "advertising, 37 data).  Peak current: 10–15 mA TX; average current "
            "with 100 ms connection interval: ≈ 0.1–1 mA.  Max throughput: "
            "≈ 1 Mbps PHY (BLE 5.0); application data ≈ 50–250 kbps.  GATT "
            "profile (Generic Attribute Profile) defines services and "
            "characteristics for robot control (start/stop, mode, cleaning map).  "
            "BLE is used for initial pairing and local control; WiFi is used for "
            "cloud connectivity and firmware updates."
        ),
        "source": "Bluetooth SIG, Bluetooth Core Specification v5.3; Nordic Semiconductor BLE Guide",
        "confidence_score": 0.98,
        "tags": ["BLE", "Bluetooth", "wireless", "app-control", "IoT", "robot-vacuum", "electrical"],
    },
    {
        "title": "OTA Firmware Update for Embedded Devices",
        "domain": "software",
        "category": "embedded systems",
        "subcategory": "firmware management",
        "detail_level": "intermediate",
        "content": (
            "Over-the-Air (OTA) firmware updates deliver new software to "
            "embedded devices wirelessly, enabling remote bug fixes, feature "
            "additions, and security patches without physical access."
        ),
        "extended_content": (
            "OTA requires: (1) dual-bank flash (active + staging) or delta "
            "patching; (2) secure transport (TLS/DTLS); (3) image integrity "
            "check (SHA-256 hash + RSA/ECDSA signature); (4) rollback to last "
            "good image on boot failure.  Robot vacuums use WiFi (HTTP/HTTPS "
            "or MQTT) to download firmware from cloud (AWS IoT Jobs, Azure IoT "
            "Hub).  Minimum flash requirement: 2 × image size + metadata.  "
            "Update must be atomic — power loss during write must not brick the "
            "device; watchdog timer triggers rollback if the new firmware fails "
            "to confirm itself within N seconds."
        ),
        "source": "Moran et al., Embedded Systems Security, Elsevier; ESP-IDF OTA Guide; Mbed OS OTA Framework",
        "confidence_score": 0.97,
        "tags": ["OTA", "firmware", "update", "security", "IoT", "robot-vacuum", "software"],
    },

    # ----------------------------------------------------------------
    # IMU
    # ----------------------------------------------------------------
    {
        "title": "IMU (Inertial Measurement Unit) for Robot Navigation",
        "domain": "electrical",
        "category": "sensors",
        "subcategory": "inertial sensing",
        "detail_level": "intermediate",
        "content": (
            "An IMU combines a 3-axis accelerometer and 3-axis gyroscope (and "
            "optionally a magnetometer) to measure linear acceleration and "
            "angular rate, enabling dead-reckoning pose estimation in the "
            "absence of wheel odometry."
        ),
        "extended_content": (
            "Gyroscope output: angular rate ω (rad/s); integrating ω gives "
            "angle θ but drift accumulates (bias instability 0.1–10 °/√h for "
            "MEMS).  Accelerometer provides gravity vector for tilt but is "
            "noisy.  Sensor fusion (Kalman filter or complementary filter) "
            "combines gyro (short-term) and accelerometer (long-term) for "
            "stable orientation.  In robot vacuums, IMU detects wheel slip "
            "(acceleration inconsistent with encoder), floor tilt, and "
            "bump/collision events.  Typical MEMS IMU (MPU-6050, BMI088): "
            "gyro noise 0.01 °/s/√Hz, accel noise 100 µg/√Hz, I²C/SPI output."
        ),
        "formula": "θ(t) = ∫ ω(t) dt  (gyro integration, prone to drift)",
        "units": "ω: rad/s, θ: rad, a: m/s²",
        "source": "Titterton & Weston, Strapdown Inertial Navigation Technology, 2nd ed.; Invensense MPU-6050 PS",
        "confidence_score": 0.97,
        "tags": ["IMU", "gyroscope", "accelerometer", "inertial", "navigation", "robot-vacuum", "electrical"],
    },
]


# ---------------------------------------------------------------------------
# Relationships between device-design facts
# ---------------------------------------------------------------------------

DEVICE_FACT_RELATIONSHIPS: list[dict] = [
    # Weather Station
    {
        "source_title": "ADC Resolution and Measurement Precision",
        "target_title": "Nyquist–Shannon Sampling Theorem",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "Correct ADC sampling requires the Nyquist criterion to be met.",
    },
    {
        "source_title": "NTC Thermistor Temperature Sensing",
        "target_title": "ADC Resolution and Measurement Precision",
        "relationship_type": "depends_on",
        "weight": 0.9,
        "description": "Thermistor voltage output must be digitised by the ADC.",
    },
    {
        "source_title": "RTD (PT100/PT1000) Temperature Measurement",
        "target_title": "ADC Resolution and Measurement Precision",
        "relationship_type": "depends_on",
        "weight": 0.9,
        "description": "RTD resistance is converted to voltage for ADC input.",
    },
    {
        "source_title": "Sensor Calibration and Traceability to SI",
        "target_title": "NTC Thermistor Temperature Sensing",
        "relationship_type": "supports",
        "weight": 0.9,
        "description": "Calibration improves the accuracy of thermistor readings.",
    },
    {
        "source_title": "Sensor Calibration and Traceability to SI",
        "target_title": "MEMS Barometric Pressure Sensor",
        "relationship_type": "supports",
        "weight": 0.9,
        "description": "Pressure sensor calibration is required for accurate QNH data.",
    },
    {
        "source_title": "Solar Panel Sizing for Remote IoT Stations",
        "target_title": "Li-Ion Battery Capacity and Energy Calculation",
        "relationship_type": "depends_on",
        "weight": 0.9,
        "description": "Battery sizing is required before determining solar panel output.",
    },
    {
        "source_title": "Low-Power Microcontroller Sleep Modes",
        "target_title": "Solar Panel Sizing for Remote IoT Stations",
        "relationship_type": "supports",
        "weight": 0.8,
        "description": "Lower average current reduces required panel and battery size.",
    },
    {
        "source_title": "MQTT Protocol for IoT Sensor Data",
        "target_title": "NTP Time Synchronisation for Data Logging",
        "relationship_type": "depends_on",
        "weight": 0.7,
        "description": "Accurate timestamps on MQTT messages require synchronised clocks.",
    },
    {
        "source_title": "LoRa / LoRaWAN — LPWAN for Remote Telemetry",
        "target_title": "MQTT Protocol for IoT Sensor Data",
        "relationship_type": "supports",
        "weight": 0.7,
        "description": "MQTT can be carried over a LoRaWAN uplink.",
    },
    {
        "source_title": "Radiation Shield for Meteorological Temperature Sensors",
        "target_title": "NTC Thermistor Temperature Sensing",
        "relationship_type": "supports",
        "weight": 0.95,
        "description": "A radiation shield is essential for accurate thermistor readings.",
    },
    {
        "source_title": "IP (Ingress Protection) Rating — IEC 60529",
        "target_title": "I²C Serial Communication Protocol",
        "relationship_type": "supports",
        "weight": 0.6,
        "description": "Enclosure IP rating protects the electronics hosting the I²C bus.",
    },
    # Robot Vacuum
    {
        "source_title": "SLAM — Simultaneous Localisation and Mapping",
        "target_title": "Particle Filter Algorithm for Robot Localisation (Monte Carlo)",
        "relationship_type": "depends_on",
        "weight": 0.9,
        "description": "Particle filter MCL is a core algorithm for SLAM localisation.",
    },
    {
        "source_title": "SLAM — Simultaneous Localisation and Mapping",
        "target_title": "2D LiDAR Distance Measurement Principle",
        "relationship_type": "depends_on",
        "weight": 0.95,
        "description": "LiDAR point clouds are the primary sensor input for LiDAR SLAM.",
    },
    {
        "source_title": "Coverage Path Planning — Boustrophedon (Lawnmower) Algorithm",
        "target_title": "SLAM — Simultaneous Localisation and Mapping",
        "relationship_type": "depends_on",
        "weight": 0.85,
        "description": "Coverage planning requires a consistent map from SLAM.",
    },
    {
        "source_title": "A* Pathfinding Algorithm",
        "target_title": "SLAM — Simultaneous Localisation and Mapping",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "A* navigates the occupancy grid map produced by SLAM.",
    },
    {
        "source_title": "Differential Drive Robot Kinematics",
        "target_title": "Wheel Encoder Odometry",
        "relationship_type": "depends_on",
        "weight": 0.95,
        "description": "Differential drive pose estimation depends on encoder odometry.",
    },
    {
        "source_title": "SLAM — Simultaneous Localisation and Mapping",
        "target_title": "Differential Drive Robot Kinematics",
        "relationship_type": "depends_on",
        "weight": 0.85,
        "description": "SLAM motion model uses differential-drive kinematic equations.",
    },
    {
        "source_title": "DC Motor Speed Control via PWM",
        "target_title": "H-Bridge Motor Driver Circuit",
        "relationship_type": "depends_on",
        "weight": 1.0,
        "description": "PWM speed control is applied through the H-bridge driver.",
    },
    {
        "source_title": "Brushless DC (BLDC) Motor for Suction Fan",
        "target_title": "Suction Pressure and Airflow in Vacuum Systems",
        "relationship_type": "supports",
        "weight": 0.9,
        "description": "BLDC motor performance determines the achievable suction and airflow.",
    },
    {
        "source_title": "HEPA Filter Efficiency and Filtration Grade",
        "target_title": "Suction Pressure and Airflow in Vacuum Systems",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "HEPA filter pressure drop directly reduces system airflow.",
    },
    {
        "source_title": "Robot Runtime Estimation from Battery Capacity",
        "target_title": "Li-Ion Battery Capacity and Energy Calculation",
        "relationship_type": "derived_from",
        "weight": 1.0,
        "description": "Runtime estimation formula is derived from battery capacity equations.",
    },
    {
        "source_title": "Automatic Charging Dock — IR Beacon Homing",
        "target_title": "Infrared Cliff Detection for Robot Vacuums",
        "relationship_type": "example_of",
        "weight": 0.5,
        "description": "Both systems use modulated IR sensing; docking homing is a related application.",
    },
    {
        "source_title": "OTA Firmware Update for Embedded Devices",
        "target_title": "Bluetooth Low Energy (BLE) for App Control",
        "relationship_type": "supports",
        "weight": 0.6,
        "description": "BLE can be used as the transport channel for OTA updates.",
    },
    {
        "source_title": "IMU (Inertial Measurement Unit) for Robot Navigation",
        "target_title": "Differential Drive Robot Kinematics",
        "relationship_type": "supports",
        "weight": 0.75,
        "description": "IMU angular rate supplements wheel odometry for improved pose estimation.",
    },
    {
        "source_title": "Particle Filter Algorithm for Robot Localisation (Monte Carlo)",
        "target_title": "A* Pathfinding Algorithm",
        "relationship_type": "supports",
        "weight": 0.7,
        "description": "Accurate localisation from MCL provides reliable start pose for A*.",
    },
    # Cross-product shared knowledge
    {
        "source_title": "I²C Serial Communication Protocol",
        "target_title": "IMU (Inertial Measurement Unit) for Robot Navigation",
        "relationship_type": "supports",
        "weight": 0.8,
        "description": "IMU sensors typically communicate with the MCU over I²C or SPI.",
    },
    {
        "source_title": "Low-Power Microcontroller Sleep Modes",
        "target_title": "Robot Runtime Estimation from Battery Capacity",
        "relationship_type": "supports",
        "weight": 0.7,
        "description": "MCU sleep modes reduce standby power, extending robot battery life.",
    },
]
