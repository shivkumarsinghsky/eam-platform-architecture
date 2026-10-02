# Work Order Lifecycle

The work order is the central transaction in EAM. Its lifecycle encodes how an organisation authorises, plans,
executes and learns from maintenance work. The reference implementation is
[`src/eam/work_orders.py`](../src/eam/work_orders.py) with tests in
[`tests/test_work_orders.py`](../tests/test_work_orders.py).

## State machine

```mermaid
stateDiagram-v2
    [*] --> REQUESTED
    REQUESTED --> APPROVED
    REQUESTED --> IN_PROGRESS: emergency only
    APPROVED --> PLANNED
    PLANNED --> SCHEDULED
    PLANNED --> WAITING_MATERIAL
    WAITING_MATERIAL --> PLANNED
    WAITING_MATERIAL --> SCHEDULED
    SCHEDULED --> WAITING_MATERIAL
    SCHEDULED --> PLANNED: rescheduled
    SCHEDULED --> IN_PROGRESS
    IN_PROGRESS --> ON_HOLD
    ON_HOLD --> IN_PROGRESS
    IN_PROGRESS --> COMPLETED
    COMPLETED --> IN_PROGRESS: reopened
    COMPLETED --> CLOSED
    REQUESTED --> CANCELLED
    APPROVED --> CANCELLED
    PLANNED --> CANCELLED
    SCHEDULED --> CANCELLED
    WAITING_MATERIAL --> CANCELLED
    ON_HOLD --> CANCELLED
    CLOSED --> [*]
    CANCELLED --> [*]
```

## Guards (business rules)

| Transition | Rule | Why |
|---|---|---|
| → `IN_PROGRESS` | A technician must be assigned | Accountability, labor capture, safety (who is on site) |
| → `COMPLETED` | Labor actuals recorded | Cost and backlog accuracy |
| → `COMPLETED` (CM/EM) | Failure report (problem/cause/remedy) present | Without it, reliability analysis is impossible |
| `REQUESTED` → `IN_PROGRESS` | Only for emergency work | Emergencies skip approval/planning; reviewed afterwards |
| `CLOSED`, `CANCELLED` | Terminal and immutable | Closed WOs feed cost and reliability history; corrections are new transactions |
| `COMPLETED` → `IN_PROGRESS` | Reopen allowed until closed | A repair that did not hold is the same job, not a new failure |

The SQL schema backs the most important guard with a constraint: corrective/emergency work orders cannot be
`COMPLETED`/`CLOSED` without a problem code.

## End-to-end sequence (corrective work)

```mermaid
sequenceDiagram
    participant Op as Operator / Monitoring
    participant WM as Work Management
    participant Pl as Planner
    participant Inv as Inventory
    participant Sch as Scheduler
    participant Tech as Technician (mobile)
    Op->>WM: work request (asset, symptom)
    WM->>Pl: REQUESTED, approval queue by priority
    Pl->>WM: approve, apply job plan (labor, materials)
    WM->>Inv: reserve materials
    alt materials not available
        Inv-->>WM: shortage, WAITING_MATERIAL
        Inv-->>WM: received, back to PLANNED
    end
    Sch->>WM: schedule week, assign technician
    Tech->>WM: start (IN_PROGRESS), issue materials
    Tech->>WM: labor, failure codes, completion notes
    WM->>WM: COMPLETED
    Pl->>WM: review costs and codes, CLOSED
    WM-->>Inv: return unused reserved materials
```

## Priority

Priority is typically derived, not chosen freely: **priority = f(asset criticality, consequence/urgency of the
reported condition)**, for example a matrix where an A-critical asset with a safety-relevant symptom yields P1.
Deriving it keeps the backlog honest — when everything is P1, nothing is.

## Events emitted

`WorkOrderCreated`, `WorkOrderStatusChanged` (from, to, by, at), `MaterialIssued`, `LaborReported`,
`WorkOrderCompleted` (with failure codes and downtime), `WorkOrderClosed` (final cost). See
[event architecture](08-event-architecture.md).

Next: [Maintenance Strategies](05-maintenance-strategies.md)
