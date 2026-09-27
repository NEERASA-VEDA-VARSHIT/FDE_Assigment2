# FlashEats Data Validation & Quality Audit Report (Class 6 & Assessment 2)

## Executive Summary
Data validation in an FDE context is **decision-dependent**. The central inquiry is not:
> *"How do we clean this dataframe to look tidy?"*

Rather, the FDE asks:
> *"Is this data safe enough to support this business decision, what remains unresolved, and who must govern the business rules?"*

This report audits the FlashEats operational datasets, details the validation contract, resolves the **56.39% vs. 55.03% KPI discrepancy**, evaluates category semantics and freshness SLAs, and establishes the operational failure contract.

---

## 1. The FDE Failure Contract

| Status | Policy Definition | Pipeline Action | Example Anomaly |
|---|---|---|---|
| **PASS** | Data conforms cleanly to technical and semantic expectations. | Proceed without modification. | 100% foreign key mapping from orders to registered restaurants. |
| **WARN** | Non-fatal anomaly detected. Data remains usable for documented batch modeling with explicit limitations. | Log warning, quarantine offending records, apply deterministic remediation, proceed. | 3 duplicate order IDs quarantined; 37 delivered orders missing completion times. |
| **FAIL** | Critical data corruption or missingness that invalidates a specific business use-case. | For scoped use cases: mark output as **UNSAFE**.<br>For pipeline execution: halt if ingestion is incomplete. | API record count mismatch halts pipeline; 33% post-pickup update lag marks live ETA as UNSAFE. |
| **UNKNOWN** | Ambiguity in business rules or KPI definitions lacking documented ownership. | Calculate candidate alternatives; designate metric status as **UNRATIFIED**; do not declare a canonical metric. | Divergent stakeholder definitions of "Late Delivery Rate". |

---

## 2. Validation Contract & Targeted Executable Checks

| Validation Assumption | Data Expectation | Executable Check | Observed Result | Severity | Pipeline Status |
|---|---|---|---|---|---|
| **1. Business Grain** | `order_id` is unique primary key (1 row = 1 order). | `orders['order_id'].duplicated().sum() == 0` | **3 duplicate rows** (`O00120`, `O00723`, `O01302`). Conflicting `traffic_bucket` attributes. | High | **WARN** (Quarantined, deterministic deduplication applied) |
| **2. Completion Timestamps** | Delivered orders must have valid completion timestamps. | `orders[delivered]['actual_delivery_at'].isna().sum() == 0` | **37 delivered orders** have `NaN` delivery timestamps (2.42% of delivered volume). | High | **WARN** (Excluded from zero-tolerance denominator) |
| **3. Promised ETA Validity** | Promised delivery time must be after order placement. | `(orders['promised_eta'] < orders['created_at']).sum() == 0` | **4 orders** have `promised_eta < created_at` (up to -20 min inverted). | High | **WARN** (Chronology error logged) |
| **4. Event Chronology** | Lifecycle progression must follow: `created <= pickup <= delivery`. | `(orders['pickup_at'] > orders['actual_delivery_at']).sum() == 0` | **5 orders** show delivery recorded before driver pickup. | High | **WARN** (Corrupted event logs recorded) |
| **5. Cross-Source Mapping** | Foreign keys must map to upstream master tables. | Foreign key coverage checks across restaurants, drivers, tickets, and status. | 100% on restaurants and drivers. **3 support tickets lack `order_id`**. Restaurant status covers only **31.38%** of orders. | Medium | **WARN** (Unmapped volume documented) |
| **6. Update Freshness** | Status updates must precede or coincide with physical actions. | `restaurant_status.last_updated_at - pickup_at <= 0` | **33.07% of status updates** (166 / 502) logged *after* driver pickup. | Critical for Live ETA | **FAIL for Live ETA** / **WARN for Batch** |
| **7. KPI Ownership** | Formally documented and ratified KPI owner. | Inspect `client_metric_definitions.json`. | *"No canonical KPI owner is formally documented."* | Critical | **UNKNOWN** (Candidate metrics marked UNRATIFIED) |

---

## 3. Resolving the 56.39% vs. 55.03% KPI Discrepancy

Leadership asserts:
> **"Late Delivery Rate is 56%."**

Our dynamic empirical analysis reveals that this figure is **strictly denominator-dependent**:

| Candidate Definition | Formula | Numerator | Denominator | Calculated Late Rate | Governance Status |
|---|---|---|---|---|---|
| **A. Historical Dashboard (VP Ops)** | `delay > 0 min` on delivered orders with non-null completion timestamp | 843 | 1,495 | **56.39%** | **UNRATIFIED** |
| **B. All Delivered Orders** | `delay > 0 min` across all delivered orders (including 37 missing timestamps) | 843 | 1,532 | **55.03%** | **UNRATIFIED** |
| **C. Total Placed Orders** | `delay > 0 min` across total orders placed (including 68 cancellations) | 843 | 1,600 | **52.69%** | **UNRATIFIED** |
| **D. Customer-Impact Tolerance (Support Lead)** | `delay > 10 min` on delivered orders with non-null completion timestamp | 349 | 1,495 | **23.34%** | **UNRATIFIED** |

### FDE Governance Resolution
1. **The 56.39% Figure**: Arises from a zero-tolerance operational definition (`delay_min > 0`) that silently drops 37 delivered orders because their delivery timestamps were never captured by the mobile app.
2. **The 55.03% Figure**: Retains all delivered orders in the denominator, assuming that orders lacking delivery timestamps cannot be proven late.
3. **The 23.34% Figure**: Reflects the Support Lead's operational reality that deliveries delayed by under 10 minutes rarely trigger customer complaints.
4. **Publish Decision**: **DO NOT PUBLISH 56% TODAY.** No single figure can be published until an appointed Executive KPI Owner formally ratifies:
   - Whether zero-tolerance (0m) or friction tolerance (10m) represents the corporate standard.
   - How uncompleted orders (cancellations and missing delivery timestamps) are governed in the denominator.

---

## 4. Deterministic Duplicate Quarantine Procedure

The orders dataset contains 1,603 rows representing 1,600 unique `order_id`s. Three duplicate order IDs exist:
- `O00120`: 2 rows with conflicting `traffic_bucket` (`severe` vs `medium`).
- `O00723`: 2 rows with conflicting `traffic_bucket` (`medium` vs `high`).
- `O01302`: 2 rows with conflicting `traffic_bucket` (`medium` vs `high`).

### Deterministic Resolution Protocol
1. **Quarantine**: All raw duplicate records are preserved in full within `outputs/validation_report.json` under `quarantine.duplicate_orders`.
2. **Deterministic Selection Rule**: The pipeline executes deterministic tie-breaking via `orders.drop_duplicates('order_id', keep='first')`.
3. **Audit Tracking**:
   - Raw Ingested Orders: **1,603**
   - Unique Order IDs: **1,600**
   - Quarantined Duplicate Rows: **3**
   - Canonical Cleaned Orders: **1,600**

---

## 5. Category Semantics: Representation vs. Semantic Differences

| Category Field | Observed Values | Representation Differences (Safe to Normalize) | Potential Semantic Differences (Requires Owner Confirmation) |
|---|---|---|---|
| `final_status` | `delivered` (1530), `cancelled` (68), `Delivered` (5) | `'Delivered'` vs `'delivered'`: Normalized to lowercase. | None. Status transitions are unambiguous. |
| `traffic_bucket` | `medium` (635), `high` (448), `low` (381), `severe` (136), `HIGH` (3) | `'HIGH'` vs `'high'`: Normalized to lowercase. | None. Values represent ordinal congestion estimates. |
| Restaurant `status` | `preparing` (171), `handed_off` (168), `ready` (157), `ready ` (2), `READY` (1), `Ready` (1), `handoff` (1), `unknown` (1) | Whitespace and casing normalized safely via `.str.strip().str.lower()`. | **`'handoff'` vs `'handed_off'`**: May represent active handover in-progress vs completed handoff event.<br>**`'unknown'`**: Explicit unmapped state. Must not be silently coerced to valid status without merchant app lead approval. |
| Support `category` | `late_delivery` (38), `eta_changed` (37), `restaurant_delay` (37), `ready_but_waiting` (33), `status_mismatch` (29), `driver_not_moving` (25), `Late Delivery` (1), `late_delivery ` (1), `ETA issue` (1) | Whitespace and casing normalized safely. | **`'ETA issue'` vs `'eta_changed'`**: Could indicate front-end rendering bug rather than back-end calculation drift. Requires Support Lead confirmation. |

---

## 6. Freshness as an SLA Question

The pipeline evaluates `restaurant_status.last_updated_at` against order lifecycle timestamps:
- Mean update latency from order creation: **15.92 minutes** (min: -354 min, max: +35 min).
- Negative lags indicate **severe clock drift** (updates logged hours before order creation).
- **In 33.07% of tracked orders (166 / 502), the merchant status was updated *after* the driver had already picked up the order**.

### SLA Fitness Matrix
- **Weekly Analytics (WARN - Acceptable with Caveats)**: Batch weekly reporting tolerates logging latency, but analysis is limited because restaurant status covers only 31.38% of total order volume.
- **Live Customer ETA (FAIL - UNSAFE)**: Displaying merchant status to customers when 33% of updates lag driver departure actively erodes customer trust.
- **Restaurant Accountability (FAIL - UNSAFE)**: Enforcing partner contractual penalties using timestamps with documented clock drift and post-pickup logging would trigger immediate legal and commercial disputes.
