# EAM Domain Overview and Terminology

Enterprise Asset Management (EAM) is the discipline — and the class of software — for managing physical assets
over their whole life: what we own, where it is, what condition it is in, what work it needs, what that work
costs, and whether the asset is still worth keeping. Field Service Management (FSM) is the closely related
practice of dispatching technicians to work at distributed or customer sites.

This page defines the vocabulary used across the repository. Precise terms matter: most EAM integration problems
start with two systems meaning different things by "asset" or "completed".

## Organisation and place

| Term | Meaning |
|---|---|
| **Organization** | Legal/financial entity; owns sites, currencies, GL accounts. |
| **Site** | Operational unit (plant, campus, depot) with its own planners, storerooms and calendars. |
| **Functional location** | A position in a process or building where an asset performs a function ("feed pump position in feedwater system"). Locations persist when the physical asset is swapped. |
| **Asset / equipment** | A physical, individually tracked item (serial-numbered pump, motor, chiller). Has a class, attributes, criticality and a lifecycle. |
| **Asset hierarchy** | Parent/child structure: site → area → system → equipment → component. Used for cost and downtime roll-ups. |
| **Asset class / specification** | Category that defines attributes (flow, power), failure code sets and default job plans. |
| **Criticality** | Ranking (e.g. A/B/C) of consequence of failure on safety, environment, production and cost. Drives priority and maintenance strategy. |

## Work

| Term | Meaning |
|---|---|
| **Work request** | A report that something needs attention (from an operator, a tenant, or an automated condition rule). Not yet approved work. |
| **Work order (WO)** | Authorised unit of work with a type, priority, plan, schedule and actuals. The central transaction of EAM. |
| **Work type** | CM (corrective), EM (emergency), PM (preventive), PdM (predictive / condition-based), INSP (inspection). |
| **Job plan** | Reusable template: tasks, estimated labor by craft, materials, tools, safety precautions. |
| **Craft / trade** | Skill category (mechanical, electrical, instrumentation) with labor rates. |
| **Actuals** | Labor hours, materials, services and tools actually used; the source of maintenance cost. |
| **Backlog** | Approved work not yet completed, usually measured in crew-weeks. |
| **Permit to work / LOTO** | Safety authorisation and lock-out/tag-out isolation required before certain work. |

## Maintenance strategy

| Term | Meaning |
|---|---|
| **Preventive maintenance (PM)** | Recurring work scheduled by time (every 90 days) or usage (every 500 running hours). |
| **Fixed vs. floating schedule** | Fixed: due dates stay on the original cadence. Floating: next due date counts from last completion. |
| **Meter** | Usage counter (running hours, cycles, km) or gauge (temperature, vibration). |
| **Condition-based / predictive maintenance (CBM / PdM)** | Work triggered by measured condition crossing a threshold, or by a model predicting failure. |
| **RCM** | Reliability-centred maintenance: choosing the strategy per failure mode based on consequence. |
| **Failure codes** | Hierarchy of problem → cause → remedy codes recorded on corrective work; the basis for reliability analysis. |

## Materials, contracts and cost

| Term | Meaning |
|---|---|
| **Item** | Stocked part or material (seal kit, bearing). |
| **Storeroom** | Physical stock location; holds balances, reorder points and average cost. |
| **Reservation** | Material committed to a planned work order but not yet issued. |
| **Issue / return** | Movement of stock to/from a work order; issues carry cost to the work order. |
| **Vendor / contract** | Supplier; contracts cover service, warranty, lease or purchase terms for assets. |
| **Warranty** | Contract that makes the vendor liable for certain failures — work orders on warrantied assets should be flagged. |

## Reliability metrics

| Metric | Definition (as used here) |
|---|---|
| **MTBF** | Mean time between failures = operating time / number of failures. |
| **MTTR** | Mean time to repair = total repair downtime / number of failures. |
| **Availability** | Uptime / (uptime + downtime) for the period. |
| **PM compliance** | PM work orders completed within their tolerance window / PM work orders due. |
| **Planned maintenance %** | Planned labor hours / total maintenance labor hours. |
| **Schedule compliance** | Scheduled work completed in the scheduled week / scheduled work. |

The Python implementations are in [`src/eam/kpis.py`](../src/eam/kpis.py) and the SQL equivalents in
[`sql/03_operational_views.sql`](../sql/03_operational_views.sql).

Next: [Bounded Contexts](02-bounded-contexts.md)
