# Field Service Management

Field Service extends work management to technicians working away from a fixed plant — utilities, facilities,
telecom, equipment service providers. The defining constraints are **unreliable connectivity**, **travel time**
and **customer commitments (SLAs)**.

## Architecture

```mermaid
flowchart LR
    WM["Work Management"] -->|"work-order.created"| Disp["Dispatch and scheduling<br/>skills, location, SLA"]
    Disp -->|"assignment"| Sync["Mobile sync service"]
    Sync <-->|"delta sync when online"| App["Mobile app<br/>local database, offline-first"]
    App -->|"status, labor, parts,<br/>photos, signature"| Sync
    Sync -->|"commands"| WM
    Disp --> Map["Routing / travel time"]
    SLA["SLA tracking"] --> Disp
```

## Dispatch

Assignment optimises across: required **skills/certifications**, **location** and travel time, **SLA deadline**,
**priority**, technician **shift/calendar** and **parts** on the van. A practical approach is a scoring function
(greedy assignment) for real-time dispatch, with a batch optimiser for next-day planning.

## Offline-first mobile synchronisation

```mermaid
sequenceDiagram
    participant App as Mobile app (offline)
    participant Sync as Sync service
    participant WM as Work Management
    App->>App: start job, record labor, issue parts (local queue)
    Note over App: no connectivity for 3 hours
    App->>Sync: push queued commands (each with client id + base version)
    Sync->>WM: apply in order (idempotent by client command id)
    alt server version changed meanwhile (e.g. planner rescheduled)
        WM-->>Sync: conflict on field X
        Sync-->>App: resolution per field policy
    end
    Sync-->>App: pull deltas since last sync token
```

| Design point | Choice |
|---|---|
| Unit of sync | **Commands** (start, record labor, complete) rather than whole-record overwrites |
| Idempotency | Client-generated command ids; server dedupes |
| Conflicts | Field-level policy: technician wins for actuals and notes; planner wins for schedule/assignment; status transitions re-validated by the lifecycle |
| Data scope | Only the technician's assigned work, related assets and job plans — bounded local storage |
| Attachments | Uploaded separately (resumable), referenced by id |

See [ADR-006](decisions/ADR-006-offline-first-field-sync.md).

## SLAs

SLA clocks (response, restore, resolve) start from the work request and pause in defined states (e.g. waiting for
customer). Status history timestamps make SLA compliance computable after the fact — another reason the status
history table exists.

Back to: [README](../README.md)
