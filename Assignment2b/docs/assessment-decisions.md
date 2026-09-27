# NASA C-MAPSS Engineering & Governance Decisions

**Domain**: Commercial Turbofan Engine Health Telemetry & Fleet Maintenance Modeling  
**Primary Scope**: Sub-dataset FD001 (100 Training Engines, Run-to-Failure HPC Degradation)  
**Document Purpose**: Documenting Strategic Engineering Decisions, Trade-Offs, Evidence Boundaries, and What the Data Can and Cannot Support  

---

## 1. Decision 1: Establishing Data Foundations Before Predictive Machine Learning

### Engineering Stance
**Do NOT proceed directly to building predictive Remaining Useful Life (RUL) regression models (e.g. LSTMs, random forests, or neural networks) before establishing source reliability, sensor variance profiling, and trajectory validation.**

### Engineering Evidence & Rationale
1. **Uninformative Flatline Channels**: In FD001, **6 of the 21 sensors exhibit zero within-dataset variation** ($\sigma = 0.000$). Feeding all 21 raw columns unvetted into black-box algorithms risks model instability or learning noise artifacts.
2. **Operating Regime Confounding**: In multi-condition datasets (FD002/FD004), sensor variance is dominated by environmental flight regime shifts (altitude, Mach) rather than wear. Premature machine learning without flight condition normalization simply models flight phases rather than engine health.
3. **Exploratory Baseline Requirements**: Initial cycles exhibit engine-to-engine manufacturing variation. Normalizing telemetry against early per-engine baselines is a necessary data foundation step before any predictive modeling.

---

## 2. Decision 2: Evaluating Fleet Lifetime Heterogeneity

### Observed Evidence
Under identical single-condition sea-level flight profiles and a single simulated degradation mechanism (High-Pressure Compressor degradation), simulated engine failure lifetimes vary substantially:
* Minimum Lifespan: **128 cycles**
* Maximum Lifespan: **362 cycles**
* Median Lifespan: **199.0 cycles**
* Sample Mean Lifespan: **206.31 cycles** ($\sigma = 46.34$, $\text{CV} = 22.46\%$)

### Engineering Interpretation & Boundaries
* **What the Data Shows**: The observed variation demonstrates that simulated engine trajectories do not all terminate at the same cycle. Lifetimes span a wide distribution around the mean.
* **What the Data Does NOT Prove**: The dataset does **not** prove that condition-based monitoring is economically superior to fixed-interval maintenance in actual airline operations. Establishing economic superiority or optimal maintenance policies requires maintenance costs, overhaul expenditures, parts logistics, and operational downtime penalties—none of which are present in the C-MAPSS dataset.

---

## 3. Decision 3: Governed Handling of Zero-Variance Sensors

### Engineering Dilemma
In FD001, Sensors 1, 5, 10, 16, 18, and 19 have $\sigma < 10^{-4}$. Should the data pipeline silently drop these columns during ingestion?

### Governed Decision
**Do NOT silently drop columns from the data architecture.**
1. **Preserve Raw Schema**: Ingestion retains all 26 columns in raw and validation stages to preserve complete data provenance and ensure cross-compatibility with FD002–FD004 (where these channels are active under varying flight conditions).
2. **Explicit Quarantine / Masking**: The transformation module explicitly isolates active non-constant sensors (15 channels) from constant channels (6 channels) when computing thermal wear indices.
3. **Failure Contract Transparency**: The validation gate explicitly records the flatline status under `sensor_variance_audit` as `WARN` in `outputs/validation_report.json`.

---

## 4. Decision 4: Deterministic Idempotence as the Minimum Engineering Standard

### Principle
A data foundations pipeline must be deterministically repeatable. Executing the pipeline consecutively on identical raw inputs must produce bit-for-bit identical outputs.

### Technical Scope
* Clean-room verification enforces identical SHA-256 digests across `validation_report.json`, `final_output.csv`, and `metrics.csv`.
* **Important FDE Boundary**: SHA-256 digest equality verifies **deterministic repeatability**. It does **not** prove analytical correctness. Analytical correctness is validated separately through domain assertions and automated unit tests.

---

## 5. Strategic Conclusion: Supported vs. Not Supported by Data

### Supported by Data
* **Simulated Trajectory Structure**: Clear temporal sequence starting at cycle 1, progressing with $\Delta \text{cycle} \equiv 1$ until simulated failure.
* **Sensor Variance Profiling**: Exactly 15 of 21 sensors show variation; 6 sensors are constant under FD001.
* **Correlation with Cycle**: Several sensors (e.g. $T_{50}, P_{s30}, Nc$) correlate systematically with cycle progression ($|r| > 0.50$).
* **Lifespan Dispersion**: Substantial variation in failure cycles ($128$ to $362$ cycles, $\text{CV} = 22.46\%$).
* **Data Quality Traps**: Naive single-space parsing creates two phantom NaN columns; robust regex parsing produces clean 26 columns.
* **Source Reconciliation**: Identification of the documentation/file-count discrepancy in `readme.txt` for FD004.

### NOT Supported by Data
* **Maintenance Economics**: Overhaul costs, inspection costs, or economic trade-offs of maintenance policies.
* **Real-World Safety Risk**: Probability of in-flight engine shutdowns, catastrophic component failures, or airworthiness compliance.
* **Regulatory Thresholds**: FAA or EASA mandated engine removal limits or inspection criteria.
* **Real-World Engine Failure Probability**: Conversion of synthetic run-to-failure cycles into actual calendar flight-hour failure probabilities.
* **Optimal Maintenance Policies**: Quantitative proof of the economic or operational superiority of condition-based monitoring over fixed schedules.
* **Causal Attribution**: Correlation between sensor drift and cycle progression is not proof of physical causation.
