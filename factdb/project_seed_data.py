"""
Mechatronics project seed data for FactDB.

Ten complete mechatronics projects, each with:
  • High-level project metadata (title, description, objective, constraints)
  • Multiple DesignDecision records covering every major subsystem
  • Alternatives considered (and fact-backed reasons for rejection)
  • Verification notes tracing decisions back to DB facts

Facts are referenced by title; the seeder resolves them at load time.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helper: alternative dict shorthand
# ---------------------------------------------------------------------------


def _alt(approach: str, reason_rejected: str) -> dict:
    return {"approach": approach, "reason_rejected": reason_rejected}


# ---------------------------------------------------------------------------
# PROJECT DEFINITIONS
# ---------------------------------------------------------------------------

MECHATRONICS_PROJECTS: list[dict] = [

    # ====================================================================
    # PROJECT 1 — Automated Plant Watering System
    # ====================================================================
    {
        "title": "Automated Plant Watering System",
        "description": (
            "A solar-powered IoT device that monitors soil moisture and ambient "
            "temperature, then actuates a solenoid valve (or peristaltic pump) "
            "to irrigate a houseplant or small garden bed autonomously and "
            "reports data to an MQTT broker."
        ),
        "objective": (
            "Maintain soil volumetric water content (VWC) between 20–60% "
            "without manual intervention; log sensor data at 15-minute intervals."
        ),
        "constraints": (
            "Budget ≤ £30; outdoor IP54+ enclosure; ≥ 1-week autonomy from "
            "a small solar panel + 2 Ah LiFePO₄ battery; single PCB ≤ 100×60 mm."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Capacitive Soil Moisture Sensing",
            "NTC Thermistor Temperature Sensing",
            "MQTT Protocol for IoT Sensor Data",
            "Solar Panel Sizing for Remote IoT Stations",
            "Li-Ion Battery Capacity and Energy Calculation",
            "N-Channel MOSFET as a Low-Side Power Switch",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
        "designs": [
            {
                "title": "Soil Moisture Sensing Subsystem",
                "component_category": "sensing",
                "design_question": (
                    "Which sensing principle most accurately measures soil VWC "
                    "without electrode corrosion?"
                ),
                "selected_approach": (
                    "Capacitive soil moisture sensor (e.g., SparkFun SEN-13637) "
                    "inserted 5 cm deep, output voltage 1.2–3.0 V read by ESP32 "
                    "12-bit ADC.  Calibrated against known dry/wet weight method "
                    "per soil type."
                ),
                "rationale": (
                    "Capacitive probes do not corrode and provide a continuous "
                    "voltage output linearly proportional to VWC after single-"
                    "point calibration per soil mix.  ADC resolution of 0.8 mV "
                    "translates to ~0.5% VWC resolution — sufficient for the "
                    "20–60% target range."
                ),
                "alternatives": [
                    _alt(
                        "Resistive moisture sensor (YL-69)",
                        "Electrolytic corrosion of sensing electrodes within "
                        "weeks; non-linear response; accuracy poor — rejected.",
                    ),
                    _alt(
                        "TDR (Time-Domain Reflectometry) probe",
                        "High accuracy but module cost > £40 and complex RF "
                        "circuitry; over-engineered for this budget — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Capacitive Soil Moisture Sensing' confirms voltage "
                    "output 1.2–3.0 V and recommends temperature compensation "
                    "above 30 °C.  FACT: 'ADC Resolution and Measurement "
                    "Precision' confirms 12-bit ADC gives 0.8 mV / LSB for "
                    "3.3 V full-scale — adequate for 0.5% VWC resolution."
                ),
                "supporting_fact_titles": [
                    "Capacitive Soil Moisture Sensing",
                    "ADC Resolution and Measurement Precision",
                ],
            },
            {
                "title": "Pump/Valve Actuation Subsystem",
                "component_category": "actuation",
                "design_question": (
                    "How to switch water flow on/off from a 5 V GPIO pin safely?"
                ),
                "selected_approach": (
                    "N-channel MOSFET (IRLZ44N) low-side switch driving a 12 V "
                    "solenoid valve (NC type, 0.5 W).  Gate driven by ESP32 GPIO "
                    "via 100 Ω series resistor.  1N4007 flyback diode across valve "
                    "coil for inductive spike suppression."
                ),
                "rationale": (
                    "Logic-level MOSFET (V_th ≈ 1–2 V) is fully enhanced by 3.3 V "
                    "GPIO; R_DS(on) < 0.022 Ω at I = 0.05 A → power loss "
                    "< 0.1 mW.  NC valve keeps plants watered on power failure."
                ),
                "alternatives": [
                    _alt(
                        "Relay module (SRD-05VDC)",
                        "Relays rated ≥ 100 mA coil current — too high for "
                        "battery-powered duty cycle; audible clicking noise; "
                        "larger PCB footprint — rejected.",
                    ),
                    _alt(
                        "Peristaltic pump (5 V, 300 mA)",
                        "Higher power draw (300 mA vs 42 mA for solenoid) "
                        "increases battery size requirement; acceptable if "
                        "pump-head replacements are needed — alternative for "
                        "indoor potted plants.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'N-Channel MOSFET as a Low-Side Power Switch' "
                    "confirms IRLZ44N R_DS(on) suitability, logic-level gate "
                    "threshold, and flyback diode requirement for inductive loads."
                ),
                "supporting_fact_titles": [
                    "N-Channel MOSFET as a Low-Side Power Switch",
                ],
            },
            {
                "title": "Power Subsystem",
                "component_category": "power",
                "design_question": (
                    "How to achieve ≥ 1-week battery life from solar + battery "
                    "with ≤ 50 mW average consumption?"
                ),
                "selected_approach": (
                    "60×90 mm 1 W solar panel + 3.2 V 2 Ah LiFePO₄ cell via "
                    "CN3791 MPPT charge controller.  ESP32 in deep sleep between "
                    "15-min measurement cycles.  Average I_avg ≈ "
                    "25 mA × (0.5 s / 900 s) + 0.01 mA ≈ 0.024 mA → 96 µW."
                ),
                "rationale": (
                    "LiFePO₄ preferred over Li-ion: safer chemistry for "
                    "unattended outdoor use, tolerates higher temperature, "
                    "2000+ cycle life.  1 W panel in 2 PSH gives 2 Wh/day → "
                    "83× the 24 µW needed — comfortably covers cloudy days."
                ),
                "alternatives": [
                    _alt(
                        "AAA alkaline battery pack (3× AAA = 3.6 V, 1.2 Ah)",
                        "Non-rechargeable; ~500 h life at 2.4 µA standby but "
                        "~83 h at 14.6 µA active average — requires monthly "
                        "replacement — rejected for autonomous deployment.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Solar Panel Sizing for Remote IoT Stations' formula "
                    "P = E_daily / (η·PSH) with E_daily = 0.0024×24 = 0.058 Wh, "
                    "η = 0.76, PSH = 2 gives P_min = 0.038 W — well under 1 W "
                    "panel.  FACT: 'Low-Power Microcontroller Sleep Modes' "
                    "confirms I_avg formula for duty-cycled MCU."
                ),
                "supporting_fact_titles": [
                    "Solar Panel Sizing for Remote IoT Stations",
                    "Li-Ion Battery Capacity and Energy Calculation",
                    "Low-Power Microcontroller Sleep Modes",
                ],
            },
            {
                "title": "Connectivity Subsystem",
                "component_category": "communication",
                "design_question": (
                    "How to transmit sensor data to a home server over WiFi "
                    "with minimum power impact?"
                ),
                "selected_approach": (
                    "ESP32 WiFi to home router; MQTT over TCP (QoS 0) to a "
                    "Mosquitto broker on a Raspberry Pi.  WiFi active for "
                    "< 1 s per 15-min cycle; connection uses stored credentials."
                ),
                "rationale": (
                    "ESP32 integrates WiFi + BLE on-chip — zero external "
                    "component cost.  MQTT QoS 0 minimises transmission time "
                    "(fire-and-forget).  NTP sync on each wake ensures accurate "
                    "timestamps on all readings."
                ),
                "alternatives": [
                    _alt(
                        "LoRa (SX1276) point-to-point to gateway",
                        "No home WiFi router needed but requires separate LoRa "
                        "gateway hardware; overkill for ≤ 100 m indoor range — "
                        "rejected for home use, preferred for remote gardens.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'MQTT Protocol for IoT Sensor Data' confirms QoS 0 "
                    "minimises overhead.  FACT: 'ESP32 WiFi + BLE System-on-Chip' "
                    "confirms deep-sleep current ≈ 10 µA with WiFi off."
                ),
                "supporting_fact_titles": [
                    "MQTT Protocol for IoT Sensor Data",
                    "ESP32 WiFi + BLE System-on-Chip",
                    "NTP Time Synchronisation for Data Logging",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 2 — Self-Balancing Robot (Segway Style)
    # ====================================================================
    {
        "title": "Self-Balancing Two-Wheel Robot",
        "description": (
            "A two-wheeled inverted-pendulum robot that maintains upright "
            "balance using an IMU-based tilt measurement and a cascaded PID "
            "controller driving differential DC motors."
        ),
        "objective": (
            "Balance autonomously on flat surfaces; accept forward/reverse/turn "
            "commands via BLE app; maintain balance within ±5° of vertical."
        ),
        "constraints": (
            "Height ≤ 300 mm; total mass ≤ 1.5 kg; battery life ≥ 30 min "
            "continuous; maximum speed ≥ 0.5 m/s."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Kalman Filter for Sensor Fusion",
            "PID Controller — Transfer Function",
            "H-Bridge Motor Driver Circuit",
            "DC Motor Speed Control via PWM",
            "Differential Drive Robot Kinematics",
            "Bluetooth Low Energy (BLE) for App Control",
        ],
        "designs": [
            {
                "title": "Tilt Sensing and Angle Estimation",
                "component_category": "sensing",
                "design_question": (
                    "How to accurately estimate the robot's tilt angle in "
                    "real-time at ≥ 100 Hz with < 1° noise?"
                ),
                "selected_approach": (
                    "MPU-6050 IMU (gyro + accel) on I²C at 200 Hz.  "
                    "Complementary filter: θ = α·(θ + ω·dt) + (1−α)·θ_accel, "
                    "α = 0.98.  Kalman filter as an alternative for sub-0.1° "
                    "accuracy if needed."
                ),
                "rationale": (
                    "Complementary filter is computationally cheap (single "
                    "multiply-add per cycle) and stable.  FACT: 'Kalman Filter' "
                    "gives lower noise but requires matrix operations — "
                    "complementary filter is sufficient for ±5° balance target. "
                    "MPU-6050 gyro noise 0.01 °/s/√Hz gives < 0.05° accumulated "
                    "error over 10 ms control cycle."
                ),
                "alternatives": [
                    _alt(
                        "Kalman filter (EKF) for attitude estimation",
                        "More accurate but higher CPU load on ATmega328P; "
                        "complementary filter meets spec — use Kalman if "
                        "upgrading to STM32 or ESP32.",
                    ),
                    _alt(
                        "Single-axis tilt sensor (MMA7361L accel only)",
                        "Accelerometer measures gravity + linear acceleration — "
                        "vibration from motors corrupts reading during motion; "
                        "gyro fusion is essential — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'IMU (Inertial Measurement Unit) for Robot Navigation' "
                    "confirms gyro drift accumulation and necessity of accel "
                    "fusion.  FACT: 'Kalman Filter for Sensor Fusion' provides "
                    "the mathematical upgrade path."
                ),
                "supporting_fact_titles": [
                    "IMU (Inertial Measurement Unit) for Robot Navigation",
                    "Kalman Filter for Sensor Fusion",
                    "I²C Serial Communication Protocol",
                ],
            },
            {
                "title": "Balance Control Algorithm",
                "component_category": "control",
                "design_question": (
                    "Which control law maintains balance and rejects disturbances "
                    "faster than the robot's fall time?"
                ),
                "selected_approach": (
                    "Cascaded PID: inner loop (balance) at 200 Hz controls "
                    "motor torque based on tilt angle error (θ − 0°); outer "
                    "loop (speed) at 50 Hz generates tilt setpoint from desired "
                    "speed.  Ziegler-Nichols step-response tuning: K_p = 15, "
                    "K_i = 40, K_d = 0.4 (inner loop)."
                ),
                "rationale": (
                    "Fall time of a 300 mm pendulum ≈ √(2L/g) ≈ 0.25 s from "
                    "5° offset — control cycle must be << 100 ms.  200 Hz inner "
                    "loop (5 ms) gives > 50:1 margin.  Cascaded PID is standard "
                    "practice for this topology."
                ),
                "alternatives": [
                    _alt(
                        "LQR (Linear Quadratic Regulator)",
                        "Optimal for linearised pendulum model; requires state "
                        "estimator and model identification; more complex to tune "
                        "than PID; PID meets requirements — rejected for initial "
                        "design.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'PID Controller — Transfer Function' confirms K_p "
                    "reduces rise time, K_i eliminates steady-state error, K_d "
                    "reduces overshoot — matches cascaded design intent."
                ),
                "supporting_fact_titles": [
                    "PID Controller — Transfer Function",
                ],
            },
            {
                "title": "Drive Subsystem",
                "component_category": "actuation",
                "design_question": (
                    "Which motor driver topology provides bidirectional control "
                    "for two 12 V DC gearmotors from a 3.3 V MCU?"
                ),
                "selected_approach": (
                    "Dual TB6612FNG H-bridge IC (two full-bridges on one package, "
                    "1.2 A continuous, 3.2 A peak, PWM up to 100 kHz).  "
                    "20 kHz PWM above audible range.  Encoder feedback (600 CPR "
                    "magnetic) for speed measurement."
                ),
                "rationale": (
                    "TB6612FNG accepts 3.3 V logic directly, handles 12 V motor "
                    "supply, includes built-in protection.  Two motors in one IC "
                    "simplifies PCB layout."
                ),
                "alternatives": [
                    _alt(
                        "L298N bridge",
                        "Outdated design: voltage drop 2–3 V (saturation loss) "
                        "wastes significant power at 12 V; no current limit; "
                        "bulky package — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'H-Bridge Motor Driver Circuit' confirms TB6612FNG "
                    "architecture, dead-time insertion, and PWM frequency above "
                    "audible range.  FACT: 'DC Motor Speed Control via PWM' "
                    "confirms V_avg = D·V_supply proportionality."
                ),
                "supporting_fact_titles": [
                    "H-Bridge Motor Driver Circuit",
                    "DC Motor Speed Control via PWM",
                    "Wheel Encoder Odometry",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 3 — Line-Following Robot
    # ====================================================================
    {
        "title": "PID Line-Following Robot",
        "description": (
            "A small differential-drive robot that follows a black line on a "
            "white surface using an array of IR reflectance sensors and a "
            "PID controller that corrects heading in real-time."
        ),
        "objective": (
            "Follow a 19 mm wide black line at ≥ 0.3 m/s with ≤ 30 mm "
            "cross-track error on 90° corners."
        ),
        "constraints": (
            "Total cost ≤ £20; powered by 4× AA NiMH; chassis ≤ 20×15 cm."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "PID Controller — Transfer Function",
            "Differential Drive Robot Kinematics",
            "DC Motor Speed Control via PWM",
            "H-Bridge Motor Driver Circuit",
        ],
        "designs": [
            {
                "title": "Line Sensing Array",
                "component_category": "sensing",
                "design_question": (
                    "How many IR reflectance sensors are needed to detect "
                    "the line position and compute a reliable error signal?"
                ),
                "selected_approach": (
                    "8-sensor TCRT5000 IR reflectance array spaced 10 mm apart "
                    "(80 mm total span).  Sensors modulated at 38 kHz to reject "
                    "ambient IR.  Position computed as weighted average: "
                    "error = Σ(w_i · x_i) / Σ(w_i), where w_i = (1 − reflectance_i)."
                ),
                "rationale": (
                    "8 sensors give sub-millimetre resolution for position; "
                    "weighted-average centroid is smooth and differentiable "
                    "for the derivative term of the PID controller."
                ),
                "alternatives": [
                    _alt(
                        "Camera + OpenCV (Raspberry Pi)",
                        "Camera gives rich image but needs Raspberry Pi (power "
                        "budget 3–5 W vs 0.1 W for IR array); latency 30–50 ms "
                        "vs < 1 ms for analogue IR — rejected for speed requirement.",
                    ),
                    _alt(
                        "Single IR sensor with bang-bang control",
                        "Bang-bang causes oscillatory weaving; cannot follow "
                        "smooth curves accurately — rejected.",
                    ),
                ],
                "verification_notes": (
                    "PID requires a continuous error signal; 8-sensor weighted "
                    "average produces this naturally.  Modulation at 38 kHz "
                    "rejects sunlight interference (confirmed by TCRT5000 AN)."
                ),
                "supporting_fact_titles": [],
            },
            {
                "title": "PID Heading Controller",
                "component_category": "control",
                "design_question": (
                    "How to tune the PID gains for line-following at 0.3 m/s "
                    "without overshoot on straights or undershooting corners?"
                ),
                "selected_approach": (
                    "PID with error = position_from_centre (range −35 to +35 mm). "
                    "Motor commands: L = base_speed + PID_output; "
                    "R = base_speed − PID_output.  Tuning: K_p = 0.4, K_i = 0, "
                    "K_d = 8 (derivative-heavy for fast heading correction)."
                ),
                "rationale": (
                    "High K_d damps oscillation on straights; low/zero K_i "
                    "prevents integral windup during sharp corners (where error "
                    "is transiently large).  K_i added only for offset "
                    "compensation on banked surfaces."
                ),
                "alternatives": [
                    _alt(
                        "Pure proportional control (P-only)",
                        "Oscillates at high speed; K_p large enough to follow "
                        "corners produces steady-state oscillation — K_d "
                        "term essential.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'PID Controller — Transfer Function' — K_d reduces "
                    "overshoot and improves stability; K_i eliminates "
                    "steady-state error.  Consistent with chosen gain strategy."
                ),
                "supporting_fact_titles": [
                    "PID Controller — Transfer Function",
                    "Differential Drive Robot Kinematics",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 4 — 3-DOF Desktop Robotic Arm
    # ====================================================================
    {
        "title": "3-DOF Desktop Robotic Arm",
        "description": (
            "A three-joint planar robotic arm (shoulder, elbow, wrist) driven "
            "by RC servo motors and controlled by an ESP32 accepting joint-space "
            "commands or inverse-kinematics Cartesian targets over USB serial "
            "or BLE."
        ),
        "objective": (
            "Reach any point in a 200 mm radius working envelope; "
            "position accuracy ±2 mm; payload ≥ 100 g; repeat to ±1 mm."
        ),
        "constraints": (
            "Total mass ≤ 500 g; 3D-printed frame; 5 V USB-C powered; "
            "cost ≤ £25."
        ),
        "domain": "mechanical",
        "status": "completed",
        "supporting_fact_titles": [
            "RC Servo Motor PWM Control",
            "Forward and Inverse Kinematics — Serial Robot Arm",
            "ESP32 WiFi + BLE System-on-Chip",
            "Bluetooth Low Energy (BLE) for App Control",
        ],
        "designs": [
            {
                "title": "Joint Actuation — Servo Selection",
                "component_category": "actuation",
                "design_question": (
                    "What servo torque is required at the shoulder joint to "
                    "hold 100 g payload at full extension (200 mm)?"
                ),
                "selected_approach": (
                    "MG996R servo at shoulder (10 kg·cm at 5 V); MG90S at "
                    "elbow (2.2 kg·cm); SG90 at wrist (1.8 kg·cm).  "
                    "Torque at shoulder: T = m·g·r = 0.1×9.81×0.2 = 0.196 N·m "
                    "= 2 kg·cm — MG996R provides 5× safety margin."
                ),
                "rationale": (
                    "MG996R metal gears prevent stripping under peak loads; "
                    "10 kg·cm torque vs 2 kg·cm required → FoS = 5 which "
                    "exceeds the typical structural FoS of 3–5 for mechanisms."
                ),
                "alternatives": [
                    _alt(
                        "Stepper motor + belt drive at shoulder",
                        "Higher holding torque and no position drift but "
                        "requires separate driver IC, more complex wiring, "
                        "and frame design; servo self-contains gearbox, "
                        "driver, and feedback — rejected for simplicity.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'RC Servo Motor PWM Control' confirms MG996R "
                    "command protocol (1–2 ms pulse at 50 Hz) and torque "
                    "ratings.  FACT: 'Factor of Safety' confirms FoS = 5 "
                    "exceeds the 3–5 recommendation for mechanisms."
                ),
                "supporting_fact_titles": [
                    "RC Servo Motor PWM Control",
                    "Factor of Safety",
                ],
            },
            {
                "title": "Inverse Kinematics Solver",
                "component_category": "software",
                "design_question": (
                    "How to convert (x, y) Cartesian target coordinates to "
                    "joint angles θ₁, θ₂, θ₃ for the arm controller?"
                ),
                "selected_approach": (
                    "Analytical 2R planar IK for shoulder + elbow: "
                    "θ₂ = ±acos((x²+y²−l₁²−l₂²)/(2l₁l₂)); "
                    "θ₁ = atan2(y,x) − atan2(l₂·sin(θ₂), l₁+l₂·cos(θ₂)). "
                    "Wrist angle θ₃ = target_orientation − θ₁ − θ₂. "
                    "Elbow-up solution selected by default; boundary check "
                    "against joint limits before commanding servos."
                ),
                "rationale": (
                    "Analytical IK is deterministic and runs in < 1 ms on "
                    "ESP32, vs iterative Jacobian methods (10–100 ms). "
                    "Two solutions (elbow-up/down) handled explicitly."
                ),
                "alternatives": [
                    _alt(
                        "Numerical IK (Jacobian pseudo-inverse iteration)",
                        "Required for non-planar or redundant arms; adds "
                        "convergence time and may fail near singularities; "
                        "analytical solution is exact for 2R planar — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Forward and Inverse Kinematics — Serial Robot Arm' "
                    "provides the exact θ₂ = ±acos(...) formula used and "
                    "confirms singularities occur at full extension (l₁+l₂). "
                    "Joint limits [-90°, 90°] prevent singularity entry."
                ),
                "supporting_fact_titles": [
                    "Forward and Inverse Kinematics — Serial Robot Arm",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 5 — CNC 2D Plotter
    # ====================================================================
    {
        "title": "2-Axis CNC Belt-Drive Plotter",
        "description": (
            "A CoreXY belt-drive 2D plotter using two NEMA 17 stepper motors, "
            "a servo-controlled Z-axis pen lift, and Grbl firmware accepting "
            "G-code over USB-C serial to draw vector graphics on A4 paper."
        ),
        "objective": (
            "Plot A4 (210×297 mm) drawings with ±0.5 mm accuracy at up to "
            "100 mm/s; interface via USB-C to a PC running Inkscape + gcode-sender."
        ),
        "constraints": (
            "Frame built from 2020 aluminium extrusion; total cost ≤ £60; "
            "12 V / 3 A supply; must home on startup using limit switches."
        ),
        "domain": "mechanical",
        "status": "completed",
        "supporting_fact_titles": [
            "Stepper Motor Drive — Full Step and Microstepping",
            "G-code and CNC Motion Control",
            "RC Servo Motor PWM Control",
            "H-Bridge Motor Driver Circuit",
        ],
        "designs": [
            {
                "title": "Motion Architecture — CoreXY vs Cartesian",
                "component_category": "mechanical",
                "design_question": (
                    "Should the plotter use a standard Cartesian H-bot, "
                    "CoreXY, or polar topology?"
                ),
                "selected_approach": (
                    "CoreXY: both motors stationary on frame, lightweight moving "
                    "carriage.  Both motors contribute to X and Y motion "
                    "simultaneously: X = (M₁+M₂)/2; Y = (M₁−M₂)/2. "
                    "Timing belt GT2 2 mm pitch, 20T pulley → 0.01 mm/step at "
                    "1/16 microstepping."
                ),
                "rationale": (
                    "CoreXY keeps both motors on the fixed frame → lower moving "
                    "mass → higher acceleration without resonance.  Resolution: "
                    "at 1/16 step, 200 steps/rev × 16 = 3200 steps/rev; "
                    "20T GT2 = 40 mm/rev → 0.0125 mm/step — exceeds 0.5 mm "
                    "spec by 40×."
                ),
                "alternatives": [
                    _alt(
                        "Cartesian H-bot (one motor on moving Y-axis)",
                        "Moving motor adds mass to Y-axis carriage; lower "
                        "acceleration; introduces racking (frame twist) at "
                        "speed — CoreXY avoids this.",
                    ),
                    _alt(
                        "Polar/SCARA topology",
                        "Non-uniform resolution across workspace; complex "
                        "G-code to Cartesian conversion; not natively supported "
                        "by Grbl — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Stepper Motor Drive — Full Step and Microstepping' "
                    "confirms 1/16 microstepping resolution formula. "
                    "FACT: 'G-code and CNC Motion Control' confirms Grbl "
                    "supports CoreXY kinematics natively."
                ),
                "supporting_fact_titles": [
                    "Stepper Motor Drive — Full Step and Microstepping",
                    "G-code and CNC Motion Control",
                ],
            },
            {
                "title": "Stepper Motor Driver Selection",
                "component_category": "actuation",
                "design_question": (
                    "Which stepper driver IC minimises vibration / resonance "
                    "at low speeds (< 10 mm/s for fine detail work)?"
                ),
                "selected_approach": (
                    "DRV8825 at 1/32 microstepping, 1.5 A current limit with "
                    "Vref = 0.75 V.  UART-configurable TMC2209 StealthChop2 "
                    "as preferred alternative for silent operation."
                ),
                "rationale": (
                    "TMC2209 SpreadCycle / StealthChop2 virtually eliminates "
                    "mid-speed resonance and audible noise; UART configuration "
                    "enables stall detection (sensorless homing).  DRV8825 is "
                    "lower cost if noise not critical."
                ),
                "alternatives": [
                    _alt(
                        "A4988 driver (1/16 max)",
                        "Only 1/16 step resolution; audible 'screech' at mid-"
                        "speed resonance; DRV8825 and TMC2209 are superior "
                        "for plotting — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Stepper Motor Drive — Full Step and Microstepping' "
                    "confirms A4988 max 1/16, DRV8825 max 1/32, and torque-"
                    "speed trade-off with microstepping."
                ),
                "supporting_fact_titles": [
                    "Stepper Motor Drive — Full Step and Microstepping",
                ],
            },
            {
                "title": "Pen Lift (Z-axis) Mechanism",
                "component_category": "actuation",
                "design_question": (
                    "How to lift the pen 5 mm off paper quickly and quietly "
                    "between strokes?"
                ),
                "selected_approach": (
                    "SG90 micro-servo (5 g, 1.8 kg·cm) mounted on carriage; "
                    "M2 pushrod converts servo rotation (0° down / 45° up) to "
                    "5 mm vertical pen travel.  ESP32 LEDC PWM channel drives "
                    "servo; transition < 150 ms."
                ),
                "rationale": (
                    "Servo gives precise repeatable pen height; lightweight "
                    "(5 g on carriage); SG90 torque 1.8 kg·cm >> 0.01 kg·cm "
                    "required to lift 5 g pen → adequate margin."
                ),
                "alternatives": [
                    _alt(
                        "Solenoid plunger lift",
                        "Faster response (< 20 ms) but constant power draw "
                        "when energised (0.5–1 W) and louder impact; servo "
                        "holds position with zero power once at stop — "
                        "preferred for quiet operation.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'RC Servo Motor PWM Control' confirms SG90 command "
                    "protocol and torque specification."
                ),
                "supporting_fact_titles": [
                    "RC Servo Motor PWM Control",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 6 — Quadcopter Drone Flight Controller
    # ====================================================================
    {
        "title": "250 mm Quadcopter Drone Flight Controller",
        "description": (
            "A 250 mm wheelbase racing/photography quadcopter with a custom "
            "flight controller based on STM32F4, ICM-42688-P IMU, and "
            "cascaded PID attitude control running at 4 kHz inner loop. "
            "Motor outputs to 4× 30A ESCs driving 2306 brushless motors."
        ),
        "objective": (
            "Stable hover ±5 cm altitude; attitude hold ±2°; "
            "response bandwidth > 20 Hz; compatible with Betaflight configurator."
        ),
        "constraints": (
            "AUW ≤ 500 g including 4S 1500 mAh LiPo; flight time ≥ 5 min; "
            "STM32F4 @ 168 MHz; 4-layer PCB."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "IMU (Inertial Measurement Unit) for Robot Navigation",
            "Kalman Filter for Sensor Fusion",
            "PID Controller — Transfer Function",
            "Brushless DC (BLDC) Motor for Suction Fan",
            "Li-Ion Battery Capacity and Energy Calculation",
            "Nyquist–Shannon Sampling Theorem",
        ],
        "designs": [
            {
                "title": "IMU Attitude Estimation",
                "component_category": "sensing",
                "design_question": (
                    "How to estimate roll/pitch/yaw at 4 kHz with < 0.5° noise "
                    "for the inner rate loop?"
                ),
                "selected_approach": (
                    "ICM-42688-P IMU on SPI at 8 MHz; gyro sampled at 8 kHz "
                    "(downsampled to 4 kHz for attitude loop).  "
                    "Mahony complementary filter for attitude; "
                    "EKF optional for GPS-aided mode.  "
                    "Anti-aliasing filter at 1/4 Nyquist (1 kHz) before "
                    "attitude calculation."
                ),
                "rationale": (
                    "SPI bus at 8 MHz gives < 5 µs latency vs I²C 400 kHz "
                    "which would be 40 µs — critical for 4 kHz control.  "
                    "Mahony filter is proven in Betaflight; tuning two gains "
                    "(Kp, Ki) simpler than full EKF."
                ),
                "alternatives": [
                    _alt(
                        "MPU-6050 on I²C at 400 kHz",
                        "I²C limiting at 400 kHz cannot service 8 kHz sample "
                        "rate; bus latency 40 µs unacceptable for 4 kHz loop — "
                        "rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Nyquist–Shannon Sampling Theorem' — sampling at "
                    "8 kHz satisfies Nyquist for rotor vibrations up to 4 kHz "
                    "(400 Hz blade-pass for 10000 RPM 4-blade prop).  "
                    "FACT: 'Kalman Filter for Sensor Fusion' provides the EKF "
                    "upgrade path with Q/R matrices."
                ),
                "supporting_fact_titles": [
                    "IMU (Inertial Measurement Unit) for Robot Navigation",
                    "Kalman Filter for Sensor Fusion",
                    "Nyquist–Shannon Sampling Theorem",
                ],
            },
            {
                "title": "Cascaded PID Flight Controller",
                "component_category": "control",
                "design_question": (
                    "What control topology achieves attitude hold and rate "
                    "control simultaneously?"
                ),
                "selected_approach": (
                    "Cascaded PID: outer attitude loop (50 Hz) generates "
                    "angular rate setpoints; inner rate loop (4 kHz) generates "
                    "motor mix outputs.  Motor mix: "
                    "M₁ = throttle + pitch − roll + yaw; "
                    "M₂ = throttle − pitch + roll + yaw; etc.  "
                    "Betaflight RPM filter removes motor harmonics from gyro "
                    "before D-term calculation."
                ),
                "rationale": (
                    "Cascaded loops separate attitude tracking (outer) from "
                    "disturbance rejection (inner rate loop).  Inner loop "
                    "must be ≥ 10× outer loop bandwidth: 4 kHz >> 50 Hz — "
                    "satisfied.  D-term on rate reduces oscillation."
                ),
                "alternatives": [
                    _alt(
                        "Single-loop PID on attitude only",
                        "Cannot achieve 20 Hz bandwidth — oscillation occurs "
                        "due to slow D-term acting on attitude angle rather "
                        "than rate.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'PID Controller — Transfer Function' confirms K_d "
                    "reduces overshoot; cascaded structure is standard for "
                    "multi-rotor attitude control."
                ),
                "supporting_fact_titles": [
                    "PID Controller — Transfer Function",
                ],
            },
            {
                "title": "Motor and ESC Selection",
                "component_category": "actuation",
                "design_question": (
                    "Which BLDC motor/ESC combination achieves 5-min flight "
                    "time with AUW 450 g?"
                ),
                "selected_approach": (
                    "4× Emax RS2306 2750 KV BLDC motors + 4× BLHeli-32 30A "
                    "ESCs.  Propellers: 5×4.5×3 (5 inch, 3-blade).  "
                    "Hover throttle 30% @ 4S 14.8 V; max thrust per motor "
                    "≈ 800 g → total 3200 g >> 450 g AUW (thrust-weight ratio "
                    "7:1)."
                ),
                "rationale": (
                    "KV × V = RPM_no-load → 2750 × 14.8 ≈ 40,000 RPM.  "
                    "Thrust at hover = AUW / 4 = 112 g/motor at ~15% max thrust "
                    "→ highly efficient operating point.  "
                    "FACT: 'BLDC Motor' confirms electronic commutation and "
                    "efficiency advantage over brushed."
                ),
                "alternatives": [
                    _alt(
                        "Coreless brushed motors (cheaper)",
                        "60–70% efficiency vs 85–95% for BLDC; shorter brush "
                        "life; cannot spin fast enough for 5-inch props — "
                        "rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Brushless DC (BLDC) Motor for Suction Fan' confirms "
                    "electronic commutation principle; same physics applies to "
                    "propulsion BLDC.  'Robot Runtime Estimation from Battery "
                    "Capacity': t = 22.2 Wh × 0.8 / (450×9.81×10⁻³ × "
                    "v_climb ÷ η) ≈ 5 min at moderate pace."
                ),
                "supporting_fact_titles": [
                    "Brushless DC (BLDC) Motor for Suction Fan",
                    "Robot Runtime Estimation from Battery Capacity",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 7 — Smart Access Control System
    # ====================================================================
    {
        "title": "RFID Smart Door Access Controller",
        "description": (
            "A wall-mounted access control unit using an RFID reader, ESP32 "
            "MCU, electric door strike, and OLED status display.  "
            "Authorised UIDs stored in flash; events logged to MQTT broker. "
            "OTA firmware updates via WiFi."
        ),
        "objective": (
            "Grant / deny access within 500 ms of card presentation; log all "
            "events with UTC timestamp; support ≥ 100 enrolled UIDs; "
            "fail-safe (locked) on power loss."
        ),
        "constraints": (
            "Powered from 12 V / 1 A supply; PoE option; "
            "IP54 flush-mount enclosure; GDPR-compliant logging (no biometrics)."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "RFID/NFC Reader — ISO 14443 / 15693 Interface",
            "N-Channel MOSFET as a Low-Side Power Switch",
            "MQTT Protocol for IoT Sensor Data",
            "OTA Firmware Update for Embedded Devices",
            "ESP32 WiFi + BLE System-on-Chip",
            "NTP Time Synchronisation for Data Logging",
        ],
        "designs": [
            {
                "title": "Card / Credential Technology",
                "component_category": "sensing",
                "design_question": (
                    "Which RFID standard provides adequate security for "
                    "an office access-control system?"
                ),
                "selected_approach": (
                    "MFRC522 reader + NTAG216 NFC tags (ISO 14443A, 888 byte "
                    "EEPROM, UID 7 bytes).  Reader connected via SPI at 10 MHz. "
                    "UID + timestamp MAC-signed with HMAC-SHA256 in firmware."
                ),
                "rationale": (
                    "NTAG216 has unique 7-byte UID (not clone-able at low cost) "
                    "and supports NDEF; HMAC prevents replay attacks even if "
                    "UID is observed.  Mifare Classic (CRYPTO1) is vulnerable "
                    "to cloning attacks documented since 2008 — rejected."
                ),
                "alternatives": [
                    _alt(
                        "Mifare Classic 1K",
                        "CRYPTO1 cipher broken (Garcia et al. 2008); UID "
                        "cloneable with £5 device; unacceptable for security "
                        "applications — rejected.",
                    ),
                    _alt(
                        "Fingerprint sensor (AS608)",
                        "Higher security but GDPR complexity for biometric "
                        "data storage; higher cost; user friction — rejected "
                        "for this application.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'RFID/NFC Reader — ISO 14443 / 15693 Interface' "
                    "explicitly warns about Mifare Classic CRYPTO1 weakness "
                    "and recommends NTAG216 or DESFire EV2 for access control."
                ),
                "supporting_fact_titles": [
                    "RFID/NFC Reader — ISO 14443 / 15693 Interface",
                    "I²C Serial Communication Protocol",
                ],
            },
            {
                "title": "Door Strike Actuation",
                "component_category": "actuation",
                "design_question": (
                    "How to drive a 12 V electric door strike from a 3.3 V GPIO "
                    "with fail-safe behaviour?"
                ),
                "selected_approach": (
                    "N-channel MOSFET (IRLZ44N) + flyback diode driving NC "
                    "(Normally Closed) electric strike.  MOSFET gate driven by "
                    "GPIO through 470 Ω resistor.  NC: strike locked when "
                    "MOSFET off (no power).  Energised 300 ms to allow passage. "
                    "12 V rail separate from logic 3.3 V."
                ),
                "rationale": (
                    "NC strike locks on power failure (fail-safe).  MOSFET low "
                    "R_DS(on) minimises heating at 0.5 A strike current. "
                    "300 ms pulse limits power dissipation."
                ),
                "alternatives": [
                    _alt(
                        "Relay for door strike switching",
                        "Relay coil (50 mA) adds load to logic supply; audible "
                        "click is informative but undesirable; MOSFET silent "
                        "and faster — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'N-Channel MOSFET as a Low-Side Power Switch' "
                    "confirms flyback diode requirement for NC solenoid load "
                    "and logic-level gate requirements."
                ),
                "supporting_fact_titles": [
                    "N-Channel MOSFET as a Low-Side Power Switch",
                ],
            },
            {
                "title": "Event Logging and OTA",
                "component_category": "communication",
                "design_question": (
                    "How to log access events with accurate timestamps and "
                    "keep firmware updatable remotely?"
                ),
                "selected_approach": (
                    "ESP32 publishes access events (UID, timestamp, ALLOW/DENY) "
                    "to MQTT broker (QoS 1 for guaranteed delivery). "
                    "NTP sync on boot and every 6 h for accurate UTC timestamps. "
                    "OTA updates via ESP-IDF HTTPS OTA; dual-bank flash; "
                    "rollback on first-boot watchdog failure."
                ),
                "rationale": (
                    "QoS 1 ensures events reach the broker even with brief "
                    "WiFi instability (retained in ESP32 buffer).  OTA critical "
                    "for security patches without physical access."
                ),
                "alternatives": [],
                "verification_notes": (
                    "FACT: 'NTP Time Synchronisation for Data Logging' confirms "
                    "SNTP accuracy < 50 ms — adequate for audit logs. "
                    "FACT: 'OTA Firmware Update for Embedded Devices' confirms "
                    "dual-bank + HMAC-signed image requirement."
                ),
                "supporting_fact_titles": [
                    "MQTT Protocol for IoT Sensor Data",
                    "NTP Time Synchronisation for Data Logging",
                    "OTA Firmware Update for Embedded Devices",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 8 — Portable Air Quality Monitor
    # ====================================================================
    {
        "title": "Portable Indoor Air Quality Monitor",
        "description": (
            "A handheld IoT device measuring CO₂, PM2.5, temperature, and "
            "relative humidity.  Results shown on a 0.96-inch OLED; logged to "
            "InfluxDB via MQTT over WiFi.  BLE for smartphone display. "
            "USB-C charged Li-Po battery."
        ),
        "objective": (
            "Measure CO₂ 400–5000 ppm (±50 ppm), PM2.5 0–500 µg/m³ (±10%), "
            "RH 0–100% (±2%), temperature −10–60 °C (±0.3 °C); "
            "battery life ≥ 8 h continuous."
        ),
        "constraints": (
            "Enclosure 120×60×25 mm; < £50; USB-C charged; "
            "3.3 V logic; no calibration required by user after factory setup."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "NDIR CO₂ Sensor — Non-Dispersive Infrared",
            "PM2.5 Optical Particle Counter",
            "Capacitive Relative Humidity Sensing",
            "NTC Thermistor Temperature Sensing",
            "ADC Resolution and Measurement Precision",
            "MQTT Protocol for IoT Sensor Data",
            "Bluetooth Low Energy (BLE) for App Control",
            "ESP32 WiFi + BLE System-on-Chip",
        ],
        "designs": [
            {
                "title": "CO₂ Sensing — NDIR vs Electrochemical",
                "component_category": "sensing",
                "design_question": (
                    "Which CO₂ sensing technology provides ±50 ppm accuracy "
                    "without frequent user recalibration?"
                ),
                "selected_approach": (
                    "Sensirion SCD41 NDIR CO₂ sensor (I²C, ±40 ppm accuracy, "
                    "ABC self-calibration).  Factory-calibrated; on-chip "
                    "temperature and pressure compensation."
                ),
                "rationale": (
                    "NDIR is a primary sensing technique (Beer-Lambert law) "
                    "with proven long-term stability (< 2% drift/year).  "
                    "SCD41 ABC algorithm auto-calibrates using fresh-air "
                    "reference — no user action.  Electrochemical CO₂ sensors "
                    "drift significantly and require monthly zero-span "
                    "calibration."
                ),
                "alternatives": [
                    _alt(
                        "MQ-135 electrochemical / metal-oxide gas sensor",
                        "Sensitive to multiple gases (NH₃, benzene, CO₂); "
                        "heavy cross-sensitivity; requires weeks of burn-in; "
                        "not selective for CO₂ — rejected.",
                    ),
                    _alt(
                        "MH-Z19B NDIR (lower cost)",
                        "Acceptable accuracy but larger (35×33×9 mm) and no "
                        "on-chip RH compensation; SCD41 integrates temp+RH "
                        "on same die for better accuracy.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'NDIR CO₂ Sensor — Non-Dispersive Infrared' "
                    "confirms Beer-Lambert principle, ±50 ppm typical accuracy, "
                    "and ABC baseline correction mechanism."
                ),
                "supporting_fact_titles": [
                    "NDIR CO₂ Sensor — Non-Dispersive Infrared",
                    "I²C Serial Communication Protocol",
                ],
            },
            {
                "title": "Particulate Matter Sensing",
                "component_category": "sensing",
                "design_question": (
                    "How to measure PM2.5 and PM10 without a bulky fan-driven "
                    "optical bench?"
                ),
                "selected_approach": (
                    "Sensirion SPS30 optical PM sensor (UART/I²C, 5×5×7.5 cm, "
                    "built-in fan and laser, PM1/PM2.5/PM4/PM10 in µg/m³).  "
                    "Auto-cleaning fan cycle every 168 h prevents dust "
                    "accumulation on optics."
                ),
                "rationale": (
                    "SPS30 is self-contained and factory-calibrated; "
                    "auto-cleaning extends service life to 8 years.  "
                    "PLANTOWER PMS5003 is cheaper but larger and no auto-clean."
                ),
                "alternatives": [
                    _alt(
                        "Sharp GP2Y1010AU0F (optical dust sensor, £2)",
                        "Single-photodiode, no size classification — gives "
                        "total dust count only, not PM2.5/PM10 fractions; "
                        "accuracy ±30% vs SPS30 ±10% — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'PM2.5 Optical Particle Counter' confirms Mie "
                    "scattering principle and humidity cross-sensitivity above "
                    "75% RH — noted in datasheet; RH reading from SCD41 "
                    "provides correction flag."
                ),
                "supporting_fact_titles": [
                    "PM2.5 Optical Particle Counter",
                ],
            },
            {
                "title": "Power Budget and Battery Sizing",
                "component_category": "power",
                "design_question": (
                    "What battery capacity is needed for 8 h continuous operation?"
                ),
                "selected_approach": (
                    "Power budget: ESP32 (active WiFi avg) 80 mA, SCD41 19 mA, "
                    "SPS30 55 mA, OLED 20 mA, total ≈ 174 mA @ 3.3 V = 574 mW. "
                    "Battery: 3.7 V 2000 mAh LiPo → 7.4 Wh; usable 80% = "
                    "5.92 Wh; runtime = 5.92 / 0.574 ≈ 10.3 h — meets 8 h spec."
                ),
                "rationale": (
                    "2000 mAh is available in standard 103450 format fitting "
                    "the 120×60×25 mm enclosure.  Runtime margin of 2.3 h "
                    "accounts for battery aging and BLE overhead."
                ),
                "alternatives": [],
                "verification_notes": (
                    "FACT: 'Robot Runtime Estimation from Battery Capacity': "
                    "t = C × V × DoD / P = 2.0 × 3.7 × 0.8 / 0.574 ≈ 10.3 h. "
                    "Consistent with target."
                ),
                "supporting_fact_titles": [
                    "Li-Ion Battery Capacity and Energy Calculation",
                    "Robot Runtime Estimation from Battery Capacity",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 9 — Automated Greenhouse Controller
    # ====================================================================
    {
        "title": "Automated Greenhouse Climate Controller",
        "description": (
            "A multi-zone embedded controller managing temperature, humidity, "
            "CO₂, soil moisture, and lighting for a 6×3 m hobby greenhouse. "
            "Actuates ventilation fans, irrigation solenoids, heating mats, "
            "and supplemental LED grow lights.  Data logged to InfluxDB + "
            "Grafana dashboard over WiFi."
        ),
        "objective": (
            "Maintain temperature 18–26 °C (±1 °C), RH 60–80% (±5%), "
            "CO₂ 800–1200 ppm, soil VWC 30–60%.  Automated irrigation "
            "and ventilation schedules override by manual dashboard."
        ),
        "constraints": (
            "Mains-powered (230 V / 13 A circuit breaker); "
            "safety interlock on heating; ≤ 4 sensor zones; "
            "data retention ≥ 30 days locally."
        ),
        "domain": "systems",
        "status": "completed",
        "supporting_fact_titles": [
            "Capacitive Soil Moisture Sensing",
            "NTC Thermistor Temperature Sensing",
            "Capacitive Relative Humidity Sensing",
            "NDIR CO₂ Sensor — Non-Dispersive Infrared",
            "N-Channel MOSFET as a Low-Side Power Switch",
            "MQTT Protocol for IoT Sensor Data",
            "ESP32 WiFi + BLE System-on-Chip",
            "Solar Panel Sizing for Remote IoT Stations",
        ],
        "designs": [
            {
                "title": "Multi-Sensor Zone Architecture",
                "component_category": "sensing",
                "design_question": (
                    "How to cost-effectively instrument 4 zones with "
                    "temperature, RH, soil moisture, and CO₂?"
                ),
                "selected_approach": (
                    "Per-zone: SHT41 (temp + RH, I²C) + capacitive soil "
                    "moisture probe (ADC).  One shared SCD41 CO₂ sensor "
                    "in the central zone (CO₂ is well-mixed in a small "
                    "greenhouse).  All I²C devices on TCA9548A multiplexer "
                    "(8 channels) to resolve address conflicts.  4-zone "
                    "scanning at 1-min intervals."
                ),
                "rationale": (
                    "SHT41 includes factory NIST-traceable calibration — "
                    "no field calibration needed.  I²C multiplexer allows "
                    "4 identical SHT41 (all address 0x44) on one bus. "
                    "Single CO₂ sensor saves £30 vs 4 sensors with <5% "
                    "spatial variation in a mixed-air space."
                ),
                "alternatives": [
                    _alt(
                        "DHT22 temperature/humidity sensors",
                        "1-wire protocol requires precise timing; no factory "
                        "calibration; ±0.5 °C accuracy vs SHT41 ±0.2 °C; "
                        "SHT41 preferred for accuracy.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'I²C Serial Communication Protocol' confirms "
                    "TCA9548A address multiplexing pattern.  "
                    "FACT: 'Capacitive Relative Humidity Sensing' confirms "
                    "SHT41 performance and I²C interface.  "
                    "FACT: 'NDIR CO₂ Sensor' confirms SCD41 ABC operation "
                    "and I²C interface."
                ),
                "supporting_fact_titles": [
                    "Capacitive Relative Humidity Sensing",
                    "Capacitive Soil Moisture Sensing",
                    "NDIR CO₂ Sensor — Non-Dispersive Infrared",
                    "I²C Serial Communication Protocol",
                ],
            },
            {
                "title": "Mains Actuator Control (Fans, Heating, Lights)",
                "component_category": "actuation",
                "design_question": (
                    "How to switch 230 V AC loads (fan, heater, LED driver) "
                    "safely from an ESP32 GPIO?"
                ),
                "selected_approach": (
                    "Solid-State Relays (SSRs, e.g., Fotek SSR-40DA) for each "
                    "mains load.  DC control input 3–32 V (3.3 V compatible); "
                    "zero-crossing switching reduces EMI.  Each SSR on a "
                    "separate GPIO.  Thermal fuse on heater mat as secondary "
                    "safety interlock."
                ),
                "rationale": (
                    "SSR: no moving parts, silent, fast switching (< 10 ms), "
                    "zero-crossing reduces capacitive transients.  "
                    "Separate fuse on heater prevents fire if software fails. "
                    "MOSFETs not used directly for mains loads — requires "
                    "isolated gate drive."
                ),
                "alternatives": [
                    _alt(
                        "Mechanical relay module",
                        "Relay click audible; contacts degrade with switching "
                        "cycles (rated ~100,000); SSR rated 500,000+ cycles — "
                        "preferred for 10 actuations/hour × 8760 h/year.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'N-Channel MOSFET as a Low-Side Power Switch' "
                    "applies to DC loads; for 230 V AC mains SSR with opto-"
                    "isolation is the safe standard approach."
                ),
                "supporting_fact_titles": [
                    "N-Channel MOSFET as a Low-Side Power Switch",
                ],
            },
        ],
    },

    # ====================================================================
    # PROJECT 10 — Non-Invasive Smart Energy Meter
    # ====================================================================
    {
        "title": "Non-Invasive Smart Energy Meter",
        "description": (
            "A clamp-on energy monitor that attaches to a 230 V AC single-"
            "phase supply cable without any wiring modification.  Measures "
            "real power (W), apparent power (VA), power factor, and cumulative "
            "energy (kWh).  Publishes data to MQTT and displays on a small "
            "OLED.  Powered from a USB-C 5 V adapter."
        ),
        "objective": (
            "Measure real power to ±2% accuracy; energy accumulation error "
            "< 1% over 24 h; 1-second update rate; 1-year data history on "
            "external microSD."
        ),
        "constraints": (
            "No direct mains connection (CT clamp only); "
            "5 V USB-C powered; enclosure ≤ 120×80×35 mm; "
            "cost ≤ £35."
        ),
        "domain": "electrical",
        "status": "completed",
        "supporting_fact_titles": [
            "CT Clamp Current Sensing and RMS Calculation",
            "ADC Resolution and Measurement Precision",
            "Ohm's Law",
            "Kirchhoff's Voltage Law (KVL)",
            "ESP32 WiFi + BLE System-on-Chip",
            "MQTT Protocol for IoT Sensor Data",
            "NTP Time Synchronisation for Data Logging",
        ],
        "designs": [
            {
                "title": "Current Measurement — CT Clamp",
                "component_category": "sensing",
                "design_question": (
                    "How to measure 0–100 A AC current non-invasively with "
                    "< 0.5% gain error?"
                ),
                "selected_approach": (
                    "SCT-013-100 split-core CT (100 A : 50 mA, turns ratio "
                    "N = 2000).  Burden resistor R_b = 33 Ω → peak output "
                    "V_peak = (100/2000) × 33 × √2 = 2.33 V.  "
                    "AC signal biased to mid-supply (1.65 V) using voltage "
                    "divider.  Sampled at 4800 Hz (80 samples / 60 Hz cycle) "
                    "by ESP32 ADC (12-bit, 3.3 V full-scale)."
                ),
                "rationale": (
                    "SCT-013 is accurate ±1% over 10–120% rated current.  "
                    "33 Ω burden keeps secondary terminal voltage < 3.3 V "
                    "(safe for ESP32 ADC).  4800 Hz ≫ 2 × 60 Hz Nyquist — "
                    "captures 40 harmonics for true RMS computation.  "
                    "CT must never be open-circuited under load."
                ),
                "alternatives": [
                    _alt(
                        "ACS712 Hall-effect current sensor (inline)",
                        "Requires cutting the monitored wire; sensor IC in "
                        "series with mains — defeats non-invasive objective — "
                        "rejected.",
                    ),
                    _alt(
                        "Shunt resistor (0.001 Ω inline)",
                        "Requires mains-side connection and isolated ADC; "
                        "safety risk; CT is inherently isolated — rejected.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'CT Clamp Current Sensing and RMS Calculation' "
                    "confirms SCT-013-000/100 parameters, burden resistor "
                    "formula, and safety warning on open-circuit secondary. "
                    "FACT: 'ADC Resolution and Measurement Precision' confirms "
                    "12-bit @ 3.3 V = 0.8 mV/LSB — current resolution "
                    "= 0.8 mV / 33 Ω × 2000 = 0.048 A — adequate for 100 A "
                    "range at ±0.05% resolution."
                ),
                "supporting_fact_titles": [
                    "CT Clamp Current Sensing and RMS Calculation",
                    "ADC Resolution and Measurement Precision",
                    "Nyquist–Shannon Sampling Theorem",
                ],
            },
            {
                "title": "Voltage Sensing and Power Factor",
                "component_category": "sensing",
                "design_question": (
                    "How to measure mains voltage safely for real-power "
                    "(not just apparent power) calculation?"
                ),
                "selected_approach": (
                    "Resistive voltage divider transformer: 9 V AC plug-in "
                    "wall-wart provides proportional mains voltage reference "
                    "(9/230 = 1:25.6 ratio); biased to 1.65 V mid-rail. "
                    "Phase-corrected in software for CT phase delay (≈ 3°). "
                    "Real power: P = (1/N) · Σ(v_n · i_n)."
                ),
                "rationale": (
                    "9 V wall-wart is fully isolated from mains — no user "
                    "shock risk.  Proportional waveform preserves voltage "
                    "waveform shape for phase/THD analysis.  "
                    "KVL: voltage across load = supply − cable drop; "
                    "measuring at service entrance is conservative."
                ),
                "alternatives": [
                    _alt(
                        "Direct resistive divider from live/neutral",
                        "Mains potential on PCB — requires certified isolation "
                        "and creepage distances; unacceptable for DIY device — "
                        "rejected on safety grounds.",
                    ),
                ],
                "verification_notes": (
                    "FACT: 'Ohm's Law' — voltage divider: V_out = V_in × "
                    "R₂/(R₁+R₂).  FACT: 'Kirchhoff's Voltage Law (KVL)' — "
                    "confirms loop voltage analysis for the divider circuit."
                ),
                "supporting_fact_titles": [
                    "Ohm's Law",
                    "Kirchhoff's Voltage Law (KVL)",
                    "CT Clamp Current Sensing and RMS Calculation",
                ],
            },
            {
                "title": "Data Logging and Connectivity",
                "component_category": "communication",
                "design_question": (
                    "How to store 1 year of 1-second energy data and report "
                    "in real-time?"
                ),
                "selected_approach": (
                    "ESP32 with SPI microSD (32 GB) logs raw CSV at 1 Hz → "
                    "~2 GB/year.  Summary (1-min averages) published to MQTT. "
                    "NTP keeps timestamps accurate to < 50 ms.  "
                    "Grafana/InfluxDB for time-series visualisation."
                ),
                "rationale": (
                    "MicroSD provides local storage without network dependency; "
                    "MQTT provides live streaming.  1-min MQTT messages at "
                    "~100 bytes = 52 MB/year — manageable bandwidth."
                ),
                "alternatives": [],
                "verification_notes": (
                    "FACT: 'NTP Time Synchronisation for Data Logging' "
                    "confirms < 50 ms accuracy for energy audit timestamps. "
                    "FACT: 'MQTT Protocol for IoT Sensor Data' confirms "
                    "fire-and-forget QoS 0 adequate for non-critical metrics."
                ),
                "supporting_fact_titles": [
                    "MQTT Protocol for IoT Sensor Data",
                    "NTP Time Synchronisation for Data Logging",
                    "ESP32 WiFi + BLE System-on-Chip",
                ],
            },
        ],
    },
]
