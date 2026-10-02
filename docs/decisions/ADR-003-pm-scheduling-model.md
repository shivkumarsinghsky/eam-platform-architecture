# ADR-003: PM Scheduling — Fixed/Floating, Whichever-First, Idempotent Generation

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

PM schedules must support statutory calendar compliance (fixed), wear-based intervals (floating) and usage-based
intervals (meters), and the generator runs repeatedly (nightly and on meter readings). Duplicate or missed PM work
orders are among the most common EAM data-quality issues.

## Decision

- A PM has an optional calendar frequency (`FIXED` or `FLOATING`) and an optional meter interval; when both exist,
  **whichever comes first** triggers.
- Fixed schedules compute from the **last due date**, floating from the **last completion**.
- Work orders are generated `lead_days` before the due date with a natural key — `(pm, due date)` or
  `(pm, meter threshold)` — enforced by a unique index.
- The evaluation is a pure function (`eam.pm.evaluate`) so it is exhaustively unit-tested.

## Alternatives Considered

- **Generating far ahead (e.g. a year of WOs)** — visible workload, but clutters the backlog and must be
  regenerated when schedules change. Forecasting (`forecast()`) gives the visibility without creating records.
- **Cron-like recurrence rules** — expressive, but do not model "from last completion" or meters.

## Trade-offs

Seasonal schedules, nested PMs (a 12-month PM suppressing the 3-month PM it includes) and route-based PMs are not
modelled; they are extensions of the same evaluation function.

## Consequences

Re-running the generator is always safe; the scheduler can be triggered by events (meter readings, completions)
as well as by time.
