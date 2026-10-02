# ADR-004: Star Schema With SCD2 Asset Dimension for Maintenance Analytics

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Maintenance analytics spans years and many dimensions (asset class, criticality, site, failure mode, craft, work
type). Running such queries on operational databases competes with planners and technicians and produces
inconsistent KPI definitions across reports.

## Decision

Feed a warehouse from operational data (CDC/outbox) into a star schema with three facts (`fact_work_order`,
`fact_labor`, `fact_downtime`) and conformed dimensions; `dim_asset` is **SCD type 2**. KPI definitions live in
version-controlled SQL with tests. Small operational KPIs (backlog, open WOs) stay as OLTP views.

## Alternatives Considered

- **Reports directly on OLTP** — no pipeline; slow, contended, no history of changing attributes.
- **Wide denormalised tables only** — easy for BI tools, but history of changing attributes and consistent
  definitions are harder.
- **Data vault** — strong auditability for many sources; heavier than needed for a single EAM source.

## Trade-offs

Analytics is near-real-time at best (minutes) and the pipeline must be operated and reconciled.

## Consequences

Trend reports respect historical criticality/location; the same KPI gives the same answer in every dashboard.
