# FlashEats FDE Coursework Completion Report (Classes 5, 6, & 7)

This document certifies the complete, end-to-end execution and analytical findings of the FlashEats Forward Deployed Engineer (FDE) coursework across Classes 5, 6, and 7, adhering strictly to `Agent.md`, course READMEs, and empirical data validation standards. All numbers are derived dynamically from the source datasets.

---

# Class 5 — Fetching Data Using SQL, APIs, and Files

### What Was Completed
- **Source Reasoning**: Evaluated all core entities against the FDE source reasoning framework (`business question → information required → source → ownership → freshness → semantics → reliability`), distinguishing authoritative system contracts from contextual telemetry.
- **SQL & File Ingestion**: Connected to SQLite (`database/flasheats.db`), loaded and parsed `orders`, `customers`, `drivers`, `restaurants`, `support_tickets.csv`, and `driver_events.json` without mutating raw source structures.
- **Problem Sizing (Challenge 1)**: Formulated explicit definitions upfront; deduplicated `orders` on `order_id`; calculated late delivery rate, median lateness, percentile distributions, worst delayed orders, and data-quality gaps.
- **Hypothesis Testing (Challenge 2)**: Tested Operations' claim that *"Traffic is the problem"* across traffic tiers, weather conditions, distance bins, and order hours. Separated association from causation.
- **Customer Support Analysis (Challenge 3)**: Audited `support_tickets.csv` categories, uniqueness, and missing order linkages; synthesized a *System View vs Customer View* friction comparison.
- **Reliable Dispatch API Ingestion (Challenge 4)**: Implemented `fetch_all_dispatch_orders()` with automatic pagination, retry handling for transient HTTP 500 and rate-limiting HTTP 429, raw page response archiving, and programmatic completeness verification.
- **Delay Attribution & Driver Telematics (Challenge 5)**: Flattened `driver_events.json`; audited observed event types; identified the critical unobserved restaurant arrival gap.
- **Executive Synthesis**: Produced a 6-point FDE recommendation slide addressing problem size, evidence, trusted sources, uncertainty, instrumentation recommendations, and the AI predictor build decision.

### Retrieval Sources
- **SQLite Database** (`database/flasheats.db`): `orders` (1,603 rows; 1,600 unique orders), `customers` (900 rows), `drivers` (120 rows), `restaurants` (60 rows).
- **Tabular Files**: `data/support_tickets.csv` (202 rows), `data/restaurant_status.csv` (502 rows), `data/restaurants.csv` (60 rows).
- **Nested JSON**: `data/driver_events.json` (120 driver telemetry streams).
- **REST API**: Mock Dispatch API (`/dispatch/orders`, `/dispatch/orders/<order_id>`, `/health`).

### Retrieval Evidence
- SQL queries and file parsing executed without error.
- Successfully retrieved all tables into pandas DataFrames.
- Verified orders dataset: 1,603 rows deduplicated to 1,600 unique orders; isolated 3 duplicate order IDs (`O00120`, `O00723`, `O01302`) created by conflicting `traffic_bucket` entries.
- Valid delivered population: 1,495 delivered orders with non-null completion timestamps.
- Zero-tolerance lateness (`delay_min > 0`): 843 late orders out of 1,495 (56.39% late delivery rate). Median delay among late orders: 8.03 minutes; 90th percentile: 20.73 minutes.

### Pagination Evidence
- Mock API `/dispatch/orders` consumed with `page_size=50`.
- Pagination traversed exactly 32 consecutive pages (`page=1` to `page=32`), terminating cleanly when `has_more == False`.
- Ingestion completeness programmatically verified: 1,600 records retrieved matches the API response metadata `total_records == 1600` exactly.

### Raw Preservation
- Raw API JSON payloads preserved on disk at `student_output/raw_dispatch/page_1.json` through `page_32.json`.
- Each file retains original API headers, pagination metadata, and nested record structures prior to any transformation.

### Failure Handling
- **HTTP 500 (Temporary Upstream Failure)**: Encountered on `page=3`, attempt 1. Caught via status code inspection; inspected `retryable: true` payload; retried after 0.5s backoff and succeeded on attempt 2.
- **HTTP 429 (Rate Limit Exceeded)**: Encountered on `page=5`, attempt 1. Extracted `retry_after_seconds: 1`; paused execution for the requested duration; retried and succeeded on attempt 2.
- **Unrecoverable Failures**: Capped retry attempts at 5 with explicit error raising if retries exhausted.

### Remaining Limitations
- **Unobserved Restaurant Arrival**: `driver_events.json` contains only `gps_ping`, `assigned`, `picked_up`, and `delivered`. There is NO directly recorded `driver_arrived_at_restaurant` event. Arrival can only be inferred via GPS proximity, which lacks ground-truth accuracy.
- **Unmeasured Kitchen Dwell Time**: Because driver arrival at the merchant is unrecorded, we cannot separate road transit time from kitchen wait time.
- **Missing Delivery Timestamps**: 37 delivered orders lack completion timestamps, introducing denominator sensitivity.

---

# Class 6 — Data Validation

### Validation Contract
Formulated across 5 fundamental business assumptions:
1. **One row = one business order**: Tested via primary key uniqueness on `orders.order_id`. Status: **WARN** (3 duplicate order IDs detected).
2. **Delivered orders have completion time**: Tested via null checks on `actual_delivery_at` where `final_status == 'delivered'`. Status: **WARN** (37 delivered orders missing completion timestamp).
3. **Promised ETA is valid**: Tested via `promised_eta >= created_at`. Status: **FAIL** (4 orders had promised ETA prior to order creation).
4. **Event chronology is valid**: Tested via `created_at <= pickup_at <= actual_delivery_at`. Status: **FAIL** (5 orders had pickup timestamp recorded *after* delivery timestamp).
5. **"Late" has an agreed definition**: Tested against `client_metric_definitions.json`. Status: **UNKNOWN** (no canonical owner documented; stakeholders disagree).

### Key Data-Quality Findings
- **Duplicate Rows**: 3 order IDs (`O00120`, `O00723`, `O01302`) appear twice with conflicting `traffic_bucket` attributes (e.g. `severe` vs `medium`), indicating upstream event fanout during status updates.
- **Missing Completion Timestamps**: 37 orders marked `delivered` have `NaN` for `actual_delivery_at`.
- **Chronology Inversions**: 4 orders feature ETAs preceding order creation; 5 orders show physical delivery occurring before driver pickup.

### KPI-Definition Issue
Calculated late rates across stakeholder definitions:
- **Historical Dashboard / VP Ops** (`delay_min > 0`, non-null delivered): **56.39%** (843 / 1,495). Zero tolerance: a delivery 1 second late is counted late.
- **Support Lead** (`delay_min > 10`, non-null delivered): **23.34%** (349 / 1,495). Grace period: only delays over 10 minutes generate customer dissatisfaction.
- **All Delivered Orders** (denominator includes 37 missing timestamps): **55.03%** (843 / 1,532).
- **All Placed Orders** (denominator includes cancellations): **52.69%** (843 / 1,600).
- **Core Dilemma**: The "56% Late Rate" claim is entirely definition-dependent. Because `client_metric_definitions.json` explicitly states *"No canonical KPI owner is formally documented,"* publishing 56% without executive consensus is misleading.

### Category Semantics
- **Representation Differences (Safe to Normalize)**:
  - `orders.final_status`: `'Delivered'` (5) vs `'delivered'` (1530) — casing variance.
  - `orders.traffic_bucket`: `'HIGH'` (3) vs `'high'` (448) — casing variance.
  - `restaurant_status.status`: `'READY'`, `'Ready'`, `'ready '` vs `'ready'` — casing/trailing whitespace.
  - `support_tickets.category`: `'Late Delivery'`, `'late_delivery '` vs `'late_delivery'` — casing/whitespace.
- **Semantic Differences (UNSAFE to normalize without owner confirmation)**:
  - `restaurant_status.status`: `'handoff'` (1) vs `'handed_off'` (168) — may represent in-progress action vs completed state.
  - `restaurant_status.status`: `'unknown'` (1) — explicit unmapped state.
  - `support_tickets.category`: `'ETA issue'` (1) vs `'eta_changed'` (37) — could indicate app UI glitch rather than ETA calculation drift.

### Cross-Source Validation
- `orders.restaurant_id → restaurants.restaurant_id`: **100.00%** coverage (PASS).
- `orders.driver_id → drivers.driver_id`: **100.00%** coverage (PASS).
- `tickets.order_id → orders.order_id`: **98.51%** coverage (WARN — 3 tickets have `NaN` order_id).
- `restaurant_status.order_id → orders.order_id`: **100.00%** foreign key validity, but only covers **31.38%** of orders (502 out of 1,600 orders) (WARN).
- **Is 1% unmapped acceptable?**: Strictly decision-dependent. For high-level volume reporting, 1% missingness is negligible. For customer churn, dispute resolution, or fraud audits, 1% missingness represents severe blind spots.

### Freshness Findings
- Evaluated `restaurant_status.last_updated_at` against order lifecycle timestamps:
  - Average update latency from creation: 15.92 minutes (range: -354 min to +35 min).
  - Negative lags (updates logged before order creation) indicate clock drift or timezone misconfiguration.
  - **In 33.07% of orders (166 / 502), the restaurant status was updated *after* the driver had already picked up the food**.
- **SLA Suitability**:
  - *Weekly analytics*: WARN (acceptable latency for batch trends, but crippled by 31.4% coverage).
  - *Live customer ETA*: **FAIL** (completely unsafe; 33% update lag misleads customer live tracking).
  - *Restaurant accountability*: **FAIL** (unsafe; lagging timestamps would trigger false penalty disputes).

### Final Validation Gate & Publishability of 56%
| Check | Status | Evidence | Action |
|---|---|---|---|
| Business grain | **WARN** | 3 duplicate order IDs (`O00120`, `O00723`, `O01302`) | Deduplicate deterministically; patch upstream event ingestion. |
| Timestamp chronology | **FAIL** | 4 bad ETAs, 5 inverted pickups, 37 missing completion timestamps | Enforce database check constraints; audit driver app event capture. |
| KPI definition | **UNKNOWN** | No documented KPI owner; rates range from 23.3% to 56.4% | Appoint Executive KPI Owner; ratify canonical definition. |
| Category semantics | **WARN** | Casing discrepancies; ambiguous `handoff` and `unknown` | Normalize safe representations; confirm semantic edge cases with merchant lead. |
| Cross-source mapping | **WARN** | 3 tickets lack order_id; 68.6% of orders lack kitchen status | Mandate order_id on ticket intake; expand merchant tablet rollout. |
| Freshness | **FAIL** | 33% of status updates logged post-pickup; clock skew up to -354 min | Reject status updates for real-time customer ETA and merchant SLAs. |
| **Publish 56%** | **FAIL** | Metric relies on an unowned, disputed zero-tolerance formula | **DO NOT PUBLISH TODAY.** |

**Verdict**: Leadership must **NOT publish 56% today**. It is an unratified, zero-tolerance metric with known data-quality confounds.

---

# Class 7 — Model the Business Workflow with Data

### Workflow Model
Rather than treating tables as disconnected CSVs, data is structured along the natural business lifecycle:
`Order Placement → Kitchen & Driver Lifecycle Events → Customer Interaction → Operational Intervention → Order Outcome`

### Order-Level Model
- **Pre-Aggregation**: One-to-many tables (`customer_app_actions`, `support_tickets`, `order_interventions`) were aggregated to the `order_id` grain prior to joining, completely eliminating Cartesian join multiplication.
- **Canonical Model Schema**:
  `order_id, customer_id, support_opened, cancel_attempted, intervention_count, intervention_types, final_status, late_flag, delay_min`
- **Grain Verification**: Exactly 1,600 rows, 1,600 unique `order_id`s, 0 duplicate rows (Verified 1 row = 1 order).

### Customer Interaction Findings
- **Late Orders with Support Interaction**: 163 out of 843 late orders (**19.34%**).
  - *WHAT THE DATA SHOWS*: Approximately 1 in 5 late customers actively reached out to support or clicked help.
  - *WHAT THE DATA DOES NOT PROVE*: Does not prove the remaining 80.66% were happy; silent customer dissatisfaction is unmeasured.
- **Support Delay Elevation**: Orders with support interactions averaged **10.99 minutes of delay** (median 11.43 min), compared to **1.93 minutes** (median 0.50 min) for orders without support.
  - *WHAT THE DATA SHOWS*: Support interactions are concentrated in severely delayed deliveries.
  - *WHAT THE DATA DOES NOT PROVE*: Support contact does not cause delay; delay causes support contact (reverse causality).

### Intervention Findings
- **Total Orders Receiving Intervention**: 430 out of 1,600 orders (**26.88%**).
- **Most Common Intervention**: `DRIVER_REASSIGNMENT` (155), followed by `RESTAURANT_CONTACT` (116), `PRIORITY_DISPATCH` (95), and `CUSTOMER_CREDIT` (64).
- **Unassisted Frustrated Journeys**: **149 orders** featured customer friction (`support_opened == 1` or `cancel_attempted == 1`) but received **0 operational interventions**.
  - *WHAT THE DATA SHOWS*: A substantial population of struggling customers experienced zero operational remediation.
  - *WHAT THE DATA DOES NOT PROVE*: Does not prove deliberate operational neglect; indicates operational silos between support ticketing and dispatch tools.
- **Intervention Efficacy & Adverse Selection**:
  - Late rate with intervention: **56.44%** (228 / 404).
  - Late rate without intervention: **56.37%** (615 / 1,091).
  - *WHAT THE DATA SHOWS*: Late rates are identical between intervened and non-intervened orders.
  - *WHAT THE DATA DOES NOT PROVE*: Does NOT mean interventions fail. Interventions are applied reactively to orders already in severe delay (adverse selection); without intervention, their late rate would likely be much higher.
  - Performance by type: `PRIORITY_DISPATCH` achieved the lowest late rate (**51.16%**), whereas post-facto `CUSTOMER_CREDIT` had the highest (**66.67%**).

### Outcome Findings
- 843 orders delivered late (56.39% of evaluated delivered orders).
- Concentration by merchant: Top 5 restaurants (`R050`, `R004`, `R051`, `R024`, `R023`) account for 102 late orders (~12% of total late orders).

### Selected Business Metrics
1. **Late Delivery Rate (Primary Outcome Metric)**
   - *Formula*: `Count(orders with delay_min > 0) / Count(delivered orders with non-null actual_delivery_at)`
   - *Grain*: Order Outcome
   - *Value*: **56.39%**
   - *Why It Matters*: Core contract delivery commitment.
   - *KPI Linkage*: The exact project KPI to be reduced.
2. **Customer Friction Rate (Interaction Metric)**
   - *Formula*: `Count(orders with support_opened == 1 or cancel_attempted == 1) / Count(total orders)`
   - *Grain*: Order Customer Interaction
   - *Value*: **12.56%** (201 / 1,600)
   - *Why It Matters*: Quantifies direct customer dissatisfaction and risk of app churn.
   - *KPI Linkage*: Reducing delivery delays directly eliminates customer app anxiety and support costs.
3. **Operational Intervention Rate (Workflow Metric)**
   - *Formula*: `Count(orders with intervention_count > 0) / Count(total orders)`
   - *Grain*: Order Operations
   - *Value*: **26.88%** (430 / 1,600)
   - *Why It Matters*: Measures operational friction and manual workload on dispatchers.
   - *KPI Linkage*: A stable, predictable logistics pipeline reduces the need for emergency manual interventions.
4. **Intervention Rescue Rate (Operational Recovery Metric)**
   - *Formula*: `Count(intervened orders delivered on time) / Count(evaluated intervened orders)`
   - *Grain*: Order Intervention Recovery
   - *Value*: **43.56%** (176 / 404)
   - *Why It Matters*: Measures operational effectiveness in successfully recovering at-risk orders before dropoff.
   - *KPI Linkage*: Directly drives down the late delivery rate by converting endangered orders into on-time completions.

### Limitations
- **Missing Kitchen vs Transit Boundary**: Without a recorded `driver_arrived_at_restaurant` timestamp, operations cannot decompose pre-pickup time into travel delay vs kitchen dwell time.
- **Support-Dispatch Disconnection**: Support tickets are unlinked from automated dispatch triggers, allowing 149 frustrated journeys to slip through without intervention.

---

# Files Changed

| File | Status | Description |
|---|---|---|
| `FlashEats_Class5_Student.ipynb` | **MODIFIED** | Completed all Class 5 challenges, source mapping table, SQL problem sizing, traffic hypothesis testing, support ticket analysis, paginated API ingestion with retry/preservation, driver event attribution, and final executive slide. Fully executed with persisted outputs. |
| `FlashEats_Class6_Student.ipynb` | **MODIFIED** | Completed all Class 6 challenges, validation contract, targeted executable checks, stakeholder definition comparisons, representation vs semantic category auditing, foreign key coverage calculations, freshness SLA evaluation, and final validation gate report. Fully executed with persisted outputs. |
| `FlashEats_Class7_Challenge.ipynb` | **MODIFIED** | Completed all Class 7 challenges, multi-source order lifecycle reconstruction (`build_order_timeline`), relational model architecture, pre-aggregated order-level table (1,600 rows, 0 duplicates), data answers to 4 business questions, 4 operational metrics, workflow investigations (A-E) with *What the data shows vs What the data does not prove*, and one-page KPI hierarchy. Fully executed with persisted outputs. |
| `student_output/raw_dispatch/page_1.json` ... `page_32.json` | **CREATED / VERIFIED** | All 32 raw API JSON response pages preserved on disk verifying complete ingestion of 1,600 records. |
| `CLASS_5_6_7_COMPLETION.md` | **CREATED** | Comprehensive final coursework summary report strictly adhering to `Agent.md`. |
