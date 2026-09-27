# FlashEats Source Map & Source Reasoning Framework (Class 4 Deliverable)

## Executive Summary
In forward deployed data engineering, data sources cannot be treated as flat, interchangeable tables. Every data field reflects an underlying business process, technical system, organizational owner, update frequency, and semantic contract. 

This document defines the canonical **FlashEats Source Map** using the 7-dimension FDE source reasoning framework:
$$\text{Business Question} \longrightarrow \text{Information Required} \longrightarrow \text{Source} \longrightarrow \text{Ownership} \longrightarrow \text{Freshness} \longrightarrow \text{Semantics} \longrightarrow \text{Reliability}$$

---

## 1. The 7-Dimension Source Reasoning Framework

| Dimension | FDE Core Question | Operational Significance |
|---|---|---|
| **1. Business Question** | What decision or operational intervention is the business attempting to make? | Prevents collecting data without a clear decision purpose. |
| **2. Information Required** | What factual data points or telemetry are necessary to answer the question? | Defines the minimal required data payload. |
| **3. Source System** | Which database, API, log stream, or file holds the underlying record? | Identifies the physical infrastructure and architectural origin. |
| **4. Ownership** | Which team or service is accountable for the schema, uptime, and definitions? | Identifies who has authority to alter business rules or fix upstream bugs. |
| **5. Freshness & SLA** | How frequently is the data updated, and what is the latency from real-world event to database write? | Determines whether the data is safe for real-time dispatch vs. batch reporting. |
| **6. Semantics** | What do the statuses, timestamps, and categories physically represent in the real world? | Prevents conflating representation differences with true operational state changes. |
| **7. Reliability & Gaps** | What can corrupt this signal (clock drift, human input lag, dropped pings, unobserved boundaries)? | Establishes the boundaries of what the data can and cannot prove. |

---

## 2. Canonical FlashEats Source Mapping Matrix

| Information Entity | Primary Source | System of Origin | Technical Ownership | Freshness SLA | Semantic Meaning | Reliability & Authority Status |
|---|---|---|---|---|---|---|
| **Promised Delivery Time** | `orders.promised_eta` | SQLite Database (`database/flasheats.db`) | Pricing & Dispatch Engine | Static at checkout | Contractual delivery commitment given to customer at order placement. | **Authoritative SLA baseline**. Reliable for measuring platform promise, but static once physical delays occur. |
| **Actual Delivery Time** | `orders.actual_delivery_at` & `driver_events.json` | Order Platform & Driver App | Mobile Engineering / Logistics Ops | Event-driven (driver button tap) | The moment the driver marks the order as handed to the customer. | **Authoritative for order outcome**. Subject to human behavioral lag (drivers may tap early at customer door or late upon returning to bike). 37 delivered orders lack this timestamp. |
| **Driver Assignment** | `orders.driver_id` & `/dispatch/orders` API | Core Dispatch Engine / Service | Dispatch & Logistics Team | Real-time during dispatch matching | The registered identifier of the courier assigned to transport the order. | **Authoritative for assignment audit**. Does not measure driver physical proximity or readiness to accept. |
| **Customer Complaints** | `data/support_tickets.csv` | Support Desk CRM (Zendesk equivalent) | Customer Experience / Support Lead | Real-time on ticket submission | Customer-reported friction, complaint categories, and escalation text. | **Authoritative for customer perception & sentiment**. Contextual for physical delivery facts. 3 tickets lack `order_id` linkages. |
| **Restaurant Prep Status** | `data/restaurant_status.csv` | Merchant Tablet App / KDS | Merchant Partner Engineering | Manual merchant update | Kitchen states: `preparing`, `ready`, `handed_off`. | **Contextual only**. Severe latency: 33% of status updates occur *after* the driver has already picked up the order. Fails live ETA and partner accountability SLAs. |
| **Driver Movement / Telematics** | `data/driver_events.json` | Driver Mobile Telematics | Driver Platform Engineering | Asynchronous GPS ping streams | Discrete latitude/longitude coordinates and driver state transitions. | **Authoritative for movement traces**. Contextual for restaurant arrival; arrival is **unobserved** and must not be treated as ground truth. |
| **In-Flight App Actions** | `data/customer_app_actions.csv` | Customer Mobile App Event Stream | Product Analytics / Mobile Platform | Real-time event streaming | Customer behavior during active orders (`ETA_VIEWED`, `CANCEL_ATTEMPTED`, `SUPPORT_CONTACTED`). | **Authoritative for customer engagement**. High frequency of ETA views indicates customer friction and anxiety before promised ETA expiration. |
| **Operational Interventions** | `data/order_interventions.csv` | Dispatch Console / Support Portal | Live Operations & Support Teams | Event-driven when remedy applied | Remedial actions taken to rescue troubled orders (`PRIORITY_DISPATCH`, `DRIVER_REASSIGNMENT`, `RESTAURANT_CONTACT`, `CUSTOMER_CREDIT`). | **Authoritative for operational cost & action**. Subject to adverse selection: interventions are applied reactively to orders already in severe jeopardy. |
| **Order Outcome & Evaluation** | `data/order_outcomes.csv` | Data Platform / Analytics Warehouse | Core Data Engineering | Batch analytical derivation | Consolidated outcome flags (`delivered_flag`, `late_flag`, `delay_min`, `outcome_bucket`). | **Authoritative for analytical modeling**. Requires explicit governance of denominator exclusions. |

---

## 3. Authoritative vs. Contextual Classification

### Authoritative Sources (System Contracts)
These sources hold formal system of record authority for business states, contractual commitments, and financial transactions:
1. `orders.promised_eta`: Authoritative contractual delivery target.
2. `orders.final_status`: Authoritative platform lifecycle state.
3. `support_tickets.csv`: Authoritative record of customer support contact volume.
4. `order_interventions.csv`: Authoritative record of operational adjustments and financial credits.

### Contextual Sources (Operational Telemetry)
These sources provide explanatory context regarding physical progression and environmental conditions, but do not represent legally binding states:
1. `driver_events.json` (GPS pings): Periodic position telemetry. Cannot prove exact dwell duration without validated geofencing.
2. `restaurant_status.csv`: Merchant self-reported kitchen progression. Frequently updated post-facto.
3. `orders.traffic_bucket`: Static routing estimate assigned at checkout, not dynamic route telematics.

---

## 4. Critical Authority & Instrumentation Boundaries

An essential FDE principle is recognizing **what the data cannot prove**:

### Boundary 1: The Unobserved Restaurant Arrival
- **The Gap**: `driver_events.json` records `assigned`, `picked_up`, and `delivered`. It contains **no directly observed `driver_arrived_at_restaurant` event**.
- **Operational Impact**: Total elapsed duration between assignment and pickup cannot be accurately decomposed into:
  $$\text{Transit Time to Restaurant} \quad \text{vs.} \quad \text{Kitchen Dwell / Wait Time}$$
- **Instrumentation Recommendation**: Implement automated Bluetooth BLE beacon or geofenced arrival logging on the driver app upon reaching the restaurant premises.

### Boundary 2: Merchant Tablet Update Latency
- **The Gap**: In 33.07% of tracked orders, merchants log `ready` or `handed_off` *after* the driver has already initiated pickup.
- **Operational Impact**: Kitchen status updates cannot be ingested into real-time ETA calculation or used to penalize restaurant partners.
- **Instrumentation Recommendation**: Replace manual merchant tablet status taps with kitchen display system (KDS) printer integration or courier QR-code scanning at handoff.

### Boundary 3: Missing Support Ticket Order Linkages
- **The Gap**: 3 support tickets (1.49%) possess `NaN` for `order_id`.
- **Operational Impact**: Customer complaints cannot be attributed to specific couriers, merchants, or delay root causes.
- **Instrumentation Recommendation**: Mandate active order context in the customer support intake UI.
