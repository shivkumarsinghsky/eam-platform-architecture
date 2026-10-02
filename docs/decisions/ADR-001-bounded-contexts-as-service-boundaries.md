# ADR-001: Bounded Contexts as Service Boundaries

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

EAM covers assets, work, planning, inventory, workforce, field service, monitoring, contracts and reporting.
A single shared model ("the asset table everyone writes to") couples teams and makes every change risky.
Splitting into many fine-grained services creates chatty, inconsistent workflows (a work order cannot be created
without five synchronous calls).

## Decision

Model the domain as nine bounded contexts ([02-bounded-contexts.md](../02-bounded-contexts.md)) and deploy them
as **six or seven services**, grouping contexts that change together and need transactional consistency:
Work Management and Maintenance Planning share a service (PM generation writes work orders atomically); the
high-volume Monitoring context is a separate platform.

## Alternatives Considered

- **Monolith with one schema** — simplest operations; coupling grows with every module.
- **One service per context (9+)** — maximum autonomy; PM generation and work management would need a saga for
  what is naturally one transaction.
- **Modular monolith** — a valid starting point; the context boundaries in this ADR become its module boundaries.

## Trade-offs

Cross-context queries (e.g. "open work on A-critical assets in this system") need read models or the warehouse
instead of joins.

## Consequences

- Asset identifiers and site codes are the only shared kernel.
- Contexts integrate by events ([event architecture](../08-event-architecture.md)); Monitoring integrates through an
  anti-corruption layer.
