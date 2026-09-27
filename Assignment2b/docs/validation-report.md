# NASA C-MAPSS Validation Report & Quality Audit (Class 6)

**Domain**: Commercial Turbofan Engine Health Telemetry  
**Primary Dataset**: Sub-dataset FD001 (Single Condition, Single Fault Mode)  
**Execution Artifact**: `outputs/validation_report.json`  
**Document Purpose**: Comprehensive Audit of the Executable Validation Gate across Technical, Semantic, and Operational Decision Dimensions  

---

## 1. Validation Architecture & FDE Failure Contracts

The validation gate executes before transformation to protect downstream analytics and operational decision-making from data corruption, formatting anomalies, and invalid physical bounds. Every check implements the formal **FDE Failure Contract**:

* **`PASS`**: Data satisfies strict physical, technical, and relational invariants. Execution continues.
* **`WARN`**: Anomaly or limitation detected that does not halt processing, but must be explicitly documented and governed (e.g., constant sensors under single-condition flight). Execution continues.
* **`FAIL`**: Critical data corruption detected that violates physical reality or system integrity (e.g., broken cycle sequence, duplicate primary keys, schema corruption). Execution halts immediately.
* **`UNKNOWN`**: Metric, maintenance threshold, or operational economic cost is not present in the dataset. Recorded transparently without fabricating assumptions.

---

## 2. Multi-Dimensional Validation Audit Summary

```
====================================================================================================
CHECK NAME                       DIMENSION          STATUS   OBSERVED EVIDENCE        VERDICT
====================================================================================================
composite_grain_uniqueness       Technical/Semantic PASS     0 dups in 20,631 rows    CLEAN GRAIN
engine_unit_contiguity           Technical          PASS     100 engines (1..100)     VERIFIED
cycle_sequence_continuity        Semantic           PASS     0 broken trajectories    100% UNBROKEN
sensor_variance_audit            Technical/Measure  WARN     6 of 21 sensors constant AUDITED / FLAGGED
trajectory_lifespan_bounds       Semantic           PASS     Lifespans [128, 362]     PLAUSIBLE
test_rul_alignment               Technical          PASS     100 test units == 100 RUL 1:1 ALIGNED
operational_decision_context     Decision/Gov       UNKNOWN  Maintenance costs &      UNOBSERVED
                                                             thresholds not in data
----------------------------------------------------------------------------------------------------
OVERALL PIPELINE STATUS          Technical Pipeline WARN     (Advisory: 6 flatline)   ACCEPTED
====================================================================================================
```

---

## 3. Detailed Validation Check Audits

### Check 1: Composite Primary Key Grain Uniqueness (Technical / Semantic)
* **Relational Contract**: Each row must represent an atomic snapshot uniquely identified by `(unit_number, time_in_cycles)`.
* **Empirical Findings**:
  - `train_FD001.txt`: Exactly 20,631 records; **0 duplicate snapshots**.
  - `test_FD001.txt`: Exactly 13,096 records; **0 duplicate snapshots**.
* **Status**: **`PASS`** (Zero duplicate snapshots detected across both training and test corpora).

---

### Check 2: Contiguous Engine Identifiers (Technical)
* **Relational Contract**: Engine units must be numbered contiguously as integers $1, 2, \dots, N_{\text{engines}}$ without missing identifiers.
* **Empirical Findings**:
  - Training units: Contiguous sequence $1 \dots 100$ ($N = 100$).
  - Test units: Contiguous sequence $1 \dots 100$ ($N = 100$).
* **Status**: **`PASS`** (Zero missing or omitted engine units).

---

### Check 3: Monotonic Cycle Continuity & Zero Missing Cycles (Semantic)
* **Physical / Simulation Contract**: Trajectories must begin at Cycle 1 and increment monotonically by exactly $+1$ per flight cycle ($\Delta \text{cycle} \equiv 1$).
* **Empirical Findings**:
  - 100 out of 100 training engines start at `cycle = 1`.
  - 100 out of 100 test engines start at `cycle = 1`.
  - Zero missing cycles, zero time inversions, and zero step gaps across all 33,727 combined cycles.
* **Status**: **`PASS`** (100% temporal continuity verified).

---

### Check 4: Sensor Variance & Flatline Channel Audit (Technical / Measurement)
* **Measurement Contract**: Audit sensor columns for within-dataset variation under the evaluated flight regime.
* **Empirical Findings**:
  In FD001 (Sea Level cruise), **6 of the 21 sensors exhibit zero within-dataset variance**:

| Sensor Column | Documented Symbol | Standard Deviation | Min Value | Max Value | Physical Simulation Cause |
|---|---|---:|---:|---:|---|
| `sensor_1` | $T_2$ | $0.000000$ | $518.67$ | $518.67$ | Total temp at fan inlet: Fixed at standard sea-level temperature. |
| `sensor_5` | $P_2$ | $0.000000$ | $14.62$ | $14.62$ | Pressure at fan inlet: Fixed at sea-level ambient pressure. |
| `sensor_10`| `epr` | $0.000000$ | $1.30$ | $1.30$ | Engine Pressure Ratio ($P_{50}/P_2$): Constant under sea-level HPC wear. |
| `sensor_16`| `farB`| $0.000000$ | $0.03$ | $0.03$ | Burner Fuel-Air Ratio: Fixed control schedule at sea-level cruise. |
| `sensor_18`| `Nf_dmd` | $0.000000$ | $2388$ | $2388$ | Demanded Fan Speed: Fixed controller setpoint. |
| `sensor_19`| `PCNfR_dmd` | $0.000000$ | $100.0$ | $100.0$ | Demanded Corrected Fan Speed: Fixed controller setpoint. |

*In addition, `sensor_6` ($P_{15}$) takes only two discrete values ($21.60$ and $21.61\text{ psia}$, $\sigma = 0.00139$), providing negligible variation.*

* **FDE Finding**: These 6 channels exhibit zero within-dataset variation under FD001 and therefore cannot distinguish degradation progression in this analysis.
* **Status**: **`WARN`** (Flagged as non-informative channels for FD001; preserved in raw schema for auditability).

---

### Check 5: Trajectory Lifespan Distribution & Bounds (Semantic)
* **Semantic Contract**: Turbofan engines under run-to-failure simulation must demonstrate lifespans within physically plausible simulation boundaries ($[50, 1000]$ cycles).
* **Empirical Findings**:
  - Minimum Lifespan to Endpoint: **128 cycles** (Engine Unit 31).
  - Maximum Lifespan to Endpoint: **362 cycles** (Engine Unit 69).
  - Median Lifespan: **199.0 cycles**.
  - Sample Mean Lifespan: **206.31 cycles**.
  - Sample Standard Deviation ($s$, with $\text{ddof}=1$): **46.34 cycles**.
  - Coefficient of Variation ($\text{CV} = s / \bar{C}$): **22.46%**.
* **Status**: **`PASS`** (All lifespans are well within plausible bounds).

---

### Check 6: Ground Truth RUL Alignment & Documentation Discrepancy (Technical)
* **Data Contract**: Test set engines must map 1:1 with ground-truth RUL vector entries.
* **Empirical Findings**:
  - `test_FD001.txt` has **100 unique engines**.
  - `RUL_FD001.txt` has **100 rows**.
  - RUL Values: Range $[7, 145]$ cycles, Median **86.0 cycles**, Mean **75.54 cycles**.
  - Implied Total Life ($C_{\text{test}} + \text{RUL}_{\text{true}}$): Range $[141, 341]$ cycles, Median **199.0 cycles**, Mean **206.50 cycles**.
* **Documentation Discrepancy Identified in FD004**:
  Programmatic validation discovered a documentation/file-count discrepancy in `readme.txt` for sub-dataset FD004:
  - `readme.txt` claims: Train trajectories = 248, Test trajectories = 249.
  - Actual data files: `train_FD004.txt` contains **249 unique engines**; `test_FD004.txt` contains **248 unique engines**; `RUL_FD004.txt` contains **248 rows**.
  - Validation decision: The actual data files are the operational source of truth.
* **Status**: **`PASS`** for FD001 (1:1 alignment verified).

---

### Check 7: Operational Decision Context Contracts (Decision / Governance)
* **Governance Contract**: Audit whether operational maintenance thresholds, economic cost parameters, or real-world failure probabilities exist in the dataset.
* **Empirical Findings**:
  - **Validated Maintenance Thresholds**: `UNKNOWN` (Not present in C-MAPSS dataset).
  - **Maintenance Cost Matrix**: `UNKNOWN` (Economic parameters not modeled in simulation).
  - **Real-World Failure Probability**: `UNKNOWN` (Simulation runs to synthetic stopping criteria).
* **Governance Takeaway**: All derived analytical thresholds (e.g. $\text{RUL} \le 30$) are exploratory analytical definitions, not validated maintenance policies.
* **Status**: **`UNKNOWN`** (Explicitly acknowledged governance limitation).

---

## 4. Ingestion Formatting Trap (Trailing Whitespace)

* **Finding**: Raw text files feature trailing whitespace on every line (`" \n"`).
* **Impact of Naive Parsing**: Standard whitespace/space separation `pd.read_csv(sep=' ')` creates **28 columns**, where columns 26 and 27 are 100% `NaN`.
* **Resolution**: The dependable pipeline enforces regex delimiter parsing `sep=r'\s+'`, producing exactly 26 columns with **zero null values**.
