# FlashEats — Operational Delivery Reliability

## 1. Problem

On-demand delivery platform FlashEats experienced an increase in late delivery complaints, with customers reporting unreliable estimated times of arrival (ETAs). Operations and leadership required a dependable analytical investigation to understand where delivery delays accumulate across the fulfillment workflow, how customer friction escalates, and how operational remedies interact with late deliveries.

This assessment performs a comprehensive data foundations investigation: establishing source provenance, validating schemas and timestamps, identifying telemetry blind spots, and determining whether operational data is dependable enough to govern business metrics and support automated dispatch or prediction.

---

## 2. Stakeholders

The assessment investigates the operational problem across five primary stakeholder domains:

| Stakeholder Domain | Operational Focus | Primary Decision Need |
|---|---|---|
| **Operations / Leadership** | Platform fulfillment and delivery SLA compliance. | Determining true late delivery prevalence and evaluating fulfillment telemetry dependability. |
| **Customer Support / CX** | In-flight customer friction and compensation costs. | Understanding customer complaint thresholds and ticket escalation drivers. |
| **Restaurant Operations** | Merchant kitchen prep times and food readiness. | Evaluating kitchen display status update latency and handoff bottlenecks. |
| **Driver / Dispatch Operations** | Courier transit times, fleet availability, and routing. | Assessing dispatch matching, transit vs. dwell duration, and road congestion. |
| **Data Platform / Analytics** | Warehouse integrity, schema contracts, and metrics. | Enforcing clean-room reproducibility, zero Cartesian fanout, and data quality contracts. |

---

## 3. KPI / Business Question

Executive leadership initiated this investigation citing an unverified metric:
> *"Late Delivery Rate is 56%."*

### KPI Governance & Denominator Sensitivity
Empirical analysis demonstrates that **56.39% is not an established corporate fact**, but rather an unowned candidate definition that is highly sensitive to denominator choices and tolerance buffers:

| Candidate Definition | Formula | Numerator | Denominator | Calculated Rate | Governance Status |
|---|---|---|---|---|---|
| **Zero-Tolerance Delivered (VP Ops)** | `delay > 0 min` on delivered orders with valid delivery timestamp | 843 | 1,495 | **56.39%** | `UNRATIFIED` |
| **All Delivered Orders** | `delay > 0 min` across all delivered orders (including missing delivery timestamps) | 843 | 1,532 | **55.03%** | `UNRATIFIED` |
| **Total Placed Orders** | `delay > 0 min` across total orders placed (including 68 cancellations) | 843 | 1,600 | **52.69%** | `UNRATIFIED` |
| **Friction Buffer (Support Lead)** | `delay > 10 min` on delivered orders with valid delivery timestamp | 349 | 1,495 | **23.34%** | `UNRATIFIED` |

### Governance Finding
`data/client_metric_definitions.json` explicitly states: *"No canonical KPI owner is formally documented."* Publishing 56% without executive consensus conceals that 37 delivered orders lack completion timestamps and that delays under 10 minutes rarely trigger customer complaints. Official KPI publication must be halted until an appointed Executive KPI Owner ratifies the standard formula.

---

## 4. Data Sources

The FlashEats data landscape spans operational databases, file extracts, event streams, and REST endpoints:

| Data Entity | Physical Source | Business Grain | Primary Operational Role |
|---|---|---|---|
| **`orders`** | SQLite (`database/flasheats.db`) | 1 row per order attempt | Core transaction table: customer, restaurant, courier, promised ETA, and delivery timestamps. |
| **`customers`** | SQLite (`database/flasheats.db`) | 1 row per customer | Customer master profile, signup date, and location coordinates. |
| **`drivers`** | SQLite (`database/flasheats.db`) | 1 row per courier | Registered courier fleet, vehicle type, rating, and tenure. |
| **`restaurants`** | SQLite (`database/flasheats.db`) | 1 row per restaurant partner | Merchant profile, cuisine type, coordinates, and operational tier. |
| **`restaurant_status`** | CSV (`data/restaurant_status.csv`) | 1 row per merchant status update | Merchant self-reported kitchen progression (`preparing`, `ready`, `handed_off`). |
| **`driver_events`** | JSON (`data/driver_events.json`) | 1 stream per courier | Courier mobile telemetry: GPS coordinates, assignment, pickup, and delivery timestamps. |
| **`customer_app_actions`**| CSV (`data/customer_app_actions.csv`) | 1 row per in-app user action | Mobile app interactions (`ETA_VIEWED`, `CANCEL_ATTEMPTED`, `SUPPORT_CONTACTED`). |
| **`support_tickets`** | CSV (`data/support_tickets.csv`) | 1 row per support ticket | Customer complaints, issue category, and qualitative escalation text. |
| **`order_interventions`** | CSV (`data/order_interventions.csv`) | 1 row per operational remedy | Remedial actions applied (`PRIORITY_DISPATCH`, `DRIVER_REASSIGNMENT`, `CUSTOMER_CREDIT`). |
| **`order_outcomes`** | CSV (`data/order_outcomes.csv`) | 1 row per completed order | Evaluated SLA fulfillment flags (`delivered_flag`, `late_flag`, `delay_min`). |
| **`dispatch_api`** | REST API (`/dispatch/orders`) | Paginated JSON payload | Live dispatch assignment telemetry consumed with automated pagination and retry. |

---

## 5. Validation

Data quality was audited using a formal FDE failure contract (`PASS`, `WARN`, `FAIL`, `UNKNOWN`):

| Validation Check | Expected Behavior | Observed Result | Severity | Status |
|---|---|---|---|:---:|
| **Composite Grain Uniqueness** | `order_id` is unique primary key | **3 duplicate rows** (`O00120`, `O00723`, `O01302`) with conflicting `traffic_bucket` values. | High | **`WARN`** |
| **Completion Timestamps** | Delivered orders have delivery timestamps | **37 delivered orders** have `NaN` for `actual_delivery_at` (2.42% of delivered volume). | High | **`WARN`** |
| **Promised ETA Validity** | Promised ETA occurs after order creation | **4 orders** have `promised_eta < created_at` (up to -20 min inverted). | High | **`WARN`** |
| **Event Chronology** | Sequence: `created <= pickup <= delivered` | **5 orders** show delivery recorded before driver pickup. | High | **`WARN`** |
| **Cross-Source Linkages** | Foreign keys match upstream entities | 100% on restaurants and drivers; **3 support tickets lack `order_id`**. | Medium | **`WARN`** |
| **Update Freshness** | Merchant updates precede physical pickup | **33.07% of status updates** (166 / 502) logged *after* driver pickup. | Critical | **`FAIL` for Live ETA** / **`WARN` for Batch** |
| **KPI Ownership** | Formally documented corporate KPI owner | *"No canonical KPI owner is formally documented."* | Critical | **`UNKNOWN`** |

*Note on Duplicate Resolution*: Duplicates are quarantined in `outputs/validation_report.json` under `quarantine.duplicate_orders` and resolved via deterministic selection (`keep='first'`), producing exactly 1,600 unique canonical orders.

---

## 6. Workflow Model

Joining raw one-to-many tables (`customer_app_actions` with 2,365 rows, `support_tickets` with 202 rows, `order_interventions` with 430 rows) directly to `orders` creates severe **Cartesian join fanouts**, multiplying row counts and distorting financial metrics.

### Pre-Aggregation Requirement
The pipeline pre-aggregates all 1-to-many tables to the `order_id` grain prior to merging:
1. `customer_app_actions` $\rightarrow$ aggregated to `cancel_attempted` (binary) and `support_opened_app` (binary).
2. `support_tickets` $\rightarrow$ aggregated to `support_opened_ticket` (binary) and ticket counts.
3. `order_interventions` $\rightarrow$ aggregated to `intervention_count` (integer) and `intervention_types` (concatenated string).

The resulting canonical table (`outputs/final_output.csv`) maintains exact grain invariance:
$$\text{len}(\text{canonical\_output}) = \text{orders['order\_id'].nunique()} = 1,600 \text{ rows (0 duplicates)}$$

---

## 7. Metrics

The project derives four governed operational metrics exported to `outputs/metrics.csv`:

| Metric Name | Formula | Population / Grain | Value | Status | Operational Interpretation | Explicit Limitation |
|---|---|---|:---:|:---:|---|---|
| **`late_delivery_rate`** | $\frac{\text{count}(\text{delay} > 0)}{N_{\text{delivered, non-null}}} \times 100$ | Delivered orders with completion time ($N=1,495$) | **56.39%** | `UNRATIFIED` | Percentage of delivered orders exceeding promised ETA at zero tolerance. | Silently excludes 37 missing timestamps; unratified KPI. |
| **`customer_friction_rate`** | $\frac{\text{count}(\text{support} \lor \text{cancel})}{N_{\text{total\_orders}}} \times 100$ | Total unique orders placed ($N=1,600$) | **12.56%** | `OBSERVATIONAL` | Proportion of orders where customer opened support or attempted cancellation ($201 / 1,600$). | Measures app and ticket friction; does not capture silent customer dissatisfaction. |
| **`operational_intervention_rate`** | $\frac{\text{count}(\text{interventions} \ge 1)}{N_{\text{total\_orders}}} \times 100$ | Total unique orders placed ($N=1,600$) | **26.88%** | `OBSERVATIONAL` | Proportion of orders receiving at least one operational remedy ($430 / 1,600$). | Reflects operational effort; subject to adverse selection. |
| **`intervention_rescue_rate`** | $\frac{\text{count}(\text{intervened} \land \text{on-time})}{N_{\text{intervened, valid}}} \times 100$ | Intervened delivered orders ($N=404$) | **43.56%** | `OBSERVATIONAL` | Percentage of intervened orders successfully delivered on-time ($176 / 404$). | Observational recovery rate; not causal proof of efficacy. |

---

## 8. Key Findings

All findings are supported directly by the validated pipeline outputs:

1. **Late Delivery is Denominator-Dependent**: The late delivery rate ranges from **23.34%** (under a 10-minute customer friction buffer) to **56.39%** (under zero tolerance), demonstrating that perceived platform lateness is driven by business tolerance definitions.
2. **Interventions Experience Adverse Selection**: Orders receiving interventions show a **43.56%** on-time completion rate versus **43.63%** on-time completion for orders without intervention. 
   > *Governance Caveat*: This is an observational comparison and does **not** establish intervention ineffectiveness. Operations applies interventions reactively to orders already in severe delay jeopardy; without intervention, on-time rates among this troubled cohort would likely have been substantially lower.
3. **Customer Friction Concentrates on Severe Delays**: Over 80% of support contacts and cancellation attempts occur when orders exceed 15 minutes of delay.
4. **Merchant Status Logging Lags Physical Reality**: In 33.07% of tracked orders, merchants logged status updates after the driver had already departed with the food.

---

## 9. Important Data Gaps

The investigation identified critical data gaps that constrain operational analysis:

1. **Unobserved Restaurant Arrival**: `driver_events.json` records courier assignment, pickup, and delivery, but contains **no directly observed `driver_arrived_at_restaurant` event**. Total time between assignment and pickup cannot be partitioned into courier transit vs. kitchen wait time.
2. **Missing Delivery Timestamps**: 37 delivered orders lack completion timestamps, introducing denominator uncertainty.
3. **Clock Drift in Merchant Telemetry**: Negative time differences between restaurant updates and order creation indicate uncalibrated device clocks on merchant hardware.
4. **Unlinked Support Tickets**: 3 support tickets lack `order_id` values, preventing attribution to specific orders.

---

## 10. Pipeline Architecture

The dependable data pipeline executes sequentially without circular dependencies:

```
RAW INPUTS (Database, CSVs, JSON, Dispatch API)
   ↓
INGESTION (pipeline/ingest.py: extract SQLite, load CSVs, paginate API with retry)
   ↓
VALIDATION (pipeline/validate.py: audit grain, chronology, freshness, quarantine duplicates)
   ↓
TRANSFORMATION (pipeline/transform.py: pre-aggregate 1-to-many tables, join canonical model)
   ↓
METRICS (pipeline/metrics.py: compute candidate operational metrics, assign governance)
   ↓
REPRODUCIBLE OUTPUTS (outputs/final_output.csv, metrics.csv, validation_report.json, log)
```

---

## 11. Reproducibility

Execute the complete end-to-end pipeline:
```powershell
python pipeline/run_pipeline.py
```

Execute the automated test suite:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

*Verification Standard*: Matching SHA-256 hashes across consecutive runs demonstrate **deterministic repeatability** of the pipeline outputs; they do not establish business correctness.

---

## 12. Limitations

* **Single-City Sample**: The dataset reflects an isolated operational sample ($1,600$ orders) and cannot be generalized to other markets without validation.
* **Non-Randomized Remedies**: Because operational interventions are triggered reactively, their causal impact cannot be evaluated without controlled A/B experimentation.
* **Unobserved In-Store Bottlenecks**: Telemetry does not track food bagging, kitchen queue length, or handoff counter congestion.

---

## 13. Repository Structure

```text
flasheats/
├── README.md                          # Primary project documentation
├── api/
│   ├── mock_dispatch_api.py           # REST API mock server with rate-limiting and retry simulation
│   ├── dispatch_data.json             # Seed records for mock dispatch API
│   └── requirements.txt               # API dependencies
├── data/                              # Operational data files
│   ├── raw/
│   │   └── dispatch/                  # Preserved raw paginated API response pages (pages 1-32)
│   ├── customer_app_actions.csv
│   ├── customer_interactions.csv
│   ├── driver_events.json
│   ├── order_events.csv
│   ├── order_interventions.csv
│   ├── order_outcomes.csv
│   ├── restaurant_status.csv
│   ├── restaurants.csv
│   └── support_tickets.csv
├── database/
│   └── flasheats.db                   # SQLite transactional database
├── docs/                              # Technical governance documentation
│   ├── assessment-decisions.md        # Architectural decisions and AI model rejection memo
│   ├── source-map.md                  # 7-dimension source reasoning and authority matrix
│   ├── validation-report.md           # Executable validation gate and failure contract
│   └── workflow-model.md              # Lifecycle model and anti-fanout join strategy
├── outputs/                           # Generated pipeline outputs
│   ├── final_output.csv               # Canonical order-level dataset (1,600 rows, 0 duplicates)
│   ├── metrics.csv                    # Governed candidate operational metrics
│   ├── pipeline.log                   # Execution audit log
│   └── validation_report.json         # Executable validation gate report
├── pipeline/                          # Modular production pipeline code
│   ├── config.py                      # Paths, endpoints, and structured logging
│   ├── ingest.py                      # Multi-source extraction and resilient API pagination
│   ├── validate.py                    # Formal validation gate and duplicate quarantine
│   ├── transform.py                   # Pre-aggregated joins and grain preservation
│   ├── metrics.py                     # Metric derivation and governance tagging
│   └── run_pipeline.py                # Idempotent orchestrator
└── tests/
    └── test_pipeline.py               # Automated unit and integration test suite
```

All documentation links are relative:
* [docs/source-map.md](docs/source-map.md)
* [docs/validation-report.md](docs/validation-report.md)
* [docs/workflow-model.md](docs/workflow-model.md)
* [docs/assessment-decisions.md](docs/assessment-decisions.md)

---

## 14. Final Decision

**FlashEats telemetry does not currently provide a dependable foundation for automated delay prediction or algorithm-driven dispatch.**

Because courier arrival at the restaurant is unobserved in telemetry, the duration between assignment and pickup is an indivisible black box. A predictive model trained on the current telemetry could confound courier transit with unobserved restaurant wait time, making attribution and downstream ETA decisions unreliable. The resulting predictions could be unreliable because a key part of the pre-pickup workflow is unobserved.

**Strategic Recommendation**: FlashEats must first implement automated restaurant arrival beacons (e.g. BLE / geofencing) and merchant kitchen ready confirmations. **Fix physical instrumentation and telemetry boundaries before building predictive models.**
