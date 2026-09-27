# NASA C-MAPSS FD001 Data Dictionary

**Document Classification**: FDE Data Foundations — Technical Data Dictionary  
**Target Domain**: Turbofan Jet Engine Prognostics & Health Management (PHM)  
**Primary Sub-dataset**: NASA C-MAPSS Sub-dataset FD001 (100 Training Engines, 20,631 Operational Cycles)  
**Reference Document**: Saxena et al., *"Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation"*, PHM 2008.

---

## 1. Overview & Data Architecture

The NASA C-MAPSS (Commercial Modular Aero-Propulsion System Simulation) sub-dataset FD001 captures simulated run-to-failure telemetry for a fleet of commercial turbofan engines in the 90,000 lb thrust class. 

The dataset is recorded at a discrete temporal grain:
$$\text{Data Grain} = (\text{unit\_number},\; \text{time\_in\_cycles})$$

Every row represents an instantaneous steady-state snapshot of 3 operational settings and 21 gas-path sensor measurements recorded during the cruise phase of one operational flight cycle.

### 1.1 Field Summary & Analytical Grain Reference

| Field | Meaning | Grain | Used for |
|---|---|:---:|---|
| **`unit_number`** | Engine identifier | Engine | Grouping, entity identity, fleet partitioning |
| **`time_in_cycles`** | Operational flight cycle count | Engine-cycle | Temporal ordering, sequence continuity validation |
| **`op_setting_1..3`** | Operational settings (Altitude, Mach, TRA) | Engine-cycle | Boundary operating context, regime verification |
| **`sensor_1..21`** | Continuous gas-path sensor telemetry | Engine-cycle | Degradation tracking, variance & correlation analysis |
| **`true_rul` / `RUL`** | Remaining useful life until simulated failure | Engine-cycle / test endpoint | Lifecycle analysis, late-life volume segmentation |

---

## 2. Core Entity Identifiers & Temporal Coordinates

| Field Name (Pipeline) | Raw Column Index | Documented Name | Meaning | Engineering Units | Analytical Grain | Governance Status | Used For |
|---|:---:|---|---|:---:|:---:|:---:|---|
| **`engine_id`** | `0` | `unit_number` | Unique numeric identifier for the aircraft engine | Integer ($1 \dots 100$) | Engine | `FACT` | Fleet partitioning, grouping, within-unit longitudinal aggregation |
| **`cycle`** | `1` | `time_in_cycles` | Elapsed operational flight cycle counter | Integer ($1 \dots C_{\max}$) | Engine-Cycle | `FACT` | Temporal ordering, sequence continuity validation, trajectory timeline |

---

## 3. Operational Setting Variables

Sub-dataset FD001 simulates flight exclusively under a **single nominal operating condition** (Sea-Level Static/Cruise):

| Field Name (Pipeline) | Raw Column Index | Documented Name | Meaning | Engineering Units | Observed Range (FD001) | Governance Status | Operational Role |
|---|:---:|---|---|:---:|:---:|:---:|---|
| **`op_setting_1`** | `2` | `setting_1` | Flight Altitude | $10^3\text{ ft}$ (kft) | $[-0.0087, +0.0087]$ | `OBSERVATIONAL` | Ambient boundary condition; sea-level nominal variation ($\approx 0\text{ kft}$) |
| **`op_setting_2`** | `3` | `setting_2` | Flight Mach Number | Mach | $[-0.0006, +0.0006]$ | `OBSERVATIONAL` | Ambient boundary condition; sea-level nominal variation ($\approx 0\text{ Mach}$) |
| **`op_setting_3`** | `4` | `setting_3` | Throttle Resolver Angle (TRA) | Degrees / % | $[100.0, 100.0]$ | `FACT` | Demanded engine thrust; constant at $100\%$ cruise power |

---

## 4. Gas-Path Sensor Measurements (`sensor_1` .. `sensor_21`)

The 21 sensor measurements represent physical instrumentation stationed along the gas-path of the two-spool turbofan engine. 

Definitions, station symbols, and engineering units are cross-referenced from **Table 2 of Saxena et al. (2008)**:

| Field Name | Raw Col | Symbol | Thermodynamic Station Meaning | Engineering Units | Observed Range (FD001) | Within-Dataset Status (FD001) | Diagnostic Utility under FD001 |
|---|:---:|:---:|---|:---:|:---:|:---:|---|
| **`sensor_1`** | `5` | $T_2$ | Total temperature at fan inlet | $^\circ\text{R}$ | $[518.67, 518.67]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Ambient sea-level boundary; flatline) |
| **`sensor_2`** | `6` | $T_{24}$ | Total temperature at LPC outlet | $^\circ\text{R}$ | $[641.21, 644.53]$ | `ACTIVE` ($\sigma = 0.5001$) | Moderate positive drift ($r = +0.55$) tracking compression heat |
| **`sensor_3`** | `7` | $T_{30}$ | Total temperature at HPC outlet | $^\circ\text{R}$ | $[1571.04, 1616.91]$ | `ACTIVE` ($\sigma = 6.1311$) | Strong positive drift ($r = +0.54$) tracking HPC thermal load |
| **`sensor_4`** | `8` | $T_{50}$ | Total temperature at LPT outlet (EGT) | $^\circ\text{R}$ | $[1382.25, 1441.49]$ | `ACTIVE` ($\sigma = 9.0006$) | **Primary degradation marker** ($r = +0.62$, within-unit $\rho = +0.77$) |
| **`sensor_5`** | `9` | $P_2$ | Total pressure at fan inlet | $\text{psia}$ | $[14.62, 14.62]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Ambient sea-level pressure; flatline) |
| **`sensor_6`** | `10` | $P_{15}$ | Total pressure in bypass-duct | $\text{psia}$ | $[21.60, 21.61]$ | **`NEAR_CONSTANT`** ($\sigma = 0.0014$) | Only 2 discrete quantization values; near-zero diagnostic info |
| **`sensor_7`** | `11` | $P_{30}$ | Total pressure at HPC outlet | $\text{psia}$ | $[549.85, 556.06]$ | `ACTIVE` ($\sigma = 0.8851$) | Strong negative drift ($r = -0.60$, within-unit $\rho = -0.75$) |
| **`sensor_8`** | `12` | $N_f$ | Physical fan speed | $\text{rpm}$ | $[2387.90, 2388.56]$ | `ACTIVE` ($\sigma = 0.0710$) | Moderate positive drift ($r = +0.48$) tracking spool speed |
| **`sensor_9`** | `13` | $N_c$ | Physical core speed | $\text{rpm}$ | $[9021.73, 9244.59]$ | `ACTIVE` ($\sigma = 22.0829$) | High absolute variance; positive drift ($r = +0.44$) |
| **`sensor_10`** | `14` | `epr` | Engine pressure ratio ($P_{50} / P_2$) | Dimensionless | $[1.30, 1.30]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Flatline under single sea-level setting) |
| **`sensor_11`** | `15` | $P_{s30}$ | Static pressure at HPC outlet | $\text{psia}$ | $[46.85, 48.53]$ | `ACTIVE` ($\sigma = 0.2671$) | **Primary degradation marker** ($r = +0.63$, within-unit $\rho = +0.81$) |
| **`sensor_12`** | `16` | $\phi$ | Ratio of fuel flow to $P_{s30}$ | $\text{pps/psi}$ | $[518.69, 523.38]$ | `ACTIVE` ($\sigma = 0.7376$) | Strong negative drift ($r = -0.61$, within-unit $\rho = -0.78$) |
| **`sensor_13`** | `17` | $NR_f$ | Corrected fan speed | $\text{rpm}$ | $[2387.88, 2388.56]$ | `ACTIVE` ($\sigma = 0.0719$) | Moderate positive drift ($r = +0.48$) |
| **`sensor_14`** | `18` | $NR_c$ | Corrected core speed | $\text{rpm}$ | $[8099.94, 8255.33]$ | `ACTIVE` ($\sigma = 19.0762$) | Moderate positive drift ($r = +0.37$) |
| **`sensor_15`** | `19` | $BPR$ | Bypass Ratio | Dimensionless | $[8.3249, 8.5848]$ | `ACTIVE` ($\sigma = 0.0375$) | Strong positive drift ($r = +0.59$, within-unit $\rho = +0.71$) |
| **`sensor_16`** | `20` | `farB` | Burner fuel-air ratio | Dimensionless | $[0.03, 0.03]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Constant combustion ratio; flatline) |
| **`sensor_17`** | `21` | $htBleed$ | Bleed Enthalpy | Dimensionless | $[388, 400]$ | `ACTIVE` ($\sigma = 1.5488$) | Moderate positive step-like drift ($r = +0.57$) |
| **`sensor_18`** | `22` | $N_{f,\text{dmd}}$ | Demanded fan speed | $\text{rpm}$ | $[2388, 2388]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Fixed controller demand; flatline) |
| **`sensor_19`** | `23` | $\text{PCNfR}_{\text{dmd}}$ | Demanded corrected fan speed | $\text{rpm}$ | $[100.0, 100.0]$ | **`CONSTANT`** ($\sigma = 0$) | **Zero variation** (Fixed controller demand; flatline) |
| **`sensor_20`** | `24` | $W_{31}$ | High-Pressure Turbine coolant bleed | $\text{lbm/s}$ | $[38.14, 39.43]$ | `ACTIVE` ($\sigma = 0.1807$) | Moderate negative drift ($r = -0.58$, within-unit $\rho = -0.70$) |
| **`sensor_21`** | `25` | $W_{32}$ | Low-Pressure Turbine coolant bleed | $\text{lbm/s}$ | $[22.89, 23.61]$ | `ACTIVE` ($\sigma = 0.1083$) | Moderate negative drift ($r = -0.59$, within-unit $\rho = -0.70$) |

---

## 5. Engineered Lifecycle & Transformation Fields

In the transformed dataset (`outputs/final_output.csv`), several analytical fields are derived from the raw sequence:

| Field Name | Formula / Derivation | Analytical Grain | Status | Operational Role |
|---|---|:---:|:---:|---|
| **`max_cycle`** | $\max_{c}(\text{cycle} \mid \text{engine\_id})$ | Engine | `OBSERVATIONAL` | Total simulated lifespan of the engine unit |
| **`RUL`** | $\text{max\_cycle} - \text{cycle}$ | Engine-Cycle | `OBSERVATIONAL` | Remaining operational cycles until simulated failure endpoint |
| **`cycle_ratio`** | $\frac{\text{cycle}}{\text{max\_cycle}}$ | Engine-Cycle | `OBSERVATIONAL` | Normalized trajectory progression ($0.0 \dots 1.0$) |
| **`sensor_4_baseline`** | $\text{mean}(s_{4} \mid \text{cycle} \le 5)$ | Engine | `OBSERVATIONAL` | Initial healthy reference state for LPT outlet temperature ($T_{50}$) |
| **`sensor_4_drift`** | $s_{4} - \text{sensor\_4\_baseline}$ | Engine-Cycle | `OBSERVATIONAL` | Cumulative thermal deviation from initial healthy baseline |
| **`sensor_9_drift`** | $s_{9} - \text{mean}(s_{9} \mid \text{cycle} \le 5)$ | Engine-Cycle | `OBSERVATIONAL` | Cumulative core speed deviation from initial healthy baseline |
| **`sensor_11_drift`** | $s_{11} - \text{mean}(s_{11} \mid \text{cycle} \le 5)$ | Engine-Cycle | `OBSERVATIONAL` | Cumulative HPC static pressure deviation from baseline |
| **`lifecycle_phase`** | $\begin{cases} \text{CRITICAL} & \text{RUL} \le 30 \\ \text{ADVISORY} & 30 < \text{RUL} \le 60 \\ \text{HEALTHY} & \text{RUL} > 60 \end{cases}$ | Engine-Cycle | `UNRATIFIED` | Analytical lifecycle cohort segmentation for exploratory exposure analysis |

---

## 6. Explicitly Marked Unknowns & Data Gaps

To maintain strict Forward Deployed Engineering governance, the following data dimensions are explicitly classified as **`UNKNOWN`** (not present or deducible from the C-MAPSS FD001 data files):

1. **`[UNKNOWN]` Calendar Timestamps & Elapsed Time**:
   - The data logs integer cycles ($1, 2, 3 \dots$).
   - The real-world flight duration (e.g., 45-minute short haul vs. 6-hour transcontinental flight) is unrecorded.
   - The elapsed calendar time between cycles (hours, days, or months) is unrecorded.

2. **`[UNKNOWN]` Exact Commercial Engine Identity**:
   - The simulation reflects physical parameters of a generic high-bypass turbofan in the 90,000 lb thrust class (similar to GE90, PW4000, or Trent 800).
   - The proprietary manufacturer, airline operator, and specific airframe installation are intentionally omitted.

3. **`[UNKNOWN]` Instantaneous Health Index ($H(t)$)**:
   - Ground truth initial state ($H(0) \approx 1.0$) and failure criterion ($H(C_{\text{fail}}) \le 0$) are documented in the literature.
   - However, the instantaneous numerical degradation values ($m_{\text{Fan}}, m_{\text{HPC}}, m_{\text{HPT}}, m_{\text{EGT}}$) are not provided in the raw data files.

4. **`[UNKNOWN]` Exact Fault Inception Cycle**:
   - The simulation injects an exponential wear trajectory that accelerates over time.
   - The exact discrete cycle at which linear baseline wear transitions into exponential damage propagation is unannotated.

5. **`[UNKNOWN]` Financial & Maintenance Economics**:
   - The dataset provides no cost metrics for routine hangar inspections, line maintenance labor, spare engine leasing, unscheduled removals, or catastrophic in-flight shutdown penalties.
   - No cost-benefit optimization or economic comparison against fixed-interval maintenance can be established from this dataset alone.

6. **`[UNKNOWN]` Competing Multi-Component Failure Modes**:
   - Sub-dataset FD001 isolates a single failure mode: High-Pressure Compressor (HPC) degradation.
   - Degradation signatures for fan erosion, turbine blade creep, combustor burnout, or bearing failures are absent from FD001.
