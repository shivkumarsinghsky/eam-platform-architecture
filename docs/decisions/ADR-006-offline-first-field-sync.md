# ADR-006: Offline-First Mobile Sync Using Commands

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

Technicians work in basements, plant rooms and remote sites without connectivity for hours. Online-only mobile
apps lose work; naive "last write wins" record sync overwrites planners' changes or technicians' actuals.

## Decision

The mobile app keeps a local database of the technician's assigned work and records **commands** (start, record
labor, issue part, complete) with client-generated ids and the base version they were made against. The sync
service applies commands idempotently through the same lifecycle rules as online calls, and resolves conflicts
with field-level ownership (technician owns actuals and notes; planner owns schedule and assignment).

## Alternatives Considered

- **Online-only** — simplest; unusable for field work.
- **Record-level last-write-wins** — silent data loss.
- **CRDT-based document sync** — elegant for collaborative editing; poor fit for state machines with business
  guards.

## Trade-offs

A command can be rejected after the fact (e.g. the work order was cancelled while the technician was offline); the
app must surface these rejections clearly.

## Consequences

The server remains the single place where lifecycle rules are enforced, online or offline.
