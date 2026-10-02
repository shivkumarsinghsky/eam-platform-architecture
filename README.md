# EAM Platform Architecture — Enterprise Asset Management Reference Architecture

[![CI](https://github.com/shivkumarsinghsky/eam-platform-architecture/actions/workflows/ci.yml/badge.svg)](https://github.com/shivkumarsinghsky/eam-platform-architecture/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-ltree-336791)
![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-6ba539)
![License](https://img.shields.io/badge/license-MIT-green)

A reference architecture for **Enterprise Asset Management (EAM)** and **Field Service Management (FSM)**
platforms by **Shiv Kumar**. It covers the domain model, bounded contexts, service boundaries, database and
reporting design, event architecture, API contract and real-time telemetry integration of a modern EAM system.
The domain rules and data model are backed by executable code and SQL with tests.

It is written from the perspective of building EAM/FSM products: asset registries and hierarchies, work order
lifecycles, preventive and predictive maintenance, inventory, labor, failure analysis, downtime, cost, contracts,
field service, monitoring and maintenance KPIs.

> Reference architecture and portfolio implementation. It describes patterns and models, not a specific
> commercial product.

## Domain Map

```mermaid
flowchart TB
    AM["Asset Management<br/>registry, hierarchy, lifecycle"]
    AM --> MNT["Maintenance<br/>PM, PdM, inspections"]
    AM --> WK["Work Management<br/>requests, work orders, actuals"]
    AM --> INV["Inventory<br/>parts, storerooms, reservations"]
    AM --> FS["Field Service<br/>dispatch, mobile, SLAs"]
    AM --> MON["Monitoring<br/>telemetry, condition rules"]
    AM --> REP["Reporting<br/>KPIs, star schema, dashboards"]
    MNT -->|"generates"| WK
    MON -->|"work requests"| WK
    WK -->|"consumes"| INV
    WK -->|"dispatches"| FS
    WK -->|"facts"| REP
```

## What This Repository Covers

| Area | Document | Executable artefact |
|---|---|---|
| EAM terminology (asset, location, WO, PM, PdM, failure codes, MTBF/MTTR …) | [01 Domain overview](docs/01-eam-domain-overview.md) | — |
| Bounded contexts, context map, service boundaries | [02 Bounded contexts](docs/02-bounded-contexts.md) | — |
| Asset lifecycle, repair-vs-replace | [03 Asset lifecycle](docs/03-asset-lifecycle.md) | `asset.lifecycle_status` in SQL |
| Work order lifecycle and guards | [04 Work order lifecycle](docs/04-work-order-lifecycle.md) | [`work_orders.py`](src/eam/work_orders.py) |
| Maintenance strategies, PM scheduling | [05 Maintenance strategies](docs/05-maintenance-strategies.md) | [`pm.py`](src/eam/pm.py) |
| Service boundaries, API design | [06 Services and API](docs/06-service-boundaries-and-api.md) | [`openapi.yaml`](docs/api/openapi.yaml) |
| Database design (hierarchy, constraints, history) | [07 Database design](docs/07-database-design.md) | [`sql/01_schema.sql`](sql/01_schema.sql) |
| Event architecture | [08 Events](docs/08-event-architecture.md) | — |
| Reporting, star schema, KPIs | [09 Reporting](docs/09-reporting-architecture.md) | [`sql/04_*`–`06_*`](sql/), [`kpis.py`](src/eam/kpis.py) |
| Real-time telemetry integration | [10 Telemetry](docs/10-telemetry-integration.md) | [`condition.py`](src/eam/condition.py) |
| Field service, offline mobile sync | [11 Field service](docs/11-field-service.md) | — |
| Asset hierarchy roll-ups | [07 Database design](docs/07-database-design.md) | [`hierarchy.py`](src/eam/hierarchy.py) |

## Key Capabilities Demonstrated

- **Work order state machine** with EAM business guards (assignment before start, failure codes on corrective
  work, labor before completion, emergency shortcut, reopen, immutable closed WOs) and cost actuals.
- **PM scheduling**: fixed vs. floating calendars, meter-based intervals, "whichever first", lead time,
  idempotent generation keys, forecasting.
- **Asset hierarchy**: materialised paths, subtree queries, cost/downtime roll-ups, inherited criticality.
- **Condition monitoring**: rules with sustain windows and hysteresis that raise one work request per episode.
- **Maintenance KPIs**: MTBF, MTTR, availability, PM compliance, planned maintenance %, backlog in crew-weeks.
- **Operational PostgreSQL schema** with `ltree`, constraints encoding business rules, status history, downtime and
  contract models — executed in tests.
- **Reporting star schema** with an SCD2 asset dimension, ETL and analytical queries — executed in tests.
- **OpenAPI 3.1 contract** with lifecycle commands, ETags and idempotency keys — validated in tests.

## Architecture

### Components and responsibilities

| Service | Bounded contexts | Data |
|---|---|---|
| `asset-service` | Asset Registry, Contracts & Vendors | Assets, locations, hierarchy, meters, contracts |
| `work-service` | Work Management, Maintenance Planning | Work orders, history, actuals, PM schedules, job plans |
| `inventory-service` | Inventory & Procurement | Items, storerooms, balances, reservations |
| `workforce-service` | Workforce | Labor, crafts, calendars, qualifications |
| `field-service` | Field Service | Dispatch, mobile sync, SLAs |
| `monitoring-platform` | Monitoring & Telemetry | Time-series, condition rules |
| `reporting` | Reporting & Analytics | Star schema warehouse |

### Communication and data flow

- Synchronous REST for user-facing commands and queries ([OpenAPI](docs/api/openapi.yaml)).
- Domain events via a transactional outbox for integration between contexts
  ([event architecture](docs/08-event-architecture.md)).
- Telemetry → condition rules → **anti-corruption layer** → work requests.
- Operational data → CDC → warehouse star schema → dashboards.

### Scalability

- Work and asset services scale horizontally; the hot path is work order reads/updates by planners and technicians.
- Meter readings and telemetry are the highest-volume data: partitioned by time, raw telemetry kept in the
  monitoring platform and only summarised readings in EAM.
- Partial indexes on open work orders keep backlog queries fast as closed history grows.
- Hierarchy roll-ups use indexed `ltree` subtree queries instead of recursive CTEs.
- Analytics runs on the warehouse, not on operational databases.

### Failure handling

- Idempotent PM generation (unique per occurrence) and idempotent API creates (`Idempotency-Key`).
- Optimistic concurrency (`ETag`/`If-Match`) for work orders edited by planners and technicians concurrently.
- Condition rules suppress duplicates during alarm storms; stale sensor data is an alarm of its own.
- Offline mobile commands are applied idempotently with field-level conflict policies.

## Technology Stack

| Area | Choice |
|---|---|
| Domain model | Python 3.10+ (standard library only), typed (`mypy --strict`) |
| Database | PostgreSQL 14+ with `ltree` |
| API contract | OpenAPI 3.1 |
| Diagrams | Mermaid |
| Tests / lint | pytest, ruff, mypy, psycopg (SQL tests), openapi-spec-validator |
| CI | GitHub Actions with a PostgreSQL service container |

The architecture is technology-neutral: the services in the target architecture are typically implemented in
.NET/C#, Java or Node.js with PostgreSQL or SQL Server.

## Repository Structure

```text
eam-platform-architecture/
├── docs/
│   ├── 01-eam-domain-overview.md … 11-field-service.md
│   ├── api/openapi.yaml          # reference API contract
│   └── decisions/                # ADR-001 … ADR-006
├── src/eam/                      # domain model: work_orders, pm, hierarchy, condition, kpis
├── sql/
│   ├── 01_schema.sql             # operational schema (ltree hierarchy, constraints)
│   ├── 02_seed.sql               # illustrative plant data and work history
│   ├── 03_operational_views.sql  # cost roll-up, reliability, PM compliance, backlog, reorder
│   ├── 04_reporting_star_schema.sql
│   ├── 05_load_dw.sql            # OLTP → star schema load
│   └── 06_analytics_queries.sql  # named analytical queries
├── tests/                        # domain, SQL (PostgreSQL) and OpenAPI tests
└── scripts/                      # documentation checks
```

## Getting Started

```bash
git clone https://github.com/shivkumarsinghsky/eam-platform-architecture.git
cd eam-platform-architecture
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

### Explore the domain model

```python
from datetime import date
from eam.pm import PMState, PreventiveMaintenance, ScheduleType, evaluate, forecast

pm = PreventiveMaintenance(id="PM-P101", asset_id="P101", job_plan="JP-PUMP-90D",
                           start_date=date(2026, 1, 5), frequency_days=90,
                           schedule_type=ScheduleType.FLOATING, meter_interval=2000.0)
state = PMState(last_completed=date(2026, 4, 8), last_due=date(2026, 4, 5), last_completed_meter=10_400.0)

evaluate(pm, state, today=date(2026, 6, 30))
# GenerationDecision(generate=True, due_date=datetime.date(2026, 7, 7), reason='due 2026-07-07 within lead time', ...)
forecast(pm, state, 3)
# [datetime.date(2026, 7, 7), datetime.date(2026, 10, 5), datetime.date(2027, 1, 3)]
```

### Run the SQL model

```bash
docker run -d --name eam-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine
for f in sql/0[1-6]_*.sql; do psql postgresql://postgres:postgres@localhost:5432/postgres -f "$f"; done
psql postgresql://postgres:postgres@localhost:5432/postgres \
  -c "SELECT * FROM asset_reliability('2026-01-01', '2026-10-01');"
```

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `EAM_DATABASE_URL` | `tests/test_sql.py` | Disposable PostgreSQL database for SQL tests (its `public`/`dw` schemas are recreated) |

There are no runtime services or secrets in this repository.

## API Examples

From [`docs/api/openapi.yaml`](docs/api/openapi.yaml):

```http
GET  /api/v1/assets?under=SITE01.BOILER.FW&criticality=A
POST /api/v1/work-orders                      (Idempotency-Key)
POST /api/v1/work-orders/{id}/transitions     { "to": "COMPLETED" }   (If-Match)
PUT  /api/v1/work-orders/{id}/failure-report  { "problemCode": "LEAK", "causeCode": "SEAL-WEAR", "remedyCode": "REPLACE" }
POST /api/v1/work-orders/{id}/labor           { "laborId": "T07", "hours": 2.5, "workDate": "2026-10-01" }
GET  /api/v1/pm-schedules/{pmId}/forecast?count=12
POST /api/v1/meters/{meterId}/readings        [ { "at": "...", "value": 10450.5 } ]
```

## Testing

```bash
pytest                       # domain model + OpenAPI tests (SQL tests skip without a database)
EAM_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest   # include SQL tests
ruff check . && ruff format --check . && mypy
python scripts/check_links.py . && bash scripts/check_mermaid.sh .
```

| Suite | What it verifies |
|---|---|
| `test_work_orders.py` | Lifecycle transitions, guards, emergency shortcut, reopen, cost actuals |
| `test_pm.py` | Fixed vs. floating, lead time, meter "whichever first", idempotency keys, forecasting |
| `test_hierarchy_condition_kpis.py` | Subtrees, roll-ups, criticality inheritance, sustain/hysteresis, KPI formulas |
| `test_sql.py` | Schema + seed + views + star schema + ETL on PostgreSQL; KPI results; constraint-enforced rules |
| `test_openapi.py` | OpenAPI document validity; API statuses match the domain model |

## Docker

`docker-compose.yml` starts PostgreSQL with the reference model loaded on first start (schema, sample plant data, KPI
views, star schema and warehouse load) and provides a test-runner container:

```bash
docker compose up -d postgres
docker compose run --rm tests        # 36 tests, including the SQL tests against this database
psql postgresql://eam:eam-local-dev@localhost:5432/eam \
  -c "SELECT * FROM asset_reliability('2026-01-01', '2026-10-01');"
```

The SQL tests recreate the `public` and `dw` schemas; run `docker compose down -v && docker compose up -d postgres`
to reload the sample data afterwards. Set `POSTGRES_PORT` if 5432 is already in use.

## Architecture Decisions

| ADR | Decision |
|---|---|
| [ADR-001](docs/decisions/ADR-001-bounded-contexts-as-service-boundaries.md) | Bounded contexts as service boundaries |
| [ADR-002](docs/decisions/ADR-002-asset-hierarchy-materialised-path.md) | Asset hierarchy as materialised path (`ltree`) |
| [ADR-003](docs/decisions/ADR-003-pm-scheduling-model.md) | PM scheduling model |
| [ADR-004](docs/decisions/ADR-004-star-schema-reporting.md) | Star schema with SCD2 for analytics |
| [ADR-005](docs/decisions/ADR-005-condition-rules-and-acl.md) | Condition rules behind an anti-corruption layer |
| [ADR-006](docs/decisions/ADR-006-offline-first-field-sync.md) | Offline-first field service sync |

## Reliability

Idempotent PM generation and API creates; optimistic concurrency on work orders; immutable closed work orders;
status history for audit and SLA computation; deduplicated condition alarms; stale-data detection; offline command
replay with conflict policies.

## Security

- Authorization per site/organisation and role (planner, supervisor, technician, storekeeper); technicians only sync
  their assigned work.
- Multi-tenant deployments add tenant isolation at the database (row-level security) — implemented in
  [enterprise-saas-plateform](https://github.com/shivkumarsinghsky/enterprise-saas-plateform).
- Input validation via the OpenAPI schemas; database constraints as a last line of defence.
- Audit trail through work order status history and immutable closed records.

## Observability

Business observability matters as much as technical: backlog size and age, PM compliance, overdue emergency work,
stuck `WAITING_MATERIAL` orders, condition alarm rates per site, and sync lag per mobile device — alongside the
usual service metrics, structured logs and correlation ids (alarm episode id → work request → work order).

## Future Improvements

Not implemented yet:

- Runnable services for the work and asset contexts (the API contract and domain model are ready for them).
- Nested and seasonal PMs, route-based inspections, and capacity-aware scheduling.
- Reliability analytics beyond KPIs (Weibull analysis per failure mode).
- Inventory replenishment with lead times and criticality-based safety stock.
- Mobile sync reference implementation.

## Related Projects

- [Real-Time Monitoring Platform](https://github.com/shivkumarsinghsky/realtime-monitoring-platform) — telemetry ingestion and alerting that feeds condition-based maintenance
- [Enterprise SaaS Platform](https://github.com/shivkumarsinghsky/enterprise-saas-plateform) — multi-tenant platform with an asset module and RLS isolation
- [Event-Driven Platform](https://github.com/shivkumarsinghsky/event-driven-platform) — outbox, idempotent consumers and DLQs used for EAM integration
- [Microservices Patterns](https://github.com/shivkumarsinghsky/microservices-patterns) — event-sourced work order example and CQRS worklist
- [Enterprise AI Agent Platform](https://github.com/shivkumarsinghsky/enterprise-ai-agent-plateform) — AI agents over maintenance data
- [System Design Architecture](https://github.com/shivkumarsinghsky/system-design-architecture) — real-time monitoring and multi-tenant SaaS designs

## Author

**Shiv Kumar** — Senior Software Engineer / Software Architect with 12+ years of experience building enterprise
platforms, including EAM/FSM and real-time monitoring systems.
GitHub: [github.com/shivkumarsinghsky](https://github.com/shivkumarsinghsky)

## License

[MIT](LICENSE)
