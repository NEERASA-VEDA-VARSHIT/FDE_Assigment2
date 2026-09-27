# NASA C-MAPSS Source Reasoning Framework (Class 4)

**Domain**: Commercial Turbofan Jet Engine Telemetry & Degradation Modeling  
**Primary Dataset**: Sub-dataset FD001 (Single Condition, Single Fault Mode)  
**Document Purpose**: Source-by-Source Reasoning, Artifact Categorization, and Provenance Mapping across 7 FDE Dimensions  

---

## 1. Source Document Classification Architecture

Forward deployed engineering establishes transparent boundaries between raw source data, official documentation, derived analytical outputs, and client-scenario assumptions:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           NASA C-MAPSS ARTIFACTS                          │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│   DATA SOURCES   │        │  DOCUMENTATION   │        │ DERIVED OUTPUTS  │
│ train_FD001.txt  │        │ Damage Prop. pdf │        │ final_output.csv │
│ test_FD001.txt   │        │ readme.txt       │        │ validation_rep.  │
│ RUL_FD001.txt    │        │ NASA Open Portal │        │ metrics.csv      │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

---

## 2. Source-by-Source Inventory & Provenance

### Source 1: `train_FD001.txt`
* **Artifact Category**: `DATA SOURCE`
* **Owner / Origin**: NASA Prognostics Center of Excellence (PCoE) & NASA Glenn Research Center.
* **Content**: 26 space-delimited numeric columns capturing run-to-failure operational profiles and sensor measurements for 100 engines.
* **Grain**: 1 record per engine unit per operational flight cycle `(unit_number, time_in_cycles)`.
* **Purpose**: Provide full-lifecycle degradation trajectories from initial wear to simulated failure endpoint.
* **Authority**: **Authoritative simulation record** for training trajectories.
* **Limitations**: Synthetic simulation data; does not contain calendar flight hours, real-world maintenance actions, or intermediate health index labels.
* **Retrieval Method**: Whitespace regex extraction (`sep=r'\s+'`) from `data/raw/CMAPSSData/train_FD001.txt`.

---

### Source 2: `test_FD001.txt`
* **Artifact Category**: `DATA SOURCE`
* **Owner / Origin**: NASA Prognostics Center of Excellence (PCoE).
* **Content**: 26 space-delimited numeric columns capturing censored operational profiles for 100 engines.
* **Grain**: 1 record per engine unit per operational flight cycle `(unit_number, time_in_cycles)`.
* **Purpose**: Provide truncated operating histories that stop at an undisclosed point prior to failure.
* **Authority**: **Authoritative simulation record** for test evaluation.
* **Limitations**: Truncated prior to failure; actual remaining life is unknown within the file itself.
* **Retrieval Method**: Whitespace regex extraction (`sep=r'\s+'`) from `data/raw/CMAPSSData/test_FD001.txt`.

---

### Source 3: `RUL_FD001.txt`
* **Artifact Category**: `DATA SOURCE` (Ground Truth)
* **Owner / Origin**: NASA Prognostics Center of Excellence (PCoE).
* **Content**: Single-column integer vector containing true remaining operational cycles for each test engine.
* **Grain**: 1 record per test engine unit ($N = 100$).
* **Purpose**: Benchmark ground truth for evaluating prognostic horizon accuracy on test units.
* **Authority**: **Authoritative ground truth** for test set evaluation.
* **Limitations**: Provided as a post-hoc evaluation vector; not available in live streaming operations.
* **Retrieval Method**: Text reading and integer conversion from `data/raw/CMAPSSData/RUL_FD001.txt`.

---

### Source 4: `Damage Propagation Modeling.pdf`
* **Artifact Category**: `DOCUMENTATION` (Technical Literature)
* **Owner / Origin**: Saxena, Goebel, Simon, and Eklund (IEEE PHM 2008 Conference Proceedings).
* **Content**: 9-page research paper detailing C-MAPSS simulation thermodynamics, wear equations, sensor station descriptions (Table 2), and asymmetric scoring function.
* **Grain**: System and publication level.
* **Purpose**: Authoritative domain documentation defining the engineering meaning of sensor channels and simulation logic.
* **Authority**: **Authoritative scientific documentation** for the dataset.
* **Limitations**: Describes simulation design principles; does not disclose exact proprietary commercial engine configuration.
* **Retrieval Method**: Extracted from raw ZIP archive (`data/raw/CMAPSSData/Damage Propagation Modeling.pdf`).

---

### Source 5: `readme.txt`
* **Artifact Category**: `DOCUMENTATION` (Dataset Metadata)
* **Owner / Origin**: NASA PCoE Dataset Curators.
* **Content**: Summary text file outlining trajectory counts, operational settings, and column format.
* **Grain**: Dataset level.
* **Purpose**: High-level user guidance for dataset structure.
* **Authority**: Contextual metadata (contains a documented discrepancy in FD004 trajectory counts).
* **Limitations**: High-level summary; does not define individual sensor physical engineering units or locations.
* **Retrieval Method**: Text decoding from `data/raw/CMAPSSData/readme.txt`.

---

### Source 6: `outputs/final_output.csv`
* **Artifact Category**: `DERIVED OUTPUT`
* **Owner / Origin**: FDE Dependable Pipeline (`pipeline/transform.py`).
* **Content**: Transformed 26-column condition-monitoring dataset containing raw observations, per-engine baselines, cumulative sensor drift, standardized drift index, and analytical lifecycle stages.
* **Grain**: 1 record per engine unit per operational flight cycle `(unit_number, time_in_cycles)`.
* **Purpose**: Standardized, clean canonical dataset for exploratory analysis and condition tracking.
* **Authority**: Derived pipeline output; verified by unit tests and dynamic grain assertions.
* **Limitations**: Enriched analytical representation; downstream interpretations depend on exploratory baseline definitions.
* **Retrieval Method**: Generated dynamically by `python pipeline/run_pipeline.py`.

---

### Source 7: `outputs/validation_report.json`
* **Artifact Category**: `DERIVED OUTPUT`
* **Owner / Origin**: FDE Dependable Pipeline (`pipeline/validate.py`).
* **Content**: JSON audit log detailing results of technical, semantic, and decision validation contracts (`PASS`, `WARN`, `FAIL`, `UNKNOWN`).
* **Grain**: Pipeline run execution level.
* **Purpose**: Machine-readable proof of data quality, contiguity, and channel variance auditing.
* **Authority**: Derived pipeline audit; verifiable via automated test suite.
* **Limitations**: Diagnostic snapshot of dataset state under evaluated pipeline parameters.
* **Retrieval Method**: Generated dynamically by `python pipeline/run_pipeline.py`.

---

### Source 8: `outputs/metrics.csv`
* **Artifact Category**: `DERIVED OUTPUT`
* **Owner / Origin**: FDE Dependable Pipeline (`pipeline/metrics.py`).
* **Content**: Tabular export of the 5 governed analytical metrics with explicit formulas, grains, values, and limitations.
* **Grain**: Metric definition level ($N = 5$).
* **Purpose**: Governed metric registry providing transparent, reproducible indicators.
* **Authority**: Derived analytical metrics; strictly labeled as candidate indicators, not official KPIs.
* **Limitations**: Metrics reflect simulated characteristics and analytical definitions, not commercial airline KPIs.
* **Retrieval Method**: Generated dynamically by `python pipeline/run_pipeline.py`.

---

## 3. Client-Scenario Stakeholders (Assumptions)

In this assessment, organizational stakeholders are **CLIENT-SCENARIO ASSUMPTIONS** established to guide analytical inquiry. They do not represent real-world NASA organizational personnel:

| Stakeholder Persona | Organizational Focus (Scenario Assumption) | Primary Information Requirement | Analytical Governance Role |
|---|---|---|---|
| **Maintenance Leadership** | Fleet reliability and hangar overhaul capacity planning. | Early wear detection and lead time prior to failure endpoint. | *Client Scenario Assumption*: Evaluates whether telemetry provides sufficient lead time for maintenance planning. |
| **Reliability Engineering** | Failure mode analysis and component degradation tracking. | Gas-path sensor trend consistency ($T_{50}, T_{30}, N_c$) and noise characterization. | *Client Scenario Assumption*: Interrogates physical plausibility of sensor drift and changepoint detection. |
| **Data Platform Team** | Pipeline architecture, data quality, and warehouse schemas. | Clean-room repeatability, schema contracts, zero nulls, and automated test coverage. | *Client Scenario Assumption*: Enforces deterministic processing, idempotence, and failure contracts. |

---

## 4. Seven-Dimension FDE Source Map (FD001 Telemetry)

| Dimension | Physical Gas-Path Sensors (`sensor_1`–`sensor_21`) | Operating Setting Variables (`op_setting_1`–`op_setting_3`) | Ground-Truth RUL Vector (`RUL_FD001.txt`) | Engine Lifecycle Grain (`unit_number`, `time_in_cycles`) |
|---|---|---|---|---|
| **1. Business Question** | Which sensor channels exhibit measurable changes over cycle progression? | What are the operating condition boundaries for the evaluated flight regime? | What is the true remaining operational lifespan for test units? | What is the historical trajectory sequence of each engine? |
| **2. Information Required** | Multi-channel physical sensor measurements across turbofan gas-path stations. | Altitude, Mach number, and Throttle Resolver Angle (TRA) setpoints. | Ground-truth cycle count from cutoff to simulated failure endpoint. | Contiguous unit numbering and unbroken cycle counter. |
| **3. Source System** | C-MAPSS simulation telemetry (`train_FD001.txt`, `test_FD001.txt`). | C-MAPSS simulation controls (`op_setting_1`, `op_setting_2`, `op_setting_3`). | NASA PCoE Simulation Benchmark (`RUL_FD001.txt`). | C-MAPSS engine-cycle indexing keys. |
| **4. System Ownership** | NASA PCoE simulation developers (*Saxena et al., 2008*). | NASA PCoE simulation developers. | NASA PCoE simulation developers. | NASA PCoE simulation developers. |
| **5. Freshness / Latency** | Static snapshot per completed flight cycle (recorded at cruise conditions). | Synchronous snapshot captured concurrently with sensor readings at cruise. | Post-hoc validation vector (withheld during initial blind competition). | Synchronous discrete counter ($t = 1 \dots C_{\max}$). |
| **6. Semantics & Grain** | 21 continuous float measurements; temperatures ($^\circ\text{R}$), pressures ($\text{psia}$), speeds ($\text{rpm}$). | 3 continuous floats; Altitude ($10^3\text{ ft}$), Mach number ($0\dots0.84$), TRA ($20\dots100$). | Integer vector of remaining cycles ($RUL \ge 0$) corresponding 1:1 with test engines. | Discrete integer composite key `(unit_number, time_in_cycles)`. |
| **7. Reliability & Authority** | **Contextual Telemetry**: Corrupted by process and sensor noise; 6 sensors are constant at sea level. | **Authoritative Controls**: Fixed at Sea Level in FD001 ($TRA = 100, Alt \approx 0, Mach \approx 0$). | **Authoritative Ground Truth**: Exact simulated stopping point ($H = 0$). | **Authoritative Key**: Strict contiguity ($1\dots100$) and unbroken monotonic cycle sequence. |
