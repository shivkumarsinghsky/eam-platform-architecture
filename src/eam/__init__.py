"""Enterprise Asset Management (EAM) reference domain model.

Modules map to bounded contexts described in docs/02-bounded-contexts.md:

- ``work_orders``  – Work Management: work order lifecycle, actuals, failure reporting
- ``pm``           – Maintenance Planning: time- and meter-based preventive maintenance scheduling
- ``hierarchy``    – Asset Registry: location/asset hierarchy and roll-ups
- ``condition``    – Monitoring: condition rules that turn telemetry into work requests
- ``kpis``         – Reporting: maintenance KPIs (MTBF, MTTR, availability, PM compliance, ...)
"""

__version__ = "1.0.0"
