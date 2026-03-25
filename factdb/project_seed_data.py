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

    # ------------------------------------------------------------------
    # CONTROL — Arduino MCU Platforms
    # ------------------------------------------------------------------

    {
        "title": "Arduino Uno/Nano MCU Platform",
        "component_category": "control",
        "design_question": "Which low-cost 8-bit MCU board suits simple sensor/actuator projects?",
        "selected_approach": (
            "ATmega328P-based Arduino Uno (5 V, 16 MHz, 14 digital I/O, 6 ADC) "
            "or Arduino Nano (same chip, smaller footprint). "
            "Programmed via Arduino IDE with C++ Arduino framework over USB."
        ),
        "rationale": (
            "Arduino Uno/Nano provides ample I/O for projects with < 10 actuators "
            "and < 8 sensors. The 5 V operating voltage is directly compatible "
            "with common modules (HC-05, L298N, servos). Wide community support."
        ),
        "alternatives": [
            _alt("Raspberry Pi", "Overkill for simple actuator projects; higher cost and Linux boot time."),
            _alt("STM32 Blue Pill", "More performant but harder to program for beginners."),
        ],
        "verification_notes": (
            "FACT: 'DC Motor Speed Control via PWM' confirms Arduino hardware "
            "PWM at 490/980 Hz on pins 3/5/6/9/10/11."
        ),
        "supporting_fact_titles": [
            "DC Motor Speed Control via PWM",
            "RC Servo Motor PWM Control",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "Arduino Mega 2560 MCU Platform",
        "component_category": "control",
        "design_question": "Which MCU handles projects with many I/O pins and multiple serial buses?",
        "selected_approach": (
            "ATmega2560-based Arduino Mega 2560 (5 V, 16 MHz, 54 digital I/O, "
            "16 ADC channels, 4 hardware UARTs, 20 PWM pins). "
            "Programmed via Arduino IDE; shields stack directly."
        ),
        "rationale": (
            "54 I/O pins support large servo arrays, multiple sensors, and "
            "4 independent serial devices (RF, GPS, Bluetooth, LCD) without "
            "software serial emulation overhead. Cost ~£10—acceptable for lab projects."
        ),
        "alternatives": [
            _alt("Arduino Uno", "Only 14 digital pins and 1 hardware UART—insufficient for complex projects."),
            _alt("ESP32", "WiFi/BLE onboard but 3.3 V I/O requires level-shifting for 5 V modules."),
        ],
        "verification_notes": (
            "FACT: 'Forward and Inverse Kinematics — Serial Robot Arm' confirms "
            "servo array requirements for 5+ DOF arms."
        ),
        "supporting_fact_titles": [
            "Forward and Inverse Kinematics — Serial Robot Arm",
            "RC Servo Motor PWM Control",
            "Stepper Motor Drive — Full Step and Microstepping",
        ],
    },

    # ------------------------------------------------------------------
    # COMMUNICATION — RF and Bluetooth
    # ------------------------------------------------------------------

    {
        "title": "HC-05 Bluetooth Serial Bridge",
        "component_category": "communication",
        "design_question": "How to enable Android smartphone control of an Arduino project?",
        "selected_approach": (
            "HC-05 Bluetooth 2.0 SPP module wired to Arduino UART TX/RX. "
            "Android app (e.g. Bluetooth RC Controller or custom MIT App Inventor "
            "app) sends single-byte ASCII commands at 9600 baud."
        ),
        "rationale": (
            "HC-05 pairs as a virtual serial port on Android with no custom "
            "BLE GATT profile required. AT commands reconfigure baud rate and "
            "name. Total cost < £3. Round-trip latency < 50 ms typical."
        ),
        "alternatives": [
            _alt("BLE HM-10 module", "Preferred for iOS; slightly higher latency; lower power."),
            _alt("WiFi ESP8266", "Requires TCP/IP stack; higher latency and complexity for joystick commands."),
        ],
        "verification_notes": (
            "FACT: 'Bluetooth Classic SPP — HC-05 Serial Bridge Module' confirms "
            "9600–115200 baud UART bridge and 10 m class-2 range."
        ),
        "supporting_fact_titles": [
            "Bluetooth Classic SPP — HC-05 Serial Bridge Module",
            "Bluetooth Low Energy (BLE) for App Control",
        ],
    },

    {
        "title": "nRF24L01 2.4 GHz RF Transceiver Link",
        "component_category": "communication",
        "design_question": "How to achieve real-time bidirectional wireless control up to 100 m without infrastructure?",
        "selected_approach": (
            "Pair of nRF24L01+ modules (one on transmitter joystick controller, "
            "one on robot/vehicle). SPI on both MCUs; 250 kbps, 6-byte address, "
            "auto-ACK. Transmitter sends 8–32 byte command frame at 20–50 Hz."
        ),
        "rationale": (
            "nRF24L01 operates without WiFi/BT infrastructure, has 100 m open-air "
            "range, and auto-ACK ensures delivery. At £1 per module it is the "
            "lowest-cost bidirectional wireless option. Suitable for RC robots."
        ),
        "alternatives": [
            _alt("HC-12 433 MHz", "1 km range but half-duplex UART only; 100 ms latency—too slow for RC."),
            _alt("ESP-NOW (ESP32)", "No extra module needed but requires ESP32 on both sides."),
        ],
        "verification_notes": (
            "FACT: '2.4 GHz RF Transceiver — nRF24L01 SPI Interface' confirms "
            "250 kbps rate, 100 m open air range, and auto-retransmit."
        ),
        "supporting_fact_titles": [
            "2.4 GHz RF Transceiver — nRF24L01 SPI Interface",
        ],
    },

    # ------------------------------------------------------------------
    # SENSING — Distance, Gas, Thermal, Camera, Position
    # ------------------------------------------------------------------

    {
        "title": "HC-SR04 Ultrasonic Obstacle-Distance Sensor",
        "component_category": "sensing",
        "design_question": "How to detect obstacles at 2 cm–4 m range with a low-cost sensor?",
        "selected_approach": (
            "HC-SR04 module (40 kHz burst, ToF measurement). MCU triggers "
            "a 10 µs pulse on TRIG; measures echo pulse width on ECHO pin. "
            "Distance = (pulse_µs × 0.0343) / 2 cm."
        ),
        "rationale": (
            "HC-SR04 provides ≤ 3 mm resolution, ±3 mm accuracy over 20–200 cm, "
            "at < £1. Standard Arduino NewPing library simplifies usage. "
            "Adequate for obstacle avoidance at robot walking speeds ≤ 0.5 m/s."
        ),
        "alternatives": [
            _alt("TFMini-S LiDAR", "Better for 0.1 m–12 m at higher accuracy but costs 20× more."),
            _alt("Sharp IR distance", "Faster (38 ms) but nonlinear analog output; narrower range."),
        ],
        "verification_notes": (
            "FACT: 'Ultrasonic Proximity Sensor — ToF Distance Measurement' "
            "confirms 40 kHz frequency and ±3 mm accuracy."
        ),
        "supporting_fact_titles": [
            "Ultrasonic Proximity Sensor — ToF Distance Measurement",
            "Differential Drive Robot Kinematics",
        ],
    },

    {
        "title": "L298N Dual H-Bridge Motor Driver Module",
        "component_category": "actuation",
        "design_question": "How to drive two DC motors bidirectionally from a 5 V MCU at up to 2 A each?",
        "selected_approach": (
            "L298N-based dual full H-bridge module (5–35 V motor supply, 2 A "
            "continuous per channel, logic 5 V). "
            "IN1/IN2/ENA for motor A; IN3/IN4/ENB for motor B. "
            "ENx tied HIGH for full speed or driven by PWM for speed control."
        ),
        "rationale": (
            "L298N module is universally available at < £2, accepts 5 V Arduino "
            "logic directly, and drives 12 V DC gear motors up to 2 A each. "
            "Built-in flyback diodes protect against inductive kickback."
        ),
        "alternatives": [
            _alt("TB6612FNG", "Lower voltage drop (0.5 V vs 3 V), more efficient—preferred for battery projects."),
            _alt("BTS7960 43A driver", "Required for high-current motors (> 5 A); more expensive."),
        ],
        "verification_notes": (
            "FACT: 'H-Bridge Motor Driver Circuit' confirms full H-bridge "
            "topology and PWM speed control principle."
        ),
        "supporting_fact_titles": [
            "H-Bridge Motor Driver Circuit",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "DC Gear Motor with PWM Speed Control",
        "component_category": "actuation",
        "design_question": "Which motor provides sufficient torque for wheeled robot locomotion?",
        "selected_approach": (
            "Standard DC gear motor (12 V, 100–300 RPM, gear ratio 1:30–1:100). "
            "Speed controlled via L298N or TB6612FNG PWM. "
            "Gear reduction provides high torque at low speed for reliable traction."
        ),
        "rationale": (
            "Gear motors rated 0.5–2 kg·cm provide adequate drive for robots "
            "up to 2 kg. 12 V operation compatible with common Li-Ion packs. "
            "Encoder-equipped variants enable closed-loop speed control."
        ),
        "alternatives": [
            _alt("BLDC + ESC", "Higher speed/efficiency but needs ESC; overkill for slow indoor robots."),
            _alt("Servo motor (continuous)", "Limited to 360° rotation hack; lower torque than gearbox."),
        ],
        "verification_notes": (
            "FACT: 'DC Motor Speed Control via PWM' confirms H-bridge PWM "
            "direction and speed control."
        ),
        "supporting_fact_titles": [
            "DC Motor Speed Control via PWM",
            "H-Bridge Motor Driver Circuit",
            "Differential Drive Robot Kinematics",
        ],
    },

    {
        "title": "12 V Peristaltic Pump Liquid Dispenser",
        "component_category": "actuation",
        "design_question": "How to dispense or transfer precise volumes of liquid without contaminating the pump interior?",
        "selected_approach": (
            "12 V DC peristaltic pump (0–100 mL/min, food-grade silicone tube). "
            "N-channel MOSFET low-side switched by MCU PWM or on/off. "
            "Flow rate calibrated by timing the pump to dispense a known volume."
        ),
        "rationale": (
            "Peristaltic pumps keep fluid inside the tube—no contamination of "
            "the pump body. Suitable for water, fertiliser, and sanitiser dispensing. "
            "Self-priming and can run dry briefly."
        ),
        "alternatives": [
            _alt("Centrifugal pump", "Higher flow rate but not self-priming; requires submergence."),
            _alt("Syringe pump (stepper-driven)", "Highest accuracy (µL) but slow; preferred for medical infusion."),
        ],
        "verification_notes": (
            "FACT: 'Solenoid Valve for Pneumatic and Fluid Control' confirms "
            "flow actuation requirements."
        ),
        "supporting_fact_titles": [
            "Solenoid Valve for Pneumatic and Fluid Control",
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    {
        "title": "MQ-3 Alcohol and Combustible Gas Sensor",
        "component_category": "sensing",
        "design_question": "How to detect alcohol vapour concentration for ignition interlock applications?",
        "selected_approach": (
            "MQ-3 SnO₂ metal-oxide sensor (5 V heater, analog A0 out). "
            "Voltage divider with 200 kΩ load resistor. "
            "ADC reading compared to threshold calibrated to 0.05 mg/L "
            "(legal BAC limit) during sensor warm-up ≥ 30 s."
        ),
        "rationale": (
            "MQ-3 is selective to ethanol at low concentrations and costs < £2. "
            "Relay output interrupts ignition circuit when threshold exceeded. "
            "Preheat managed by microcontroller power-on sequence."
        ),
        "alternatives": [
            _alt("Electrochemical BAC sensor", "±0.005 % BAC precision but costs 10× and requires periodic electrolyte replacement."),
            _alt("MQ-135", "Broad air quality sensor; lower ethanol selectivity."),
        ],
        "verification_notes": (
            "FACT: 'MQ-Series Metal-Oxide Gas Sensor — Alcohol, CO, LPG' "
            "confirms 30 s preheat and R0 calibration procedure."
        ),
        "supporting_fact_titles": [
            "MQ-Series Metal-Oxide Gas Sensor — Alcohol, CO, LPG",
            "ADC Resolution and Measurement Precision",
        ],
    },

    {
        "title": "Voice Recognition UART Speech Module",
        "component_category": "sensing",
        "design_question": "How to add offline voice command control to an embedded system?",
        "selected_approach": (
            "LD3320-based module (DFRobot SEN0089 or compatible). "
            "Up to 50 keywords stored and recognised offline. "
            "UART at 9600 baud returns command ID on recognition. "
            "Onboard microphone; 1–3 m recognition range in quiet environment."
        ),
        "rationale": (
            "Offline recognition eliminates network dependency. Command ID "
            "mapped in firmware to actuator action. < £8 module cost. "
            "Satisfactory accuracy for 10–20 distinct command vocabulary."
        ),
        "alternatives": [
            _alt("Android STT (Google ASR)", "Unlimited vocabulary but requires smartphone and internet—rejected for standalone."),
            _alt("Raspberry Pi + PocketSphinx", "Unlimited offline vocab but adds £35 cost and Linux complexity."),
        ],
        "verification_notes": (
            "FACT: 'Voice Recognition — Keyword Spotting UART Module (LD3320)' "
            "confirms 50-command limit and 1–3 m range."
        ),
        "supporting_fact_titles": [
            "Voice Recognition — Keyword Spotting UART Module (LD3320)",
        ],
    },

    {
        "title": "Flex Sensor Hand-Gesture Glove Interface",
        "component_category": "sensing",
        "design_question": "How to translate finger bend angles into servo commands for a robotic arm?",
        "selected_approach": (
            "5× Spectra Symbol 2.2″ flex sensors sewn onto glove fingers. "
            "Each sensor in voltage-divider (47 kΩ load); ADC reads 0–1023. "
            "Linear mapping: 0° (flat) → min PWM; 90° (bent) → max servo PWM. "
            "MPU-6050 on wrist adds 3-axis orientation for wrist joint."
        ),
        "rationale": (
            "Direct analogue mapping gives intuitive zero-latency control. "
            "nRF24L01 on glove transmits 5 servo values + IMU data at 20 Hz. "
            "Total glove cost < £15."
        ),
        "alternatives": [
            _alt("Data glove with Hall sensors", "Lower hysteresis but requires permanent magnets on each finger segment."),
            _alt("Computer vision hand tracking (MediaPipe)", "Camera-based; affected by occlusion—rejected for wearable."),
        ],
        "verification_notes": (
            "FACT: 'Capacitive Flex Sensor — Finger Bend Angle Measurement' "
            "confirms voltage divider circuit and mapping procedure."
        ),
        "supporting_fact_titles": [
            "Capacitive Flex Sensor — Finger Bend Angle Measurement",
            "RC Servo Motor PWM Control",
            "IMU (Inertial Measurement Unit) for Robot Navigation",
        ],
    },

    {
        "title": "IR Night-Vision Camera Module",
        "component_category": "sensing",
        "design_question": "How to enable video surveillance in zero-light environments?",
        "selected_approach": (
            "Board camera with 1/3\" CMOS sensor and onboard 850 nm IR LED array "
            "(6–12 LEDs, 5–10 m night range). "
            "Composite or USB-UVC output; pairs with an FPV transmitter or "
            "USB capture card on the control station."
        ),
        "rationale": (
            "850 nm IR is invisible to human eye yet clearly detected by the "
            "sensor. All-in-one camera+LED board costs < £10. "
            "Suitable for spy/patrol robots and night patrol drones."
        ),
        "alternatives": [
            _alt("Thermal MLX90640", "Detects heat through darkness—no IR illumination needed but lower resolution."),
            _alt("Starlight Sony sensor", "Usable at 0.001 lux without IR illumination but 5× cost."),
        ],
        "verification_notes": (
            "FACT: 'Infrared Cliff Detection for Robot Vacuums' confirms 850 nm "
            "IR reflectance detection principle."
        ),
        "supporting_fact_titles": [
            "Infrared Cliff Detection for Robot Vacuums",
        ],
    },

    {
        "title": "MLX90640 Thermal Infrared Imaging Array",
        "component_category": "sensing",
        "design_question": "How to detect hot bodies, fever, or fire without visible light?",
        "selected_approach": (
            "MLX90640 32×24 FIR array (I²C, 3.3 V). "
            "ESP32 reads 64 Hz frames via Melexis API, applies calibration, "
            "publishes hotspot temperature and grid to MQTT. "
            "Displayed as colour-mapped heatmap on OLED or remote dashboard."
        ),
        "rationale": (
            "Detects body heat at 5 m distance with ±1 °C accuracy. "
            "I²C interface is simple to integrate. At £20 it is the most "
            "cost-effective FIR array for fever screening and fire detection."
        ),
        "alternatives": [
            _alt("FLIR Lepton 3.5 (160×120)", "4× resolution but £150 and requires SPI + specialised breakout."),
            _alt("AMG8833 (8×8)", "Cheaper (£15) but 8×8 resolution too coarse for reliable screening."),
        ],
        "verification_notes": (
            "FACT: 'MLX90640 Far-Infrared Thermal Camera Array' confirms "
            "32×24 pixels, ±1 °C, 64 Hz, I²C 0x33."
        ),
        "supporting_fact_titles": [
            "MLX90640 Far-Infrared Thermal Camera Array",
            "I²C Serial Communication Protocol",
        ],
    },

    {
        "title": "TFMini-S Single-Point LiDAR Distance Sensor",
        "component_category": "sensing",
        "design_question": "How to measure altitude or obstacle distance on a drone with < 5 g sensor?",
        "selected_approach": (
            "Benewake TFMini-S (5 V, UART 115 200 baud, 0.1–12 m, 100 Hz). "
            "Downward-facing for altitude hold < 10 m; "
            "forward-facing for close-range obstacle avoidance."
        ),
        "rationale": (
            "5 g mass, ±6 mm accuracy, 2.3° FOV makes TFMini-S ideal for drones. "
            "UART output parsed in flight controller interrupt service routine. "
            "12 m range covers indoor-to-outdoor low-altitude flight scenarios."
        ),
        "alternatives": [
            _alt("HC-SR04 ultrasonic", "Cheaper but 40 ms sample rate and affected by airframe vibration."),
            _alt("VL53L1X (4 m)", "Compact but insufficient range for outdoor altitude hold."),
        ],
        "verification_notes": (
            "FACT: 'TFMini-S Micro LiDAR — 0.1–12 m Time-of-Flight' confirms "
            "5 g mass, 115 200 baud UART, and 100 Hz rate."
        ),
        "supporting_fact_titles": [
            "TFMini-S Micro LiDAR — 0.1–12 m Time-of-Flight",
            "2D LiDAR Distance Measurement Principle",
        ],
    },

    {
        "title": "TCS3200 Color Sensor for Product Sorting",
        "component_category": "sensing",
        "design_question": "How to classify product colour for automated sorting?",
        "selected_approach": (
            "TCS3200 RGB photodiode array (8×8 filtered array + frequency converter). "
            "MCU reads R, G, B pulse frequencies; converts to RGB 0–255 scale "
            "after white-balance calibration on each product run."
        ),
        "rationale": (
            "TCS3200 gives repeatable colour classification under controlled "
            "illumination. < £2 cost. Simple digital frequency output eliminates "
            "need for ADC. Classification accuracy > 95 % for distinct colours "
            "at 2–5 cm sensing distance."
        ),
        "alternatives": [
            _alt("Camera + OpenCV colour detection", "Higher accuracy and shape recognition but requires Raspberry Pi and 10× cost."),
            _alt("Proximity colour TCS34725 (I²C)", "Better ambient-light rejection but smaller die—similar cost."),
        ],
        "verification_notes": (
            "FACT: 'ADC Resolution and Measurement Precision' confirms frequency-"
            "to-colour mapping accuracy constraints."
        ),
        "supporting_fact_titles": [
            "ADC Resolution and Measurement Precision",
        ],
    },

    {
        "title": "NEO-6M GPS Module for Navigation",
        "component_category": "sensing",
        "design_question": "How to add outdoor position tracking to a drone or robot?",
        "selected_approach": (
            "u-blox NEO-6M GPS module (UART 9600 baud, NMEA 0183, 5 Hz update, "
            "2.5 m CEP). Parses $GPRMC and $GPGGA sentences for lat/lon/altitude. "
            "External active patch antenna for vehicle and indoor use."
        ),
        "rationale": (
            "NEO-6M has < 2 s hot-start TTFF, 2.5 m CEP, and is available on "
            "breakout boards for < £5. NMEA UART output is directly readable "
            "by Arduino/ESP32 hardware UART."
        ),
        "alternatives": [
            _alt("NEO-M8N (concurrent GNSS)", "< 2 m accuracy and GPS+GLONASS+Galileo—preferred for critical applications."),
            _alt("LoRa APRS position beacon", "No GPS on-device; relies on ground network—unsuitable for mobile robots."),
        ],
        "verification_notes": (
            "FACT: 'GPS Module — NMEA Sentence Parsing and Fix Accuracy' confirms "
            "NMEA sentences and 2.5–5 m CEP accuracy."
        ),
        "supporting_fact_titles": [
            "GPS Module — NMEA Sentence Parsing and Fix Accuracy",
            "A* Pathfinding Algorithm",
        ],
    },

    {
        "title": "PIR HC-SR501 Motion Detection Module",
        "component_category": "sensing",
        "design_question": "How to trigger an action only when a person is present, saving power?",
        "selected_approach": (
            "HC-SR501 PIR module wired to MCU digital interrupt pin. "
            "On HIGH output (person detected) MCU activates dispenser, pump, "
            "or alarm; auto-resets after configurable hold time (0.5–200 s)."
        ),
        "rationale": (
            "HC-SR501 requires no MCU processing—purely digital interrupt. "
            "Quiescent < 50 µA enables battery-powered installations. "
            "Simple and reliable for hands-free/touchless triggering."
        ),
        "alternatives": [
            _alt("Ultrasonic distance sensor", "Requires active MCU polling; detects objects, not specifically warm bodies."),
            _alt("Microwave radar RCWL-0516", "Detects through walls but high false-positive rate in cluttered environments."),
        ],
        "verification_notes": (
            "FACT: 'PIR Passive Infrared Motion Sensor — HC-SR501' confirms "
            "50 µA quiescent and 0.5–200 s hold time."
        ),
        "supporting_fact_titles": [
            "PIR Passive Infrared Motion Sensor — HC-SR501",
        ],
    },

    {
        "title": "Load Cell IV-Bag / Fluid Weight Monitor",
        "component_category": "sensing",
        "design_question": "How to monitor drip-bag remaining volume and trigger a low-volume alert?",
        "selected_approach": (
            "50–100 g single-point load cell + HX711 24-bit ADC bridge amplifier. "
            "MCU reads weight at 10 Hz; triggers audible/WiFi alert at "
            "programmed threshold (e.g. 50 g remaining in IV bag)."
        ),
        "rationale": (
            "Load cell gives direct mass measurement (±0.1 g accuracy with HX711). "
            "IV bag density ≈ 1 g/mL so mass = volume directly. "
            "Completely non-invasive—no contact with fluid."
        ),
        "alternatives": [
            _alt("Optical drip counter", "Counts drops but errors accumulate; affected by bubbles."),
            _alt("Ultrasonic level sensor", "Requires reflective surface; impractical for flexible IV bags."),
        ],
        "verification_notes": (
            "FACT: 'Load Cell and Wheatstone Bridge' confirms Wheatstone bridge "
            "and HX711 24-bit ADC instrumentation amplifier."
        ),
        "supporting_fact_titles": [
            "Load Cell and Wheatstone Bridge",
        ],
    },

    # ------------------------------------------------------------------
    # ACTUATION — Drivers, Pumps, Brakes
    # ------------------------------------------------------------------

    {
        "title": "Pneumatic Cylinder + 5/2 Solenoid Valve Actuator",
        "component_category": "actuation",
        "design_question": "How to produce fast, high-force linear strokes in a reciprocating cutting or forming mechanism?",
        "selected_approach": (
            "Double-acting pneumatic cylinder (bore 32–63 mm, stroke 50–200 mm) "
            "controlled by a 12 V 5/2-way solenoid valve. "
            "Compressed air supply at 4–7 bar. "
            "MCU drives solenoid via MOSFET; cylinder extends/retracts in < 100 ms."
        ),
        "rationale": (
            "Pneumatic cylinders provide 500–3000 N force at 6 bar with "
            "< 50 ms stroke time—exceeding what a DC motor can achieve at "
            "comparable cost. Ideal for punching, paper cup forming, and hacksaw reciprocation."
        ),
        "alternatives": [
            _alt("Linear servo or stepper-driven leadscrew", "Precise position but < 200 N force and 10× slower stroke."),
            _alt("Hydraulic cylinder", "Higher force but requires hydraulic pump and oil—impractical for lab scale."),
        ],
        "verification_notes": (
            "FACT: 'Pneumatic Cylinder Force and Stroke' confirms F = P × A formula. "
            "FACT: 'Solenoid Valve for Pneumatic and Fluid Control' confirms 5/2 valve logic."
        ),
        "supporting_fact_titles": [
            "Pneumatic Cylinder Force and Stroke",
            "Solenoid Valve for Pneumatic and Fluid Control",
        ],
    },

    {
        "title": "Eddy-Current Electromagnetic Brake",
        "component_category": "actuation",
        "design_question": "How to provide contactless, wear-free braking using electromagnetic induction?",
        "selected_approach": (
            "Electromagnet coil positioned adjacent to a rotating aluminium or "
            "copper disc on the wheel/axle. "
            "MCU-controlled MOSFET ramps coil current 0–12 V for variable braking torque. "
            "Braking force scales with disc speed and coil current squared."
        ),
        "rationale": (
            "No friction pads—zero wear and instant response. "
            "Braking torque is proportional to current and speed, enabling "
            "precise modulated braking for emergency stop systems. "
            "Effective at vehicle speeds > 5 km/h."
        ),
        "alternatives": [
            _alt("Hydraulic disc brake", "Higher braking force at zero speed but requires fluid system."),
            _alt("Regenerative BLDC braking", "Recovers energy but requires BLDC traction motor."),
        ],
        "verification_notes": (
            "FACT: 'Eddy Current Braking Principle' confirms torque ∝ I² × ω relationship."
        ),
        "supporting_fact_titles": [
            "Eddy Current Braking Principle",
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    {
        "title": "UV-C LED Germicidal + Ozone Sterilisation Module",
        "component_category": "actuation",
        "design_question": "How to achieve chemical-free sterilisation of surfaces and equipment?",
        "selected_approach": (
            "UV-C LED array (265–280 nm, 100–500 mW/cm²) combined with "
            "optional ozone generator (3–5 mg/h) in a sealed or vented chamber. "
            "Timer-controlled MCU (5–30 min cycle); safety interlock (PIR) "
            "disables UV if presence detected."
        ),
        "rationale": (
            "UV-C at 265 nm achieves 4-log (99.99 %) microbial reduction in "
            "60 s at 30 mJ/cm² dose. No chemicals required. "
            "Ozone oxidises residual pathogens in shadowed areas. "
            "Mandatory safety interlock prevents human exposure."
        ),
        "alternatives": [
            _alt("Chemical disinfectant spray", "Requires manual application; chemical residue; slower contact time."),
            _alt("Autoclave steam sterilisation", "Complete sterility but 134 °C—incompatible with electronics."),
        ],
        "verification_notes": (
            "FACT: 'UV-C LED Germicidal Irradiation' confirms 265 nm peak and "
            "30 mJ/cm² dose for 4-log reduction."
        ),
        "supporting_fact_titles": [
            "UV-C LED Germicidal Irradiation",
            "PIR Passive Infrared Motion Sensor — HC-SR501",
        ],
    },

    {
        "title": "IGBT Resonant Induction Heating Circuit",
        "component_category": "actuation",
        "design_question": "How to heat a ferromagnetic cooking vessel rapidly without an open flame or contact element?",
        "selected_approach": (
            "ZVS half-bridge IGBT driver (IRFP260N or STGW30NC60W pair) "
            "driving a 10–30 µH copper work coil at 25–50 kHz resonance. "
            "Series resonant capacitor bank; output 1–2 kW. "
            "NTC thermistor feedback into PID loop adjusts switching frequency."
        ),
        "rationale": (
            "Induction cooktop reaches operating temperature in < 30 s. "
            "90 % efficiency vs 74 % for resistive element. "
            "Precise temperature control via PID loop. "
            "ZVS topology minimises IGBT switching losses."
        ),
        "alternatives": [
            _alt("Resistive coil heating", "Simpler but slower heat-up and 74 % efficiency."),
            _alt("Propane burner", "Uncontrolled temperature; open flame hazard—unsuitable for lab or indoor use."),
        ],
        "verification_notes": (
            "FACT: 'Induction Heating — IGBT Resonant Series Circuit' confirms "
            "ZVS topology and f₀ = 1/(2π√(LC)) design equation."
        ),
        "supporting_fact_titles": [
            "Induction Heating — IGBT Resonant Series Circuit",
            "PID Controller — Transfer Function",
        ],
    },

    # ------------------------------------------------------------------
    # MECHANICAL — Linkages, Locomotion, Specialised Mechanisms
    # ------------------------------------------------------------------

    {
        "title": "Klann / Theo-Jansen Leg Linkage Mechanism",
        "component_category": "mechanical",
        "design_question": "How to produce smooth bipedal or multi-legged walking motion from a single rotating crank?",
        "selected_approach": (
            "Theo Jansen or Klann 6-bar linkage: one DC motor crank drives "
            "4- or 8-leg set via coupler links producing a near-sinusoidal "
            "foot trajectory. All legs share a common drive shaft with "
            "phase offsets (45° or 90°) for smooth gait."
        ),
        "rationale": (
            "Single-motor drive simplifies electronics: one L298N channel "
            "drives all legs simultaneously. Jansen linkage creates a natural "
            "walking gait with ground clearance. Fabricated from 3 mm acrylic or "
            "laser-cut plywood at < £10 materials."
        ),
        "alternatives": [
            _alt("Servo-per-leg hexapod", "Independent control of each joint—more versatile but 12+ servos required."),
            _alt("Wheeled locomotion", "Simpler but cannot handle uneven terrain obstacles the leg linkage traverses."),
        ],
        "verification_notes": (
            "FACT: 'Slider-Crank Mechanism — Rotary to Linear Conversion' provides "
            "the base theory for crank-coupler kinematic analysis."
        ),
        "supporting_fact_titles": [
            "Slider-Crank Mechanism — Rotary to Linear Conversion",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "Rocker-Bogie Rough-Terrain Drive System",
        "component_category": "mechanical",
        "design_question": "How to traverse obstacles up to 2× wheel diameter without active suspension?",
        "selected_approach": (
            "Rocker-bogie 6-wheel passive suspension (3 wheels per side, "
            "differential bar links). Each wheel independently DC-gear-motor-driven. "
            "Passive geometry distributes load across all 6 wheels over rocks/steps."
        ),
        "rationale": (
            "Passive rocker-bogie requires no actuated suspension—only 6 motor "
            "controllers. Proven on Mars rovers to traverse 25 cm obstacles with "
            "25 cm diameter wheels. No electronics in the pivot joints."
        ),
        "alternatives": [
            _alt("4-wheel independent suspension", "Simpler but handles obstacles only up to 1× wheel diameter."),
            _alt("Track drive", "Better obstacle climbing but lower efficiency on flat surfaces."),
        ],
        "verification_notes": (
            "FACT: 'Differential Drive Robot Kinematics' covers independent wheel "
            "speed control principles applicable to the 6-drive system."
        ),
        "supporting_fact_titles": [
            "Differential Drive Robot Kinematics",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "Hovercraft Lift and Thrust Propulsion System",
        "component_category": "mechanical",
        "design_question": "How to achieve frictionless ground effect locomotion over land and water?",
        "selected_approach": (
            "Separate lift fan (centrifugal, 12 V BLDC) inflating a rubber skirt; "
            "two thrust propellers (BLDC, 1045 props) for forward propulsion "
            "and differential thrust steering. "
            "MCU commands lift fan duty and two ESC thrust channels via RC inputs."
        ),
        "rationale": (
            "Hovercraft achieves near-frictionless travel over water, sand, and grass "
            "by maintaining a 2–5 cm air cushion. "
            "Separate lift and thrust motors decouple altitude from propulsion."
        ),
        "alternatives": [
            _alt("Combined lift/thrust (single fan)", "Simpler but steering requires movable duct vanes—mechanically complex."),
            _alt("Wheeled vehicle", "No water traversal capability."),
        ],
        "verification_notes": (
            "FACT: 'Brushless DC (BLDC) Motor for Suction Fan' covers centrifugal "
            "fan characteristics used for the lift chamber."
        ),
        "supporting_fact_titles": [
            "Brushless DC (BLDC) Motor for Suction Fan",
            "Suction Pressure and Airflow in Vacuum Systems",
        ],
    },

    {
        "title": "Worm Gear Lead-Screw Linear Actuator",
        "component_category": "mechanical",
        "design_question": "How to convert rotary motor motion to a self-locking linear stroke for lifting applications?",
        "selected_approach": (
            "M8 or M10 threaded lead screw + T8 brass nut driven by DC gear motor "
            "via worm gearbox (gear ratio 20:1–50:1). "
            "Limit switches at each end of travel. "
            "Self-locking worm prevents back-driving under load."
        ),
        "rationale": (
            "Worm gear ratio provides high mechanical advantage (hold load "
            "without power) and self-locking property prevents lowering under gravity. "
            "Suitable for scissor jacks, forklifts, and folding tables."
        ),
        "alternatives": [
            _alt("Ball screw + stepper", "Back-drivable—requires holding current; higher efficiency (90 % vs 50 %) but not self-locking."),
            _alt("Rack and pinion", "Fast linear motion but not self-locking—needs brake for vertical loads."),
        ],
        "verification_notes": (
            "FACT: 'Worm Gear Ratio and Self-Locking Property' confirms "
            "self-locking condition (lead angle < friction angle)."
        ),
        "supporting_fact_titles": [
            "Worm Gear Ratio and Self-Locking Property",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "Servo-Based Gripper Jaw Mechanism",
        "component_category": "mechanical",
        "design_question": "How to grip and release objects with a compact, lightweight end-effector?",
        "selected_approach": (
            "Parallel-jaw gripper driven by MG996R servo (180° range, 10 kg·cm). "
            "Rack-and-pinion or scissor linkage converts servo rotation to "
            "symmetric jaw closure. Jaw gap 0–60 mm; grip force up to 5 N."
        ),
        "rationale": (
            "Single servo gripper is compact (< 80 g), inexpensive (< £5), and "
            "directly controlled by PWM from the robot arm controller. "
            "Adequate for picking objects up to 200 g."
        ),
        "alternatives": [
            _alt("Pneumatic gripper", "Faster and stronger but requires compressor and solenoid valves."),
            _alt("3-finger underactuated gripper", "Handles irregular objects but 3 servos and complex linkage."),
        ],
        "verification_notes": (
            "FACT: 'RC Servo Motor PWM Control' confirms MG996R PWM range "
            "and 10 kg·cm stall torque."
        ),
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
            "Forward and Inverse Kinematics — Serial Robot Arm",
        ],
    },

    {
        "title": "Pan-Tilt Servo Camera Gimbal",
        "component_category": "mechanical",
        "design_question": "How to aim a camera or sensor in any horizontal and vertical direction?",
        "selected_approach": (
            "Two RC servos (SG90 or MG90S) in pan-tilt bracket. "
            "Pan servo rotates ±90°; tilt servo elevates ±60°. "
            "Controlled by joystick potentiometers via MCU PWM, or autonomously "
            "tracking a detected object."
        ),
        "rationale": (
            "Pan-tilt bracket adds full hemisphere coverage at < £5. "
            "SG90 servos provide 1.8 kg·cm torque—adequate for cameras < 100 g. "
            "Standard PWM interface requires no additional driver ICs."
        ),
        "alternatives": [
            _alt("3-axis brushless gimbal (BGC)", "Electronic stabilisation—needed for drone cinematography but 10× cost."),
            _alt("Fixed camera mount", "No aiming flexibility."),
        ],
        "verification_notes": (
            "FACT: 'RC Servo Motor PWM Control' confirms SG90 50 Hz PWM and "
            "1–2 ms pulse range."
        ),
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
        ],
    },

    {
        "title": "Vacuum Suction Cup Wall-Climbing Drive",
        "component_category": "mechanical",
        "design_question": "How to enable a robot to adhere to and traverse vertical glass or smooth walls?",
        "selected_approach": (
            "Miniature centrifugal or diaphragm vacuum pump (12 V, −30 kPa) "
            "maintaining sub-atmospheric pressure in a compliant silicone cup array. "
            "DC gear motors drive wheels pressed against the wall surface. "
            "Suction maintained continuously during movement."
        ),
        "rationale": (
            "Vacuum adhesion can support robots up to 2 kg on glass at −25 kPa "
            "(F = ΔP × A). Compliant cups accommodate slight surface irregularities. "
            "No surface modification required."
        ),
        "alternatives": [
            _alt("Magnetic adhesion", "Only works on ferromagnetic steel surfaces—not applicable to glass."),
            _alt("Electrostatic adhesion", "Works on any surface but requires high-voltage (3–5 kV) supply."),
        ],
        "verification_notes": (
            "FACT: 'Suction Pressure and Airflow in Vacuum Systems' confirms "
            "adhesion force F = ΔP × A calculation."
        ),
        "supporting_fact_titles": [
            "Suction Pressure and Airflow in Vacuum Systems",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "Eccentric Cam Vibration Massager Drive",
        "component_category": "mechanical",
        "design_question": "How to generate therapeutic periodic percussion using a simple motor mechanism?",
        "selected_approach": (
            "DC gear motor (12 V, 60–120 RPM) driving an eccentric cam (offset "
            "mass on shaft). Cam pushes a foam or roller head through a spring-loaded "
            "follower producing 1–2 Hz deep-tissue percussion. "
            "Speed controlled by PWM for variable intensity."
        ),
        "rationale": (
            "Eccentric cam converts rotation to reciprocating linear force with "
            "zero additional mechanisms. Motor gear ratio sets percussion depth "
            "and frequency. < £8 mechanism."
        ),
        "alternatives": [
            _alt("Linear vibration motor (coin/ERM)", "High frequency (200 Hz) vibration for surface massage—insufficient for deep tissue percussion."),
            _alt("Servo-driven rack piston", "Precise stroke but 5× cost and noisier."),
        ],
        "verification_notes": (
            "FACT: 'Slider-Crank Mechanism — Rotary to Linear Conversion' describes "
            "the cam-follower equivalent rotary-to-linear conversion."
        ),
        "supporting_fact_titles": [
            "Slider-Crank Mechanism — Rotary to Linear Conversion",
            "DC Motor Speed Control via PWM",
        ],
    },

    {
        "title": "Abrasive Drum Food-Peeling Mechanism",
        "component_category": "mechanical",
        "design_question": "How to peel potato or root vegetable skins automatically in batch?",
        "selected_approach": (
            "Abrasive carborundum-coated drum (stainless inner bowl with "
            "grooved or coated walls) rotated by DC gear motor (12 V, 60 RPM). "
            "Wet process: continuous water spray washes away peel. "
            "Batch size 1–3 kg; peel time 2–4 min."
        ),
        "rationale": (
            "Abrasive peeling removes 2–3 mm of skin without a blade—safe and "
            "usable with irregular shapes. Water flow carries peel through a "
            "bottom drain. Motor torque requirement ≈ 2 N·m at 60 RPM."
        ),
        "alternatives": [
            _alt("Rotary blade peeler", "Higher peel removal rate but uneven depth on irregular produce."),
            _alt("Steam peeling", "Rapid industrial process but requires pressure vessel—impractical for lab scale."),
        ],
        "verification_notes": (
            "FACT: 'DC Motor Speed Control via PWM' covers speed control for the "
            "drum motor. FACT: 'Hooke's Law — Linear Elasticity' covers abrasion "
            "surface normal force calculation."
        ),
        "supporting_fact_titles": [
            "DC Motor Speed Control via PWM",
            "Hooke's Law — Linear Elasticity",
        ],
    },

    {
        "title": "Coin Acceptor + Solenoid Dispenser Vending Mechanism",
        "component_category": "mechanical",
        "design_question": "How to reliably accept coins, accumulate credit, and dispense product in a vending machine?",
        "selected_approach": (
            "CH-926 coin acceptor wired to MCU interrupt pin (pulse count). "
            "MCU accumulates credit; when credit ≥ item price, "
            "energises a 12 V solenoid (or DC motor auger) for 500 ms "
            "to release one product unit. Relay-driven by N-channel MOSFET."
        ),
        "rationale": (
            "Pulse-count coin acceptor is vendor-programmable for local "
            "currency denominations. Solenoid dispense is faster (< 200 ms) "
            "than auger motors; suitable for cups, cans, or water spouts."
        ),
        "alternatives": [
            _alt("NFC tap-to-pay", "No coin handling but requires payment gateway hardware."),
            _alt("Gravity-feed ramp without actuator", "No electricity needed but uncontrolled dispensing."),
        ],
        "verification_notes": (
            "FACT: 'Coin Acceptor — Pulse-Count Authentication and Relay Dispense' "
            "confirms pulse protocol and solenoid control method."
        ),
        "supporting_fact_titles": [
            "Coin Acceptor — Pulse-Count Authentication and Relay Dispense",
            "Solenoid Valve for Pneumatic and Fluid Control",
        ],
    },

    # ------------------------------------------------------------------
    # POWER — Wind, Wave, Regenerative, Marine
    # ------------------------------------------------------------------

    {
        "title": "Permanent Magnet Wind Turbine Generator",
        "component_category": "power",
        "design_question": "How to generate off-grid electrical power from local wind for IoT sensors?",
        "selected_approach": (
            "3-blade horizontal-axis turbine (0.5–1 m diameter), axial-flux PMA, "
            "3-phase AC bridge-rectified to 12 V DC. "
            "MPPT controller (CN3791 or wind-specific boost converter) charges "
            "12 V 10 Ah LiFePO₄ battery. "
            "Mechanical overspeed protection via furling tail."
        ),
        "rationale": (
            "Wind generation complements PV in low-insolation and nighttime periods. "
            "Typical mini turbine (0.5 m) generates 50–100 W at 8 m/s wind speed. "
            "LiFePO₄ buffer handles calm periods up to 5 days."
        ),
        "alternatives": [
            _alt("Solar PV only", "Zero output at night or in low wind/high cloud regions."),
            _alt("Vertical-axis Savonius", "Lower Cp (0.15) but lower cut-in speed (1.5 m/s) for calm regions."),
        ],
        "verification_notes": (
            "FACT: 'Permanent Magnet Alternator — Small Wind Turbine' confirms "
            "Betz limit and power equation P = ½ρAv³."
        ),
        "supporting_fact_titles": [
            "Permanent Magnet Alternator — Small Wind Turbine",
            "Solar Panel Sizing for Remote IoT Stations",
            "Li-Ion Battery Capacity and Energy Calculation",
        ],
    },

    {
        "title": "BLDC Regenerative Braking Energy Recovery System",
        "component_category": "power",
        "design_question": "How to recover kinetic energy during braking to extend electric vehicle range?",
        "selected_approach": (
            "Traction BLDC motor driven via 4-quadrant H-bridge or VESC ESC. "
            "On brake input, ESC switches to generation mode: "
            "back-EMF feeds current back to LiPo/LiFePO₄ battery. "
            "INA226 current/power monitor logs regenerated power on 1 Hz log."
        ),
        "rationale": (
            "Recovers 60–75 % of braking energy, extending range by 10–20 %. "
            "VESC ESC supports regenerative braking in firmware. "
            "INA226 telemetry validates efficiency and builds design-database evidence."
        ),
        "alternatives": [
            _alt("Friction brake only", "Dissipates all kinetic energy as heat—no recovery."),
            _alt("Supercapacitor buffer", "Faster charge/discharge than Li-Ion but lower energy density."),
        ],
        "verification_notes": (
            "FACT: 'Regenerative Braking — BLDC Back-EMF Energy Recovery' confirms "
            "60–75 % recovery efficiency."
        ),
        "supporting_fact_titles": [
            "Regenerative Braking — BLDC Back-EMF Energy Recovery",
            "Brushless DC (BLDC) Motor for Suction Fan",
            "Li-Ion Battery Capacity and Energy Calculation",
        ],
    },

    {
        "title": "Oscillating Water Column Wave Energy Converter",
        "component_category": "power",
        "design_question": "How to harvest wave energy to power an autonomous maritime IoT buoy?",
        "selected_approach": (
            "Miniature OWC chamber (open-bottom column, sealed top, Wells turbine). "
            "Wave action oscillates air column driving turbine → PMA generator → "
            "bridge rectifier → LiFePO₄ battery. "
            "Combined with 10 W solar panel for hybrid power."
        ),
        "rationale": (
            "OWC operates bidirectionally—Wells turbine produces power on both "
            "intake and exhaust strokes. Hybrid solar+wave increases availability "
            "to > 95 % uptime for offshore IoT buoys."
        ),
        "alternatives": [
            _alt("Heaving point absorber", "Higher capture efficiency but requires precision mooring—more complex."),
            _alt("Solar only", "Zero power during nighttime and storms."),
        ],
        "verification_notes": (
            "FACT: 'Wave Energy Conversion — Oscillating Water Column Principle' "
            "confirms P/w = ρg²H²T/(32π) flux calculation."
        ),
        "supporting_fact_titles": [
            "Wave Energy Conversion — Oscillating Water Column Principle",
            "Solar Panel Sizing for Remote IoT Stations",
        ],
    },

    {
        "title": "Capacitor Bank High-Voltage Pulsed Power Supply",
        "component_category": "power",
        "design_question": "How to deliver a very high instantaneous current pulse to accelerate a ferromagnetic projectile?",
        "selected_approach": (
            "Bank of 400 V electrolytic capacitors (total 1–10 mF, 500–2000 J). "
            "Charged via high-voltage flyback or boost converter from 12 V. "
            "SCR/IGBT triggered by MCU to discharge through copper solenoid coil "
            "in < 1 ms, producing a magnetic pulse accelerating the projectile."
        ),
        "rationale": (
            "Capacitor bank provides multi-kA pulse impossible from a battery alone. "
            "Energy E = ½ CV² ; 10 mF at 400 V = 800 J per shot. "
            "Stage 2 and 3 coils timed by photogate projectile sensors."
        ),
        "alternatives": [
            _alt("Direct battery discharge", "Insufficient peak current (limited by internal resistance)."),
            _alt("Gas-powered (pneumatic)", "Higher muzzle velocity but regulated under firearms law in most jurisdictions."),
        ],
        "verification_notes": (
            "FACT: 'Eddy Current Braking Principle' provides the electromagnetic "
            "induction theory underpinning coil-gun acceleration."
        ),
        "supporting_fact_titles": [
            "Eddy Current Braking Principle",
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
    },

    {
        "title": "4S LiPo Marine RC Power System",
        "component_category": "power",
        "design_question": "How to power a high-speed RC boat or underwater drone propulsion system?",
        "selected_approach": (
            "4S (14.8 V nominal) LiPo 3000–5000 mAh pack with waterproof "
            "XT60 connectors and IP67 battery compartment. "
            "ESC rated for 30–60 A continuous with water-cooling jacket. "
            "Low-voltage cutoff at 3.3 V/cell protects cells."
        ),
        "rationale": (
            "4S LiPo provides high power density (250 Wh/kg) for fast RC boats. "
            "Marine-rated ESC cooling prevents thermal shutdown during sustained "
            "high-throttle operation. XT60 connectors rated for 60 A."
        ),
        "alternatives": [
            _alt("3S LiPo", "Suitable for smaller boats; 25 % less power than 4S."),
            _alt("NiMH", "Lower energy density, safer chemistry but 50 % heavier for same capacity."),
        ],
        "verification_notes": (
            "FACT: 'Li-Ion Battery Capacity and Energy Calculation' confirms "
            "Wh = V × Ah energy calculation and 3.3 V/cell LVC."
        ),
        "supporting_fact_titles": [
            "Li-Ion Battery Capacity and Energy Calculation",
            "Brushless DC (BLDC) Motor for Suction Fan",
        ],
    },

    {
        "title": "Waterproof IP67 Marine Enclosure Design",
        "component_category": "mechanical",
        "design_question": "How to protect electronics in an underwater or marine environment?",
        "selected_approach": (
            "Clear polycarbonate dome or ABS housing with dual O-ring groove seals "
            "on each joint surface (O-ring cross-section 3 mm, squeeze 20–25 %). "
            "Cable penetrations via polyurethane cable glands rated IP68. "
            "Silica gel desiccant pack inside; pressure equalization valve optional."
        ),
        "rationale": (
            "IP67 (1 m immersion, 30 min) achieved with correctly dimensioned and "
            "lubricated O-rings. Polycarbonate provides optical transparency for "
            "cameras. Desiccant prevents condensation fogging optics."
        ),
        "alternatives": [
            _alt("Commercial Pelican-style case", "IP67 rated but heavy and opaque—unsuitable for camera housings."),
            _alt("Conformal coating only", "IP43 at best—insufficient for submersion."),
        ],
        "verification_notes": (
            "FACT: 'IP (Ingress Protection) Rating — IEC 60529' confirms IP67 "
            "test: 1 m immersion for 30 min."
        ),
        "supporting_fact_titles": [
            "IP (Ingress Protection) Rating — IEC 60529",
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

    {
        "title": "Autonomous Robot Vacuum Cleaner",
        "description": (
            "Differential-drive vacuum robot with 360° LiDAR and sonar obstacle avoidance, "
            "boustrophedon coverage path planning, SLAM localisation, HEPA filter, and BLE "
            "smartphone app. Returns autonomously to charging dock when battery is low."
        ),
        "objective": (
            "Clean ≥ 90 % of reachable floor area in ≤ 30 min; ≥ 90 min runtime; "
            "cliff-safe; return to dock ≤ 5 % battery."
        ),
        "constraints": "≤ 350 mm diameter; ≤ 100 mm height; ≤ 2 kg; 24 V 3 Ah LiPo; IP31.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "SLAM — Simultaneous Localisation and Mapping",
            "Coverage Path Planning — Boustrophedon (Lawnmower) Algorithm",
            "Differential Drive Robot Kinematics",
            "H-Bridge Motor Driver Circuit",
            "Brushless DC (BLDC) Motor for Suction Fan",
            "HEPA Filter Efficiency and Filtration Grade",
            "Robot Runtime Estimation from Battery Capacity",
            "Automatic Charging Dock — IR Beacon Homing",
            "Infrared Cliff Detection for Robot Vacuums",
            "Bluetooth Low Energy (BLE) for App Control",
        ],
        "design_element_titles": [
            "TFMini-S Single-Point LiDAR Distance Sensor",
            "HC-SR04 Ultrasonic Obstacle-Distance Sensor",
            "L298N Dual H-Bridge Motor Driver Module",
            "DC Gear Motor with PWM Speed Control",
            "Magnetic Quadrature Wheel Encoders",
            "BLE GATT Smartphone App Interface",
            "MCU Deep-Sleep Duty Cycle Power Management",
        ],
        "element_usage_notes": {
            "TFMini-S Single-Point LiDAR Distance Sensor": (
                "Mounted on 360° spinning platform at 10 Hz; 8 m range for room mapping."
            ),
            "L298N Dual H-Bridge Motor Driver Module": (
                "Two 12 V 200 RPM gearmotors; 180 mm wheelbase; 20 kHz PWM."
            ),
        },
    },

    {
        "title": "Automatic Weather Station",
        "description": (
            "Solar-powered outdoor station measuring air temperature, RH, barometric pressure, "
            "wind speed, wind direction, and rainfall. Logs at 1-min intervals to microSD and "
            "publishes over MQTT. Sensors housed in radiation shield and anemometer mast."
        ),
        "objective": (
            "T ±0.3 °C; RH ±2 %; pressure ±1 hPa; wind ±0.5 m/s; rainfall 0.2 mm resolution; "
            "30-day local data retention."
        ),
        "constraints": "Outdoor IP65; mast-mounted; 12 V LiFePO₄ + 10 W solar; WiFi uplink.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Cup Anemometer — Wind Speed Measurement",
            "Wind Vane — Wind Direction Measurement",
            "Tipping Bucket Rain Gauge",
            "Capacitive Relative Humidity Sensing",
            "MEMS Barometric Pressure Sensor",
            "Solar Panel Sizing for Remote IoT Stations",
            "MQTT Protocol for IoT Sensor Data",
            "NTP Time Synchronisation for Data Logging",
            "Radiation Shield for Meteorological Temperature Sensors",
            "Sensor Calibration and Traceability to SI",
        ],
        "design_element_titles": [
            "SHT41 Digital Temperature and RH Sensing",
            "I²C TCA9548A Multi-Device Sensor Bus",
            "Solar Panel + LiFePO₄ MPPT Power System",
            "MCU Deep-Sleep Duty Cycle Power Management",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "NTP UTC Timestamped Data Logging",
            "MicroSD 1 Hz Time-Series Data Logger",
        ],
        "element_usage_notes": {
            "SHT41 Digital Temperature and RH Sensing": (
                "Housed in Stevenson screen; radiation shield reduces solar error to < 0.3 °C."
            ),
            "MicroSD 1 Hz Time-Series Data Logger": (
                "1-min interval averages; CSV with UTC timestamp; 30-day FAT32 rolling archive."
            ),
        },
    },

    {
        "title": "Thermal Anomaly Inspection Camera",
        "description": (
            "Pan-tilt thermal camera using MLX90640 and servo gimbal for detecting hot spots "
            "in electrical panels, PCBs, or building envelopes. ESP32 streams false-colour MJPEG "
            "over WiFi and publishes alerts via MQTT."
        ),
        "objective": (
            "Detect anomalies ≥ 5 °C above ambient in 32×24 pixel array; ≤ 1 s stream latency; "
            "±1.5 °C absolute accuracy; ≥ 8 h battery."
        ),
        "constraints": "≤ 150×80×50 mm; USB-C charged; WiFi MJPEG stream; ≤ £80.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
            "I²C Serial Communication Protocol",
            "MQTT Protocol for IoT Sensor Data",
        ],
        "design_element_titles": [
            "MLX90640 Thermal Infrared Imaging Array",
            "Pan-Tilt Servo Camera Gimbal",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "BLE GATT Smartphone App Interface",
            "Li-Po 3.7 V USB-C Rechargeable Battery Pack",
        ],
        "element_usage_notes": {
            "MLX90640 Thermal Infrared Imaging Array": (
                "32×24 @ 4 Hz; false-colour mapped to 320×240 JPEG for MJPEG stream."
            ),
            "Pan-Tilt Servo Camera Gimbal": (
                "±45° pan, ±30° tilt via SG90 servos; remote-controlled from BLE app."
            ),
        },
    },

    {
        "title": "GPS Outdoor Asset Tracker",
        "description": (
            "Low-power GPS tracker for vehicles or outdoor equipment. Publishes location over "
            "MQTT via ESP32 WiFi on movement events and periodic heartbeat; logs to microSD "
            "when offline."
        ),
        "objective": (
            "Fix ≤ 10 m CEP; ≤ 5 s cold start outdoors; wake on >5 m movement; "
            "≥ 1-week battery at 1 fix/10 min."
        ),
        "constraints": "90×50×25 mm; IP54; USB-C; WiFi-only (no cellular); ≤ £30.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "NTP Time Synchronisation for Data Logging",
            "Low-Power Microcontroller Sleep Modes",
        ],
        "design_element_titles": [
            "NEO-6M GPS Module for Navigation",
            "MCU Deep-Sleep Duty Cycle Power Management",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "Li-Po 3.7 V USB-C Rechargeable Battery Pack",
            "NTP UTC Timestamped Data Logging",
            "MicroSD 1 Hz Time-Series Data Logger",
        ],
        "element_usage_notes": {
            "NEO-6M GPS Module for Navigation": (
                "Sleep between fixes; 1 Hz NMEA UART 9600 baud; backup battery for warm start."
            ),
            "MCU Deep-Sleep Duty Cycle Power Management": (
                "ESP32 10-min deep sleep; RTC wakeup; ≤ 12 µA idle current."
            ),
        },
    },

    {
        "title": "Autonomous Obstacle-Avoidance Rover",
        "description": (
            "Six-wheel rocker-bogie rover navigating rough terrain using forward-facing LiDAR "
            "and sonar array. Performs A* path replanning on obstacle detection; operated via "
            "nRF24L01 wireless link from a remote base station."
        ),
        "objective": (
            "Traverse 30° inclines; detect obstacles ≥ 50 mm at 1 m; navigate a 10×10 m "
            "outdoor area without manual intervention."
        ),
        "constraints": "≤ 5 kg; 12 V LiPo; nRF24 link ≤ 100 m; ≤ £150 BOM.",
        "domain": "systems",
        "status": "in_design",
        "supporting_fact_titles": [
            "A* Pathfinding Algorithm",
            "Ultrasonic Proximity Sensor — ToF Distance Measurement",
            "2D LiDAR Distance Measurement Principle",
            "Differential Drive Robot Kinematics",
            "DC Motor Speed Control via PWM",
        ],
        "design_element_titles": [
            "TFMini-S Single-Point LiDAR Distance Sensor",
            "HC-SR04 Ultrasonic Obstacle-Distance Sensor",
            "Rocker-Bogie Rough-Terrain Drive System",
            "L298N Dual H-Bridge Motor Driver Module",
            "DC Gear Motor with PWM Speed Control",
            "nRF24L01 2.4 GHz RF Transceiver Link",
            "Arduino Mega 2560 MCU Platform",
        ],
        "element_usage_notes": {
            "Rocker-Bogie Rough-Terrain Drive System": (
                "6-wheel passive suspension; 3D-printed PETG links; 80 mm diameter wheels."
            ),
            "nRF24L01 2.4 GHz RF Transceiver Link": (
                "Auto-ACK; 250 kbps; 100 m open-field range; pipe 0 = telemetry, pipe 1 = cmd."
            ),
        },
    },

    {
        "title": "Smart Coin-Operated Vending Machine",
        "description": (
            "Single-row vending machine accepting coins or RFID cards, driving per-lane solenoid "
            "dispensers, with MQTT sales logging, NTP-timestamped audit trail, and OTA firmware "
            "updates."
        ),
        "objective": (
            "Accept 20p/50p/£1 coins and RFID cards; ≤ 5 dispense lanes; ≤ 3 s dispense; "
            "100 % sales event logging."
        ),
        "constraints": "230 V mains-powered; RS232 coin validator; ≤ £100 BOM; WiFi uplink.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "RFID/NFC Reader — ISO 14443 / 15693 Interface",
            "OTA Firmware Update for Embedded Devices",
        ],
        "design_element_titles": [
            "Coin Acceptor + Solenoid Dispenser Vending Mechanism",
            "MFRC522 RFID Card Reader (NTAG216)",
            "Arduino Mega 2560 MCU Platform",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "OTA HTTPS Dual-Bank Firmware Update",
            "MQTT QoS-1 Secure Event Logger",
            "NTP UTC Timestamped Data Logging",
        ],
        "element_usage_notes": {
            "Coin Acceptor + Solenoid Dispenser Vending Mechanism": (
                "5-lane solenoid dispensers; coin acceptor UART @ 9600 baud."
            ),
            "Arduino Mega 2560 MCU Platform": (
                "Handles coin/RFID validation and lane control; ESP32 co-processor for WiFi/MQTT."
            ),
        },
    },

    {
        "title": "BLE Hand-Gesture Glove Controller",
        "description": (
            "Wearable glove embedding five-channel flex sensors and MPU-6050 IMU to map hand "
            "gestures to servo commands. Streams gesture data over BLE for robot arm or "
            "prosthetic control applications."
        ),
        "objective": (
            "Recognise 8 distinct static gestures; ≤ 50 ms BLE latency; ≥ 8 h battery; "
            "10 m BLE range."
        ),
        "constraints": "Fits adult size-M glove; Li-Po ≤ 200 mAh; USB-C charge; no skin electrodes.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Bluetooth Low Energy (BLE) for App Control",
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "RC Servo Motor PWM Control",
        ],
        "design_element_titles": [
            "Flex Sensor Hand-Gesture Glove Interface",
            "MPU-6050 IMU Gyro + Accel (I²C)",
            "BLE GATT Smartphone App Interface",
            "RC Servo Joint Actuator",
            "Li-Po 3.7 V USB-C Rechargeable Battery Pack",
        ],
        "element_usage_notes": {
            "Flex Sensor Hand-Gesture Glove Interface": (
                "Five 2.2-inch flex sensors; ADC averaged over 16 samples; 10 kΩ voltage divider."
            ),
            "RC Servo Joint Actuator": (
                "Mapped to prosthetic finger tendons via Bowden cable; 1 servo per digit."
            ),
        },
    },

    {
        "title": "UV-C Automated Sterilisation Cabinet",
        "description": (
            "Enclosed UV-C LED cabinet with PIR door-occupancy interlock, timed sterilisation "
            "cycle controller, OLED status display, and MQTT audit log. Suitable for tools, "
            "masks, or small medical equipment."
        ),
        "objective": (
            "≥ 99.9 % microbial reduction in ≤ 10 min at 275 nm; door interlock prevents UV "
            "exposure to occupants; ≥ 1000 h LED rated life."
        ),
        "constraints": "40×30×20 cm internal; 230 V mains; ≤ £60; CE safety markings.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "N-Channel MOSFET as a Low-Side Power Switch",
        ],
        "design_element_titles": [
            "UV-C LED Germicidal + Ozone Sterilisation Module",
            "PIR HC-SR501 Motion Detection Module",
            "N-Channel MOSFET Low-Side Load Switch",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "MQTT QoS-1 Secure Event Logger",
            "NTP UTC Timestamped Data Logging",
        ],
        "element_usage_notes": {
            "UV-C LED Germicidal + Ozone Sterilisation Module": (
                "Six 3 W LEDs at 275 nm; timed 10-min cycle; PWM dimming for dose control."
            ),
            "PIR HC-SR501 Motion Detection Module": (
                "Door-open proxy; HIGH output immediately kills UV driver via MOSFET."
            ),
        },
    },

    {
        "title": "Voice-Controlled Home Automation Hub",
        "description": (
            "Offline voice recognition controller switching mains loads (lights, fans, pumps) "
            "via solid-state relays, with MQTT status reporting and BLE fallback app control. "
            "No cloud dependency."
        ),
        "objective": (
            "Recognise 10 voice commands offline; ≤ 500 ms response; control ≥ 4 mains "
            "channels; ≥ 30 operations/day."
        ),
        "constraints": "230 V; DIN-rail mount; no cloud dependency; CE-compliant; ≤ £45 BOM.",
        "domain": "systems",
        "status": "in_design",
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "Bluetooth Low Energy (BLE) for App Control",
        ],
        "design_element_titles": [
            "Voice Recognition UART Speech Module",
            "Solid-State Relay Mains Actuator Switching",
            "ESP32 WiFi + MQTT IoT Telemetry",
            "BLE GATT Smartphone App Interface",
            "MQTT QoS-1 Secure Event Logger",
        ],
        "element_usage_notes": {
            "Voice Recognition UART Speech Module": (
                "LD3320 UART @ 9600 baud; 20-word vocabulary; 1-shot user retrain supported."
            ),
            "Solid-State Relay Mains Actuator Switching": (
                "4-channel SSR board; 230 V / 10 A per channel; zero-cross switching."
            ),
        },
    },

    {
        "title": "Wireless Temperature and Gas Monitoring Node",
        "description": (
            "Battery-powered wireless sensor node detecting combustible gas and temperature "
            "with MQ-3 sensor and nRF24L01 link to a central hub. Relay alarm triggered on "
            "threshold breach; deep sleep between measurements for long battery life."
        ),
        "objective": (
            "Detect ≥ 100 ppm alcohol/combustible gas in ≤ 5 s; transmit alert in ≤ 500 ms; "
            "≥ 6-month battery at 1-min sensing interval."
        ),
        "constraints": "3× AA alkaline; ≤ £15 per node; ≤ 50 m indoor range; IP30.",
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "MQTT Protocol for IoT Sensor Data",
            "ADC Resolution and Measurement Precision",
        ],
        "design_element_titles": [
            "MQ-3 Alcohol and Combustible Gas Sensor",
            "nRF24L01 2.4 GHz RF Transceiver Link",
            "Arduino Uno/Nano MCU Platform",
            "MCU Deep-Sleep Duty Cycle Power Management",
        ],
        "element_usage_notes": {
            "MQ-3 Alcohol and Combustible Gas Sensor": (
                "RS/R0 threshold 0.4 for alarm; 30 s preheat on wake-up before sample."
            ),
            "nRF24L01 2.4 GHz RF Transceiver Link": (
                "PTX mode; 1-min intervals; hub is PRX coordinator; auto-ACK 250 kbps."
            ),
        },
    },
]
