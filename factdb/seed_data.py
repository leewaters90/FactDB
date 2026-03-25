"""
Seed data — curated engineering facts for FactDB.

Each fact includes varying levels of detail (fundamental → expert) and
is tagged to support efficient retrieval by AI planners.
"""

from __future__ import annotations

ENGINEERING_FACTS: list[dict] = [
    # ----------------------------------------------------------------
    # MECHANICAL — Thermodynamics
    # ----------------------------------------------------------------
    {
        "title": "First Law of Thermodynamics",
        "domain": "mechanical",
        "category": "thermodynamics",
        "subcategory": "energy conservation",
        "detail_level": "fundamental",
        "content": (
            "Energy cannot be created or destroyed; it can only be converted "
            "from one form to another.  For a closed system: ΔU = Q − W."
        ),
        "extended_content": (
            "The internal energy change (ΔU) of a system equals the heat added "
            "(Q) minus the work done by the system (W).  In differential form: "
            "dU = δQ − δW.  For a flow process the steady-flow energy equation "
            "adds enthalpy, kinetic energy, and potential energy terms."
        ),
        "formula": "ΔU = Q − W",
        "units": "Joules (J)",
        "source": "Cengel & Boles, Thermodynamics: An Engineering Approach, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["thermodynamics", "energy", "fundamental-law", "mechanical"],
    },
    {
        "title": "Second Law of Thermodynamics — Entropy",
        "domain": "mechanical",
        "category": "thermodynamics",
        "subcategory": "entropy",
        "detail_level": "fundamental",
        "content": (
            "The total entropy of an isolated system can only increase over "
            "time or remain constant in ideal (reversible) processes."
        ),
        "extended_content": (
            "Entropy (S) is a measure of disorder or unavailable energy.  For "
            "any real process the entropy generation is non-negative: "
            "dS_total ≥ 0.  The Clausius inequality states: ∮ δQ/T ≤ 0 for a "
            "cycle.  Practical consequence: heat engines cannot achieve 100% "
            "efficiency."
        ),
        "formula": "dS ≥ δQ / T",
        "units": "J/K",
        "source": "Cengel & Boles, Thermodynamics: An Engineering Approach, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["thermodynamics", "entropy", "fundamental-law", "mechanical"],
    },
    {
        "title": "Carnot Efficiency",
        "domain": "mechanical",
        "category": "thermodynamics",
        "subcategory": "heat engines",
        "detail_level": "intermediate",
        "content": (
            "The maximum thermal efficiency of any heat engine operating "
            "between two temperature reservoirs is the Carnot efficiency: "
            "η_max = 1 − T_L / T_H."
        ),
        "extended_content": (
            "T_H is the absolute temperature of the hot reservoir and T_L is "
            "the absolute temperature of the cold reservoir (both in Kelvin). "
            "No real engine can exceed this limit; practical engines are further "
            "limited by irreversibilities such as friction, heat transfer across "
            "finite temperature differences, and internal leakage."
        ),
        "formula": "η_Carnot = 1 − T_L / T_H",
        "units": "dimensionless (0–1)",
        "source": "Cengel & Boles, Thermodynamics: An Engineering Approach, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["thermodynamics", "heat-engine", "efficiency", "mechanical"],
    },
    # ----------------------------------------------------------------
    # MECHANICAL — Mechanics of Materials
    # ----------------------------------------------------------------
    {
        "title": "Hooke's Law — Linear Elasticity",
        "domain": "mechanical",
        "category": "mechanics of materials",
        "subcategory": "stress-strain",
        "detail_level": "fundamental",
        "content": (
            "Within the elastic limit, stress is proportional to strain: "
            "σ = E·ε, where E is Young's modulus."
        ),
        "extended_content": (
            "Young's modulus (E) is a material constant representing stiffness. "
            "Steel: ~200 GPa; Aluminium: ~70 GPa; Concrete: ~30 GPa.  "
            "Hooke's Law holds only in the linear elastic region; beyond the "
            "yield strength, permanent (plastic) deformation occurs."
        ),
        "formula": "σ = E · ε",
        "units": "σ: Pa, E: Pa, ε: dimensionless",
        "source": "Beer & Johnston, Mechanics of Materials, 7th ed.",
        "confidence_score": 1.0,
        "tags": ["stress", "strain", "elasticity", "mechanical", "materials"],
    },
    {
        "title": "Factor of Safety",
        "domain": "mechanical",
        "category": "mechanics of materials",
        "subcategory": "design",
        "detail_level": "fundamental",
        "content": (
            "The factor of safety (FoS) is the ratio of the material's failure "
            "strength to the maximum expected applied stress: FoS = S_f / σ."
        ),
        "extended_content": (
            "A FoS > 1 provides a margin against unexpected overloads, material "
            "variability, and modelling errors.  Typical values: structural "
            "steel 1.5–4, pressure vessels 3–5, aerospace 1.2–1.5 (weight-critical).  "
            "A FoS that is too high wastes material and increases cost/weight."
        ),
        "formula": "FoS = S_failure / σ_applied",
        "units": "dimensionless",
        "source": "Shigley's Mechanical Engineering Design, 10th ed.",
        "confidence_score": 1.0,
        "tags": ["safety", "design", "stress", "mechanical"],
    },
    # ----------------------------------------------------------------
    # ELECTRICAL — Circuit Theory
    # ----------------------------------------------------------------
    {
        "title": "Ohm's Law",
        "domain": "electrical",
        "category": "circuit theory",
        "subcategory": "DC circuits",
        "detail_level": "fundamental",
        "content": (
            "The current through a conductor is directly proportional to the "
            "voltage across it and inversely proportional to its resistance: "
            "V = I · R."
        ),
        "extended_content": (
            "Ohm's Law applies to linear, resistive, and time-invariant elements "
            "at constant temperature.  It forms the basis for DC circuit analysis "
            "and is used alongside Kirchhoff's laws for complex networks."
        ),
        "formula": "V = I · R",
        "units": "V: Volts, I: Amperes, R: Ohms (Ω)",
        "source": "Hayt & Kemmerly, Engineering Circuit Analysis, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["circuit", "voltage", "current", "resistance", "electrical"],
    },
    {
        "title": "Kirchhoff's Voltage Law (KVL)",
        "domain": "electrical",
        "category": "circuit theory",
        "subcategory": "network analysis",
        "detail_level": "fundamental",
        "content": (
            "The algebraic sum of all voltages around any closed loop in a "
            "circuit is zero: Σ V_k = 0."
        ),
        "extended_content": (
            "KVL is a consequence of conservation of energy.  Sign convention: "
            "voltage drops are positive, voltage rises are negative (or vice-"
            "versa, as long as consistent).  Together with KCL it enables nodal "
            "and mesh analysis of any planar circuit."
        ),
        "formula": "∑ V_k = 0  (around a closed loop)",
        "units": "Volts (V)",
        "source": "Hayt & Kemmerly, Engineering Circuit Analysis, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["circuit", "voltage", "kirchhoff", "electrical"],
    },
    {
        "title": "Kirchhoff's Current Law (KCL)",
        "domain": "electrical",
        "category": "circuit theory",
        "subcategory": "network analysis",
        "detail_level": "fundamental",
        "content": (
            "The algebraic sum of currents entering a node equals the sum of "
            "currents leaving that node: Σ I_in = Σ I_out."
        ),
        "extended_content": (
            "KCL is a statement of conservation of charge.  It holds at every "
            "node (junction) in a circuit and is the basis of nodal analysis."
        ),
        "formula": "∑ I_in = ∑ I_out  (at a node)",
        "units": "Amperes (A)",
        "source": "Hayt & Kemmerly, Engineering Circuit Analysis, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["circuit", "current", "kirchhoff", "electrical"],
    },
    # ----------------------------------------------------------------
    # CIVIL — Structural
    # ----------------------------------------------------------------
    {
        "title": "Euler's Column Buckling Formula",
        "domain": "civil",
        "category": "structural engineering",
        "subcategory": "column buckling",
        "detail_level": "intermediate",
        "content": (
            "The critical axial load at which a slender column buckles "
            "elastically is P_cr = π²·E·I / (K·L)², where K is the effective-"
            "length factor."
        ),
        "extended_content": (
            "E is Young's modulus, I is the second moment of area about the "
            "weak axis, L is the unsupported length, and K depends on end "
            "conditions (K=1 for pin-pin, K=0.5 for fixed-fixed, K=2 for "
            "fixed-free cantilever).  Valid only in the elastic (Euler) range; "
            "use Johnson's formula for stocky columns."
        ),
        "formula": "P_cr = π² E I / (K L)²",
        "units": "N",
        "source": "Gere & Goodno, Mechanics of Materials, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["buckling", "columns", "structural", "civil", "compression"],
    },
    {
        "title": "Beam Bending — Flexure Formula",
        "domain": "civil",
        "category": "structural engineering",
        "subcategory": "beam theory",
        "detail_level": "intermediate",
        "content": (
            "The bending stress in a beam at distance y from the neutral axis "
            "is σ = M·y / I."
        ),
        "extended_content": (
            "M is the applied bending moment, y is the distance from the neutral "
            "axis, and I is the second moment of area.  Maximum stress occurs at "
            "the extreme fibres (y = c).  The section modulus Z = I/c simplifies "
            "design: σ_max = M / Z."
        ),
        "formula": "σ = M · y / I",
        "units": "σ: Pa, M: N·m, y: m, I: m⁴",
        "source": "Gere & Goodno, Mechanics of Materials, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["bending", "beam", "structural", "civil", "stress"],
    },
    # ----------------------------------------------------------------
    # SOFTWARE — Algorithms & Complexity
    # ----------------------------------------------------------------
    {
        "title": "Big-O Notation — Time Complexity",
        "domain": "software",
        "category": "algorithms",
        "subcategory": "complexity analysis",
        "detail_level": "fundamental",
        "content": (
            "Big-O notation O(f(n)) describes the asymptotic upper bound on the "
            "growth rate of an algorithm's resource usage as input size n → ∞."
        ),
        "extended_content": (
            "Common classes (best to worst): O(1) constant, O(log n) logarithmic, "
            "O(n) linear, O(n log n) linearithmic, O(n²) quadratic, O(2ⁿ) exponential. "
            "Use Big-Ω for lower bounds and Big-Θ for tight bounds."
        ),
        "formula": "f(n) = O(g(n)) iff ∃ c,n₀ : f(n) ≤ c·g(n) ∀ n ≥ n₀",
        "source": "Cormen et al., Introduction to Algorithms, 4th ed.",
        "confidence_score": 1.0,
        "tags": ["algorithm", "complexity", "software", "performance"],
    },
    {
        "title": "Amdahl's Law — Parallel Speedup",
        "domain": "software",
        "category": "parallel computing",
        "subcategory": "scalability",
        "detail_level": "intermediate",
        "content": (
            "The maximum theoretical speedup of a program using P processors "
            "is S = 1 / ((1 − p) + p/P), where p is the parallelisable fraction."
        ),
        "extended_content": (
            "As P → ∞, speedup converges to 1/(1−p).  A program that is 90% "
            "parallel can never exceed 10× speedup regardless of the number of "
            "processors.  Gustafson's Law provides a more optimistic view when "
            "problem size scales with processor count."
        ),
        "formula": "S(P) = 1 / ((1 − p) + p / P)",
        "units": "dimensionless",
        "source": "Amdahl, G. (1967). Validity of the single processor approach.",
        "confidence_score": 1.0,
        "tags": ["parallel", "performance", "scalability", "software"],
    },
    # ----------------------------------------------------------------
    # SYSTEMS — Control Theory
    # ----------------------------------------------------------------
    {
        "title": "PID Controller — Transfer Function",
        "domain": "systems",
        "category": "control theory",
        "subcategory": "feedback control",
        "detail_level": "intermediate",
        "content": (
            "A PID controller output is u(t) = K_p·e + K_i·∫e dt + K_d·de/dt, "
            "combining proportional, integral, and derivative actions on the "
            "error signal e(t)."
        ),
        "extended_content": (
            "K_p reduces rise time; K_i eliminates steady-state error; K_d "
            "reduces overshoot and improves stability.  In the Laplace domain: "
            "C(s) = K_p + K_i/s + K_d·s.  Tuning methods include Ziegler-Nichols, "
            "Cohen-Coon, and model-based (IMC) approaches."
        ),
        "formula": "u(t) = K_p·e(t) + K_i·∫e(t)dt + K_d·(de/dt)",
        "source": "Ogata, Modern Control Engineering, 5th ed.",
        "confidence_score": 1.0,
        "tags": ["control", "PID", "feedback", "systems"],
    },
    {
        "title": "Nyquist Sampling Theorem",
        "domain": "systems",
        "category": "signal processing",
        "subcategory": "sampling",
        "detail_level": "intermediate",
        "content": (
            "A continuous signal must be sampled at a rate at least twice its "
            "highest frequency component to be perfectly reconstructed: "
            "f_s ≥ 2·f_max."
        ),
        "extended_content": (
            "Sampling below the Nyquist rate causes aliasing — high-frequency "
            "components fold back and corrupt lower-frequency content.  "
            "Anti-aliasing low-pass filters are applied before sampling to "
            "remove frequencies above f_s / 2 (the Nyquist frequency)."
        ),
        "formula": "f_s ≥ 2 · f_max",
        "units": "Hz",
        "source": "Oppenheim & Schafer, Discrete-Time Signal Processing, 3rd ed.",
        "confidence_score": 1.0,
        "tags": ["signal-processing", "sampling", "systems", "frequency"],
    },
    # ----------------------------------------------------------------
    # MATERIALS
    # ----------------------------------------------------------------
    {
        "title": "Ashby Material Selection — Property Charts",
        "domain": "materials",
        "category": "material selection",
        "subcategory": "performance indices",
        "detail_level": "advanced",
        "content": (
            "Material performance indices (e.g. E/ρ for stiffness-limited "
            "beams) allow objective comparison of materials on Ashby charts "
            "by plotting relevant properties on logarithmic axes."
        ),
        "extended_content": (
            "Common indices: E^(1/2)/ρ (minimum weight beam, stiffness-limited), "
            "σ_y/ρ (minimum weight, strength-limited), K_Ic/σ_y (fracture "
            "toughness / yield strength for damage tolerance).  "
            "Constraint lines on log-log axes separate feasible materials."
        ),
        "source": "Ashby, Materials Selection in Mechanical Design, 5th ed.",
        "confidence_score": 1.0,
        "tags": ["materials", "selection", "ashby", "design", "weight"],
    },
    # ----------------------------------------------------------------
    # AEROSPACE
    # ----------------------------------------------------------------
    {
        "title": "Tsiolkovsky Rocket Equation",
        "domain": "aerospace",
        "category": "propulsion",
        "subcategory": "rocket dynamics",
        "detail_level": "intermediate",
        "content": (
            "The ideal delta-v of a rocket is Δv = v_e · ln(m_0 / m_f), where "
            "v_e is the effective exhaust velocity and m_0/m_f is the mass ratio."
        ),
        "extended_content": (
            "v_e = I_sp · g_0 where I_sp is specific impulse (s) and g_0 = 9.81 m/s².  "
            "The equation quantifies the trade-off between propellant fraction "
            "and delta-v capability.  Staging allows higher total Δv by discarding "
            "empty tankage."
        ),
        "formula": "Δv = v_e · ln(m₀ / m_f)",
        "units": "m/s",
        "source": "Sutton, Rocket Propulsion Elements, 9th ed.",
        "confidence_score": 1.0,
        "tags": ["propulsion", "rocket", "aerospace", "delta-v"],
    },
    # ----------------------------------------------------------------
    # CHEMICAL
    # ----------------------------------------------------------------
    {
        "title": "Ideal Gas Law",
        "domain": "chemical",
        "category": "thermodynamics",
        "subcategory": "gas laws",
        "detail_level": "fundamental",
        "content": (
            "The pressure, volume, temperature, and amount of an ideal gas are "
            "related by PV = nRT."
        ),
        "extended_content": (
            "P: absolute pressure (Pa), V: volume (m³), n: moles (mol), "
            "R: universal gas constant (8.314 J/mol·K), T: absolute temperature (K).  "
            "For real gases, use van der Waals or Peng-Robinson equations of state."
        ),
        "formula": "PV = nRT",
        "units": "P: Pa, V: m³, T: K, n: mol",
        "source": "Smith, Van Ness & Abbott, Introduction to Chemical Engineering Thermodynamics, 8th ed.",
        "confidence_score": 1.0,
        "tags": ["gas", "thermodynamics", "chemical", "fundamental-law"],
    },
]


# Relationships to seed between facts (by title)
FACT_RELATIONSHIPS: list[dict] = [
    {
        "source_title": "Second Law of Thermodynamics — Entropy",
        "target_title": "First Law of Thermodynamics",
        "relationship_type": "depends_on",
        "weight": 0.9,
        "description": "The Second Law builds on the framework introduced by the First Law.",
    },
    {
        "source_title": "Carnot Efficiency",
        "target_title": "Second Law of Thermodynamics — Entropy",
        "relationship_type": "derived_from",
        "weight": 1.0,
        "description": "Carnot efficiency is a direct consequence of the Second Law.",
    },
    {
        "source_title": "Carnot Efficiency",
        "target_title": "First Law of Thermodynamics",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "Energy balance (1st Law) is needed alongside entropy (2nd Law).",
    },
    {
        "source_title": "Hooke's Law — Linear Elasticity",
        "target_title": "Factor of Safety",
        "relationship_type": "supports",
        "weight": 0.9,
        "description": "Knowing the elastic stress-strain relation enables FoS calculations.",
    },
    {
        "source_title": "Hooke's Law — Linear Elasticity",
        "target_title": "Beam Bending — Flexure Formula",
        "relationship_type": "prerequisite",
        "weight": 1.0,
        "description": "Flexure formula assumes linear elastic material behaviour.",
    },
    {
        "source_title": "Beam Bending — Flexure Formula",
        "target_title": "Euler's Column Buckling Formula",
        "relationship_type": "supports",
        "weight": 0.7,
        "description": "Understanding bending stresses supports column stability analysis.",
    },
    {
        "source_title": "Kirchhoff's Voltage Law (KVL)",
        "target_title": "Ohm's Law",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "KVL circuit analysis uses Ohm's Law for resistive voltage drops.",
    },
    {
        "source_title": "Kirchhoff's Current Law (KCL)",
        "target_title": "Ohm's Law",
        "relationship_type": "depends_on",
        "weight": 0.8,
        "description": "Nodal analysis combines KCL with Ohm's Law.",
    },
    {
        "source_title": "PID Controller — Transfer Function",
        "target_title": "Nyquist Sampling Theorem",
        "relationship_type": "depends_on",
        "weight": 0.7,
        "description": "Digital PID implementation must respect the Nyquist sampling criterion.",
    },
]
