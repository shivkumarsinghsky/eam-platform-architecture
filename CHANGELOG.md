# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-10-02

### Added

- Docker compose: PostgreSQL initialised with the reference model, and a test-runner container.
- EAM architecture documentation: domain terminology, bounded contexts, asset and work order lifecycles,
  maintenance strategies, services and API, database design, events, reporting, telemetry, field service.
- Python domain model: work orders, PM scheduling, asset hierarchy, condition rules, maintenance KPIs.
- PostgreSQL operational schema, seed data, KPI views, star schema, ETL and analytics queries.
- OpenAPI 3.1 reference contract.
- ADR-001 to ADR-006; tests (domain, SQL, OpenAPI); CI with PostgreSQL.
