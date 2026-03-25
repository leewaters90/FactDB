"""
Mechatronics project seed data for FactDB.

Structure
---------
DESIGN_ELEMENTS
    Flat list of reusable, sharable design decisions.  Each element has
    a unique title that serves as its lookup key.  A single element
    (e.g. "ESP32 WiFi + MQTT Telemetry") can be linked to many projects.

MECHATRONICS_PROJECTS
    List of project metadata dicts.  Each project references elements by
    title in its ``design_element_titles`` list, and may supply optional
    ``element_usage_notes`` (a dict mapping element title → usage note) to
    record project-specific context.
"""

from __future__ import annotations


def _alt(approach: str, reason_rejected: str) -> dict:
    return {"approach": approach, "reason_rejected": reason_rejected}


# ======================================================================
# SHARED DESIGN ELEMENTS
# ======================================================================

DESIGN_ELEMENTS: list[dict] = [

    # ------------------------------------------------------------------
    # SENSING
    # ------------------------------------------------------------------

    {
        "title": "Capacitive Soil Moisture Probe",
        "component_category": "sensing",
        "design_question": "How to measure soil VWC accurately without electrode corrosion?",
        "selected_approach": (
            "Capacitive soil moisture sensor inserted 5 cm deep; "
            "voltage output 1.2–3.0 V read by MCU 12-bit ADC. "
            "Calibrated against gravimetric method per soil type."
        ),
        "rationale": (
            "Capacitive probes resist corrosion and provide a continuous "
            "voltage linearly proportional to VWC. ADC resolution of 0.8 mV "
            "at 3.3 V full-scale gives ≈0.5 % VWC resolution—adequate for "
            "the 20–60 % target range."
        ),
        "alternatives": [
            _alt("Resistive YL-69 probe",
                 "Electrolytic corrosion within weeks; nonlinear response—rejected."),
            _alt("TDR probe",
                 "High accuracy but >£40 and complex RF circuitry—over-engineered."),
        ],
        "verification_notes": (
            "FACT: 'Capacitive Soil Moisture Sensing' confirms 1.2–3.0 V output "
            "and temperature compensation above 30 °C. "
            "FACT: 'ADC Resolution' confirms 0.8 mV/LSB at 3.3 V."
        ),
        "supporting_fact_titles": [
            "Capacitive Soil Moisture Sensing",
            "ADC Resolution and Measurement Precision",
        ],
    },

    {
        "title": "SHT41 Digital Temperature and RH Sensing",
        "component_category": "sensing",
        "design_question": "Which humidity/temperature sensor provides factory-calibrated accuracy without field calibration?",
        "selected_approach": (
            "Sensirion SHT41 (I²C, ±0.2 °C, ±1.8 %RH) for each zone. "
            "NIST-traceable factory calibration; no field adjustment required."
        ),
        "rationale": (
            "SHT41 ±0.2 °C vs DHT22 ±0.5 °C; factory calibration eliminates "
            "field zeroing cost. Integrated on same I²C bus as other sensors."
        ),
        "alternatives": [
            _alt("DHT22", "1-wire timing-critical protocol; no factory calibration—rejected."),
            _alt("NTC thermistor + capacitive RH", "Two separate components; requires individual calibration."),
        ],
        "verification_notes": (
            "FACT: 'Capacitive Relative Humidity Sensing' confirms SHT4x accuracy "
            "and I²C interface. FACT: 'I²C Serial Communication Protocol'."
        ),
        "supporting_fact_titles": [
            "Capacitive Relative Humidity Sensing",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "SCD41 NDIR CO₂ Sensing Module",
        "component_category": "sensing",
        "design_question": "Which CO₂ technology provides ±50 ppm accuracy without user recalibration?",
        "selected_approach": (
            "Sensirion SCD41 NDIR sensor (I²C, ±40 ppm, ABC self-calibration). "
            "On-chip temperature and pressure compensation."
        ),
        "rationale": (
            "NDIR is a primary technique (Beer-Lambert law) with <2 %/year "
            "drift. ABC algorithm uses fresh-air reference automatically—"
            "no user action needed."
        ),
        "alternatives": [
            _alt("MQ-135 metal-oxide sensor",
                 "Heavy cross-sensitivity to multiple gases; weeks of burn-in; "
                 "not selective for CO₂—rejected."),
            _alt("MH-Z19B NDIR",
                 "Acceptable accuracy but lacks on-chip RH compensation."),
        ],
        "verification_notes": (
            "FACT: 'NDIR CO₂ Sensor — Non-Dispersive Infrared' confirms Beer-Lambert "
            "principle and ABC baseline correction."
        ),
        "supporting_fact_titles": [
            "NDIR CO₂ Sensor — Non-Dispersive Infrared",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "SPS30 PM2.5 Optical Particle Sensor",
        "component_category": "sensing",
        "design_question": "How to measure PM2.5 and PM10 in a compact enclosure without external fan plumbing?",
        "selected_approach": (
            "Sensirion SPS30 (UART/I²C, built-in fan + laser, PM1/2.5/4/10 "
            "in µg/m³). Auto-cleaning fan cycle every 168 h."
        ),
        "rationale": (
            "SPS30 is self-contained, factory-calibrated, and auto-cleaning "
            "extends service life to 8 years. ±10 % accuracy vs ±30 % for "
            "single-photodiode alternatives."
        ),
        "alternatives": [
            _alt("Sharp GP2Y1010AU0F",
                 "No particle-size classification; gives total dust count only—rejected."),
        ],
        "verification_notes": (
            "FACT: 'PM2.5 Optical Particle Counter' confirms Mie scattering principle "
            "and humidity cross-sensitivity above 75 % RH."
        ),
        "supporting_fact_titles": [
            "PM2.5 Optical Particle Counter",
        ],
    },

    {
        "title": "MPU-6050 IMU Gyro + Accel (I²C)",
        "component_category": "sensing",
        "design_question": "How to measure tilt angle and angular rate at ≥100 Hz with <1° noise?",
        "selected_approach": (
            "MPU-6050 on I²C at 200 Hz. Complementary filter "
            "θ = 0.98·(θ + ω·dt) + 0.02·θ_accel for stable angle."
        ),
        "rationale": (
            "Complementary filter is computationally cheap and stable. "
            "Gyro noise 0.01 °/s/√Hz gives <0.05° error over 10 ms cycle—"
            "sufficient for ±5° balance targets."
        ),
        "alternatives": [
            _alt("Kalman filter (EKF)", "More accurate but higher CPU load on 8-bit MCU."),
            _alt("Accelerometer only", "Noise from motor vibration corrupts reading during motion—rejected."),
        ],
        "verification_notes": (
            "FACT: 'IMU (Inertial Measurement Unit) for Robot Navigation' confirms "
            "gyro drift and necessity of accel fusion. "
            "FACT: 'Kalman Filter for Sensor Fusion' provides the EKF upgrade path."
        ),
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Kalman Filter for Sensor Fusion",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "ICM-42688-P High-Rate IMU via SPI",
        "component_category": "sensing",
        "design_question": "How to sample IMU at 8 kHz with <5 µs latency for a 4 kHz flight control loop?",
        "selected_approach": (
            "ICM-42688-P on SPI at 8 MHz; gyro at 8 kHz downsampled to "
            "4 kHz. Anti-aliasing filter at 1 kHz. Mahony complementary filter."
        ),
        "rationale": (
            "SPI at 8 MHz gives <5 µs latency vs I²C 400 kHz at 40 µs—"
            "critical for 4 kHz loop. Mahony filter proven in Betaflight."
        ),
        "alternatives": [
            _alt("MPU-6050 on I²C 400 kHz",
                 "I²C too slow for 8 kHz sample rate; 40 µs latency unacceptable—rejected."),
        ],
        "verification_notes": (
            "FACT: 'Nyquist–Shannon Sampling Theorem'—8 kHz satisfies Nyquist for "
            "rotor vibrations up to 4 kHz."
        ),
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Nyquist–Shannon Sampling Theorem",
        ],
    },

    {
        "title": "8-Sensor TCRT5000 IR Reflectance Array",
        "component_category": "sensing",
        "design_question": "How many IR reflectance sensors give sub-millimetre line position for PID?",
        "selected_approach": (
            "8 TCRT5000 sensors spaced 10 mm (80 mm span), modulated at "
            "38 kHz. Position = weighted average of reflectance values."
        ),
        "rationale": (
            "8 sensors give smooth, differentiable error signal required by "
            "PID derivative term. 38 kHz modulation rejects ambient IR."
        ),
        "alternatives": [
            _alt("Camera + OpenCV", "3–5 W vs 0.1 W; latency 30–50 ms vs <1 ms—rejected for speed."),
            _alt("Single IR sensor + bang-bang", "Bang-bang causes oscillatory weaving on curves—rejected."),
        ],
        "verification_notes": (
            "FACT: 'PID Controller — Transfer Function'—continuous error signal "
            "needed for K_d term; weighted average provides this."
        ),
        "supporting_fact_titles": [
            "PID Controller — Transfer Function",
        ],
    },

    {
        "title": "MFRC522 RFID Card Reader (NTAG216)",
        "component_category": "sensing",
        "design_question": "Which RFID standard provides adequate security for an office access-control system?",
        "selected_approach": (
            "MFRC522 reader + NTAG216 NFC tags (ISO 14443A, 7-byte UID). "
            "SPI at 10 MHz. UID + timestamp HMAC-SHA256 signed in firmware."
        ),
        "rationale": (
            "NTAG216 has a unique 7-byte UID not easily cloned; HMAC prevents "
            "replay attacks. Mifare Classic CRYPTO1 is broken since 2008."
        ),
        "alternatives": [
            _alt("Mifare Classic 1K",
                 "CRYPTO1 cipher broken; UID cloneable with £5 device—rejected on security grounds."),
            _alt("Fingerprint sensor AS608",
                 "GDPR complexity for biometric data; higher cost—rejected."),
        ],
        "verification_notes": (
            "FACT: 'RFID/NFC Reader — ISO 14443 / 15693 Interface' explicitly warns "
            "about Mifare Classic CRYPTO1 weakness and recommends NTAG216."
        ),
        "supporting_fact_titles": [
            "RFID/NFC Reader — ISO 14443 / 15693 Interface",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "SCT-013 Split-Core CT Clamp Current Sensing",
        "component_category": "sensing",
        "design_question": "How to measure 0–100 A AC current non-invasively with <0.5 % gain error?",
        "selected_approach": (
            "SCT-013-100 (100 A:50 mA, N=2000). Burden R_b=33 Ω → 2.33 V "
            "peak. Biased to mid-rail (1.65 V). Sampled at 4800 Hz."
        ),
        "rationale": (
            "SCT-013 ±1 % accuracy 10–120 % rated current. Burden voltage "
            "<3.3 V safe for ESP32 ADC. 4800 Hz ≫ 2×60 Hz Nyquist."
        ),
        "alternatives": [
            _alt("ACS712 inline Hall sensor",
                 "Requires cutting the monitored wire—defeats non-invasive objective."),
            _alt("Shunt resistor inline",
                 "Mains-side connection; isolated ADC required; safety risk—rejected."),
        ],
        "verification_notes": (
            "FACT: 'CT Clamp Current Sensing and RMS Calculation' confirms parameters "
            "and open-circuit safety warning."
        ),
        "supporting_fact_titles": [
            "CT Clamp Current Sensing and RMS Calculation",
            "ADC Resolution and Measurement Precision",
            "Nyquist–Shannon Sampling Theorem",
        ],
    },

    {
        "title": "9 V Transformer Mains Voltage Reference",
        "component_category": "sensing",
        "design_question": "How to measure mains voltage safely for real-power calculation?",
        "selected_approach": (
            "9 V AC plug-in wall-wart (1:25.6 ratio); resistive divider to "
            "1.65 V mid-rail. Phase-corrected in software (≈3° CT offset). "
            "Real power P = (1/N)·Σ(v_n·i_n)."
        ),
        "rationale": (
            "Wall-wart is fully mains-isolated—no user shock risk. Preserves "
            "waveform shape for phase and THD analysis."
        ),
        "alternatives": [
            _alt("Direct resistive divider live/neutral",
                 "Mains potential on PCB; requires certified isolation—unacceptable for DIY."),
        ],
        "verification_notes": (
            "FACT: 'Ohm's Law'—voltage divider V_out = V_in·R₂/(R₁+R₂). "
            "FACT: 'Kirchhoff's Voltage Law (KVL)'."
        ),
        "supporting_fact_titles": [
            "Ohm's Law",
            "Kirchhoff's Voltage Law (KVL)",
        ],
    },

    {
        "title": "I²C TCA9548A Multi-Device Sensor Bus",
        "component_category": "sensing",
        "design_question": "How to connect multiple identical I²C sensors (same address) to one MCU bus?",
        "selected_approach": (
            "TCA9548A 8-channel I²C multiplexer. Each channel switched in "
            "software before communicating with its sensor."
        ),
        "rationale": (
            "TCA9548A resolves address conflicts for 4 identical SHT41 "
            "(all 0x44). Scanning at 1-min intervals adds negligible overhead."
        ),
        "alternatives": [
            _alt("Separate MCU I²C ports per zone",
                 "Most MCUs have only 1–2 hardware I²C peripherals—insufficient for 4 zones."),
        ],
        "verification_notes": (
            "FACT: 'I²C Serial Communication Protocol' confirms address conflict "
            "resolution with multiplexer pattern."
        ),
        "supporting_fact_titles": [
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "Magnetic Quadrature Wheel Encoders",
        "component_category": "sensing",
        "design_question": "How to measure wheel speed and position for closed-loop motor control?",
        "selected_approach": (
            "600 CPR magnetic quadrature encoders on each drive wheel. "
            "MCU interrupt-driven counting; direction from A/B phase."
        ),
        "rationale": (
            "600 CPR×4 (quadrature) = 2400 effective counts/rev. "
            "At 75 mm wheel: Δd = π×0.075/2400 ≈ 0.098 mm/count."
        ),
        "alternatives": [
            _alt("Optical encoder", "More expensive; susceptible to dust—magnetic preferred outdoors."),
        ],
        "verification_notes": (
            "FACT: 'Wheel Encoder Odometry' confirms Δd formula and 1–3 % "
            "cumulative odometry error."
        ),
        "supporting_fact_titles": [
            "Wheel Encoder Odometry",
            "Differential Drive Robot Kinematics",
        ],
    },

    # ------------------------------------------------------------------
    # ACTUATION
    # ------------------------------------------------------------------

    {
        "title": "N-Channel MOSFET Low-Side Load Switch",
        "component_category": "actuation",
        "design_question": "How to switch a DC or 12 V inductive load (valve, lock, fan) from a 3.3 V GPIO?",
        "selected_approach": (
            "IRLZ44N N-channel MOSFET (logic-level, 55 V, 47 A). "
            "Gate driven via 100 Ω resistor. 1N4007 flyback diode for inductive loads."
        ),
        "rationale": (
            "Logic-level V_th ≈ 1–2 V means 3.3 V GPIO fully enhances the "
            "gate. R_DS(on)<0.022 Ω minimises conduction loss."
        ),
        "alternatives": [
            _alt("Relay module SRD-05VDC",
                 "100 mA coil current too high for battery nodes; audible click—rejected."),
        ],
        "verification_notes": (
            "FACT: 'N-Channel MOSFET as a Low-Side Power Switch' confirms "
            "IRLZ44N suitability and flyback diode requirement."
        ),
        "supporting_fact_titles": [
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    {
        "title": "TB6612FNG Dual H-Bridge PWM Motor Drive",
        "component_category": "actuation",
        "design_question": "Which motor driver provides bidirectional control for two DC gearmotors from a 3.3 V MCU?",
        "selected_approach": (
            "TB6612FNG dual H-bridge (1.2 A continuous, 3.2 A peak). "
            "20 kHz PWM above audible range. 3.3 V logic compatible."
        ),
        "rationale": (
            "TB6612FNG includes thermal shutdown, no external voltage drop "
            "issue (unlike L298N 2–3 V saturation loss). Two motors in one IC."
        ),
        "alternatives": [
            _alt("L298N", "2–3 V saturation drop; bulky; no current limit—rejected."),
        ],
        "verification_notes": (
            "FACT: 'H-Bridge Motor Driver Circuit' confirms dead-time insertion "
            "and 20 kHz PWM above audible range."
        ),
        "supporting_fact_titles": [
            "H-Bridge Motor Driver Circuit",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "RC Servo Joint Actuator",
        "component_category": "actuation",
        "design_question": "How to position a joint with ±1° accuracy and adequate torque from a 5 V supply?",
        "selected_approach": (
            "MG996R at shoulder (10 kg·cm); MG90S at elbow (2.2 kg·cm); "
            "SG90 for light tasks. 50 Hz PWM: 1 ms=0°, 1.5 ms=90°, 2 ms=180°."
        ),
        "rationale": (
            "RC servos self-contain gearbox, driver, and potentiometer "
            "feedback. MG996R provides 5× FoS at shoulder joint."
        ),
        "alternatives": [
            _alt("Stepper + belt drive",
                 "Higher torque but requires separate driver, complex frame—rejected for simplicity."),
        ],
        "verification_notes": (
            "FACT: 'RC Servo Motor PWM Control' confirms MG996R protocol and torque. "
            "FACT: 'Factor of Safety' confirms FoS=5 is within 3–5 spec."
        ),
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
            "Factor of Safety",
        ],
    },

    {
        "title": "NEMA17 Stepper + DRV8825 Microstepping Drive",
        "component_category": "actuation",
        "design_question": "Which stepper driver minimises vibration at low speeds for precision plotting?",
        "selected_approach": (
            "DRV8825 at 1/32 microstepping, 1.5 A limit. TMC2209 "
            "StealthChop2 preferred for silent operation and sensorless homing."
        ),
        "rationale": (
            "TMC2209 SpreadCycle/StealthChop2 eliminates mid-speed resonance "
            "and audible noise vs A4988 (max 1/16 step, screech)."
        ),
        "alternatives": [
            _alt("A4988 (1/16 max)",
                 "Only 1/16 step resolution; audible resonance at mid-speed—rejected."),
        ],
        "verification_notes": (
            "FACT: 'Stepper Motor Drive — Full Step and Microstepping' confirms "
            "DRV8825 max 1/32 and torque-speed trade-off."
        ),
        "supporting_fact_titles": [
            "Stepper Motor Drive — Full Step and Microstepping",
        ],
    },

    {
        "title": "BLDC 2306 Motor + BLHeli-32 ESC Drive",
        "component_category": "actuation",
        "design_question": "Which BLDC motor/ESC combination achieves ≥5 min flight with 450 g AUW?",
        "selected_approach": (
            "4× Emax RS2306 2750 KV + 4× BLHeli-32 30 A ESCs. "
            "5-inch 3-blade props. Hover at ≈30 % throttle on 4S 14.8 V."
        ),
        "rationale": (
            "2750 KV × 14.8 V ≈ 40 000 RPM. Thrust/motor at hover = 112 g "
            "≈15 % max thrust—highly efficient operating point."
        ),
        "alternatives": [
            _alt("Coreless brushed motors",
                 "60–70 % efficiency vs 85–95 % for BLDC; shorter brush life—rejected."),
        ],
        "verification_notes": (
            "FACT: 'Brushless DC (BLDC) Motor for Suction Fan' confirms electronic "
            "commutation principle applicable to propulsion."
        ),
        "supporting_fact_titles": [
            "Brushless DC (BLDC) Motor for Suction Fan",
            "Robot Runtime Estimation from Battery Capacity",
        ],
    },

    {
        "title": "Electric NC Door Strike Solenoid",
        "component_category": "actuation",
        "design_question": "How to actuate a door lock with fail-safe (locked on power failure) behaviour?",
        "selected_approach": (
            "Normally-Closed (NC) electric strike driven by MOSFET. "
            "Energised 300 ms to allow passage; locked when MCU or power off."
        ),
        "rationale": (
            "NC strike fail-safe: lost power = locked (safe). "
            "300 ms pulse limits thermal dissipation in solenoid coil."
        ),
        "alternatives": [
            _alt("NO electric strike",
                 "Fails open on power loss—unacceptable for security application."),
            _alt("Motor-driven deadbolt",
                 "Slower actuation (>500 ms); higher complexity—rejected."),
        ],
        "verification_notes": (
            "FACT: 'N-Channel MOSFET as a Low-Side Power Switch' confirms "
            "flyback diode for solenoid and NC configuration."
        ),
        "supporting_fact_titles": [
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    {
        "title": "Solid-State Relay Mains Actuator Switching",
        "component_category": "actuation",
        "design_question": "How to switch 230 V AC loads (fan, heater, LED driver) silently from a 3.3 V GPIO?",
        "selected_approach": (
            "Fotek SSR-40DA solid-state relay per mains load. "
            "DC control input 3–32 V (3.3 V compatible). Zero-crossing switch. "
            "Thermal fuse on heater mat as secondary interlock."
        ),
        "rationale": (
            "SSR: no moving parts, silent, zero-crossing reduces EMI, "
            "rated 500 000+ cycles vs relay ≈100 000 cycles."
        ),
        "alternatives": [
            _alt("Mechanical relay",
                 "100 000 cycle limit; audible click; contact wear—rejected for continuous duty."),
        ],
        "verification_notes": (
            "FACT: 'N-Channel MOSFET as a Low-Side Power Switch'—applies to DC; "
            "for 230 V AC, opto-isolated SSR is the safe standard."
        ),
        "supporting_fact_titles": [
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    # ------------------------------------------------------------------
    # POWER
    # ------------------------------------------------------------------

    {
        "title": "Solar Panel + LiFePO₄ MPPT Power System",
        "component_category": "power",
        "design_question": "How to achieve ≥1-week battery autonomy from solar for a remote IoT node?",
        "selected_approach": (
            "60×90 mm 1 W solar panel + 3.2 V 2 Ah LiFePO₄ via CN3791 MPPT "
            "charge controller. ESP32 deep sleep between 15-min cycles. "
            "Avg I ≈ 24 µA @ 96 µW."
        ),
        "rationale": (
            "LiFePO₄: safer chemistry, 2000+ cycle life, tolerates outdoor temp. "
            "1 W panel at 2 PSH gives 2 Wh/day—83× the 24 µW needed."
        ),
        "alternatives": [
            _alt("AAA alkaline pack",
                 "Non-rechargeable; ≈83 h at 14.6 µA average—monthly replacement—rejected."),
        ],
        "verification_notes": (
            "FACT: 'Solar Panel Sizing' formula P = E_daily/(η·PSH) confirms "
            "0.038 W minimum—well under 1 W panel. "
            "FACT: 'Low-Power Microcontroller Sleep Modes' confirms I_avg formula."
        ),
        "supporting_fact_titles": [
            "Solar Panel Sizing for Remote IoT Stations",
            "Li-Ion Battery Capacity and Energy Calculation",
            "Low-Power Microcontroller Sleep Modes",
        ],
    },

    {
        "title": "MCU Deep-Sleep Duty Cycle Power Management",
        "component_category": "power",
        "design_question": "How to minimise average current on a battery node that samples every N minutes?",
        "selected_approach": (
            "MCU enters deep sleep (5–10 µA) between measurement windows. "
            "I_avg = I_active·(t_on/T) + I_sleep. "
            "Peripheral VCC gated by GPIO MOSFET."
        ),
        "rationale": (
            "Deep sleep reduces active-fraction contribution by 1000×. "
            "Peripheral gating prevents sensor quiescent drain between samples."
        ),
        "alternatives": [
            _alt("Always-on with idle loop",
                 "Active current 25–80 mA continuously; battery life <10 h on 2 Ah—rejected."),
        ],
        "verification_notes": (
            "FACT: 'Low-Power Microcontroller Sleep Modes' confirms I_avg formula "
            "and 0.1–5 µA deep sleep range for ARM Cortex-M0+/ESP32."
        ),
        "supporting_fact_titles": [
            "Low-Power Microcontroller Sleep Modes",
        ],
    },

    {
        "title": "Li-Po 3.7 V USB-C Rechargeable Battery Pack",
        "component_category": "power",
        "design_question": "What battery capacity provides ≥8 h continuous operation for a handheld IoT device?",
        "selected_approach": (
            "3.7 V 2000 mAh Li-Po (103450 format). "
            "P_total ≈ 174 mA @ 3.3 V = 574 mW. "
            "Runtime = 2.0×3.7×0.8 / 0.574 ≈ 10.3 h—meets 8 h spec."
        ),
        "rationale": (
            "2000 mAh fits 120×60×25 mm enclosure. 2.3 h margin covers "
            "battery aging and BLE overhead."
        ),
        "alternatives": [],
        "verification_notes": (
            "FACT: 'Robot Runtime Estimation from Battery Capacity': "
            "t = C×V×DoD/P = 2.0×3.7×0.8/0.574 ≈ 10.3 h."
        ),
        "supporting_fact_titles": [
            "Li-Ion Battery Capacity and Energy Calculation",
            "Robot Runtime Estimation from Battery Capacity",
        ],
    },

    {
        "title": "4S LiPo Flight Power Budget",
        "component_category": "power",
        "design_question": "Which battery achieves ≥5 min hover with 450 g AUW on a 250 mm quad?",
        "selected_approach": (
            "4S 1500 mAh 75C LiPo (14.8 V, 22.2 Wh). "
            "Hover current ≈ 28 A total. "
            "Runtime = 22.2×0.8 / (28×14.8/1000×60) ≈ 5.4 min."
        ),
        "rationale": (
            "1500 mAh @ 75C = 112.5 A burst—adequate for aggressive manoeuvres. "
            "Weight 115 g fits under 500 g AUW budget."
        ),
        "alternatives": [
            _alt("3S 2200 mAh",
                 "Lower C-rating limits peak current for 2306 motors; "
                 "heavier than 4S 1500 mAh—rejected for performance."),
        ],
        "verification_notes": (
            "FACT: 'Robot Runtime Estimation from Battery Capacity': "
            "usable Wh = 22.2×0.8 = 17.8 Wh; P_hover = 450×9.81×(1/FoM) ≈ 200 W."
        ),
        "supporting_fact_titles": [
            "Li-Ion Battery Capacity and Energy Calculation",
            "Robot Runtime Estimation from Battery Capacity",
        ],
    },

    # ------------------------------------------------------------------
    # COMMUNICATION
    # ------------------------------------------------------------------

    {
        "title": "ESP32 WiFi + MQTT IoT Telemetry",
        "component_category": "communication",
        "design_question": "How to transmit sensor data to a home server with minimum energy and zero external hardware cost?",
        "selected_approach": (
            "ESP32 WiFi to home router. MQTT over TCP (QoS 0–1) to Mosquitto "
            "broker. WiFi active <1 s per cycle; reconnect using stored credentials."
        ),
        "rationale": (
            "ESP32 integrates WiFi+BLE on-chip—zero external component cost. "
            "MQTT QoS 0 minimises transmission time; QoS 1 for critical events."
        ),
        "alternatives": [
            _alt("LoRa point-to-point",
                 "No home router needed but requires separate gateway hardware—"
                 "overkill for ≤100 m indoor range."),
        ],
        "verification_notes": (
            "FACT: 'MQTT Protocol for IoT Sensor Data' confirms QoS 0 overhead. "
            "FACT: 'ESP32 WiFi + BLE System-on-Chip' confirms deep-sleep ≈10 µA."
        ),
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
    },

    {
        "title": "BLE GATT Smartphone App Interface",
        "component_category": "communication",
        "design_question": "How to provide a low-energy wireless user interface for a battery-powered device?",
        "selected_approach": (
            "ESP32 BLE stack (GATT server). Custom service with "
            "control/status characteristics. 100 ms connection interval. "
            "Average ≈0.3 mA when connected."
        ),
        "rationale": (
            "BLE integrated in ESP32—no extra hardware. "
            "0.3 mA average vs WiFi 80 mA—23× more efficient for local UI."
        ),
        "alternatives": [
            _alt("WiFi HTTP REST API",
                 "80 mA continuous when server active; much higher power—rejected for UI use case."),
        ],
        "verification_notes": (
            "FACT: 'Bluetooth Low Energy (BLE) for App Control' confirms "
            "GATT profile and 0.1–1 mA average current."
        ),
        "supporting_fact_titles": [
            "Bluetooth Low Energy (BLE) for App Control",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
    },

    {
        "title": "OTA HTTPS Dual-Bank Firmware Update",
        "component_category": "communication",
        "design_question": "How to deliver security patches remotely without physical access to the device?",
        "selected_approach": (
            "ESP-IDF HTTPS OTA. Dual-bank flash (active + staging). "
            "ECDSA-signed image. Watchdog triggers rollback on failed first-boot."
        ),
        "rationale": (
            "OTA critical for security patches on unattended devices. "
            "Dual-bank ensures safe rollback; signed image prevents injection."
        ),
        "alternatives": [],
        "verification_notes": (
            "FACT: 'OTA Firmware Update for Embedded Devices' confirms dual-bank, "
            "HMAC/ECDSA signing, and watchdog rollback requirement."
        ),
        "supporting_fact_titles": [
            "OTA Firmware Update for Embedded Devices",
        ],
    },

    {
        "title": "NTP UTC Timestamped Data Logging",
        "component_category": "communication",
        "design_question": "How to ensure accurate UTC timestamps on all logged events?",
        "selected_approach": (
            "SNTP sync on boot and every 6 h via public NTP pool. "
            "DS3231 RTC (±2 ppm) maintains time during network outages."
        ),
        "rationale": (
            "SNTP accuracy ≈1–50 ms—adequate for sensor logs and audit trails. "
            "RTC backup prevents timestamp gaps during WiFi outages."
        ),
        "alternatives": [
            _alt("Free-running MCU timer",
                 "Drifts ±5 min/day without NTP sync—unacceptable for audit logs."),
        ],
        "verification_notes": (
            "FACT: 'NTP Time Synchronisation for Data Logging' confirms SNTP "
            "accuracy <50 ms and WMO ±1 s requirement."
        ),
        "supporting_fact_titles": [
            "NTP Time Synchronisation for Data Logging",
        ],
    },

    {
        "title": "MQTT QoS-1 Secure Event Logger",
        "component_category": "communication",
        "design_question": "How to guarantee access events reach the broker even under brief WiFi instability?",
        "selected_approach": (
            "MQTT QoS 1 (at-least-once) with local buffer in ESP32 PSRAM. "
            "Events include: UID, timestamp, action (ALLOW/DENY), device_id."
        ),
        "rationale": (
            "QoS 1 re-transmits until broker ACKs—prevents silent event loss. "
            "Local buffer stores events during WiFi drop (up to 1000 events)."
        ),
        "alternatives": [
            _alt("HTTP POST per event",
                 "Higher overhead; not easily buffered locally; MQTT "
                 "preferred for IoT messaging—rejected."),
        ],
        "verification_notes": (
            "FACT: 'MQTT Protocol for IoT Sensor Data' confirms QoS 1 "
            "at-least-once delivery semantics."
        ),
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "NTP Time Synchronisation for Data Logging",
        ],
    },

    # ------------------------------------------------------------------
    # SOFTWARE / CONTROL
    # ------------------------------------------------------------------

    {
        "title": "Complementary Filter IMU Attitude Fusion",
        "component_category": "control",
        "design_question": "How to fuse gyro and accelerometer for stable tilt estimation with minimal CPU load?",
        "selected_approach": (
            "θ = α·(θ_prev + ω·dt) + (1−α)·θ_accel, α=0.98 at 200 Hz. "
            "Computationally trivial vs Kalman filter."
        ),
        "rationale": (
            "Complementary filter: one multiply-add per axis per cycle—"
            "negligible on any MCU. Stable and tunable via α. "
            "Accuracy sufficient for ±5° balance target."
        ),
        "alternatives": [
            _alt("Kalman EKF",
                 "Lower noise but matrix operations heavy on 8-bit MCU; "
                 "complementary filter meets spec—use Kalman if upgrading to STM32."),
        ],
        "verification_notes": (
            "FACT: 'Kalman Filter for Sensor Fusion' provides the EKF upgrade path. "
            "FACT: 'IMU' confirms gyro drift and need for accel correction."
        ),
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Kalman Filter for Sensor Fusion",
        ],
    },

    {
        "title": "Cascaded PID Rate and Attitude Controller",
        "component_category": "control",
        "design_question": "What control topology achieves attitude hold and disturbance rejection simultaneously?",
        "selected_approach": (
            "Outer attitude loop (50 Hz) generates angular rate setpoints. "
            "Inner rate loop (200–4000 Hz) generates actuator outputs. "
            "Inner must be ≥10× outer bandwidth."
        ),
        "rationale": (
            "Cascaded structure separates tracking (outer) from rejection "
            "(inner). Inner loop acts on rate—faster response than single-loop "
            "PID on angle."
        ),
        "alternatives": [
            _alt("Single-loop PID on angle only",
                 "Cannot achieve >5 Hz bandwidth—oscillation at high gain."),
        ],
        "verification_notes": (
            "FACT: 'PID Controller — Transfer Function' confirms K_d reduces "
            "overshoot; cascaded structure is standard for multi-rotor/balance."
        ),
        "supporting_fact_titles": [
            "PID Controller — Transfer Function",
        ],
    },

    {
        "title": "Mahony IMU Attitude + Heading Filter",
        "component_category": "control",
        "design_question": "How to estimate full 3D attitude (roll/pitch/yaw) for flight control at 4 kHz?",
        "selected_approach": (
            "Mahony complementary filter with two gains (Kp, Ki). "
            "Proven in Betaflight; runs in <5 µs on STM32F4."
        ),
        "rationale": (
            "Simpler to tune than EKF (2 gains vs Q/R matrices). "
            "Proven stability in open-source flight controllers."
        ),
        "alternatives": [
            _alt("Madgwick filter",
                 "Similar performance; single β gain—alternative if Mahony "
                 "proves unstable in specific configuration."),
        ],
        "verification_notes": (
            "FACT: 'Kalman Filter for Sensor Fusion' provides EKF as a more "
            "accurate alternative for GPS-aided mode."
        ),
        "supporting_fact_titles": [
            "Kalman Filter for Sensor Fusion",
            "IMU (Inertial Measurement Unit) for Robot Navigation",
        ],
    },

    {
        "title": "PID Weighted-Average Line-Tracking Controller",
        "component_category": "control",
        "design_question": "How to keep a differential-drive robot on a black line at 0.3 m/s?",
        "selected_approach": (
            "Error = weighted centroid of 8 IR sensors (−35 to +35 mm). "
            "L = base + PID_out; R = base − PID_out. "
            "K_p=0.4, K_i=0, K_d=8."
        ),
        "rationale": (
            "High K_d damps oscillation on straights. Zero K_i prevents "
            "windup during sharp corners. K_i added only for banked surfaces."
        ),
        "alternatives": [
            _alt("P-only control", "Oscillates at high speed; K_d essential."),
        ],
        "verification_notes": (
            "FACT: 'PID Controller — Transfer Function'—K_d reduces overshoot; "
            "consistent with derivative-heavy strategy."
        ),
        "supporting_fact_titles": [
            "PID Controller — Transfer Function",
            "Differential Drive Robot Kinematics",
        ],
    },

    {
        "title": "Analytical 2R Planar Inverse Kinematics Solver",
        "component_category": "software",
        "design_question": "How to convert (x,y) Cartesian targets to joint angles in <1 ms?",
        "selected_approach": (
            "θ₂ = ±acos((x²+y²−l₁²−l₂²)/(2l₁l₂)). "
            "θ₁ = atan2(y,x) − atan2(l₂·sin θ₂, l₁+l₂·cos θ₂). "
            "Elbow-up solution selected by default; joint limit check before command."
        ),
        "rationale": (
            "Analytical IK runs in <1 ms (exact, deterministic) vs iterative "
            "Jacobian (10–100 ms) that may fail near singularities."
        ),
        "alternatives": [
            _alt("Jacobian pseudo-inverse iteration",
                 "Required for non-planar/redundant arms; slower, may not converge—"
                 "analytical is exact for 2R planar."),
        ],
        "verification_notes": (
            "FACT: 'Forward and Inverse Kinematics — Serial Robot Arm' provides "
            "the exact θ₂ = ±acos(…) formula and singularity conditions."
        ),
        "supporting_fact_titles": [
            "Forward and Inverse Kinematics — Serial Robot Arm",
        ],
    },

    {
        "title": "CoreXY Belt-Drive Gantry Architecture",
        "component_category": "mechanical",
        "design_question": "Which 2D motion architecture minimises moving mass for high-acceleration plotting?",
        "selected_approach": (
            "CoreXY: both motors fixed on frame, shared belt drives lightweight "
            "carriage. X = (M₁+M₂)/2; Y = (M₁−M₂)/2. GT2 20T pulley. "
            "Resolution: 0.0125 mm/step at 1/16 step."
        ),
        "rationale": (
            "CoreXY keeps both motors on fixed frame → lower moving mass → "
            "higher acceleration without resonance."
        ),
        "alternatives": [
            _alt("Cartesian H-bot",
                 "One motor on moving Y-axis adds mass; introduces racking at speed."),
            _alt("Polar/SCARA", "Non-uniform resolution; complex G-code conversion; not in Grbl."),
        ],
        "verification_notes": (
            "FACT: 'Stepper Motor Drive' confirms 1/16 step resolution formula. "
            "FACT: 'G-code and CNC Motion Control' confirms Grbl CoreXY support."
        ),
        "supporting_fact_titles": [
            "Stepper Motor Drive — Full Step and Microstepping",
            "G-code and CNC Motion Control",
        ],
    },

    {
        "title": "Grbl G-code CNC Firmware Controller",
        "component_category": "software",
        "design_question": "Which firmware interprets G-code and generates step pulses for a 2-axis plotter?",
        "selected_approach": (
            "Grbl on ATmega328P (or STM32). Accepts G0/G1/G2/G3 over USB-CDC. "
            "30 kHz step rate. Trapezoidal acceleration profiles."
        ),
        "rationale": (
            "Grbl is battle-tested open-source CNC firmware with extensive "
            "community support and built-in CoreXY kinematics."
        ),
        "alternatives": [
            _alt("Marlin", "Aimed at 3D printing—higher flash footprint; overkill for 2D plotter."),
            _alt("Custom step-generator", "Reinvents the wheel; months of development—rejected."),
        ],
        "verification_notes": (
            "FACT: 'G-code and CNC Motion Control' confirms Grbl achieves "
            "30 kHz step rate on ATmega328P and supports CoreXY natively."
        ),
        "supporting_fact_titles": [
            "G-code and CNC Motion Control",
            "Stepper Motor Drive — Full Step and Microstepping",
        ],
    },

    {
        "title": "MicroSD 1 Hz Time-Series Data Logger",
        "component_category": "software",
        "design_question": "How to store 1 year of 1-second data locally without network dependency?",
        "selected_approach": (
            "SPI microSD (32 GB) logs raw CSV at 1 Hz → ≈2 GB/year. "
            "Summary (1-min averages) published to MQTT. NTP timestamps."
        ),
        "rationale": (
            "MicroSD gives local storage independent of network. "
            "1-min MQTT messages ≈52 MB/year—manageable bandwidth."
        ),
        "alternatives": [],
        "verification_notes": (
            "FACT: 'NTP Time Synchronisation' confirms <50 ms accuracy for "
            "energy audit timestamps."
        ),
        "supporting_fact_titles": [
            "NTP Time Synchronisation for Data Logging",
        ],
    },
]


# ======================================================================
# PROJECT DEFINITIONS — reference DESIGN_ELEMENTS by title
# ======================================================================

MECHATRONICS_PROJECTS: list[dict] = [

    {
        "title": "Automated Plant Watering System",
        "description": (
            "Solar-powered IoT device monitoring soil moisture and temperature, "
            "actuating a solenoid valve to irrigate autonomously and reporting "
            "to an MQTT broker."
        ),
        "objective": "Maintain soil VWC 20–60 % without manual intervention; log at 15-min intervals.",
        "constraints": "Budget ≤ £30; IP54+; ≥ 1-week solar autonomy; single PCB ≤ 100×60 mm.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Capacitive Soil Moisture Sensing",
            "N-Channel MOSFET as a Low-Side Power Switch",
            "MQTT Protocol for IoT Sensor Data",
            "Solar Panel Sizing for Remote IoT Stations",
            "Li-Ion Battery Capacity and Energy Calculation",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
        "design_element_titles": [
            "Capacitive Soil Moisture Probe",
            "N-Channel MOSFET Low-Side Load Switch",
            "Solar Panel + LiFePO₄ MPPT Power System",
            "MCU Deep-Sleep Duty Cycle Power Management",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "NTP UTC Timestamped Data Logging",
        ],
        "element_usage_notes": {
            "N-Channel MOSFET Low-Side Load Switch": "Drives 12 V NC solenoid valve; 1N4007 flyback diode fitted.",
            "Solar Panel + LiFePO₄ MPPT Power System": "1 W 60×90 mm panel + 2 Ah LiFePO₄ via CN3791.",
        },
    },

    {
        "title": "Self-Balancing Two-Wheel Robot",
        "description": (
            "Inverted-pendulum robot maintaining balance using IMU-based tilt "
            "measurement and cascaded PID driving differential DC motors."
        ),
        "objective": "Balance autonomously on flat surfaces; BLE app control; ±5° tilt tolerance.",
        "constraints": "Height ≤ 300 mm; ≤ 1.5 kg; battery ≥ 30 min; max speed ≥ 0.5 m/s.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "PID Controller — Transfer Function",
            "H-Bridge Motor Driver Circuit",
            "Differential Drive Robot Kinematics",
        ],
        "design_element_titles": [
            "MPU-6050 IMU Gyro + Accel (I²C)",
            "Complementary Filter IMU Attitude Fusion",
            "Cascaded PID Rate and Attitude Controller",
            "TB6612FNG Dual H-Bridge PWM Motor Drive",
            "Magnetic Quadrature Wheel Encoders",
            "BLE GATT Smartphone App Interface",
        ],
        "element_usage_notes": {
            "Cascaded PID Rate and Attitude Controller": "Inner balance loop at 200 Hz; outer speed loop at 50 Hz.",
            "TB6612FNG Dual H-Bridge PWM Motor Drive": "12 V gearmotors; 20 kHz PWM.",
        },
    },

    {
        "title": "PID Line-Following Robot",
        "description": (
            "Small differential-drive robot following a black line on white surface "
            "using an IR reflectance array and real-time PID heading correction."
        ),
        "objective": "Follow 19 mm line at ≥ 0.3 m/s with ≤ 30 mm cross-track error on 90° corners.",
        "constraints": "Cost ≤ £20; 4× AA NiMH; chassis ≤ 20×15 cm.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "PID Controller — Transfer Function",
            "Differential Drive Robot Kinematics",
            "DC Motor Speed Control via PWM",
        ],
        "design_element_titles": [
            "8-Sensor TCRT5000 IR Reflectance Array",
            "PID Weighted-Average Line-Tracking Controller",
            "TB6612FNG Dual H-Bridge PWM Motor Drive",
            "Magnetic Quadrature Wheel Encoders",
        ],
        "element_usage_notes": {
            "TB6612FNG Dual H-Bridge PWM Motor Drive": "5 V gearmotors; 20 kHz PWM.",
        },
    },

    {
        "title": "3-DOF Desktop Robotic Arm",
        "description": (
            "Three-joint planar arm driven by RC servos, controlled by ESP32 "
            "accepting joint-space commands or IK Cartesian targets over BLE."
        ),
        "objective": "200 mm reach; ±2 mm accuracy; ≥ 100 g payload; ±1 mm repeatability.",
        "constraints": "≤ 500 g; 3D-printed; 5 V USB-C; cost ≤ £25.",
        "domain": "mechanical",
        "status": "completed",
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
            "Forward and Inverse Kinematics — Serial Robot Arm",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
        "design_element_titles": [
            "RC Servo Joint Actuator",
            "Analytical 2R Planar Inverse Kinematics Solver",
            "BLE GATT Smartphone App Interface",
            "ESP32 WiFi + MQTT IoT Telemetry",
        ],
        "element_usage_notes": {
            "RC Servo Joint Actuator": "MG996R shoulder, MG90S elbow, SG90 wrist.",
            "ESP32 WiFi + MQTT IoT Telemetry": "Used primarily for BLE mode; MQTT optional telemetry.",
        },
    },

    {
        "title": "2-Axis CNC Belt-Drive Plotter",
        "description": (
            "CoreXY belt-drive 2D plotter using two NEMA 17 steppers, servo pen "
            "lift, and Grbl firmware accepting G-code over USB-C to draw A4 graphics."
        ),
        "objective": "A4 drawing area; ±0.5 mm accuracy; up to 100 mm/s.",
        "constraints": "2020 aluminium extrusion frame; ≤ £60; 12 V / 3 A supply.",
        "domain": "mechanical",
        "status": "completed",
        "supporting_fact_titles": [
            "Stepper Motor Drive — Full Step and Microstepping",
            "G-code and CNC Motion Control",
            "RC Servo Motor PWM Control",
        ],
        "design_element_titles": [
            "CoreXY Belt-Drive Gantry Architecture",
            "NEMA17 Stepper + DRV8825 Microstepping Drive",
            "Grbl G-code CNC Firmware Controller",
            "RC Servo Joint Actuator",
        ],
        "element_usage_notes": {
            "RC Servo Joint Actuator": "SG90 micro-servo for 5 mm pen lift; 0°=down, 45°=up.",
        },
    },

    {
        "title": "250 mm Quadcopter Drone Flight Controller",
        "description": (
            "250 mm wheelbase quad with custom STM32F4 flight controller, "
            "ICM-42688-P IMU, cascaded PID attitude control at 4 kHz inner loop, "
            "and 4× BLHeli-32 ESCs."
        ),
        "objective": "Hover ±5 cm altitude; attitude hold ±2°; response bandwidth >20 Hz.",
        "constraints": "AUW ≤ 500 g with 4S 1500 mAh LiPo; ≥ 5 min flight.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Kalman Filter for Sensor Fusion",
            "PID Controller — Transfer Function",
            "Brushless DC (BLDC) Motor for Suction Fan",
        ],
        "design_element_titles": [
            "ICM-42688-P High-Rate IMU via SPI",
            "Mahony IMU Attitude + Heading Filter",
            "Cascaded PID Rate and Attitude Controller",
            "BLDC 2306 Motor + BLHeli-32 ESC Drive",
            "4S LiPo Flight Power Budget",
        ],
        "element_usage_notes": {
            "Cascaded PID Rate and Attitude Controller": "Outer attitude 50 Hz; inner rate 4 kHz. Betaflight RPM filter.",
        },
    },

    {
        "title": "RFID Smart Door Access Controller",
        "description": (
            "Wall-mounted access control using RFID reader, ESP32, electric door "
            "strike, OLED display, and MQTT event logging. OTA updates via WiFi."
        ),
        "objective": "Grant/deny access within 500 ms; log all events with UTC timestamp; ≥100 enrolled UIDs.",
        "constraints": "12 V / 1 A supply; IP54 flush-mount; GDPR-compliant (no biometrics).",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "RFID/NFC Reader — ISO 14443 / 15693 Interface",
            "N-Channel MOSFET as a Low-Side Power Switch",
            "MQTT Protocol for IoT Sensor Data",
            "OTA Firmware Update for Embedded Devices",
        ],
        "design_element_titles": [
            "MFRC522 RFID Card Reader (NTAG216)",
            "N-Channel MOSFET Low-Side Load Switch",
            "Electric NC Door Strike Solenoid",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "OTA HTTPS Dual-Bank Firmware Update",
            "NTP UTC Timestamped Data Logging",
            "MQTT QoS-1 Secure Event Logger",
        ],
        "element_usage_notes": {
            "N-Channel MOSFET Low-Side Load Switch": "Drives 12 V NC door strike; 300 ms energise pulse.",
        },
    },

    {
        "title": "Portable Indoor Air Quality Monitor",
        "description": (
            "Handheld IoT device measuring CO₂, PM2.5, temperature, and RH. "
            "OLED display, MQTT logging, BLE smartphone display, USB-C charged."
        ),
        "objective": "CO₂ 400–5000 ppm (±50 ppm); PM2.5 ±10 %; RH ±2 %; T ±0.3 °C; ≥ 8 h battery.",
        "constraints": "120×60×25 mm; < £50; USB-C; no user calibration required.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "NDIR CO₂ Sensor — Non-Dispersive Infrared",
            "PM2.5 Optical Particle Counter",
            "Capacitive Relative Humidity Sensing",
        ],
        "design_element_titles": [
            "SCD41 NDIR CO₂ Sensing Module",
            "SPS30 PM2.5 Optical Particle Sensor",
            "SHT41 Digital Temperature and RH Sensing",
            "Li-Po 3.7 V USB-C Rechargeable Battery Pack",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "BLE GATT Smartphone App Interface",
            "NTP UTC Timestamped Data Logging",
        ],
        "element_usage_notes": {},
    },

    {
        "title": "Automated Greenhouse Climate Controller",
        "description": (
            "Multi-zone controller managing temperature, RH, CO₂, soil moisture, "
            "and lighting for a 6×3 m hobby greenhouse. Grafana dashboard over WiFi."
        ),
        "objective": "T 18–26 °C (±1 °C); RH 60–80 %; CO₂ 800–1200 ppm; soil VWC 30–60 %.",
        "constraints": "Mains 230 V; safety interlock on heating; ≤ 4 sensor zones; 30-day local retention.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Capacitive Soil Moisture Sensing",
            "Capacitive Relative Humidity Sensing",
            "NDIR CO₂ Sensor — Non-Dispersive Infrared",
        ],
        "design_element_titles": [
            "Capacitive Soil Moisture Probe",
            "SHT41 Digital Temperature and RH Sensing",
            "SCD41 NDIR CO₂ Sensing Module",
            "I²C TCA9548A Multi-Device Sensor Bus",
            "N-Channel MOSFET Low-Side Load Switch",
            "Solid-State Relay Mains Actuator Switching",
            "ESP32 WiFi + MQTT IoT Telemetry",
        ],
        "element_usage_notes": {
            "N-Channel MOSFET Low-Side Load Switch": "Controls 12 V irrigation solenoids (4 zones).",
            "Solid-State Relay Mains Actuator Switching": "Switches 230 V fan, heater, and LED driver.",
        },
    },

    {
        "title": "Non-Invasive Smart Energy Meter",
        "description": (
            "Clamp-on energy monitor measuring real power, apparent power, power "
            "factor, and cumulative kWh. MQTT publishing and microSD logging."
        ),
        "objective": "Real power ±2 % accuracy; energy error <1 %/24 h; 1 s update; 1-year data history.",
        "constraints": "No direct mains connection; 5 V USB-C; ≤ 120×80×35 mm; ≤ £35.",
        "domain": "electrical",
        "status": "completed",
        "supporting_fact_titles": [
            "CT Clamp Current Sensing and RMS Calculation",
            "Ohm's Law",
            "Kirchhoff's Voltage Law (KVL)",
        ],
        "design_element_titles": [
            "SCT-013 Split-Core CT Clamp Current Sensing",
            "9 V Transformer Mains Voltage Reference",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "NTP UTC Timestamped Data Logging",
            "MicroSD 1 Hz Time-Series Data Logger",
        ],
        "element_usage_notes": {
            "SCT-013 Split-Core CT Clamp Current Sensing": "4800 Hz sampling; 80 samples/60 Hz cycle for true RMS.",
        },
    },
]
