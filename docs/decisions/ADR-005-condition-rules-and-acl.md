# ADR-005: Condition Rules With Sustain and Hysteresis, Behind an Anti-Corruption Layer

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Connecting telemetry directly to work order creation floods planners with duplicates from noisy signals and lets
monitoring concepts (tags, alarm classes) leak into the work management model.

## Decision

- Condition rules require a **sustained** breach and **re-arm only below a lower reset level** (hysteresis); one
  work request per alarm episode.
- A **work request adapter** (anti-corruption layer) translates alarm episodes into Work Management's own *work
  request* with priority derived from asset criticality, and owns the signal → asset mapping.

## Alternatives Considered

- **Plain thresholds** — simple, unusable with real signals.
- **ML anomaly detection first** — powerful, but needs labelled history; rules are the baseline that ML models are
  later compared against.
- **Monitoring system creates work orders directly** — tight coupling to EAM internals.

## Trade-offs

Sustain windows delay detection by design; thresholds and windows need tuning per asset class.

## Consequences

Rule behaviour is unit-tested (`tests/test_hierarchy_condition_kpis.py`); planners see one actionable request per
episode.
