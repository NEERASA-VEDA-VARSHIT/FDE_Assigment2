# NASA C-MAPSS Governed Analytical Metrics (Class 7)

**Domain**: Commercial Turbofan Engine Health Telemetry  
**Primary Dataset**: Sub-dataset FD001 (100 Training Engines, 20,631 Operational Cycles)  
**Execution Artifact**: `outputs/metrics.csv`  
**Document Purpose**: Documenting the Formulas, Analytical Grains, Governance Statuses, Interpretations, and Honest Limitations for all 5 Project Metrics  

---

## 1. Metrics Governance Principles

In Forward Deployed Engineering, derived analytical figures must not be presented as official Key Performance Indicators (KPIs) unless an authorized organizational decision-maker has ratified the definition and tied it to operational decisions. 

In this assessment:
* All 5 metrics are designated as **Candidate Operational Metrics** or **Analytical Indicators**.
* Every metric is assigned an explicit FDE governance status:
  - **`FACT`**: Mathematically or technically provable property of the dataset schema or file structure.
  - **`OBSERVATIONAL`**: Empirically measured descriptive statistic of the simulated fleet.
  - **`UNRATIFIED`**: Analytical segmentation or threshold-dependent indicator defined by the engineer for exploratory study.
  - **`UNKNOWN`**: Metric requires real-world operational or economic context not present in the dataset.

---

## 2. Governed Metrics Definition & Summary

### 2.1 Metric Definition & Governance Hierarchy

| Metric | Formula | Grain | Status | Purpose |
|---|---|:---:|:---:|---|
| **Non-constant sensor ratio** | $\frac{\text{count}(\sigma \ge 10^{-4})}{N_{\text{sensors}}} \times 100$ | Dataset | `FACT` | Data variation |
| **Lifespan CV** | $\frac{s_{\text{lifespan}}}{\bar{C}_{\text{fail}}} \times 100$ | Engine | `OBSERVATIONAL` | Lifecycle variability |
| **Critical exposure** | $\frac{\text{count}(\text{RUL} \le 30)}{N_{\text{total\_cycles}}} \times 100$ | Engine-cycle | `UNRATIFIED` | Exploratory lifecycle view |
| **Advisory exposure** | $\frac{\text{count}(30 < \text{RUL} \le 60)}{N_{\text{total\_cycles}}} \times 100$ | Engine-cycle | `UNRATIFIED` | Exploratory lifecycle view |
| **Trajectory completeness** | $\frac{N_{\text{complete\_engines}}}{N_{\text{total\_engines}}} \times 100$ | Engine | `FACT` | Data completeness |

### 2.2 Governed Metrics Summary Table (`outputs/metrics.csv`)

| Metric Name | Formula | Analytical Grain | Status | Value | Operational Interpretation | Explicit Limitation |
|---|---|---|:---:|---:|---|---|
| **`non_constant_sensor_ratio`** | $\frac{\text{count}(\sigma \ge 10^{-4})}{N_{\text{sensors}}} \times 100$ | Dataset Schema (21 sensors) | `FACT` | **71.43%** | 15 of 21 sensors show within-dataset variation under FD001; 6 channels are constant. | Non-constant variance indicates measurement variation, not physical diagnostic causation. |
| **`lifespan_coefficient_of_variation`** | $\frac{s_{\text{lifespan}}}{\bar{C}_{\text{fail}}} \times 100$ | Engine Fleet ($N=100$ engines) | `OBSERVATIONAL` | **22.46%** | Simulated engine trajectories terminate across a wide span (128 to 362 cycles). | Descriptive measure of simulated spread; does not prove maintenance economics or real-world policy. |
| **`critical_lifecycle_exposure`** | $\frac{\text{count}(\text{RUL} \le 30)}{N_{\text{total\_cycles}}} \times 100$ | Engine-Cycle Snapshot ($N=20,631$) | `UNRATIFIED` | **15.03%** | Fraction of training records occurring within 30 cycles of simulated failure endpoint ($3,100 / 20,631$). | Analytical lifecycle segmentation only; threshold of 30 cycles is not validated for operational maintenance. |
| **`advisory_lifecycle_exposure`** | $\frac{\text{count}(30 < \text{RUL} \le 60)}{N_{\text{total\_cycles}}} \times 100$ | Engine-Cycle Snapshot ($N=20,631$) | `UNRATIFIED` | **14.54%** | Fraction of training records occurring within the 31–60 cycle window prior to endpoint ($3,000 / 20,631$). | Analytical lifecycle segmentation only; threshold is an exploratory analytical boundary. |
| **`trajectory_completeness_rate`** | $\frac{N_{\text{complete\_engines}}}{N_{\text{total\_engines}}} \times 100$ | Engine Trajectory ($N=100$ engines) | `FACT` | **100.00%** | All 100 training engines have unbroken, contiguous cycle sequences starting at cycle 1. | Confirms simulated sequence integrity, but does not provide elapsed calendar or flight hours. |

---

## 3. In-Depth Metric Technical Specifications

### Metric 1: Non-Constant Sensor Ratio
* **Objective**: Measure the proportion of sensor channels that exhibit non-zero within-dataset variance under single-regime sea-level operation.
* **Calculation**:
  - Total sensors evaluated: 21 (`sensor_1` through `sensor_21`).
  - Active channels ($\sigma \ge 10^{-4}$): 15 sensors (`sensor_2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21`).
  - Constant channels ($\sigma < 10^{-4}$): 6 sensors (`sensor_1, 5, 10, 16, 18, 19`).
  - Ratio: $15 / 21 = 71.43\%$.
* **Status**: **`FACT`**
* **Limitation**: While non-constant variance is necessary for a sensor to carry wear information, variance alone does not prove that the sensor is physically tracking compressor degradation.

---

### Metric 2: Lifespan Coefficient of Variation (CV)
* **Objective**: Quantify the relative dispersion of simulated run-to-failure endpoints across identical engines under identical nominal operating conditions.
* **Calculation**:
  - Sample mean ($\bar{C}$): **206.31 cycles**.
  - Sample standard deviation ($s$, with $\text{ddof}=1$): **46.34 cycles**.
  - Minimum lifespan: **128 cycles**; Maximum lifespan: **362 cycles**.
  - $\text{CV} = (46.34 / 206.31) \times 100 = \mathbf{22.46\%}$.
* **Status**: **`OBSERVATIONAL`**
* **Limitation**: Demonstrates that simulated trajectories do not all terminate at the same cycle. Whether this variation justifies condition-based monitoring over fixed-interval maintenance in actual airline operations requires maintenance costs, unscheduled removal penalties, and component overhaul data not present in C-MAPSS.

---

### Metric 3: Critical Lifecycle Exposure
* **Objective**: Quantify the proportion of operational telemetry snapshots captured during late-life engine operation.
* **Calculation**:
  - Numerator: Records where $\text{RUL} \le 30$ cycles = $31 \text{ cycles} \times 100 \text{ engines} = \mathbf{3,100 \text{ records}}$.
  - Denominator: Total training records = **20,631 records**.
  - Value: $3,100 / 20,631 = \mathbf{15.03\%}$.
* **Status**: **`UNRATIFIED`**
* **Limitation**: The 30-cycle cutoff is an arbitrary analytical threshold selected for exploratory segmentation. It has not been validated by airline maintenance engineers or regulatory safety authorities as a real-world maintenance trigger.

---

### Metric 4: Advisory Lifecycle Exposure
* **Objective**: Quantify the proportion of operational telemetry snapshots captured during an intermediate wear window.
* **Calculation**:
  - Numerator: Records where $30 < \text{RUL} \le 60$ cycles = $30 \text{ cycles} \times 100 \text{ engines} = \mathbf{3,000 \text{ records}}$.
  - Denominator: Total training records = **20,631 records**.
  - Value: $3,000 / 20,631 = \mathbf{14.54\%}$.
* **Status**: **`UNRATIFIED`**
* **Limitation**: Analytical window definition only. Real-world maintenance planning requires scheduling lead times based on parts availability and hangar capacity, which are not modeled in this simulation.

---

### Metric 5: Trajectory Completeness Rate
* **Objective**: Verify whether engine trajectories satisfy temporal continuity requirements without missing or skipped cycles.
* **Calculation**:
  - 100 out of 100 engines start at cycle 1 and increment with $\Delta \text{cycle} \equiv 1$ until the terminal cycle.
  - Value: $100 / 100 = \mathbf{100.00\%}$.
* **Status**: **`FACT`**
* **Limitation**: Confirms internal sequence completeness within the synthetic simulation dataset; does not provide real-world elapsed time (hours, minutes) per cycle.
