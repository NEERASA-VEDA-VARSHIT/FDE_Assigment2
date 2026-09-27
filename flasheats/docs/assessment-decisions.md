# FlashEats Architectural & Governance Decisions (Assessment 2)

## Executive Summary
This document records the critical Forward Deployed Engineering (FDE) decisions made during the FlashEats investigation. It establishes why certain technical shortcuts, premature modeling choices, and superficial data cleaning practices were rejected in favor of robust operational governance.

---

## Decision 1: Reject Building an AI Delay Prediction Model

### Executive Decision
**FlashEats must NOT build or deploy an AI delay prediction system today.**

### Rationale & Data Evidence
1. **Unobserved Confounding**:
   - `driver_events.json` records driver assignment, pickup, delivery, and GPS pings.
   - It contains **zero directly observed `driver_arrived_at_restaurant` events**.
   - As a result, the time elapsed between driver assignment and pickup is an indivisible black box. We cannot determine whether delay occurred because the courier was caught in traffic traveling to the venue or because the courier arrived promptly and waited 20 minutes for an unprepared meal.
2. **Biased Model Training**:
   - Training a machine learning model on current data would cause the algorithm to falsely attribute kitchen preparation delays to driver transit time or road congestion (`traffic_bucket`).
   - The model would produce systematically flawed ETAs, penalize high-performing drivers assigned to slow restaurants, and fail to resolve the underlying operational bottleneck.
3. **FDE Principle**: *Fix physical instrumentation and telemetry boundaries before investing in predictive machine learning models.*

---

## Decision 2: Intervention Rescue Rate is Observational, Not Causal

### Executive Decision
**Intervention Rescue Rate (43.56%) must be classified strictly as an OBSERVATIONAL RECOVERY METRIC, not causal proof of intervention efficacy.**

### Rationale & Data Evidence
1. **Empirical Findings**:
   - Late delivery rate among intervened orders: **56.44%** (228 / 404).
   - Late delivery rate among non-intervened orders: **56.37%** (615 / 1,091).
2. **The Adverse Selection Phenomenon**:
   - A naive causal interpretation would suggest that interventions have zero effect because late rates are identical (~56.4%).
   - In physical reality, operations only intervenes when an order is **already in critical jeopardy** (e.g. driver stationary, food ready but unassigned, customer complaining).
   - Without intervention, the late rate among this troubled cohort might have been 95%+. Achieving a 43.56% on-time completion rate represents significant observational recovery.
3. **Governance Mandate**:
   - The metric is exported to `outputs/metrics.csv` with status `OBSERVATIONAL`.
   - Business presentations must explicitly state: *"This metric measures on-time recovery among intervened orders, but does not constitute randomized causal proof."*

---

## 3. Decision 3: Governance of the Disputed 56% KPI

### Executive Decision
**Do not publish "Late Delivery Rate = 56%" as the official corporate KPI.**

### Rationale & Data Evidence
1. **Lack of Documented Ownership**:
   - `data/client_metric_definitions.json` explicitly states: *"No canonical KPI owner is formally documented."*
2. **Extreme Sensitivity to Business Interpretation**:
   - VP Ops (Zero-tolerance delay > 0m): **56.39%**
   - Support Lead (Friction buffer delay > 10m): **23.34%**
   - Conservative Delivered (including 37 missing timestamps): **55.03%**
   - Platform Fulfillment (including cancellations): **52.69%**
3. **Engineering Standard**:
   - Publishing 56% without executive governance enshrines a zero-tolerance formula that silently discards 37 delivered orders and ignores 68 cancellations.
   - The pipeline exports all 4 candidates with status `UNRATIFIED` until executive ratification.

---

## 4. Decision 4: Deterministic Duplicate Quarantine Over Silent Dropping

### Executive Decision
**Preserve duplicate orders in quarantine before applying deterministic deduplication.**

### Rationale & Data Evidence
1. **The Risk of Silent Cleaning**:
   - The orders dataset contains 3 duplicate order IDs (`O00120`, `O00723`, `O01302`) created by duplicate event logging with conflicting `traffic_bucket` attributes (e.g. `severe` vs `medium`).
   - Silently dropping rows conceals an upstream event pipeline flaw.
2. **Deterministic Protocol**:
   - All 6 duplicate rows are preserved verbatim in `outputs/validation_report.json` under `quarantine.duplicate_orders`.
   - Deterministic selection (`keep='first'`) produces a clean 1,600-order canonical grain while providing an actionable defect log for upstream data platform teams.

---

## 5. Next Operational Instrumentation Roadmap

To make FlashEats data trustworthy for predictive modeling and automated dispatch, operations must implement:
1. **Driver Restaurant Arrival Beacon**: Automated Bluetooth BLE / geofence arrival logging to cleanly separate road transit from kitchen dwell time.
2. **Merchant Ready Confirmation**: Tablet tap or KDS integration capturing the exact physical moment the meal is bagged and ready for courier pickup.
3. **Mandatory Ticket Context**: Enforce valid `order_id` capture on all customer support intake channels.
4. **ETA Audit Logging**: Maintain an immutable version history of all customer-facing ETA recalculations.
