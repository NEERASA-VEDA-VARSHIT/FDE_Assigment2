# NASA C-MAPSS Analytical Workflow Model (Class 7)

**Domain**: Commercial Turbofan Engine Health Telemetry & Lifecycle Modeling  
**Primary Dataset**: Sub-dataset FD001 (100 Training Engines, 20,631 Operational Cycles)  
**Document Purpose**: Documenting the Physical Telemetry Workflow, Distinguishing Observed vs. Inferred vs. Unknown Phenomena, and Relational Schema Definition  

---

## 1. The Approved Analytical Workflow

Rather than asserting unobserved physical milestones, the analytical workflow maps directly to what is verifiable from the telemetry data:

```
                          ENGINE
                             │
                             ▼
                     OPERATIONAL CYCLE
                             │
                             ▼
            SENSOR + OPERATING-SETTING OBSERVATION
                             │
                             ▼
                   TRAJECTORY OVER TIME
                             │
                             ▼
                 CHANGING SENSOR BEHAVIOR
                             │
                             ▼
                    LATE-LIFE TRAJECTORY
                             │
                             ▼
                 SIMULATED FAILURE ENDPOINT
```

---

## 2. Distinction of Knowledge: Observed vs. Inferred vs. Unknown

| Workflow Stage | Operational Evidence & Data Representation | Classification | FDE Rationale & Technical Boundary |
|---|---|:---:|---|
| **Engine Identity** | Contiguous integers `unit_number` ($1 \dots 100$). | `OBSERVED` | Verified by primary key contiguity and uniqueness checks. |
| **Operational Cycle** | Discrete integer sequence `time_in_cycles` ($1 \dots C_{\max}$). | `OBSERVED` | Verified unbroken sequence with zero step gaps ($\Delta = 1$). |
| **Operating Settings** | Float values for `op_setting_1`, `op_setting_2`, `op_setting_3`. | `OBSERVED` | Confirms single-regime flight operation ($TRA = 100, Alt \approx 0, Mach \approx 0$). |
| **Raw Sensor Readings** | 21 continuous sensor measurements (`sensor_1` to `sensor_21`). | `OBSERVED` | Recorded cruise snapshots; 15 channels show variance, 6 channels are constant. |
| **Sensor Trajectory Over Time** | Multi-cycle series of sensor observations per engine unit. | `OBSERVED` | Longitudinal sequence from initial recorded cycle to final recorded cycle. |
| **Changing Sensor Behavior** | Sensed drift from early baseline ($\Delta s_i = s_i - s_{i,\text{base}}$). | `OBSERVED` | Statistically measurable drift across core gas-path channels ($T_{50}, T_{30}, N_c$). |
| **Point of Fault Onset** | The exact cycle where nominal wear transitions to fault growth. | `UNKNOWN` | Not annotated in the dataset; can only be estimated via statistical changepoint inference. |
| **Two-Phase Degradation** | Presence of an initial stable phase followed by accelerated drift. | `INFERRED` | Inferred from trajectory curvature and rolling baseline divergence. |
| **Simulated Failure Endpoint** | Terminal cycle in training file ($C_{\max} = C_{\text{fail}}$). | `OBSERVED` | The simulation stopped recording; ground-truth operational end of run. |
| **Instantaneous Health Index $H(t)$**| Exact internal margin value ($H(t) = \min(m_{\text{Fan}}, m_{\text{HPC}}, \dots)$). | `UNKNOWN` | Calculated internally by the simulation, but withheld from the raw data files. |
| **Initial Manufacturing Wear Degree**| Exact percentage wear per engine at cycle 1. | `UNKNOWN` | Documented in literature as randomly bounded ($\le 1\%$), but exact engine values are unrecorded. |
| **Real-World Maintenance Cost** | Financial cost ($) of engine removal, overhaul, or failure. | `UNKNOWN` | No economic or cost parameters exist in the C-MAPSS dataset. |

---

## 3. Data Flow & Transformation Architecture

```
┌────────────────────────────────┐
│   Raw Telemetry Ingestion      │  train_FD001.txt (20,631 rows, 26 space-delimited cols)
│   (Whitespace regex parser)    │  Strictly eliminates 28-column trailing-space parser trap
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Early Baseline Estimation    │  Computes per-engine nominal reference across first 5 cycles:
│   (First 5 Cycles Per Engine)  │  s_base = mean(s[t <= 5]) for active non-constant sensors
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Cumulative Drift Extraction  │  Calculates observed deviation from early baseline:
│   (Zero-Fanout Transformation) │  Delta s_i(t) = s_i(t) - s_i_base
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Standardized Wear Scoring    │  Dimensionless Thermal Wear Index:
│   (Multi-Sensor Fusion)        │  Index = (Delta T50 / sigma_T50) + (Delta Nc / sigma_Nc)
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Exploratory Lifecycle Stage  │  Analytical cohorts (Exploratory definitions only):
│   (Analytical Segmentation)    │  NOMINAL (>60 cycles), ADVISORY (31-60), CRITICAL (<=30)
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│   Canonical Enriched Dataset   │  outputs/final_output.csv (20,631 rows, 26 columns)
│   (Grain Invariant Asserted)   │  assert len(canonical_df) == len(train_df) == 20,631
└────────────────────────────────┘
```

---

## 4. Pre-Aggregation Strategy (Fanout Prevention)

1. **Engine Baseline Extraction**:
   $$\text{Baseline}(u) = \frac{1}{5} \sum_{t=1}^{5} \vec{s}(u, t)$$
   Computed using `early_cycles.groupby("unit_number")[active_sensors].mean()`, producing exactly **1 row per engine** ($100$ rows total).
2. **Deterministic Left Join**:
   Joined back to the primary trajectory table on the single key `unit_number`:
   $$\text{Grain}(\text{train}) = (\text{unit\_number},\; \text{time\_in\_cycles}) \quad \text{Preserved } 100\%$$
3. **Dynamic Verification**:
   The transformation dynamically asserts:
   ```python
   expected_rows = len(df_train)
   total_rows = len(canonical_df)
   unique_snapshots = canonical_df[["unit_number", "time_in_cycles"]].drop_duplicates().shape[0]

   assert total_rows == unique_snapshots, "Cartesian fanout detected!"
   assert total_rows == expected_rows, "Transformed rows do not match raw rows!"
   ```

---

## 5. Transformed Canonical Schema (`outputs/final_output.csv`)

The enriched condition-monitoring table contains **20,631 rows** and **26 columns**:

| Column Name | Data Type | Derivation | Operational & Engineering Interpretation |
|---|---|---|---|
| `unit_number` | Integer | Raw Col 0 | Unique identifier for aircraft engine ($1 \dots 100$). |
| `time_in_cycles` | Integer | Raw Col 1 | Operational flight cycle sequence counter ($1 \dots C_{\max}$). |
| `op_setting_1` | Float | Raw Col 2 | Altitude in kft (Nominal Sea Level: $0.00 \pm 0.0087$). |
| `op_setting_2` | Float | Raw Col 3 | Mach number (Nominal Sea Level: $0.00 \pm 0.0006$). |
| `op_setting_3` | Float | Raw Col 4 | Throttle Resolver Angle (TRA = $100.0$). |
| `sensor_2` | Float | Raw Col 6 | $T_{24}$ — Total temperature at LPC outlet ($^\circ\text{R}$). |
| `sensor_3` | Float | Raw Col 7 | $T_{30}$ — Total temperature at HPC outlet ($^\circ\text{R}$). |
| `sensor_4` | Float | Raw Col 8 | $T_{50}$ — Total temperature at LPT outlet ($^\circ\text{R}$). |
| `sensor_7` | Float | Raw Col 11 | $P_{30}$ — Total pressure at HPC outlet ($\text{psia}$). |
| `sensor_8` | Float | Raw Col 12 | $N_f$ — Physical fan speed ($\text{rpm}$). |
| `sensor_9` | Float | Raw Col 13 | $N_c$ — Physical core speed ($\text{rpm}$). |
| `sensor_11` | Float | Raw Col 15 | $P_{s30}$ — Static pressure at HPC outlet ($\text{psia}$). |
| `sensor_12` | Float | Raw Col 16 | $\phi$ — Ratio of fuel flow to $P_{s30}$ ($\text{pps/psi}$). |
| `sensor_13` | Float | Raw Col 17 | $NR_f$ — Corrected fan speed ($\text{rpm}$). |
| `sensor_14` | Float | Raw Col 18 | $NR_c$ — Corrected core speed ($\text{rpm}$). |
| `sensor_15` | Float | Raw Col 19 | $BPR$ — Bypass Ratio. |
| `sensor_17` | Float | Raw Col 21 | $htBleed$ — Bleed Enthalpy. |
| `sensor_20` | Float | Raw Col 24 | $W_{31}$ — HPT coolant bleed ($\text{lbm/s}$). |
| `sensor_21` | Float | Raw Col 25 | $W_{32}$ — LPT coolant bleed ($\text{lbm/s}$). |
| `sensor_4_drift` | Float | $s_4 - s_{4,\text{base}}$ | Cumulative thermal drift in Exhaust Gas Temperature ($^\circ\text{R}$). |
| `sensor_9_drift` | Float | $s_9 - s_{9,\text{base}}$ | Cumulative mechanical drift in core rotational speed ($\text{rpm}$). |
| `thermal_wear_index` | Float | Derived composite | Dimensionless standardized thermal wear score: $(\Delta T_{50}/\sigma) + (\Delta N_c/\sigma)$. |
| `total_lifespan` | Integer | $\max(t)$ per unit | Total completed cycles to simulated endpoint ($C_{\text{fail}}$). |
| `true_rul` | Integer | $C_{\text{fail}} - t$ | True Remaining Useful Life in cycles at current snapshot. |
| `lifecycle_progression` | Float | $t / C_{\text{fail}}$ | Normalized operational progression ratio ($0.0 \dots 1.0$). |
| `analytical_lifecycle_stage`| String | Categorical | Analytical exploratory cohort: `NOMINAL`, `ADVISORY`, `CRITICAL`. |

---

## 6. Grain Invariant Proof

* **Input Raw Records**: 20,631 rows.
* **Transformed Output Records**: 20,631 rows.
* **Unique Composite Keys `(unit_number, time_in_cycles)`**: Exactly 20,631.
* **Duplicate Rows**: **0** (0.00%).
* **Missing / Null Values**: **0** (0.00%).
